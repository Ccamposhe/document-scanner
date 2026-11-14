"""Operações sobre a imagem que não fazem parte da detecção da folha.

Aqui ficam as três "peças visuais" do programa:
    - preprocessamento   as etapas didáticas (cinza -> desfoque -> binarização);
    - desenhar_contorno  mostra, sobre a foto original, onde a folha foi achada;
    - efeito_scanner     deixa a imagem final com cara de documento escaneado.
"""

import cv2
import numpy as np

from nucleo.geometria import ordenar_cantos


def preprocessamento(imagem):
    """Etapas do pré-processamento mostradas na interface.

    Retorna, nesta ordem:
        cinza      a imagem em tons de cinza;
        desfocada  o cinza suavizado por um Gaussian Blur 5x5 (reduz ruído);
        binaria    a desfocada binarizada pelo método de Otsu, que escolhe
                   sozinho o limiar que melhor separa fundo e primeiro plano.
    """
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    desfocada = cv2.GaussianBlur(cinza, (5, 5), 0)
    _, binaria = cv2.threshold(desfocada, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cinza, desfocada, binaria


def desenhar_contorno(imagem, cantos):
    """Desenha o contorno detectado sobre uma cópia da original.

    A espessura da linha cresce com o tamanho da foto, para continuar visível
    em imagens grandes.
    """
    saida = imagem.copy()
    espessura = max(2, max(imagem.shape[:2]) // 300)
    pontos = ordenar_cantos(cantos).astype(np.int32)
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
       limiarização simples, que deixa as letras serrilhadas).
    O OCR continua lendo a imagem colorida original: nos testes, o preto e
    branco forte deixou letras pequenas "gordas" e piorou um pouco a leitura.
    """
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY) if imagem.ndim == 3 else imagem.copy()

    # 1) Ampliação (só amplia; nunca reduz uma imagem que já é grande).
    escala = lado / max(cinza.shape)
    if escala > 1:
        cinza = cv2.resize(cinza, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)

    # 2) Estimativa do fundo: o fechamento "apaga" as letras (escuras e finas) e
    #    o desfoque mediano alisa o resto. O elemento precisa ser maior que a
    #    grossura das letras. Dividir a imagem pelo fundo deixa o papel
    #    uniformemente claro, sem sombras.
    tamanho = max(15, (max(cinza.shape) // 60) | 1)  # sempre ímpar
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (tamanho, tamanho))
    fundo = cv2.medianBlur(cv2.morphologyEx(cinza, cv2.MORPH_CLOSE, kernel), 21)
    plano = cv2.divide(cinza, fundo, scale=255)

    # 3) Unsharp mask: realça a diferença entre a imagem e sua versão borrada.
    borrada = cv2.GaussianBlur(plano, (0, 0), 1.2)
    nitida = cv2.addWeighted(plano, 1.8, borrada, -0.8, 0)

    # 4) Curva de tons: acima de "claro" vira branco puro; abaixo de "escuro",
    #    preto; entre os dois a transição é suave (expoente 1,3 escurece o texto).
    claro, escuro = 215.0, 95.0
    tons = np.clip((nitida.astype(np.float32) - escuro) / (claro - escuro), 0, 1)
    return (tons ** 1.3 * 255).astype(np.uint8)
