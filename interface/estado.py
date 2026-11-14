"""Os dados do documento que está sendo trabalhado.

Antes esses valores eram atributos espalhados pela classe da janela. Reuni-los
aqui deixa claro o que o programa "sabe" sobre o documento atual e permite
limpar tudo de uma vez quando a imagem muda.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Estado:
    """Estado do documento atual."""

    imagem: Optional[np.ndarray] = None            # foto original (BGR)
    nome_arquivo: str = ""                         # nome do arquivo carregado/capturado
    cantos: Optional[np.ndarray] = None            # 4 cantos detectados (ou ajustados)
    documento_encontrado: bool = False             # a detecção automática teve sucesso?
    digitalizada: Optional[np.ndarray] = None      # documento corrigido, colorido
    digitalizada_pb: Optional[np.ndarray] = None   # documento com efeito de scanner
    texto_ocr: str = ""                            # texto original do OCR (sem edições)

    def limpar_resultados(self):
        """Esquece tudo que foi calculado a partir da imagem (a imagem em si fica)."""
        self.cantos = None
        self.documento_encontrado = False
        self.digitalizada = None
        self.digitalizada_pb = None
        self.texto_ocr = ""
