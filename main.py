import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from queue import Queue, Empty
from threading import Thread

from ocr import extrair_texto, CONFIANCA_MINIMA

import cv2
import numpy as np
from PIL import Image, ImageTk

# Lado maior (em pixels) usado na detecção da folha. Reduzir a imagem deixa a
# detecção rápida e ignora detalhes pequenos (textura da mesa, letras). O
# recorte final é feito na imagem original, sem perder qualidade.
LADO_DETECCAO = 500

# O documento precisa ocupar pelo menos 15% da foto. Isso evita escolher um
# retângulo pequeno, como a foto 3x4 dentro de uma identidade.
AREA_MINIMA_RELATIVA = 0.15

# Pelo menos metade do contorno precisa estar sobre bordas reais da imagem.
APOIO_MINIMO = 0.5

# Paleta da interface
COR_FUNDO = "#f4f5f7"
COR_PAINEL = "#ffffff"
COR_DESTAQUE = "#215041"
COR_DESTAQUE_ATIVO = "#2c6b56"
COR_TEXTO = "#1f2933"
COR_SECUNDARIA = "#6b7280"
COR_BORDA = "#d9dde3"


def order_points(pts):
    # Inicializa uma lista de coordenadas que serão ordenadas
    # na ordem: topo-esquerdo, topo-direito, baixo-direito, baixo-esquerdo
    rect = np.zeros((4, 2), dtype="float32")

    # O topo-esquerdo terá a menor soma, o baixo-direito terá a maior soma
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # O topo-direito terá a menor diferença, o baixo-esquerdo terá a maior diferença
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def four_point_transform(image, points):
    # rect recebe os quatro cantos ordenados
    rect = order_points(points)

    # Desempacotamento dos quatro cantos do retângulo
    top_left, top_right, bottom_right, bottom_left = rect

    # Cálculo das dimensões aproximadas do documento.
    width_a = np.linalg.norm(bottom_right - bottom_left)
    width_b = np.linalg.norm(top_right - top_left)

    height_a = np.linalg.norm(top_right - bottom_right)
    height_b = np.linalg.norm(top_left - bottom_left)

    max_width = int(max(width_a, width_b))
    max_height = int(max(height_a, height_b))

    if max_width < 2 or max_height < 2:
        return None

    # Definir os quatro cantos da imagem de destino.
    destination = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ],
        dtype="float32"
    )

    # Calcular a matriz de transformação projetiva.
    matrix = cv2.getPerspectiveTransform(rect, destination)

    # Aplicar a transformação à imagem original colorida.
    warped = cv2.warpPerspective(
        image,
        matrix,
        (max_width, max_height)
    )

    return warped


def _apagar_texto(canal):
    """Fechamento morfológico: o "branco" cobre as letras e a folha fica lisa.

    Assim sobram apenas as bordas grandes (folha x fundo), e não as milhares
    de bordas das letras.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    return cv2.morphologyEx(canal, cv2.MORPH_CLOSE, kernel)


def _canny_automatico(canal):
    """Canny com limiares calculados a partir do brilho típico da imagem."""
    mediana = float(np.median(canal))
    return cv2.Canny(cv2.GaussianBlur(canal, (5, 5), 0),
                     0.15 * mediana, 0.3 * mediana + 30)


def _mascaras(image):
    """Gera várias imagens binárias; cada uma funciona melhor num tipo de foto.

    - cinza: brilho comum (bom para fundo escuro);
    - brancura: brilho menos saturação. Papel é claro e SEM cor, enquanto
      madeira, mesa e tecido têm cor. Bom para fundo claro e colorido.
    Para cada canal: Otsu (separa regiões) e Canny (encontra as bordas).
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    canais = {
        "cinza": _apagar_texto(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)),
        "brancura": _apagar_texto(cv2.subtract(hsv[:, :, 2], hsv[:, :, 1])),
    }
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mascaras = []
    for canal in canais.values():
        _, otsu = cv2.threshold(cv2.GaussianBlur(canal, (5, 5), 0), 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mascaras.append(("otsu", cv2.morphologyEx(otsu, cv2.MORPH_OPEN, kernel), 0))
        bordas = _canny_automatico(canal)
        mascaras.append(("canny", cv2.dilate(bordas, np.ones((3, 3), np.uint8)), 0))
        # Versão "grossa": fecha falhas da borda causadas por sombras.
        # Depois o quadrilátero é afastado 5 px para compensar.
        mascaras.append(("canny", cv2.dilate(bordas, np.ones((11, 11), np.uint8)), 5))
    return mascaras, canais


def _quadrilatero(contorno):
    """Transforma um contorno em 4 cantos, ou None se não parecer uma folha.

    O casco convexo (convexHull) "passa por cima" de dedos, clipes e sombras
    que entram na borda. Depois aumentamos a tolerância do approxPolyDP até
    o polígono ter exatamente 4 vértices.
    """
    casco = cv2.convexHull(contorno)
    perimetro = cv2.arcLength(casco, True)
    for tolerancia in np.linspace(0.01, 0.08, 15):
        aprox = cv2.approxPolyDP(casco, tolerancia * perimetro, True)
        if len(aprox) == 4:
            return aprox.reshape(4, 2).astype(np.float32)
        if len(aprox) < 4:
            break
    return None


def _afastar(cantos, pixels):
    """Afasta cada canto do centro (compensa a borda engrossada pela dilatação)."""
    direcao = cantos - cantos.mean(axis=0)
    direcao /= np.linalg.norm(direcao, axis=1, keepdims=True)
    return (cantos + direcao * pixels * 1.41).astype(np.float32)


def _reta(p, q):
    """Reta no formato a·x + b·y = c que passa pelos pontos p e q."""
    a, b = q[1] - p[1], p[0] - q[0]
    return a, b, a * p[0] + b * p[1]


def _intersecao(r1, r2):
    a1, b1, c1 = r1
    a2, b2, c2 = r2
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-6:
        return None  # retas paralelas
    return np.array([(c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det], np.float32)


def _encaixar_nas_retas(cantos, segmentos, altura, largura):
    """Ajusta cada lado do quadrilátero à reta real da borda da folha.

    Quando uma sombra "come" um canto, o quadrilátero sai torto. Aqui, para
    cada lado, procuramos o maior segmento de reta (Hough) quase paralelo e
    próximo dele. Os novos cantos são as interseções dessas retas.
    """
    if segmentos is None:
        return cantos
    # Ordena os cantos em volta do centro para percorrer os lados em sequência.
    rel = cantos - cantos.mean(axis=0)
    cantos = cantos[np.argsort(np.arctan2(rel[:, 1], rel[:, 0]))]
    menor_lado = min(altura, largura)

    retas = []
    for i in range(4):
        p1, p2 = cantos[i], cantos[(i + 1) % 4]
        lado = p2 - p1
        comprimento = np.linalg.norm(lado)
        angulo = np.arctan2(lado[1], lado[0])
        normal = np.array([-lado[1], lado[0]]) / comprimento
        melhor, melhor_comp = None, 0.3 * comprimento
        for x1, y1, x2, y2 in segmentos.reshape(-1, 4):
            seg = np.array([x2 - x1, y2 - y1], np.float32)
            diferenca = abs((np.arctan2(seg[1], seg[0]) - angulo + np.pi / 2) % np.pi
                            - np.pi / 2)
            meio = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
            posicao = np.dot(meio - p1, lado) / comprimento ** 2
            if (diferenca <= np.radians(12)                      # quase paralelo
                    and abs(np.dot(meio - p1, normal)) <= 0.12 * menor_lado  # perto
                    and -0.1 < posicao < 1.1                     # ao lado do lado
                    and np.linalg.norm(seg) > melhor_comp):
                melhor, melhor_comp = (x1, y1, x2, y2), np.linalg.norm(seg)
        if melhor is None:
            retas.append(_reta(p1, p2))
        else:
            retas.append(_reta(np.array(melhor[:2], float), np.array(melhor[2:], float)))

    novos = [_intersecao(retas[i - 1], retas[i]) for i in range(4)]
    if any(p is None for p in novos):
        return cantos
    novos = np.array(novos, np.float32)
    folga = 0.03 * max(altura, largura)
    dentro = ((novos[:, 0] >= -folga) & (novos[:, 0] <= largura + folga)
              & (novos[:, 1] >= -folga) & (novos[:, 1] <= altura + folga)).all()
    if not dentro or not cv2.isContourConvex(novos.reshape(-1, 1, 2).astype(np.int32)):
        return cantos
    novos[:, 0] = novos[:, 0].clip(0, largura - 1)
    novos[:, 1] = novos[:, 1].clip(0, altura - 1)
    return novos


def _apoio_nas_bordas(cantos, bordas):
    """Fração do contorno do quadrilátero que passa sobre bordas reais (0 a 1).

    Um quadrilátero certo tem os 4 lados em cima da borda da folha. Um
    errado corta o meio do papel ou do fundo, onde não há borda.
    Trechos colados na margem da foto não contam (não dá para saber).
    """
    linha = np.zeros(bordas.shape, np.uint8)
    cv2.polylines(linha, [cantos.astype(np.int32)], True, 255, 1)
    m = 4
    linha[:m, :] = 0
    linha[-m:, :] = 0
    linha[:, :m] = 0
    linha[:, -m:] = 0
    total = cv2.countNonZero(linha)
    if total < 0.25 * cv2.arcLength(cantos.reshape(-1, 1, 2), True):
        return 0.0  # quase todo na margem: provavelmente é a própria foto
    return cv2.countNonZero(cv2.bitwise_and(linha, bordas)) / total


def _melhor_candidato(mascaras, bordas_finas, bordas_nota, h, w, apoio_minimo=None):
    """Testa os contornos de cada máscara e devolve o quadrilátero de maior nota."""
    area_foto = h * w
    segmentos = cv2.HoughLinesP(bordas_finas, 1, np.pi / 180, 40,
                                minLineLength=0.15 * min(h, w), maxLineGap=15)
    referencia = cv2.dilate(bordas_nota, np.ones((7, 7), np.uint8))

    apoio_minimo = APOIO_MINIMO if apoio_minimo is None else apoio_minimo
    melhor_nota, melhores_cantos = 0.0, None
    for tipo, mascara, afastar in mascaras:
        # Nas bordas do Canny, o contorno de DENTRO do retângulo é a folha,
        # mesmo que a linha esteja grudada em outras (tábua, outra folha).
        modo = cv2.RETR_LIST if tipo == "canny" else cv2.RETR_EXTERNAL
        contornos, _ = cv2.findContours(mascara, modo, cv2.CHAIN_APPROX_SIMPLE)
        contornos = sorted(contornos, key=lambda c: cv2.contourArea(cv2.convexHull(c)),
                           reverse=True)
        for contorno in contornos[:6]:
            if cv2.contourArea(cv2.convexHull(contorno)) < AREA_MINIMA_RELATIVA * area_foto:
                break
            cantos = _quadrilatero(contorno)
            if cantos is None:
                continue
            if afastar:
                cantos = _afastar(cantos, afastar)
            cantos = _encaixar_nas_retas(cantos, segmentos, h, w)
            fracao_area = cv2.contourArea(cantos) / area_foto
            if not AREA_MINIMA_RELATIVA <= fracao_area <= 0.98:
                continue
            apoio = _apoio_nas_bordas(cantos, referencia)
            nota = apoio * fracao_area ** 0.5
            if apoio >= apoio_minimo and nota > melhor_nota:
                melhor_nota, melhores_cantos = nota, cantos
    return melhores_cantos


def scan_detection(image):
    """Encontra os quatro cantos do documento na imagem.

    1. Reduz a foto e apaga o texto (só sobram as bordas grandes).
    2. Gera candidatos com Otsu e Canny em dois canais (cinza e brancura).
    3. Ajusta os lados de cada candidato às retas reais (Hough).
    4. Dá uma nota: quanto do contorno está sobre bordas reais e o tamanho.
    5. Se nada servir, tenta de novo com CLAHE (bordas fracas, fundo branco).
    Retorna (cantos, encontrou). Se nada for confiável, devolve os cantos da
    imagem inteira e encontrou = False.
    """
    altura, largura = image.shape[:2]
    cantos_imagem = np.array(
        [[0, 0], [largura - 1, 0], [largura - 1, altura - 1], [0, altura - 1]],
        dtype="float32",
    )

    escala = min(1.0, LADO_DETECCAO / max(altura, largura))
    pequena = cv2.resize(image, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    h, w = pequena.shape[:2]

    # 1ª passada: canais normais
    mascaras, canais = _mascaras(pequena)
    bordas_cinza = _canny_automatico(canais["cinza"])
    cantos = _melhor_candidato(
        mascaras, bordas_cinza, bordas_cinza | _canny_automatico(canais["brancura"]), h, w)

    # 2ª passada (último recurso): folha branca sobre fundo branco.
    # O CLAHE realça diferenças pequenas de brilho em cada região da foto e faz
    # a borda fraca da folha aparecer. Não é usado sempre porque também realça
    # texturas (madeira, piso), que confundiriam as fotos que já funcionam.
    if cantos is None:
        contraste = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(canais["cinza"])
        bordas = _canny_automatico(contraste)
        mascaras_contraste = [
            ("canny", cv2.dilate(bordas, np.ones((3, 3), np.uint8)), 0),
            ("canny", cv2.dilate(bordas, np.ones((11, 11), np.uint8)), 5),
        ]
        # Exige mais apoio nas bordas: é melhor não achar do que achar errado.
        cantos = _melhor_candidato(mascaras_contraste, bordas, bordas, h, w, apoio_minimo=0.75)

    if cantos is None:
        return cantos_imagem, False
    return cantos / escala, True


def desenhar_contorno(image, cantos):
    """Desenha o contorno detectado sobre a original (mostra onde a folha foi achada)."""
    saida = image.copy()
    espessura = max(2, max(image.shape[:2]) // 300)
    pontos = order_points(cantos).astype(np.int32)
    cv2.polylines(saida, [pontos], True, (86, 160, 33), espessura, cv2.LINE_AA)
    return saida


def efeito_scanner(imagem, lado=2200):
    """Deixa o documento com cara de escaneado: papel branco e texto preto nítido.

    1. Amplia até ~2200 px no maior lado, para as letras ficarem lisas.
    2. Estima o "fundo" do papel (sem o texto) e divide a imagem por ele.
       Isso remove sombras e diferenças de iluminação.
    3. Aplica nitidez (unsharp mask: imagem + diferença para a versão borrada).
    4. Curva de tons: tudo que é quase branco vira branco puro e o texto escurece,
       mas as bordas das letras continuam suaves (fica mais bonito que um
       threshold puro, que deixa as letras serrilhadas).
    O OCR continua lendo a imagem colorida original: nos testes, o preto e
    branco forte deixou letras pequenas "gordas" e piorou um pouco a leitura.
    """
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY) if imagem.ndim == 3 else imagem.copy()
    escala = lado / max(cinza.shape)
    if escala > 1:
        cinza = cv2.resize(cinza, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)

    tamanho = max(15, (max(cinza.shape) // 60) | 1)  # maior que a grossura das letras
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (tamanho, tamanho))
    fundo = cv2.medianBlur(cv2.morphologyEx(cinza, cv2.MORPH_CLOSE, kernel), 21)
    plano = cv2.divide(cinza, fundo, scale=255)

    borrada = cv2.GaussianBlur(plano, (0, 0), 1.2)
    nitida = cv2.addWeighted(plano, 1.8, borrada, -0.8, 0)

    claro, escuro = 215.0, 95.0  # acima de "claro" vira branco; abaixo de "escuro", preto
    tons = np.clip((nitida.astype(np.float32) - escuro) / (claro - escuro), 0, 1)
    return (tons ** 1.3 * 255).astype(np.uint8)


class ImagePreprocessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Scanner de Documentos")
        self.root.geometry("1280x800")
        self.root.minsize(900, 600)
        self.root.configure(bg=COR_FUNDO)

        self.imagem = None
        self.nome_arquivo = ""
        self.cantos = None
        self.warped = None
        self.scan_pb = None
        self.texto_ocr = ""
        self.modo_saida = tk.StringVar(value="pb")  # "pb" (escaneado) ou "cor"
        self.cabecalhos = {}
        self.imagens = {}   # arrays originais de cada visor (para redimensionar)
        self.fotos = {}     # PhotoImage precisa ficar guardado, senão some
        self.visores = {}
        self.processando_ocr = False
        self.fila_ocr = Queue()
        self.inicio_ocr = 0.0
        self._redimensionar_id = None

        self._configurar_estilo()
        self._montar_cabecalho()
        self._montar_rodape()
        self._montar_conteudo()
        self._atualizar_botoes()

    # ------------------------------------------------------------------ layout
    def _configurar_estilo(self):
        familia = tkfont.nametofont("TkDefaultFont").actual("family")
        tkfont.nametofont("TkDefaultFont").configure(size=10)
        self.fonte_titulo = (familia, 14, "bold")
        self.fonte_rotulo = (familia, 9, "bold")

        estilo = ttk.Style(self.root)
        estilo.theme_use("clam")
        estilo.configure(".", background=COR_FUNDO, foreground=COR_TEXTO,
                         focuscolor=COR_PAINEL)
        # Botão principal: cor sólida, sem borda
        estilo.configure("Primario.TButton", background=COR_DESTAQUE, foreground="white",
                         bordercolor=COR_DESTAQUE, lightcolor=COR_DESTAQUE,
                         darkcolor=COR_DESTAQUE, padding=(18, 8), focusthickness=0)
        estilo.map("Primario.TButton",
                   background=[("disabled", "#b9c7c2"), ("active", COR_DESTAQUE_ATIVO)],
                   bordercolor=[("disabled", "#b9c7c2"), ("active", COR_DESTAQUE_ATIVO)],
                   lightcolor=[("disabled", "#b9c7c2"), ("active", COR_DESTAQUE_ATIVO)],
                   darkcolor=[("disabled", "#b9c7c2"), ("active", COR_DESTAQUE_ATIVO)],
                   foreground=[("disabled", "#f4f6f5")])
        # Botões secundários: fundo branco e borda fina
        for nome in ("Secundario.TButton", "Secundario.TMenubutton"):
            estilo.configure(nome, background=COR_PAINEL, foreground=COR_TEXTO,
                             bordercolor=COR_BORDA, lightcolor=COR_PAINEL,
                             darkcolor=COR_PAINEL, padding=(14, 8), focusthickness=0,
                             arrowcolor=COR_SECUNDARIA)
            estilo.map(nome, background=[("active", "#f1f3f5")],
                       foreground=[("disabled", "#a8adb5")],
                       arrowcolor=[("disabled", "#c9cdd3")])
        # Botões discretos (copiar, fechar)
        estilo.configure("Discreto.TButton", background=COR_PAINEL, foreground=COR_SECUNDARIA,
                         bordercolor=COR_PAINEL, lightcolor=COR_PAINEL, darkcolor=COR_PAINEL,
                         padding=(8, 4), focusthickness=0)
        estilo.map("Discreto.TButton", background=[("active", "#f1f3f5")],
                   foreground=[("active", COR_TEXTO)])
        # Alternador P&B / Cor
        estilo.configure("Alternar.Toolbutton", background=COR_PAINEL,
                         foreground=COR_SECUNDARIA, padding=(10, 3), focusthickness=0,
                         bordercolor=COR_BORDA, lightcolor=COR_PAINEL, darkcolor=COR_PAINEL)
        estilo.map("Alternar.Toolbutton",
                   background=[("selected", "#e6efeb"), ("active", "#f1f3f5")],
                   foreground=[("selected", COR_DESTAQUE), ("disabled", "#c9cdd3")])
        estilo.configure("Vertical.TScrollbar", background="#e5e7eb", troughcolor=COR_PAINEL,
                         bordercolor=COR_PAINEL, lightcolor="#e5e7eb", darkcolor="#e5e7eb",
                         arrowsize=0, gripcount=0)
        estilo.map("Vertical.TScrollbar", background=[("active", "#cfd3d9")])
        estilo.configure("Horizontal.TProgressbar", background=COR_DESTAQUE,
                         troughcolor="#e5e7eb", bordercolor="#e5e7eb",
                         lightcolor=COR_DESTAQUE, darkcolor=COR_DESTAQUE)

    def _montar_cabecalho(self):
        cabecalho = tk.Frame(self.root, bg=COR_PAINEL, padx=24, pady=14)
        cabecalho.pack(side="top", fill="x")
        tk.Frame(self.root, bg=COR_BORDA, height=1).pack(side="top", fill="x")

        tk.Label(cabecalho, text="Scanner de Documentos", font=self.fonte_titulo,
                 bg=COR_PAINEL, fg=COR_TEXTO).pack(side="left")
        self.info = tk.StringVar(value="")
        tk.Label(cabecalho, textvariable=self.info, bg=COR_PAINEL,
                 fg=COR_SECUNDARIA).pack(side="left", padx=(14, 0), pady=(3, 0))

        # Da direita para a esquerda: Salvar ▾, Extrair texto, Abrir imagem
        self.btn_salvar = ttk.Menubutton(cabecalho, text="Salvar", width=7,
                                         style="Secundario.TMenubutton")
        self.menu_salvar = tk.Menu(self.btn_salvar, tearoff=False)
        self.menu_salvar.add_command(label="Imagem digitalizada (.png)", command=self.salvar)
        self.menu_salvar.add_command(label="Texto extraído (.txt)", command=self.salvar_texto)
        self.btn_salvar["menu"] = self.menu_salvar
        self.btn_salvar.pack(side="right")

        self.btn_ocr = ttk.Button(cabecalho, text="Extrair texto",
                                  command=self.executar_ocr, style="Primario.TButton")
        self.btn_ocr.pack(side="right", padx=8)

        self.btn_carregar = ttk.Button(cabecalho, text="Abrir imagem",
                                       command=self.carregar, style="Secundario.TButton")
        self.btn_carregar.pack(side="right")

    def _montar_rodape(self):
        rodape = tk.Frame(self.root, bg=COR_PAINEL, padx=24, pady=6)
        rodape.pack(side="bottom", fill="x")
        tk.Frame(self.root, bg=COR_BORDA, height=1).pack(side="bottom", fill="x")
        self.status = tk.StringVar(value="Abra uma imagem para começar.")
        tk.Label(rodape, textvariable=self.status, bg=COR_PAINEL,
                 fg=COR_SECUNDARIA).pack(side="left")
        # A barra de progresso só aparece enquanto o OCR está rodando.
        self.progresso = ttk.Progressbar(rodape, mode="indeterminate", length=160)

    def _montar_conteudo(self):
        self.conteudo = tk.Frame(self.root, bg=COR_FUNDO, padx=24, pady=20)
        self.conteudo.pack(fill="both", expand=True)

        self.area_imagens = tk.Frame(self.conteudo, bg=COR_FUNDO)
        self.area_imagens.pack(side="left", fill="both", expand=True)
        for coluna, (chave, titulo, vazio) in enumerate((
            ("original", "ORIGINAL", "Abra uma imagem para começar"),
            ("warped", "DIGITALIZADO", "O documento digitalizado aparece aqui"),
        )):
            self.visores[chave] = self._criar_cartao(self.area_imagens, titulo, vazio, chave)
            self.visores[chave].master.grid(row=0, column=coluna, sticky="nsew",
                                            padx=(0, 10) if coluna == 0 else (10, 0))
            self.area_imagens.grid_columnconfigure(coluna, weight=1, uniform="cartao")
        self.area_imagens.grid_rowconfigure(0, weight=1)
        self.area_imagens.bind("<Configure>", self._agendar_redimensionamento)

        # Extras discretos nos cabeçalhos dos cartões
        self.btn_ajustar = ttk.Button(self.cabecalhos["original"], text="Ajustar cantos",
                                      command=self.ajustar_cantos, style="Discreto.TButton")
        self.btn_ajustar.pack(side="right")
        self.alternadores = []
        for texto, valor in (("Cor", "cor"), ("P&B", "pb")):
            botao = ttk.Radiobutton(self.cabecalhos["warped"], text=texto, value=valor,
                                    variable=self.modo_saida, style="Alternar.Toolbutton",
                                    command=self._exibir_digitalizado)
            botao.pack(side="right")
            self.alternadores.append(botao)

        self._montar_painel_texto()

    def _criar_cartao(self, pai, titulo, vazio, chave):
        cartao = tk.Frame(pai, bg=COR_PAINEL, highlightthickness=1,
                          highlightbackground=COR_BORDA, padx=16, pady=12)
        # Sem propagate, o tamanho do cartão vem da grade, não da imagem.
        cartao.pack_propagate(False)
        cabecalho = tk.Frame(cartao, bg=COR_PAINEL, height=28)
        cabecalho.pack(fill="x", pady=(0, 8))
        cabecalho.pack_propagate(False)
        tk.Label(cabecalho, text=titulo, font=self.fonte_rotulo, bg=COR_PAINEL,
                 fg=COR_SECUNDARIA).pack(side="left")
        self.cabecalhos[chave] = cabecalho
        visor = tk.Label(cartao, text=vazio, bg=COR_PAINEL, fg="#9ca3af", cursor="hand2")
        visor.pack(fill="both", expand=True)
        visor.bind("<Button-1>", lambda _e: self.ampliar(chave, titulo.capitalize()))
        return visor

    def _montar_painel_texto(self):
        """Painel lateral com o texto do OCR. Só aparece depois da extração."""
        self.painel_texto = tk.Frame(self.conteudo, bg=COR_PAINEL, highlightthickness=1,
                                     highlightbackground=COR_BORDA, width=360,
                                     padx=16, pady=12)
        self.painel_texto.pack_propagate(False)

        topo = tk.Frame(self.painel_texto, bg=COR_PAINEL)
        topo.pack(fill="x")
        tk.Label(topo, text="TEXTO EXTRAÍDO", font=self.fonte_rotulo, bg=COR_PAINEL,
                 fg=COR_SECUNDARIA).pack(side="left")
        ttk.Button(topo, text="✕", width=3, command=self._esconder_texto,
                   style="Discreto.TButton").pack(side="right")
        self.btn_copiar = ttk.Button(topo, text="Copiar", command=self.copiar_texto,
                                     style="Discreto.TButton")
        self.btn_copiar.pack(side="right")

        self.resumo_ocr = tk.StringVar(value="")
        tk.Label(self.painel_texto, textvariable=self.resumo_ocr, bg=COR_PAINEL,
                 fg=COR_SECUNDARIA, justify="left", anchor="w").pack(fill="x", pady=(4, 10))

        moldura = tk.Frame(self.painel_texto, bg=COR_PAINEL)
        moldura.pack(fill="both", expand=True)
        self.caixa_texto = tk.Text(moldura, wrap="word", relief="flat", bd=0,
                                   bg="#fafafa", fg=COR_TEXTO, padx=10, pady=8,
                                   highlightthickness=0, undo=True,
                                   font=(tkfont.nametofont("TkDefaultFont").actual("family"), 10))
        rolagem = ttk.Scrollbar(moldura, command=self.caixa_texto.yview)
        self.caixa_texto.configure(yscrollcommand=rolagem.set)
        rolagem.pack(side="right", fill="y")
        self.caixa_texto.pack(side="left", fill="both", expand=True)

    def _mostrar_painel_texto(self):
        if not self.painel_texto.winfo_ismapped():
            self.painel_texto.pack(side="right", fill="y", padx=(20, 0),
                                   before=self.area_imagens)

    def _esconder_texto(self):
        self.painel_texto.pack_forget()

    def _atualizar_botoes(self):
        """Habilita cada ação só quando ela faz sentido."""
        livre = not self.processando_ocr
        tem_scan = self.warped is not None
        tem_texto = bool(self.texto_ocr.strip())

        def estado(condicao):
            return "normal" if condicao and livre else "disabled"

        self.btn_carregar.config(state=estado(True))
        self.btn_ocr.config(state=estado(tem_scan),
                            text="Ver texto" if tem_texto else "Extrair texto")
        self.btn_salvar.config(state=estado(tem_scan))
        self.btn_ajustar.config(state=estado(self.imagem is not None))
        for botao in self.alternadores:
            botao.config(state=estado(tem_scan))
        self.menu_salvar.entryconfig(1, state=estado(tem_texto))

    # ----------------------------------------------------------------- ações
    def carregar(self):
        if self.processando_ocr:
            return

        # askopenfilename abre a janela nativa do sistema para escolher um arquivo
        caminho = filedialog.askopenfilename(
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                       ("Todos os arquivos", "*.*")]
        )
        if not caminho:
            return

        imagem = cv2.imread(caminho)
        if imagem is None:
            messagebox.showerror("Erro", "Não foi possível abrir essa imagem.")
            return

        self.imagem = imagem
        self.nome_arquivo = os.path.basename(caminho)
        altura, largura = imagem.shape[:2]
        self.info.set(f"{self.nome_arquivo}  ·  {largura} × {altura} px")
        # A digitalização é rápida, então acontece logo ao abrir a imagem.
        self.processar()

    def processar(self, cantos=None):
        """Recorta o documento. Sem cantos, eles são detectados automaticamente."""
        manual = cantos is not None
        if manual:
            encontrou = True
        else:
            cantos, encontrou = scan_detection(self.imagem)
        self.cantos = cantos
        # Um recorte novo invalida o texto lido antes.
        self.texto_ocr = ""
        self._definir_texto("")
        self._esconder_texto()

        self.mostrar("original", desenhar_contorno(self.imagem, cantos)
                     if encontrou else self.imagem)
        self.warped = four_point_transform(self.imagem, cantos)

        if self.warped is None:
            self.scan_pb = None
            self.visores["warped"].config(image="", text="Não foi possível digitalizar")
            self.imagens.pop("warped", None)
            self.status.set("Não foi possível aplicar a transformação de perspectiva.")
        else:
            self.scan_pb = efeito_scanner(self.warped)
            self._exibir_digitalizado()
            if manual:
                self.status.set("Cantos ajustados. Clique em Extrair texto.")
            elif encontrou:
                self.status.set("Documento detectado. Clique em Extrair texto.")
            else:
                self.status.set("Documento não detectado: a imagem inteira foi usada. "
                                "Use Ajustar cantos para marcar a folha.")
        self._atualizar_botoes()

    def _imagem_digitalizada(self):
        """A versão mostrada e salva: escaneada (P&B) ou colorida."""
        if self.modo_saida.get() == "pb" and self.scan_pb is not None:
            return self.scan_pb
        return self.warped

    def _exibir_digitalizado(self):
        if self.warped is not None:
            self.mostrar("warped", self._imagem_digitalizada())

    def ajustar_cantos(self):
        """Abre uma janela para arrastar os 4 cantos da folha com o mouse.

        É a solução quando a detecção automática falha, por exemplo com uma
        folha branca sobre um fundo branco, em que a borda quase não aparece.
        """
        if self.imagem is None or self.processando_ocr:
            return
        janela = tk.Toplevel(self.root, bg=COR_PAINEL)
        janela.title("Ajustar cantos")
        janela.transient(self.root)
        tk.Label(janela, text="Arraste os círculos até os cantos da folha.",
                 bg=COR_PAINEL, fg=COR_SECUNDARIA).pack(anchor="w", padx=16, pady=(12, 8))

        # Mostra a foto reduzida para caber na tela; guarda a escala para voltar.
        pil = self._para_pil(self.imagem)
        escala = min(self.root.winfo_screenwidth() * 0.8 / pil.width,
                     self.root.winfo_screenheight() * 0.72 / pil.height, 1.0)
        pil = pil.resize((max(1, int(pil.width * escala)), max(1, int(pil.height * escala))),
                         Image.LANCZOS)
        foto = ImageTk.PhotoImage(pil)
        canvas = tk.Canvas(janela, width=pil.width, height=pil.height,
                           highlightthickness=0, bg="#111111", cursor="crosshair")
        canvas.pack(padx=16)
        canvas.create_image(0, 0, image=foto, anchor="nw")
        canvas.foto = foto  # mantém a referência

        pontos = [list(p) for p in order_points(self.cantos) * escala]
        raio = 9
        poligono = canvas.create_polygon(*[c for p in pontos for c in p], outline="#56a021",
                                         fill="", width=2)
        alcas = [canvas.create_oval(0, 0, 0, 0, fill="white", outline="#56a021", width=3)
                 for _ in pontos]
        arrastando = {"indice": None}

        def redesenhar():
            canvas.coords(poligono, *[c for p in pontos for c in p])
            for alca, (x, y) in zip(alcas, pontos):
                canvas.coords(alca, x - raio, y - raio, x + raio, y + raio)

        def pressionar(evento):
            # Pega o canto mais próximo do clique (se estiver perto o bastante).
            distancias = [(evento.x - x) ** 2 + (evento.y - y) ** 2 for x, y in pontos]
            indice = int(np.argmin(distancias))
            arrastando["indice"] = indice if distancias[indice] < (raio * 4) ** 2 else None

        def mover(evento):
            indice = arrastando["indice"]
            if indice is not None:
                pontos[indice] = [min(max(evento.x, 0), pil.width - 1),
                                  min(max(evento.y, 0), pil.height - 1)]
                redesenhar()

        canvas.bind("<ButtonPress-1>", pressionar)
        canvas.bind("<B1-Motion>", mover)
        canvas.bind("<ButtonRelease-1>", lambda _e: arrastando.update(indice=None))
        redesenhar()

        def imagem_inteira():
            pontos[:] = [[0, 0], [pil.width - 1, 0], [pil.width - 1, pil.height - 1],
                         [0, pil.height - 1]]
            redesenhar()

        def aplicar():
            novos = np.array(pontos, np.float32)
            if not cv2.isContourConvex(order_points(novos).reshape(-1, 1, 2).astype(np.int32)):
                messagebox.showwarning("Cantos inválidos", "Os cantos se cruzaram. "
                                       "Arraste-os para formar um quadrilátero.", parent=janela)
                return
            janela.destroy()
            self.processar(novos / escala)

        botoes = tk.Frame(janela, bg=COR_PAINEL)
        botoes.pack(fill="x", padx=16, pady=12)
        ttk.Button(botoes, text="Aplicar", command=aplicar,
                   style="Primario.TButton").pack(side="right")
        ttk.Button(botoes, text="Cancelar", command=janela.destroy,
                   style="Secundario.TButton").pack(side="right", padx=8)
        ttk.Button(botoes, text="Imagem inteira", command=imagem_inteira,
                   style="Discreto.TButton").pack(side="left")
        janela.bind("<Escape>", lambda _e: janela.destroy())
        janela.bind("<Return>", lambda _e: aplicar())
        janela.grab_set()  # bloqueia a janela principal enquanto ajusta

    def executar_ocr(self):
        if self.processando_ocr or self.warped is None:
            return
        # Reutiliza a leitura enquanto a imagem não for trocada.
        if self.texto_ocr.strip():
            self._mostrar_painel_texto()
            return
        self.processando_ocr = True
        self._atualizar_botoes()
        self.status.set("Iniciando OCR…")
        self.progresso.pack(side="right")
        self.progresso.start(12)
        self.inicio_ocr = time.perf_counter()
        imagem = self.warped.copy()

        # O trabalho pesado não acessa widgets; envia mensagens para a interface.
        def trabalho():
            try:
                resultado = extrair_texto(
                    imagem, progresso=lambda etapa, _img: self.fila_ocr.put(("etapa", etapa)),
                    retornar_detalhes=True,
                )
                self.fila_ocr.put(("resultado", resultado))
            except Exception as erro:
                self.fila_ocr.put(("erro", str(erro)))

        Thread(target=trabalho, daemon=True).start()
        self.root.after(80, self._acompanhar_ocr)

    def _acompanhar_ocr(self):
        # Apenas a thread principal modifica a janela do Tkinter.
        try:
            while True:
                tipo, mensagem = self.fila_ocr.get_nowait()
                if tipo == "etapa":
                    self.status.set(mensagem)
                    continue
                self.processando_ocr = False
                self.progresso.stop()
                self.progresso.pack_forget()
                if tipo == "erro":
                    self.status.set("Falha no OCR.")
                    self._atualizar_botoes()
                    messagebox.showerror("Erro no OCR", mensagem)
                    return
                self._mostrar_resultado(mensagem)
                return
        except Empty:
            if self.processando_ocr:
                self.root.after(80, self._acompanhar_ocr)

    def _mostrar_resultado(self, resultado):
        segundos = f"{time.perf_counter() - self.inicio_ocr:.1f}".replace(".", ",")
        self.texto_ocr = resultado["texto"]
        confianca = f"{resultado['confianca_media']:.0f}"
        self.resumo_ocr.set(
            f"Confiança média: {confianca}/100\n"
            f"{resultado['caracteres_confiaveis']} de {resultado['caracteres_total']} "
            f"caracteres com confiança ≥ {CONFIANCA_MINIMA}\n"
            "(estimativa do Tesseract, não é taxa de acerto)"
        )
        if self.texto_ocr.strip():
            self._definir_texto(self.texto_ocr)
            self.status.set(f"Texto extraído em {segundos} s. Você pode corrigi-lo no painel.")
        else:
            self._definir_texto("(Nenhum texto encontrado.)")
            self.status.set("OCR concluído, mas nenhum texto foi encontrado.")
        self._mostrar_painel_texto()
        self._atualizar_botoes()

    def _definir_texto(self, texto):
        self.caixa_texto.delete("1.0", "end")
        self.caixa_texto.insert("1.0", texto)
        self.caixa_texto.edit_reset()

    def _texto_revisado(self):
        # O usuário pode corrigir o texto na caixa antes de copiar ou salvar.
        return self.caixa_texto.get("1.0", "end-1c")

    def copiar_texto(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self._texto_revisado())
        self.status.set("Texto copiado para a área de transferência.")

    def salvar_texto(self):
        if not self.texto_ocr.strip():
            messagebox.showwarning("Aviso", "Extraia o texto com OCR antes de salvar.")
            return

        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo de texto", "*.txt")],
            initialfile="texto_extraido.txt",
        )
        if not caminho:
            return

        try:
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write(self._texto_revisado())
        except OSError as erro:
            messagebox.showerror("Erro", f"Não foi possível salvar o texto:\n{erro}")
            return

        self.status.set(f"Texto salvo em {caminho}")

    def salvar(self):
        if self.warped is None:
            messagebox.showwarning("Aviso", "Abra uma imagem antes de salvar.")
            return

        # asksaveasfilename escolhe onde salvar o arquivo
        caminho = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialfile="scan_resultado.png",
        )
        if not caminho:
            return

        # fromarray cria uma imagem PIL a partir do array NumPy; save grava em PNG
        self._para_pil(self._imagem_digitalizada()).save(caminho, "PNG")
        self.status.set(f"Imagem salva em {caminho}")

    # ------------------------------------------------------------- imagens
    @staticmethod
    def _para_pil(array):
        if array.ndim == 3:
            array = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
        return Image.fromarray(array)

    def mostrar(self, chave, array):
        """Guarda a imagem e a exibe no maior tamanho que cabe no cartão."""
        self.imagens[chave] = array
        visor = self.visores[chave]
        largura = max(visor.winfo_width(), 200)
        altura = max(visor.winfo_height(), 150)
        pil = self._para_pil(array)
        # Ajusta para caber no cartão (amplia ou reduz, mantendo a proporção).
        escala = min(largura / pil.width, altura / pil.height)
        tamanho = (max(1, int(pil.width * escala)), max(1, int(pil.height * escala)))
        pil = pil.resize(tamanho, Image.LANCZOS)
        self.fotos[chave] = ImageTk.PhotoImage(pil)
        visor.config(image=self.fotos[chave], text="")

    def _agendar_redimensionamento(self, _evento):
        # Espera o usuário parar de arrastar a janela antes de redesenhar.
        if self._redimensionar_id:
            self.root.after_cancel(self._redimensionar_id)
        self._redimensionar_id = self.root.after(120, self._redesenhar_imagens)

    def _redesenhar_imagens(self):
        self._redimensionar_id = None
        for chave, array in list(self.imagens.items()):
            self.mostrar(chave, array)

    def ampliar(self, chave, titulo):
        """Abre a imagem em tela grande (ótimo para apresentar)."""
        if chave not in self.imagens:
            return
        janela = tk.Toplevel(self.root, bg="#111111")
        janela.title(titulo)
        pil = self._para_pil(self.imagens[chave])
        limite = (int(self.root.winfo_screenwidth() * 0.9),
                  int(self.root.winfo_screenheight() * 0.9))
        pil.thumbnail(limite, Image.LANCZOS)
        foto = ImageTk.PhotoImage(pil)
        rotulo = tk.Label(janela, image=foto, bg="#111111")
        rotulo.image = foto  # mantém a referência
        rotulo.pack(padx=10, pady=10)
        janela.bind("<Escape>", lambda _e: janela.destroy())
        rotulo.bind("<Button-1>", lambda _e: janela.destroy())


if __name__ == "__main__":
    root = tk.Tk()
    app = ImagePreprocessorApp(root)
    root.mainloop()