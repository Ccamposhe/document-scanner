"""A grade de cartões que mostra as imagens de cada etapa."""

import tkinter as tk

from PIL import Image, ImageTk

from interface.conversao import para_rgb
from interface.tema import (COR_BORDA, COR_CARTAO, COR_FUNDO, COR_SUAVE, COR_TEXTO_DESATIVADO,
                            TITULOS)


class VisualizacaoImagens(tk.Frame):
    """Um cartão por etapa (ver `tema.TITULOS`), organizados em grade.

    Cada cartão guarda a imagem em tamanho real e gera a miniatura conforme o
    espaço disponível, então a imagem acompanha o redimensionamento da janela.
    Só os cartões da aba atual ficam visíveis (`exibir_cartoes`).
    """

    COLUNAS_MAXIMAS = 3  # a grade cresce para baixo depois de 3 cartões por linha

    def __init__(self, pai):
        """Cria um cartão (vazio, "Aguardando") para cada etapa de `tema.TITULOS`."""
        super().__init__(pai, bg=COR_FUNDO)
        self._originais = {}   # chave -> imagem PIL em tamanho real
        self._fotos = {}       # chave -> PhotoImage atual (precisa ficar referenciada)
        self._rotulos = {}     # chave -> Label que mostra a imagem (ou "Aguardando")
        self._areas = {}       # chave -> Frame que dá o espaço disponível à imagem
        self._cartoes = {}     # chave -> Frame do cartão completo
        self._agendados = {}   # chave -> id do redimensionamento agendado

        for chave, titulo in TITULOS.items():
            self._cartoes[chave] = self._criar_cartao(titulo, chave)

    # ------------------------------------------------------------------ construção

    def _criar_cartao(self, titulo, chave):
        """Monta um cartão: título em cima e, embaixo, a área da imagem."""
        cartao = tk.Frame(self, bg=COR_CARTAO,
                          highlightbackground=COR_BORDA, highlightthickness=1)

        tk.Label(cartao, text=titulo, bg=COR_CARTAO, fg=COR_SUAVE,
                 font=("Arial", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 0))

        area = tk.Frame(cartao, bg=COR_CARTAO)
        area.pack(fill="both", expand=True, padx=8, pady=8)
        # Sempre que o espaço muda, a miniatura é refeita (de forma agrupada).
        area.bind("<Configure>", lambda _e, c=chave: self._agendar_redimensionamento(c))
        self._areas[chave] = area

        rotulo = tk.Label(area, text="Aguardando", bg=COR_CARTAO, fg=COR_TEXTO_DESATIVADO)
        rotulo.place(relx=0.5, rely=0.5, anchor="center")
        self._rotulos[chave] = rotulo
        return cartao

    # ---------------------------------------------------------------------- layout

    def exibir_cartoes(self, chaves):
        """Mostra só os cartões `chaves`, na ordem dada, em grade de até 3 colunas."""
        for cartao in self._cartoes.values():
            cartao.grid_forget()
        # Zera os pesos antigos para que o novo layout comece do zero.
        for i in range(len(self._cartoes)):
            self.grid_columnconfigure(i, weight=0, uniform="")
            self.grid_rowconfigure(i, weight=0)

        colunas = min(len(chaves), self.COLUNAS_MAXIMAS)
        linhas = (len(chaves) + colunas - 1) // colunas
        for c in range(colunas):
            self.grid_columnconfigure(c, weight=1, uniform="cartoes")
        for r in range(linhas):
            self.grid_rowconfigure(r, weight=1)

        for i, chave in enumerate(chaves):
            self._cartoes[chave].grid(row=i // colunas, column=i % colunas,
                                      padx=6, pady=6, sticky="nsew")

        # Cartões que acabaram de aparecer precisam de miniatura no tamanho novo.
        for chave in chaves:
            self._agendar_redimensionamento(chave)

    # --------------------------------------------------------------------- imagens

    def mostrar(self, chave, array):
        """Exibe `array` (imagem do OpenCV) no cartão `chave`."""
        # Guarda a imagem em tamanho real; a miniatura é gerada conforme o espaço.
        self._originais[chave] = Image.fromarray(para_rgb(array))
        self._redimensionar(chave)

    def limpar(self, chaves, texto):
        """Remove a imagem dos cartões `chaves` e mostra `texto` no lugar."""
        for chave in chaves:
            self._originais.pop(chave, None)
            self._fotos.pop(chave, None)
            self._rotulos[chave].config(image="", text=texto)

    def obter(self, chave):
        """Imagem PIL em tamanho real do cartão, ou None se estiver vazio."""
        return self._originais.get(chave)

    # ------------------------------------------------------------ redimensionamento

    def _agendar_redimensionamento(self, chave):
        """Junta vários eventos de redimensionamento em um só (a janela não trava)."""
        if chave not in self._originais:
            return
        if chave in self._agendados:
            self.after_cancel(self._agendados[chave])
        self._agendados[chave] = self.after(60, lambda: self._redimensionar(chave))

    def _redimensionar(self, chave):
        """Refaz a miniatura do cartão para caber no espaço atual."""
        self._agendados.pop(chave, None)
        original = self._originais.get(chave)
        if original is None:
            return

        area = self._areas[chave]
        largura = area.winfo_width() - 8
        altura = area.winfo_height() - 8
        # Cartão escondido ainda não tem tamanho real: espera o próximo Configure.
        if largura < 20 or altura < 20:
            return

        miniatura = original.copy()
        miniatura.thumbnail((largura, altura))
        self._fotos[chave] = ImageTk.PhotoImage(miniatura)
        self._rotulos[chave].config(image=self._fotos[chave], text="")
