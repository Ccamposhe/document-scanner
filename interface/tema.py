"""Aparência da interface: cores, abas e títulos dos cartões de imagem.

Mudar uma cor ou o nome de uma aba é um ajuste só neste arquivo.
"""

from collections import namedtuple
from tkinter import ttk

# --------------------------------------------------------------------------- cores
COR_FUNDO = "#F3F6F5"            # fundo da área principal
COR_BARRA = "#E9EFED"            # fundo da barra lateral
COR_CARTAO = "#FFFFFF"           # fundo dos cartões e da caixa de texto
COR_BORDA = "#D5DEDC"            # contorno dos cartões
COR_PRIMARIA = "#1FC6A0"         # ações principais (Processar, Escolher arquivo)
COR_SECUNDARIA = "#17363F"       # ações secundárias e títulos
COR_TEXTO = "#0F2A33"
COR_SUAVE = "#5C6B69"            # rótulos e textos de apoio
COR_DESATIVADA = "#DDE5E3"       # fundo de botão desativado
COR_TEXTO_DESATIVADO = "#8A9896"

# -------------------------------------------------------------------------- imagens
# Cada cartão de imagem tem uma chave. As etapas do processamento são:
#   original    a foto enviada            contorno   onde a folha foi detectada
#   cinza       escala de cinza           desfocada  Gaussian Blur
#   binaria     threshold (Otsu)          digitalizada  documento corrigido (cor)
#   pb          efeito de scanner (P&B)
TITULOS = {
    "original": "ENTRADA",
    "contorno": "DETECÇÃO",
    "cinza": "ESCALA DE CINZA",
    "desfocada": "GAUSSIAN BLUR",
    "binaria": "THRESHOLD",
    "digitalizada": "DIGITALIZADA (COR)",
    "pb": "SCANNER P&B",
}

# Cartões que dependem do processamento (são limpos quando a imagem muda).
CARTOES_PROCESSO = ("contorno", "cinza", "desfocada", "binaria", "digitalizada", "pb")

# ---------------------------------------------------------------------------- abas
# Cada aba escolhe quais cartões aparecem (na ordem), se a caixa de texto
# extraído é mostrada e se os botões de salvar são mostrados.
Modo = namedtuple("Modo", "chave rotulo cartoes mostra_texto mostra_salvar")

MODOS = [
    Modo("pre", "Original + pré-processamento",
         ("original", "cinza", "desfocada", "binaria", "digitalizada"), False, False),
    Modo("digitalizada", "Original + digitalizada",
         ("original", "digitalizada", "pb"), True, True),
    Modo("todos", "Todos os processos",
         ("original", "contorno", "cinza", "desfocada", "binaria", "digitalizada", "pb"),
         True, True),
]


def aplicar_tema_ttk(raiz):
    """Pinta a barra de progresso (widget ttk) com as cores do aplicativo."""
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    estilo.configure("Horizontal.TProgressbar", background=COR_PRIMARIA,
                     troughcolor=COR_CARTAO, bordercolor=COR_CARTAO,
                     lightcolor=COR_PRIMARIA, darkcolor=COR_PRIMARIA)
