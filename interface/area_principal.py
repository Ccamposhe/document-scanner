"""Área principal: abas, grade de imagens, botões de ação e caixa de texto."""

import tkinter as tk

from interface.tema import (COR_CARTAO, COR_FUNDO, COR_PRIMARIA, COR_SECUNDARIA, COR_SUAVE,
                            COR_TEXTO, MODOS)
from interface.visualizacao import VisualizacaoImagens
from interface.widgets import criar_botao, definir_estado_botao


class AreaPrincipal(tk.Frame):
    """Tudo o que fica à direita da barra lateral.

    De cima para baixo (linhas da grade):
        0  título "VISUALIZAÇÃO"
        1  abas (escolhem quais etapas aparecem)
        2  grade de imagens (VisualizacaoImagens)
        3  botões de ação (Processar, Salvar...)
        4  texto extraído (editável)

    Assim como o painel lateral, recebe as funções `ao_*` de quem a criou.
    """

    def __init__(self, pai, ao_processar, ao_salvar, ao_salvar_texto, ao_texto_editado):
        """Monta a área. As funções `ao_*` são chamadas quando o usuário:
        clica em Processar, em Salvar imagem (recebe "cor" ou "pb"), em Salvar
        texto, ou digita na caixa de texto.
        """
        super().__init__(pai, bg=COR_FUNDO, padx=24, pady=20)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=4)   # imagens: ocupam a maior parte
        self.grid_rowconfigure(4, weight=1)   # texto extraído: o resto

        tk.Label(self, text="VISUALIZAÇÃO", bg=COR_FUNDO, fg=COR_SUAVE,
                 font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w")

        # --- Abas: escolhem quais etapas aparecem ------------------------------
        abas = tk.Frame(self, bg=COR_FUNDO)
        abas.grid(row=1, column=0, sticky="w", pady=(6, 16))
        self._botoes_modo = {}
        for modo in MODOS:
            botao = tk.Button(
                abas, text=modo.rotulo, relief="flat", bd=0, font=("Arial", 10, "bold"),
                padx=16, pady=8, cursor="hand2",
                command=lambda c=modo.chave: self.selecionar_modo(c))
            botao.pack(side="left", padx=(0, 8))
            self._botoes_modo[modo.chave] = botao

        # --- Grade de imagens (os cartões que aparecem dependem da aba) ---------
        self.visualizacao = VisualizacaoImagens(self)
        self.visualizacao.grid(row=2, column=0, sticky="nsew")

        # --- Ações abaixo das imagens ---------------------------------------------
        acoes = tk.Frame(self, bg=COR_FUNDO)
        acoes.grid(row=3, column=0, pady=18)

        self.botao_processar = criar_botao(acoes, "Processar", ao_processar,
                                           COR_PRIMARIA, COR_TEXTO, padx=30)
        self.botao_processar.pack(side="left", padx=6)

        # Os botões de salvar só aparecem nas abas que mostram o resultado final.
        self._frame_salvar = tk.Frame(acoes, bg=COR_FUNDO)
        self._frame_salvar.pack(side="left")

        self.botao_salvar = criar_botao(self._frame_salvar, "Salvar imagem (cor)",
                                        lambda: ao_salvar("cor"), COR_SECUNDARIA, "white")
        self.botao_salvar.pack(side="left", padx=6)

        self.botao_salvar_pb = criar_botao(self._frame_salvar, "Salvar imagem (P&B)",
                                           lambda: ao_salvar("pb"), COR_SECUNDARIA, "white")
        self.botao_salvar_pb.pack(side="left", padx=6)

        self.botao_salvar_texto = criar_botao(self._frame_salvar, "Salvar texto (.txt)",
                                              ao_salvar_texto, COR_SECUNDARIA, "white")
        self.botao_salvar_texto.pack(side="left", padx=6)

        # --- Texto extraído (aparece nas abas que o mostram) e editável ------------
        self._quadro_texto = tk.LabelFrame(self, text="Texto extraído", bg=COR_FUNDO,
                                           fg=COR_SECUNDARIA, font=("Arial", 10, "bold"),
                                           padx=8, pady=8)
        self._quadro_texto.grid(row=4, column=0, sticky="nsew")

        barra_rolagem = tk.Scrollbar(self._quadro_texto)
        barra_rolagem.pack(side="right", fill="y")
        self._caixa_texto = tk.Text(
            self._quadro_texto, wrap="word", height=4,
            bg=COR_CARTAO, fg=COR_TEXTO, relief="flat",
            padx=10, pady=10, undo=True, yscrollcommand=barra_rolagem.set)
        self._caixa_texto.pack(side="left", fill="both", expand=True)
        barra_rolagem.config(command=self._caixa_texto.yview)
        # Ao digitar, o botão "Salvar texto" precisa saber se ainda há texto.
        self._caixa_texto.bind("<KeyRelease>", lambda _e: ao_texto_editado())

        self._modo = MODOS[0].chave
        self.selecionar_modo(self._modo)

    # ------------------------------------------------------------------------ abas

    def selecionar_modo(self, chave):
        """Troca a aba: destaca o botão escolhido e refaz o layout."""
        self._modo = chave
        for chave_modo, botao in self._botoes_modo.items():
            ativa = chave_modo == chave
            botao.config(
                bg=COR_SECUNDARIA if ativa else COR_CARTAO,
                fg="white" if ativa else COR_SECUNDARIA,
                activebackground=COR_SECUNDARIA if ativa else COR_CARTAO,
                activeforeground="white" if ativa else COR_SECUNDARIA)
        self._atualizar_layout()

    def _modo_atual(self):
        """Configuração (cartões, texto?, salvar?) da aba selecionada."""
        for modo in MODOS:
            if modo.chave == self._modo:
                return modo
        return MODOS[0]

    def _atualizar_layout(self):
        """Mostra os cartões da aba e esconde/mostra a caixa de texto e o "Salvar"."""
        modo = self._modo_atual()
        self.visualizacao.exibir_cartoes(modo.cartoes)

        if modo.mostra_texto:
            self._quadro_texto.grid()
        else:
            self._quadro_texto.grid_remove()

        if modo.mostra_salvar:
            self._frame_salvar.pack(side="left")
        else:
            self._frame_salvar.pack_forget()

    # ------------------------------------------------------------ imagens e texto

    def mostrar(self, chave, array):
        """Exibe uma imagem no cartão `chave`."""
        self.visualizacao.mostrar(chave, array)

    def limpar_imagens(self, chaves, texto):
        """Esvazia os cartões `chaves`, mostrando `texto` no lugar da imagem."""
        self.visualizacao.limpar(chaves, texto)

    def mostrar_texto(self, texto):
        """Substitui o conteúdo da caixa de texto extraído."""
        self._caixa_texto.delete("1.0", "end")
        self._caixa_texto.insert("1.0", texto)

    def texto_atual(self):
        """Conteúdo da caixa, já com as correções feitas pelo usuário."""
        return self._caixa_texto.get("1.0", "end-1c")

    # ---------------------------------------------------------------------- botões

    def atualizar_botoes(self, ocupado, tem_imagem, tem_digitalizada, tem_pb):
        """Ativa/desativa Processar e os botões de salvar conforme o momento."""
        definir_estado_botao(self.botao_processar, not ocupado and tem_imagem)
        definir_estado_botao(self.botao_salvar, not ocupado and tem_digitalizada)
        definir_estado_botao(self.botao_salvar_pb, not ocupado and tem_pb)
        definir_estado_botao(self.botao_salvar_texto,
                             not ocupado and bool(self.texto_atual().strip()))
