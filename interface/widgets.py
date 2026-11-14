"""Botão padrão do aplicativo, com visual de ativado/desativado."""

import tkinter as tk

from interface.tema import COR_DESATIVADA, COR_TEXTO_DESATIVADO


def criar_botao(pai, texto, comando, cor, cor_texto, padx=20):
    """Cria um botão chato (sem relevo) nas cores do tema.

    As cores originais ficam guardadas no próprio botão (`cores_originais`)
    para que `definir_estado_botao` possa restaurá-las ao reativá-lo.
    """
    botao = tk.Button(
        pai, text=texto, command=comando, font=("Arial", 11, "bold"),
        bg=cor, fg=cor_texto, relief="flat", bd=0, padx=padx, pady=8,
        activebackground=cor, activeforeground=cor_texto,
        disabledforeground=COR_TEXTO_DESATIVADO)
    botao.cores_originais = (cor, cor_texto)
    return botao


def definir_estado_botao(botao, ativo):
    """Ativa o botão (com as cores originais) ou o desativa (cinza, sem clique)."""
    if ativo:
        fundo, texto = botao.cores_originais
        botao.config(state="normal", bg=fundo, fg=texto, activebackground=fundo,
                     cursor="hand2")
    else:
        botao.config(state="disabled", bg=COR_DESATIVADA, fg=COR_TEXTO_DESATIVADO,
                     disabledforeground=COR_TEXTO_DESATIVADO, cursor="arrow")
