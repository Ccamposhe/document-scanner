"""Passada 3 da detecção: folha e fundo de cores parecidas (baixo contraste).

Por que as passadas 1 e 2 falham quando folha e fundo se parecem:
    - o fechamento morfológico (_apagar_texto) apaga a linha fina que marca a
      borda do papel;
    - o limiar do Canny vem da mediana do brilho, alto demais em fotos escuras
      ou sem contraste;
    - só o brilho era comparado, e a diferença entre papel e fundo costuma
      estar na COR, não no brilho.

Como esta passada resolve:
    1. CROMA: mede a distância da cor ao cinza neutro (papel é neutro; parede,
       madeira e tecido quase sempre têm algum tom).
    2. LSD: detecta segmentos de reta pela coerência da direção do gradiente,
       sem limiar de borda, então enxerga lados muito fracos, desde que retos.
    3. RETAS E QUADRILÁTERO: junta segmentos em retas e testa combinações de
       2 retas "horizontais" + 2 "verticais", pontuando cada uma.
    4. TEXTO COMO ÂNCORA: a folha precisa conter o texto; um lado que corta as
       letras nunca é a borda do papel.

Esta passada é a mais cara (chega a ~200 ms no pior caso), por isso só roda
quando as outras não acham nada, ou quando o resultado delas encosta na
margem da foto (ver pipeline.py).
"""

import cv2
import numpy as np

from nucleo.configuracao import AREA_MINIMA_RELATIVA
from nucleo.geometria import intersecao_polar


# ------------------------------------------------------------------ canais e texto

def _croma(imagem):
    """Distância da cor ao cinza neutro, no espaço Lab (0 = cinza puro).

    Papel é neutro (a ≈ b ≈ 128); parede, madeira e tecido quase sempre têm
    algum tom. Assim a folha se separa do fundo mesmo quando o BRILHO é igual.
    """
    lab = cv2.cvtColor(imagem, cv2.COLOR_BGR2LAB).astype(np.float32)
    return np.hypot(lab[:, :, 1] - 128, lab[:, :, 2] - 128)


def _mascara_texto(cinza):
    """Marca onde há texto: letras escuras e finas, em linhas, sobre fundo claro.

    Blackhat = (fechamento da imagem) - (imagem): só sobram detalhes escuros mais
    finos que o elemento estruturante, ou seja, letras. Depois juntamos as letras
    em linhas e blocos e ficamos só com o maior bloco, para ignorar manchas e
    objetos escuros fora da folha. Linhas finas demais (sombra da borda) são
    descartadas pela altura mínima.
    """
    # 1) Realça detalhes escuros e finos (as letras).
    elemento = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    blackhat = cv2.morphologyEx(cv2.GaussianBlur(cinza, (0, 0), 0.7),
                                cv2.MORPH_BLACKHAT, elemento)

    # 2) Limiar relativo ao realce mais forte da foto; depois junta as letras
    #    em linhas (fechamento horizontal).
    alto = float(np.percentile(blackhat, 99.5))
    mascara = (blackhat > max(6.0, 0.35 * alto)).astype(np.uint8) * 255
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5)))

    # 3) Descarta componentes pequenos ou finos demais (ruído e sombras de borda).
    n, rotulos, estatisticas, _ = cv2.connectedComponentsWithStats(mascara)
    limpa = np.zeros_like(mascara)
    for i in range(1, n):
        if (estatisticas[i, cv2.CC_STAT_AREA] >= 120
                and estatisticas[i, cv2.CC_STAT_HEIGHT] >= 5
                and estatisticas[i, cv2.CC_STAT_WIDTH] >= 5):
            limpa[rotulos == i] = 255

    # 4) Fica só com o maior bloco de texto (blocos próximos contam como um só).
    proximos = cv2.dilate(limpa, np.ones((25, 25), np.uint8))
    n, rotulos, estatisticas, _ = cv2.connectedComponentsWithStats(proximos)
    if n <= 1:
        return np.zeros_like(limpa)
    pesos = [cv2.countNonZero(limpa[rotulos == i]) for i in range(1, n)]
    maior = 1 + int(np.argmax(pesos))
    return cv2.bitwise_and(limpa, (rotulos == maior).astype(np.uint8) * 255)


# ------------------------------------------------------------- segmentos e retas (LSD)

def _segmentos(canal, comprimento_minimo):
    """Segmentos de reta do LSD (Line Segment Detector) com sensibilidade alta.

    O LSD não depende de um limiar de borda: ele agrupa pixels cujo gradiente
    aponta na mesma direção. Por isso acha lados MUITO fracos, desde que
    sejam retos. quant=0.5 deixa a detecção mais sensível que o padrão (2.0).
    Devolve uma lista de (x1, y1, x2, y2) com pelo menos `comprimento_minimo`.
    """
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD, 0.8, 0.6, 0.5, 22.5, 0, 0.7, 1024)
    segmentos = lsd.detect(cv2.GaussianBlur(canal, (0, 0), 0.8))[0]
    if segmentos is None:
        return []
    segmentos = segmentos.reshape(-1, 4)
    comprimentos = np.hypot(segmentos[:, 2] - segmentos[:, 0],
                            segmentos[:, 3] - segmentos[:, 1])
    return [tuple(s) for s, c in zip(segmentos, comprimentos) if c >= comprimento_minimo]


def _agrupar_retas(segmentos, altura, largura, maximo=30):
    """Une segmentos quase colineares em retas (rho, theta) com o comprimento somado.

    Uma borda fraca costuma ser detectada em vários pedaços; juntá-los dá uma
    reta "pesada" (comprimento total grande). Retorna as retas mais pesadas
    primeiro, descartando as muito curtas.
    """
    grupos = []  # cada grupo: [rho_medio, theta_medio, comprimento_total]
    for x1, y1, x2, y2 in segmentos:
        comprimento = np.hypot(x2 - x1, y2 - y1)
        # theta = direção da NORMAL da reta (0 a π); rho = distância da origem.
        theta = (np.arctan2(y2 - y1, x2 - x1) + np.pi / 2) % np.pi
        rho = x1 * np.cos(theta) + y1 * np.sin(theta)
        for grupo in grupos:
            # Mesma reta? Ângulo parecido (< 3°) e posição próxima (< 2% da foto).
            diferenca_angulo = abs((theta - grupo[1] + np.pi / 2) % np.pi - np.pi / 2)
            if diferenca_angulo < np.radians(3) and abs(rho - grupo[0]) < 0.02 * max(altura, largura):
                # Atualiza a reta do grupo com média ponderada pelo comprimento.
                total = grupo[2] + comprimento
                grupo[0] = (grupo[0] * grupo[2] + rho * comprimento) / total
                grupo[1] = grupo[1] + ((theta - grupo[1] + np.pi / 2) % np.pi - np.pi / 2) * comprimento / total
                grupo[2] = total
                break
        else:
            grupos.append([rho, theta, comprimento])
    grupos.sort(key=lambda g: -g[2])
    return [(float(r), float(t)) for r, t, c in grupos[:maximo] if c >= 0.2 * min(altura, largura)]


# ------------------------------------------------------- avaliação dos lados e do texto

def _apoio_do_lado(p, q, distancias, altura, largura, passo=2.0, tolerancia=3.0):
    """Fração do lado p→q coberta por segmentos detectados.

    `distancias` é o mapa de distância até o segmento detectado mais próximo
    (um ponto do lado "tem apoio" se está a até `tolerancia` pixels de um
    segmento). Trechos fora da foto (a folha continua além da margem) são
    ignorados; se o lado quase todo está fora, devolve None (sem como avaliar).
    """
    n = max(int(np.linalg.norm(q - p) / passo), 2)
    pontos = p[None, :] + (q - p)[None, :] * np.linspace(0, 1, n)[:, None]
    dentro = ((pontos[:, 0] >= 3) & (pontos[:, 0] <= largura - 4)
              & (pontos[:, 1] >= 3) & (pontos[:, 1] <= altura - 4))
    if dentro.sum() < 0.25 * n:
        return None  # lado quase todo fora da foto: sem como avaliar
    xs = pontos[dentro, 0].astype(int)
    ys = pontos[dentro, 1].astype(int)
    return float((distancias[ys, xs] <= tolerancia).mean())


def _contem_texto(cantos, pontos, fracao_minima=0.97):
    """True se (quase) todos os pontos de texto estão dentro do quadrilátero convexo.

    Um ponto está dentro se fica do mesmo lado dos 4 lados (produto vetorial).
    A tolerância de 2 px evita rejeitar texto colado na borda.
    """
    distancias_com_sinal = []
    for k in range(4):
        p, q = cantos[k], cantos[(k + 1) % 4]
        lado = q - p
        produto_vetorial = lado[0] * (pontos[:, 1] - p[1]) - lado[1] * (pontos[:, 0] - p[0])
        distancias_com_sinal.append(produto_vetorial / max(float(np.hypot(*lado)), 1e-6))
    distancias_com_sinal = np.stack(distancias_com_sinal)
    dentro = ((distancias_com_sinal >= -2).all(axis=0)
              | (distancias_com_sinal <= 2).all(axis=0))
    return float(dentro.mean()) >= fracao_minima


# --------------------------------------------------------- busca do melhor quadrilátero

def _quadrilatero_por_retas(retas, tracado_segmentos, altura, largura, texto=None,
                            apoio_minimo=0.5, exigir_quatro_lados=False):
    """Melhor retângulo formado por 2 retas "horizontais" e 2 "verticais".

    As retas atravessam as falhas da borda (trechos em que folha e fundo são
    quase iguais). Cada candidato recebe nota = apoio × raiz da área, e TODOS
    os lados medidos precisam de apoio mínimo, para não aceitar um lado inventado.
    Se houver texto (pontos Nx2), a folha precisa CONTER o texto: um lado que
    atravessa as letras não pode ser a borda do papel.

    `exigir_quatro_lados=True` (usado na "segunda opinião") só aceita candidatos
    em que os 4 lados puderam ser medidos dentro da foto.
    """
    if len(retas) < 4:
        return None

    # Mapa de distância até o segmento mais próximo, calculado uma vez só.
    distancias = cv2.distanceTransform(255 - tracado_segmentos, cv2.DIST_L2, 3)
    area_foto = altura * largura
    thetas = [t for _, t in retas]
    melhor_nota, melhores_cantos, familias_vistas = 0.0, None, set()

    # Caches: o mesmo cruzamento e o mesmo lado aparecem em muitas combinações.
    cache_pontos, cache_lados = {}, {}

    def ponto(i, j):
        """Cruzamento da reta i com a reta j (calculado uma vez só)."""
        chave = (min(i, j), max(i, j))
        if chave not in cache_pontos:
            cache_pontos[chave] = intersecao_polar(retas[i], retas[j])
        return cache_pontos[chave]

    def apoio_do_trecho(i, j1, j2):
        """Apoio do trecho da reta i entre os cruzamentos com as retas j1 e j2."""
        chave = (i, min(j1, j2), max(j1, j2))
        if chave not in cache_lados:
            p, q = ponto(i, j1), ponto(i, j2)
            cache_lados[chave] = (None if p is None or q is None
                                  else _apoio_do_lado(p, q, distancias, altura, largura))
        return cache_lados[chave]

    # Cada reta "âncora" define a direção principal; a outra família é a perpendicular.
    for ancora in range(min(len(retas), 8)):
        familia_a, familia_b = [], []
        for i, theta in enumerate(thetas):
            diferenca = abs((theta - thetas[ancora] + np.pi / 2) % np.pi - np.pi / 2)
            diferenca_90 = abs((theta - thetas[ancora]) % np.pi - np.pi / 2)
            if diferenca < np.radians(25):
                familia_a.append(i)       # quase paralela à âncora
            elif diferenca_90 < np.radians(25):
                familia_b.append(i)       # quase perpendicular à âncora
        chave = (tuple(familia_a), tuple(familia_b))
        if chave in familias_vistas:
            continue  # outra âncora já gerou exatamente as mesmas famílias
        familias_vistas.add(chave)

        folga = 0.03 * max(altura, largura)
        separacao = 0.2 * min(altura, largura)  # lados opostos precisam estar bem afastados

        # Todas as combinações de 2 retas de cada família formam um quadrilátero.
        for i1 in range(len(familia_a)):
            for i2 in range(i1 + 1, len(familia_a)):
                ia1, ia2 = familia_a[i1], familia_a[i2]
                if abs(retas[ia1][0] - retas[ia2][0]) < separacao:
                    continue
                for j1 in range(len(familia_b)):
                    for j2 in range(j1 + 1, len(familia_b)):
                        ib1, ib2 = familia_b[j1], familia_b[j2]
                        if abs(retas[ib1][0] - retas[ib2][0]) < separacao:
                            continue

                        # Os 4 cantos são os cruzamentos das retas, em sequência.
                        cantos = [ponto(ia1, ib1), ponto(ia1, ib2), ponto(ia2, ib2), ponto(ia2, ib1)]
                        if any(c is None for c in cantos):
                            continue
                        cantos = np.array(cantos, np.float32)

                        # Filtros baratos primeiro: dentro da foto, convexo, área plausível.
                        if ((cantos[:, 0] < -folga) | (cantos[:, 0] > largura + folga)
                                | (cantos[:, 1] < -folga) | (cantos[:, 1] > altura + folga)).any():
                            continue
                        if not cv2.isContourConvex(cantos.reshape(-1, 1, 2)):
                            continue
                        fracao = cv2.contourArea(cantos) / area_foto
                        if not AREA_MINIMA_RELATIVA <= fracao <= 0.98:
                            continue

                        # Apoio de cada lado: nenhum lado medido pode ficar sem borda.
                        apoios = [apoio_do_trecho(ia1, ib1, ib2), apoio_do_trecho(ib2, ia1, ia2),
                                  apoio_do_trecho(ia2, ib1, ib2), apoio_do_trecho(ib1, ia1, ia2)]
                        medidos = [a for a in apoios if a is not None]
                        if len(medidos) < (4 if exigir_quatro_lados else 3) or min(medidos) < 0.15:
                            continue
                        apoio = float(np.mean(medidos))
                        nota = apoio * fracao ** 0.5
                        if apoio < apoio_minimo or nota <= melhor_nota:
                            continue

                        # Teste mais caro por último: a folha precisa conter o texto.
                        if texto is not None and not _contem_texto(cantos, texto):
                            continue
                        melhor_nota, melhores_cantos = nota, cantos

    if melhores_cantos is None:
        return None
    melhores_cantos[:, 0] = melhores_cantos[:, 0].clip(0, largura - 1)
    melhores_cantos[:, 1] = melhores_cantos[:, 1].clip(0, altura - 1)
    return melhores_cantos


# --------------------------------------------------------------------- função pública

def passada_baixo_contraste(imagem_reduzida, exigir_quatro_lados=False):
    """Última tentativa: segmentos LSD em brilho e croma + busca do quadrilátero por retas.

    Retorna os 4 cantos (na escala da imagem reduzida) ou None.
    """
    altura, largura = imagem_reduzida.shape[:2]
    comprimento_minimo = 0.08 * min(altura, largura)

    # 1) Segmentos de reta em dois canais: brilho e croma (realçado ×10).
    cinza = cv2.cvtColor(imagem_reduzida, cv2.COLOR_BGR2GRAY)
    croma = np.clip(_croma(imagem_reduzida) * 10, 0, 255).astype(np.uint8)
    segmentos = _segmentos(cinza, comprimento_minimo) + _segmentos(croma, comprimento_minimo)

    # 2) O texto gera segmentos fortes (linhas de letras) que NÃO são borda de
    #    folha. Em vez de apagá-los, exigimos que a folha CONTENHA o texto: um
    #    lado que corta as letras é rejeitado em _quadrilatero_por_retas.
    texto = _mascara_texto(cinza)
    pontos_texto = None
    if cv2.countNonZero(texto) >= 400:
        ys, xs = np.nonzero(texto)
        passo = max(1, len(xs) // 300)  # amostra ~300 pontos: suficiente e rápido
        pontos_texto = np.stack([xs[::passo], ys[::passo]], axis=1)
    if not segmentos:
        return None

    # 3) Desenha todos os segmentos numa imagem vazia (usada para medir apoio),
    #    junta-os em retas e procura o melhor quadrilátero.
    tracado_segmentos = np.zeros((altura, largura), np.uint8)
    for x1, y1, x2, y2 in segmentos:
        cv2.line(tracado_segmentos, (int(round(x1)), int(round(y1))),
                 (int(round(x2)), int(round(y2))), 255, 1)
    retas = _agrupar_retas(segmentos, altura, largura)
    return _quadrilatero_por_retas(retas, tracado_segmentos, altura, largura,
                                   texto=pontos_texto,
                                   exigir_quatro_lados=exigir_quatro_lados)
