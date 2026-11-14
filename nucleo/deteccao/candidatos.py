"""Passadas 1 e 2 da detecção: candidatos a partir de contornos.

Estratégia (passada 1, "normal"):
    1. Gera várias máscaras binárias da foto (Otsu e Canny, em dois canais).
    2. Em cada máscara, procura os maiores contornos e tenta transformá-los em
       quadriláteros.
    3. Ajusta os lados do quadrilátero às retas reais da borda (Hough).
    4. Pontua cada candidato e fica com o melhor (ver pontuacao.py).

A passada 2 repete o processo sobre uma versão com contraste local realçado
(CLAHE), exigindo mais apoio nas bordas. Ela só roda se a 1ª não achar nada,
porque o CLAHE também realça texturas (madeira, piso) e confundiria as fotos
que já funcionam.
"""

import cv2
import numpy as np

from nucleo.configuracao import APOIO_MINIMO, AREA_MINIMA_RELATIVA, LADO_MINIMO
from nucleo.deteccao.pontuacao import medir_apoio_nas_bordas
from nucleo.geometria import (afastar_do_centro, intersecao_de_retas,
                              reta_por_dois_pontos)


# ----------------------------------------------------------------- canais e máscaras

def _apagar_texto(canal):
    """Fechamento morfológico: o "branco" cobre as letras e a folha fica lisa.

    Assim sobram apenas as bordas grandes (folha x fundo), e não as milhares
    de bordas das letras.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    return cv2.morphologyEx(canal, cv2.MORPH_CLOSE, kernel)


def _canny_automatico(canal):
    """Canny com limiares calculados a partir do brilho típico da imagem.

    Os limiares são proporcionais à mediana do brilho. (Por isso falha em fotos
    escuras ou de pouco contraste: a passada de baixo contraste não usa esta
    função.)
    """
    mediana = float(np.median(canal))
    return cv2.Canny(cv2.GaussianBlur(canal, (5, 5), 0),
                     0.15 * mediana, 0.3 * mediana + 30)


def _gerar_mascaras(imagem):
    """Gera várias imagens binárias; cada uma funciona melhor num tipo de foto.

    Canais usados:
        cinza     brilho comum (bom para fundo escuro);
        brancura  brilho menos saturação. Papel é claro e SEM cor, enquanto
                  madeira, mesa e tecido têm cor. Bom para fundo claro e colorido.

    Para cada canal, três máscaras:
        otsu          separa regiões claras e escuras;
        canny fina    as bordas, levemente engrossadas;
        canny grossa  bordas bem engrossadas, que fecham falhas causadas por
                      sombras (o quadrilátero é afastado 5 px para compensar).

    Retorna (lista de (tipo, máscara, afastamento), dicionário de canais).
    """
    hsv = cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)
    canais = {
        "cinza": _apagar_texto(cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)),
        "brancura": _apagar_texto(cv2.subtract(hsv[:, :, 2], hsv[:, :, 1])),
    }
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mascaras = []
    for canal in canais.values():
        # Otsu: o limiar é escolhido automaticamente; a abertura remove ruídos.
        _, otsu = cv2.threshold(cv2.GaussianBlur(canal, (5, 5), 0), 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mascaras.append(("otsu", cv2.morphologyEx(otsu, cv2.MORPH_OPEN, kernel), 0))

        # Canny: versão fina e versão "grossa" (a grossa fecha falhas da borda
        # causadas por sombras; depois o quadrilátero é afastado 5 px).
        bordas = _canny_automatico(canal)
        mascaras.append(("canny", cv2.dilate(bordas, np.ones((3, 3), np.uint8)), 0))
        mascaras.append(("canny", cv2.dilate(bordas, np.ones((11, 11), np.uint8)), 5))
    return mascaras, canais


# ------------------------------------------------------------- do contorno ao quadrilátero

def _quadrilatero(contorno):
    """Transforma um contorno em 4 cantos, ou None se não parecer uma folha.

    O casco convexo (convexHull) "passa por cima" de dedos, clipes e sombras
    que entram na borda. Depois aumentamos a tolerância do approxPolyDP até
    o polígono ter exatamente 4 vértices.
    """
    casco = cv2.convexHull(contorno)
    perimetro = cv2.arcLength(casco, True)
    for tolerancia in np.linspace(0.01, 0.08, 15):
        aproximado = cv2.approxPolyDP(casco, tolerancia * perimetro, True)
        if len(aproximado) == 4:
            return aproximado.reshape(4, 2).astype(np.float32)
        if len(aproximado) < 4:
            break  # simplificou demais: mais tolerância só piora
    return None


def _encaixar_nas_retas(cantos, segmentos, altura, largura):
    """Ajusta cada lado do quadrilátero à reta real da borda da folha.

    Quando uma sombra "come" um canto, o quadrilátero sai torto. Aqui, para
    cada lado, procuramos o maior segmento de reta (Hough) quase paralelo e
    próximo dele. Os novos cantos são as interseções dessas retas.
    """
    if segmentos is None:
        return cantos

    # Ordena os cantos em volta do centro para percorrer os lados em sequência.
    relativos = cantos - cantos.mean(axis=0)
    cantos = cantos[np.argsort(np.arctan2(relativos[:, 1], relativos[:, 0]))]
    menor_lado = min(altura, largura)

    # Para cada lado, escolhe a reta de Hough que melhor o representa.
    retas = []
    for i in range(4):
        p1, p2 = cantos[i], cantos[(i + 1) % 4]
        lado = p2 - p1
        comprimento = np.linalg.norm(lado)
        angulo = np.arctan2(lado[1], lado[0])
        normal = np.array([-lado[1], lado[0]]) / comprimento
        melhor, melhor_comprimento = None, 0.3 * comprimento
        for x1, y1, x2, y2 in segmentos.reshape(-1, 4):
            segmento = np.array([x2 - x1, y2 - y1], np.float32)
            diferenca = abs((np.arctan2(segmento[1], segmento[0]) - angulo + np.pi / 2) % np.pi
                            - np.pi / 2)
            meio = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
            posicao = np.dot(meio - p1, lado) / comprimento ** 2
            if (diferenca <= np.radians(12)                               # quase paralelo
                    and abs(np.dot(meio - p1, normal)) <= 0.12 * menor_lado  # perto do lado
                    and -0.1 < posicao < 1.1                              # na altura do lado
                    and np.linalg.norm(segmento) > melhor_comprimento):   # o mais longo
                melhor, melhor_comprimento = (x1, y1, x2, y2), np.linalg.norm(segmento)
        if melhor is None:
            retas.append(reta_por_dois_pontos(p1, p2))  # sem segmento: mantém o lado
        else:
            retas.append(reta_por_dois_pontos(np.array(melhor[:2], float),
                                              np.array(melhor[2:], float)))

    # Novos cantos = interseção de cada par de retas vizinhas.
    novos = [intersecao_de_retas(retas[i - 1], retas[i]) for i in range(4)]
    if any(p is None for p in novos):
        return cantos
    novos = np.array(novos, np.float32)

    # Só aceita se continuar sendo um quadrilátero convexo e razoável (dentro
    # da foto, com uma pequena folga); senão fica com os cantos originais.
    folga = 0.03 * max(altura, largura)
    dentro = ((novos[:, 0] >= -folga) & (novos[:, 0] <= largura + folga)
              & (novos[:, 1] >= -folga) & (novos[:, 1] <= altura + folga)).all()
    if not dentro or not cv2.isContourConvex(novos.reshape(-1, 1, 2).astype(np.int32)):
        return cantos
    novos[:, 0] = novos[:, 0].clip(0, largura - 1)
    novos[:, 1] = novos[:, 1].clip(0, altura - 1)
    return novos


def _melhor_candidato(mascaras, bordas_finas, bordas_nota, altura, largura, apoio_minimo=None):
    """Testa os contornos de cada máscara e devolve o quadrilátero de maior nota.

    nota = apoio nas bordas x raiz da fração de área. A raiz suaviza a
    preferência por áreas grandes: um candidato maior só ganha se também tiver
    apoio parecido.
    """
    area_foto = altura * largura
    # Segmentos de Hough: servem para encaixar os lados nas retas reais.
    segmentos = cv2.HoughLinesP(bordas_finas, 1, np.pi / 180, 40,
                                minLineLength=0.15 * min(altura, largura), maxLineGap=15)
    # Mapa de bordas usado na nota, engrossado para tolerar pequenas diferenças.
    referencia = cv2.dilate(bordas_nota, np.ones((7, 7), np.uint8))

    apoio_minimo = APOIO_MINIMO if apoio_minimo is None else apoio_minimo
    melhor_nota, melhores_cantos = 0.0, None
    for tipo, mascara, afastamento in mascaras:
        # Nas bordas do Canny, o contorno de DENTRO do retângulo é a folha,
        # mesmo que a linha esteja grudada em outras (tábua, outra folha).
        modo = cv2.RETR_LIST if tipo == "canny" else cv2.RETR_EXTERNAL
        contornos, _ = cv2.findContours(mascara, modo, cv2.CHAIN_APPROX_SIMPLE)
        contornos = sorted(contornos, key=lambda c: cv2.contourArea(cv2.convexHull(c)),
                           reverse=True)

        # Só os 6 maiores contornos interessam; os menores que a área mínima
        # nem são considerados (a lista está ordenada, então podemos parar).
        for contorno in contornos[:6]:
            if cv2.contourArea(cv2.convexHull(contorno)) < AREA_MINIMA_RELATIVA * area_foto:
                break
            cantos = _quadrilatero(contorno)
            if cantos is None:
                continue
            if afastamento:
                cantos = afastar_do_centro(cantos, afastamento)
            cantos = _encaixar_nas_retas(cantos, segmentos, altura, largura)

            fracao_area = cv2.contourArea(cantos) / area_foto
            if not AREA_MINIMA_RELATIVA <= fracao_area <= 0.98:
                continue  # pequeno demais ou é a própria foto inteira

            apoio, pior_lado = medir_apoio_nas_bordas(cantos, referencia)
            nota = apoio * fracao_area ** 0.5
            if apoio >= apoio_minimo and pior_lado >= LADO_MINIMO and nota > melhor_nota:
                melhor_nota, melhores_cantos = nota, cantos
    return melhores_cantos


# ------------------------------------------------------------------- as duas passadas

def passada_normal(imagem_reduzida):
    """Passada 1: máscaras de Otsu/Canny em dois canais (cinza e brancura).

    Retorna (cantos ou None, canais). Os canais são devolvidos porque a passada
    2 reaproveita o canal cinza.
    """
    altura, largura = imagem_reduzida.shape[:2]
    mascaras, canais = _gerar_mascaras(imagem_reduzida)
    bordas_cinza = _canny_automatico(canais["cinza"])
    # A nota usa as bordas dos dois canais; o encaixe de retas, só as do cinza.
    bordas_nota = bordas_cinza | _canny_automatico(canais["brancura"])
    cantos = _melhor_candidato(mascaras, bordas_cinza, bordas_nota, altura, largura)
    return cantos, canais


def passada_clahe(canal_cinza, altura, largura):
    """Passada 2 (último recurso): folha branca sobre fundo branco.

    O CLAHE realça diferenças pequenas de brilho em cada região da foto e faz
    a borda fraca da folha aparecer. Exige mais apoio nas bordas (75%): é
    melhor não achar do que achar errado.
    """
    contraste = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(canal_cinza)
    bordas = _canny_automatico(contraste)
    mascaras_contraste = [
        ("canny", cv2.dilate(bordas, np.ones((3, 3), np.uint8)), 0),
        ("canny", cv2.dilate(bordas, np.ones((11, 11), np.uint8)), 5),
    ]
    return _melhor_candidato(mascaras_contraste, bordas, bordas, altura, largura,
                             apoio_minimo=0.75)
