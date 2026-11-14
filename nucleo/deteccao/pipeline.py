"""Orquestra as três passadas e devolve o resultado final da detecção."""

import cv2
import numpy as np

from nucleo.configuracao import LADO_DETECCAO
from nucleo.deteccao.baixo_contraste import passada_baixo_contraste
from nucleo.deteccao.candidatos import passada_clahe, passada_normal
from nucleo.deteccao.pontuacao import tem_lado_na_margem


def detectar_documento(imagem, baixo_contraste=True):
    """Encontra os quatro cantos do documento na imagem.

    Passos:
        1. Reduz a foto (LADO_DETECCAO) e apaga o texto: só sobram as bordas grandes.
        2. Passada 1: candidatos com Otsu e Canny em dois canais (cinza e
           brancura), com lados ajustados às retas reais (Hough). Cada candidato
           é pontuado pelo apoio nas bordas e pelo tamanho. Nenhum lado medido
           pode ficar sem borda (LADO_MINIMO).
        3. Passada 2: se nada servir, repete com CLAHE (bordas fracas, fundo branco).
        4. Passada 3 (folha e fundo parecidos): se ainda não achou, ou se o
           resultado encosta na margem da foto, procura retas fracas com LSD em
           brilho + croma e exige que a folha contenha o texto.

    `baixo_contraste=False` pula o passo 4; é o modo rápido da câmera ao vivo.

    Retorna (cantos, encontrou), com os cantos na escala da imagem ORIGINAL.
    Se nada for confiável, devolve os cantos da imagem inteira e encontrou = False.
    """
    altura, largura = imagem.shape[:2]
    cantos_da_imagem = np.array(
        [[0, 0], [largura - 1, 0], [largura - 1, altura - 1], [0, altura - 1]],
        dtype="float32",
    )

    # Reduz a foto: a detecção fica rápida e ignora detalhes pequenos. Os cantos
    # encontrados são depois convertidos de volta para a escala original.
    escala = min(1.0, LADO_DETECCAO / max(altura, largura))
    reduzida = cv2.resize(imagem, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    altura_reduzida, largura_reduzida = reduzida.shape[:2]

    # Passada 1: canais normais.
    cantos, canais = passada_normal(reduzida)

    # Passada 2 (último recurso das passadas rápidas): folha branca sobre fundo
    # branco. Não é usada sempre porque o CLAHE também realça texturas
    # (madeira, piso), que confundiriam as fotos que já funcionam.
    if cantos is None:
        cantos = passada_clahe(canais["cinza"], altura_reduzida, largura_reduzida)

    # Passada 3 + "segunda opinião". Se o resultado das passadas anteriores tem
    # um lado colado na margem da foto, a borda daquele lado pode simplesmente
    # não ter sido vista (folha clara em fundo claro). Se a passada de baixo
    # contraste enxerga os 4 lados de um quadrilátero, ele é o mais confiável.
    if baixo_contraste and (cantos is None
                            or tem_lado_na_margem(cantos, altura_reduzida, largura_reduzida)):
        alternativa = passada_baixo_contraste(reduzida, exigir_quatro_lados=cantos is not None)
        if alternativa is not None:
            cantos = alternativa

    if cantos is None:
        return cantos_da_imagem, False
    return cantos / escala, True
