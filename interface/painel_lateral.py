"""Barra lateral esquerda: arquivo, câmera, girar, status e avaliação do OCR."""

import tkinter as tk
from tkinter import ttk

import cv2

from interface.tema import (COR_BARRA, COR_BORDA, COR_CARTAO, COR_PRIMARIA, COR_SECUNDARIA,
                            COR_SUAVE, COR_TEXTO)
from interface.widgets import criar_botao, definir_estado_botao

# Giros da imagem de entrada: (rótulo do botão, código do cv2.rotate, texto do status).
GIROS = (
    ("90° esq.", cv2.ROTATE_90_COUNTERCLOCKWISE, "90° para a esquerda"),
    ("180°", cv2.ROTATE_180, "180°"),
    ("90° dir.", cv2.ROTATE_90_CLOCKWISE, "90° para a direita"),
)


class PainelLateral(tk.Frame):
    """Os controles que dizem respeito à ENTRADA (arquivo/câmera/giro) e ao andamento.

    O painel não sabe o que cada botão faz: recebe as funções (`ao_*`) de quem o
    criou e apenas as chama. Quem manda mudar texto, progresso e estados dos
    botões é a janela principal, pelos métodos públicos abaixo.
    """

    def __init__(self, pai, ao_carregar, ao_alternar_camera, ao_capturar, ao_ajustar_cantos,
                 ao_girar):
        """Monta o painel. As funções `ao_*` são chamadas pelos botões; `ao_girar`
        recebe o código do cv2.rotate e a descrição do giro (para o status).
        """
        super().__init__(pai, bg=COR_BARRA, padx=20, pady=24, width=260)
        self.pack_propagate(False)  # largura fixa, independente do conteúdo

        tk.Label(self, text="NOVO SCAN", bg=COR_BARRA, fg=COR_SECUNDARIA,
                 font=("Arial", 14, "bold")).pack(anchor="w")

        # --- Entrada da imagem: arquivo ou câmera -------------------------------
        self.botao_carregar = criar_botao(self, "+  Escolher arquivo", ao_carregar,
                                          COR_PRIMARIA, COR_TEXTO)
        self.botao_carregar.pack(fill="x", pady=(18, 4))

        self.botao_camera = criar_botao(self, "Câmera ao vivo", ao_alternar_camera,
                                        COR_SECUNDARIA, "white")
        self.botao_camera.pack(fill="x", pady=4)

        self.botao_capturar = criar_botao(self, "Capturar quadro", ao_capturar,
                                          COR_PRIMARIA, COR_TEXTO)
        self.botao_capturar.pack(fill="x", pady=4)

        # --- Correções manuais da imagem de entrada ---------------------------
        self.botao_ajustar = criar_botao(self, "Ajustar cantos", ao_ajustar_cantos,
                                         COR_SECUNDARIA, "white")
        self.botao_ajustar.pack(fill="x", pady=4)

        # Girar a imagem de entrada (ex.: foto de cabeça para baixo). Os três
        # botões dividem a largura igualmente (grade com colunas de mesmo peso).
        tk.Label(self, text="GIRAR IMAGEM", bg=COR_BARRA, fg=COR_SUAVE,
                 font=("Arial", 9, "bold")).pack(anchor="w", pady=(10, 0))
        linha_girar = tk.Frame(self, bg=COR_BARRA)
        linha_girar.pack(fill="x", pady=(4, 4))
        self.botoes_girar = []
        for coluna, (rotulo, codigo, descricao) in enumerate(GIROS):
            botao = criar_botao(linha_girar, rotulo,
                                lambda c=codigo, d=descricao: ao_girar(c, d),
                                COR_SECUNDARIA, "white", padx=0)
            botao.config(font=("Arial", 10, "bold"))
            botao.grid(row=0, column=coluna, sticky="ew", padx=(0 if coluna == 0 else 4, 0))
            linha_girar.grid_columnconfigure(coluna, weight=1, uniform="girar")
            self.botoes_girar.append(botao)

        # --- Status e progresso ---------------------------------------------------
        self._status = tk.StringVar(value="Escolha uma imagem ou inicie a câmera.")
        tk.Label(self, textvariable=self._status, bg=COR_BARRA, fg=COR_TEXTO,
                 wraplength=200, justify="left", font=("Arial", 10)).pack(
                     fill="x", pady=(8, 8))

        # Começa escondida; é exibida só durante o processamento.
        self._progresso = ttk.Progressbar(self, mode="indeterminate")

        # --- Cartão com a avaliação do OCR ----------------------------------------
        cartao = tk.Frame(self, bg=COR_CARTAO, padx=12, pady=12,
                          highlightbackground=COR_BORDA, highlightthickness=1)
        cartao.pack(fill="x", pady=24)

        tk.Label(cartao, text="Avaliação do OCR", bg=COR_CARTAO,
                 fg=COR_SECUNDARIA, font=("Arial", 10, "bold")).pack(anchor="w")
        self._resumo = tk.StringVar(value="Processe a imagem para ver a avaliação.")
        tk.Label(cartao, textvariable=self._resumo, bg=COR_CARTAO,
                 fg=COR_TEXTO, wraplength=200, justify="left",
                 anchor="w").pack(fill="x", pady=(8, 8))
        tk.Label(cartao, text="Estimativa automática.",
                 bg=COR_CARTAO, fg=COR_SUAVE, wraplength=200,
                 justify="left", font=("Arial", 8)).pack(fill="x")

    # -------------------------------------------------------------- texto e progresso

    @property
    def texto_status(self):
        """Texto atual da linha de status."""
        return self._status.get()

    @property
    def texto_resumo(self):
        """Texto atual do cartão "Avaliação do OCR"."""
        return self._resumo.get()

    def definir_status(self, texto):
        """Atualiza a linha de status (abaixo dos botões)."""
        self._status.set(texto)

    def definir_resumo(self, texto):
        """Atualiza o texto do cartão "Avaliação do OCR"."""
        self._resumo.set(texto)

    def iniciar_progresso(self):
        """Mostra e anima a barra de progresso (durante o processamento)."""
        self._progresso.pack(fill="x")
        self._progresso.start(12)

    def encerrar_progresso(self):
        """Para e esconde a barra de progresso."""
        self._progresso.stop()
        self._progresso.pack_forget()

    # ---------------------------------------------------------------------- botões

    def atualizar_botoes(self, ocupado, camera_ativa, tem_imagem):
        """Ativa/desativa os botões conforme o momento do programa.

        ocupado        há um processamento em andamento;
        camera_ativa   a câmera ao vivo está ligada;
        tem_imagem     existe uma imagem carregada (e a câmera NÃO está ligada).
        """
        definir_estado_botao(self.botao_carregar, not ocupado)
        definir_estado_botao(self.botao_camera, not ocupado)
        self.botao_camera.config(text="Fechar câmera" if camera_ativa else "Câmera ao vivo")
        definir_estado_botao(self.botao_capturar, not ocupado and camera_ativa)
        definir_estado_botao(self.botao_ajustar, not ocupado and tem_imagem)
        for botao in self.botoes_girar:
            definir_estado_botao(botao, not ocupado and tem_imagem)
