"""Detecção dos quatro cantos do documento em uma foto.

Interface pública deste pacote: apenas `detectar_documento`. As passadas
(candidatos, baixo_contraste) e a pontuação são detalhes internos.
"""

from nucleo.deteccao.pipeline import detectar_documento

__all__ = ["detectar_documento"]
