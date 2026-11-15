"""Versão leve do processamento, usada pela prévia da câmera ao vivo.

Roda as mesmas etapas do processamento completo (as que aparecem nos cartões
da interface), só que sobre imagens reduzidas, para ser rápida o bastante para
repetir várias vezes por segundo. O OCR NÃO entra aqui: leva vários segundos
por quadro (medido: ~20 s), então só roda quando o quadro é capturado.

Esta função não depende de interface nem de threads: recebe um quadro e devolve
resultados, o que a torna fácil de testar.
"""

import cv2

from nucleo.configuracao import LADO_ETAPAS_AO_VIVO
from nucleo.deteccao import detectar_documento
from nucleo.geometria import transformar_perspectiva
from nucleo.imagem import desenhar_contorno, efeito_scanner, preprocessamento


def _reduzir(imagem, lado):
    """Reduz `imagem` para que o maior lado tenha no máximo `lado` px.

    Retorna (imagem_reduzida, escala). Nunca amplia: imagens pequenas ficam como estão.
    """
    escala = min(1.0, lado / max(imagem.shape[:2]))
    if escala >= 1.0:
        return imagem, 1.0
    return cv2.resize(imagem, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA), escala


def analisar_quadro(quadro, lado_etapas=LADO_ETAPAS_AO_VIVO):
    """Roda as etapas do processamento, em versão leve, sobre um quadro da câmera.

    Retorna (cantos, etapas):
        cantos  os 4 cantos da folha na escala do QUADRO ORIGINAL, ou None se
                nenhuma folha foi achada;
        etapas  dicionário com as imagens de cada cartão, todas com no máximo
                `lado_etapas` px: "contorno", "cinza", "desfocada", "binaria",
                "digitalizada" e "pb". As duas últimas são None quando nenhuma
                folha foi achada.

    A detecção usa só as passadas rápidas (baixo_contraste=False): a análise
    completa roda quando o quadro é capturado.
    """
    # 1) Detecção da folha (já trabalha numa cópia reduzida por dentro).
    cantos, encontrou = detectar_documento(quadro, baixo_contraste=False)

    # 2) Documento endireitado, feito sobre o quadro em tamanho completo (barato).
    #    Se os cantos forem degenerados, a folha conta como "não achada".
    previa = transformar_perspectiva(quadro, cantos) if encontrou else None
    encontrou = previa is not None

    # 3) Etapas de imagem sobre versões reduzidas: as miniaturas da tela não
    #    precisam de mais que isso.
    vista, escala = _reduzir(quadro, lado_etapas)
    cinza, desfocada, binaria = preprocessamento(vista)

    if encontrou:
        contorno = desenhar_contorno(vista, cantos * escala)
        digitalizada, _ = _reduzir(previa, lado_etapas)
        pb = efeito_scanner(digitalizada, lado=lado_etapas)
    else:
        contorno, digitalizada, pb = vista, None, None

    etapas = {"contorno": contorno, "cinza": cinza, "desfocada": desfocada,
              "binaria": binaria, "digitalizada": digitalizada, "pb": pb}
    return (cantos if encontrou else None), etapas
