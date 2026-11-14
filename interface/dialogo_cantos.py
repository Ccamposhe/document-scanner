"""Janela "Ajustar cantos": o usuário arrasta os 4 cantos da folha."""

import tkinter as tk
from tkinter import messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk

from interface.conversao import para_rgb
from interface.tema import COR_CARTAO, COR_DESATIVADA, COR_PRIMARIA, COR_SUAVE, COR_TEXTO
from interface.widgets import criar_botao
from nucleo.geometria import ordenar_cantos


def abrir_dialogo_cantos(raiz, imagem, cantos, ao_aplicar):
    """Abre a janela de ajuste de cantos sobre `imagem`.

    cantos      cantos atuais (detectados antes). Com None, começa com a imagem toda.
    ao_aplicar  função chamada com os 4 cantos escolhidos, já na escala da imagem
                ORIGINAL, quando o usuário clica em "Aplicar".
    """
    janela = tk.Toplevel(raiz, bg=COR_CARTAO)
    janela.title("Ajustar cantos")
    janela.transient(raiz)
    tk.Label(janela, text="Arraste os círculos até os cantos da folha.",
             bg=COR_CARTAO, fg=COR_SUAVE).pack(anchor="w", padx=16, pady=(12, 8))

    # --- A imagem é reduzida para caber na tela; `escala` converte as coordenadas ---
    imagem_pil = Image.fromarray(para_rgb(imagem))
    escala = min(raiz.winfo_screenwidth() * 0.8 / imagem_pil.width,
                 raiz.winfo_screenheight() * 0.72 / imagem_pil.height, 1.0)
    imagem_pil = imagem_pil.resize(
        (max(1, int(imagem_pil.width * escala)), max(1, int(imagem_pil.height * escala))),
        Image.LANCZOS)
    foto = ImageTk.PhotoImage(imagem_pil)
    tela = tk.Canvas(janela, width=imagem_pil.width, height=imagem_pil.height,
                     highlightthickness=0, bg="#111111", cursor="crosshair")
    tela.pack(padx=16)
    tela.create_image(0, 0, image=foto, anchor="nw")
    tela.foto = foto  # o Tkinter não guarda a referência: sem isto a imagem some

    # --- Pontos iniciais: cantos detectados ou a imagem inteira ---------------------
    if cantos is not None:
        base = cantos
    else:
        altura, largura = imagem.shape[:2]
        base = np.array([[0, 0], [largura - 1, 0],
                         [largura - 1, altura - 1], [0, altura - 1]], np.float32)

    pontos = [list(p) for p in ordenar_cantos(base) * escala]  # coordenadas na tela
    raio = 9  # raio das alças (círculos arrastáveis)
    poligono = tela.create_polygon(*[c for p in pontos for c in p],
                                   outline="#1FC6A0", fill="", width=2)
    alcas = [tela.create_oval(0, 0, 0, 0, fill="white", outline="#1FC6A0", width=3)
             for _ in pontos]
    arrastando = {"indice": None}  # qual alça está sendo arrastada (None = nenhuma)

    def redesenhar():
        """Reposiciona o polígono e as alças de acordo com `pontos`."""
        tela.coords(poligono, *[c for p in pontos for c in p])
        for alca, (x, y) in zip(alcas, pontos):
            tela.coords(alca, x - raio, y - raio, x + raio, y + raio)

    # --- Arrastar: pega a alça mais próxima do clique (se estiver perto o bastante) ---
    def pressionar(evento):
        """Clique: seleciona a alça mais próxima, se o clique foi perto dela."""
        distancias = [(evento.x - x) ** 2 + (evento.y - y) ** 2 for x, y in pontos]
        indice = int(np.argmin(distancias))
        arrastando["indice"] = indice if distancias[indice] < (raio * 4) ** 2 else None

    def mover(evento):
        """Arrastar: leva a alça selecionada até o ponteiro do mouse."""
        indice = arrastando["indice"]
        if indice is not None:
            # A alça não pode sair da imagem.
            pontos[indice] = [min(max(evento.x, 0), imagem_pil.width - 1),
                              min(max(evento.y, 0), imagem_pil.height - 1)]
            redesenhar()

    tela.bind("<ButtonPress-1>", pressionar)
    tela.bind("<B1-Motion>", mover)
    tela.bind("<ButtonRelease-1>", lambda _e: arrastando.update(indice=None))
    redesenhar()

    # --- Botões ------------------------------------------------------------------------
    def imagem_inteira():
        """Leva os 4 cantos aos cantos da imagem."""
        pontos[:] = [[0, 0], [imagem_pil.width - 1, 0],
                     [imagem_pil.width - 1, imagem_pil.height - 1], [0, imagem_pil.height - 1]]
        redesenhar()

    def aplicar():
        """Valida os cantos, fecha a janela e entrega-os já na escala original."""
        novos = np.array(pontos, np.float32)
        # Cantos cruzados não formam um quadrilátero convexo.
        if not cv2.isContourConvex(ordenar_cantos(novos).reshape(-1, 1, 2).astype(np.int32)):
            messagebox.showwarning("Cantos inválidos", "Os cantos se cruzaram. "
                                   "Arraste-os para formar um quadrilátero.", parent=janela)
            return
        janela.destroy()
        ao_aplicar(novos / escala)

    botoes = tk.Frame(janela, bg=COR_CARTAO)
    botoes.pack(fill="x", padx=16, pady=12)
    criar_botao(botoes, "Aplicar", aplicar, COR_PRIMARIA, COR_TEXTO).pack(side="right")
    criar_botao(botoes, "Cancelar", janela.destroy, COR_DESATIVADA, COR_TEXTO).pack(
        side="right", padx=8)
    criar_botao(botoes, "Imagem inteira", imagem_inteira, COR_DESATIVADA, COR_TEXTO).pack(
        side="left")
    janela.bind("<Escape>", lambda _e: janela.destroy())
    janela.bind("<Return>", lambda _e: aplicar())
    janela.grab_set()  # janela modal: bloqueia a principal até fechar
    return janela
