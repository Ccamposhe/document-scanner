"""Janela principal: liga as peças da interface e conduz o fluxo do programa.

Quem faz o quê:
    Estado               guarda os dados do documento atual;
    PainelLateral        barra da esquerda (entrada, girar, status);
    AreaPrincipal        abas, imagens, botões de ação e texto;
    ControladorCamera    câmera ao vivo;
    ProcessadorDocumento processamento em segundo plano.

Esta classe NÃO desenha nada nem calcula nada de imagem: ela recebe os avisos
das peças acima (cliques, quadros da câmera, etapas concluídas) e decide o que
atualizar. É o único lugar que conhece todas as peças.

Fluxo típico:
    carregar() ou capturar_quadro()  ->  processar()  ->  (etapas chegam pelos _ao_*)
    ->  salvar() / salvar_texto()
"""

import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
from PIL import Image

from interface.area_principal import AreaPrincipal
from interface.camera import ControladorCamera
from interface.conversao import para_rgb
from interface.dialogo_cantos import abrir_dialogo_cantos
from interface.estado import Estado
from interface.painel_lateral import PainelLateral
from interface.processamento import ProcessadorDocumento
from interface.tema import CARTOES_PROCESSO, COR_FUNDO, aplicar_tema_ttk
from nucleo.imagem import desenhar_contorno
from nucleo.ocr import CONFIANCA_MINIMA


class AplicativoScanner:
    """O aplicativo: cria a janela e coordena todas as peças."""

    def __init__(self, raiz):
        """Configura a janela `raiz` e cria todas as peças da interface."""
        self.raiz = raiz
        self.raiz.title("Scanner de Documentos")
        self.raiz.geometry("1280x820")
        self.raiz.minsize(1000, 700)
        self.raiz.configure(bg=COR_FUNDO)
        self.raiz.protocol("WM_DELETE_WINDOW", self.fechar)
        aplicar_tema_ttk(self.raiz)

        self.estado = Estado()

        # Interface: barra lateral à esquerda, área principal ocupando o resto.
        self.painel = PainelLateral(
            self.raiz,
            ao_carregar=self.carregar,
            ao_alternar_camera=self.alternar_camera,
            ao_capturar=self.capturar_quadro,
            ao_ajustar_cantos=self.ajustar_cantos,
            ao_girar=self.girar,
        )
        self.painel.pack(side="left", fill="y")

        self.area = AreaPrincipal(
            self.raiz,
            ao_processar=self.processar,
            ao_salvar=self.salvar,
            ao_salvar_texto=self.salvar_texto,
            ao_texto_editado=self._atualizar_botoes,
        )
        self.area.pack(side="left", fill="both", expand=True)

        # Peças que trabalham "por trás" e avisam por funções.
        self.camera = ControladorCamera(
            self.raiz,
            ao_quadro=self._ao_quadro_camera,
            ao_etapas=self._ao_etapas_camera,
            ao_falha=self._ao_falha_camera,
        )
        self.processador = ProcessadorDocumento(
            self.raiz,
            ao_etapa=self.painel.definir_status,
            ao_preprocessamento=self._ao_preprocessamento,
            ao_deteccao=self._ao_deteccao,
            ao_digitalizada=self._ao_digitalizada,
            ao_concluir=self._ao_concluir,
            ao_erro=self._ao_erro,
        )

        self._atualizar_botoes()

    # ------------------------------------------------------------ estado dos botões

    def _atualizar_botoes(self):
        """Ativa/desativa todos os botões conforme o momento do programa.

        Três fatos decidem tudo: se há processamento em andamento, se a câmera
        está ligada e se há imagem carregada (a câmera ligada não conta, porque
        a imagem é só a prévia).
        """
        ocupado = self.processador.ocupado
        camera_ativa = self.camera.ativa
        tem_imagem = self.estado.imagem is not None and not camera_ativa

        self.painel.atualizar_botoes(ocupado, camera_ativa, tem_imagem)
        self.area.atualizar_botoes(
            ocupado, tem_imagem,
            tem_digitalizada=self.estado.digitalizada is not None,
            tem_pb=self.estado.digitalizada_pb is not None,
        )

    # --------------------------------------------------------------- câmera ao vivo

    def alternar_camera(self):
        """Botão "Câmera ao vivo" / "Fechar câmera"."""
        if self.camera.ativa:
            self.parar_camera()
        else:
            self.iniciar_camera()

    def iniciar_camera(self):
        """Liga a câmera e começa a prévia (descartando o resultado anterior)."""
        if self.processador.ocupado:
            return
        erro = self.camera.abrir()
        if erro is not None:
            messagebox.showerror("Câmera indisponível", erro)
            return

        # Ao entrar no modo câmera, descarta o resultado anterior.
        self.estado.imagem = None
        self.estado.nome_arquivo = ""
        self._limpar_resultados()
        self.area.limpar_imagens(("original",), "Inicializando câmera…")

        self.painel.definir_status("Câmera iniciada. Posicione a folha no enquadramento.")
        self._atualizar_botoes()
        self.camera.iniciar_previa()

    def parar_camera(self, atualizar_status=True):
        """Desliga a câmera."""
        self.camera.parar()
        if atualizar_status:
            self.painel.definir_status("Câmera encerrada. Escolha uma imagem ou inicie a câmera.")
        self._atualizar_botoes()

    def capturar_quadro(self):
        """Congela o quadro atual da câmera e o processa."""
        quadro = self.camera.quadro_atual  # já é uma cópia
        if not self.camera.ativa or quadro is None:
            return

        self.parar_camera(atualizar_status=False)

        self.estado.imagem = quadro
        self.estado.nome_arquivo = time.strftime("captura_%Y%m%d_%H%M%S.jpg")
        # A prévia ao vivo usa só as passadas rápidas. No quadro congelado a
        # detecção completa roda (inclusive a de baixo contraste); se ainda assim
        # falhar, dá para marcar a folha com Ajustar cantos.
        self._iniciar_processamento(None)

    def _ao_quadro_camera(self, quadro, cantos):
        """Chegou um quadro novo: mostra a imagem, com o contorno se a folha foi achada."""
        if cantos is not None:
            self.area.mostrar("original", desenhar_contorno(quadro, cantos))
        else:
            self.area.mostrar("original", quadro)

    def _ao_etapas_camera(self, etapas):
        """Uma análise terminou: atualiza os cartões das etapas e a dica de status.

        Só os cartões da aba atual são atualizados (os escondidos não gastam
        processamento). Sem folha, as etapas do documento mostram o aviso.
        """
        encontrou = etapas["digitalizada"] is not None
        if encontrou:
            self.painel.definir_status("Documento detectado. Capture o quadro para digitalizar.")
        else:
            self.painel.definir_status("Aponte para uma folha com os quatro cantos visíveis.")

        visiveis = self.area.cartoes_visiveis()
        for chave in ("contorno", "cinza", "desfocada", "binaria", "digitalizada", "pb"):
            if chave not in visiveis:
                continue
            if etapas[chave] is not None:
                self.area.mostrar(chave, etapas[chave])
            else:
                self.area.limpar_imagens((chave,), "Documento não detectado")

    def _ao_falha_camera(self, titulo, mensagem):
        """A câmera não abriu ou falhou durante o uso (já está desligada)."""
        self.parar_camera()  # garante status e botões coerentes
        messagebox.showerror(titulo, mensagem)

    def fechar(self):
        """Fecha a janela, desligando antes a câmera."""
        self.parar_camera(atualizar_status=False)
        self.raiz.destroy()

    # ------------------------------------------------------------ entrada da imagem

    def carregar(self):
        """Botão "Escolher arquivo": abre uma imagem do disco."""
        if self.processador.ocupado:
            return
        if self.camera.ativa:
            self.parar_camera(atualizar_status=False)

        caminho = filedialog.askopenfilename(
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                       ("Todos os arquivos", "*.*")]
        )
        if not caminho:
            return

        imagem = cv2.imread(caminho)
        if imagem is None:
            messagebox.showerror("Erro", "Não foi possível abrir essa imagem.")
            return

        self.estado.imagem = imagem
        self.estado.nome_arquivo = os.path.basename(caminho)
        self._limpar_resultados()
        self.area.mostrar("original", imagem)
        self.painel.definir_status("Imagem carregada. Clique em Processar.")
        self._atualizar_botoes()

    def girar(self, codigo, descricao):
        """Gira a imagem de entrada (ex.: foto de cabeça para baixo).

        O giro é feito na imagem original, antes da detecção, e é sem perdas
        (múltiplos de 90°). Os resultados anteriores deixam de valer, então são
        limpos; clique em Processar para analisar a imagem na nova orientação.
        """
        if (self.estado.imagem is None or self.processador.ocupado
                or self.camera.ativa):
            return
        self.estado.imagem = cv2.rotate(self.estado.imagem, codigo)
        self._limpar_resultados()
        self.area.mostrar("original", self.estado.imagem)
        self.painel.definir_status(f"Imagem girada {descricao}. Clique em Processar.")
        self._atualizar_botoes()

    def ajustar_cantos(self):
        """Botão "Ajustar cantos": abre a janela para arrastar os 4 cantos da folha."""
        if (self.estado.imagem is None or self.processador.ocupado
                or self.camera.ativa):
            return
        abrir_dialogo_cantos(self.raiz, self.estado.imagem, self.estado.cantos,
                             ao_aplicar=self._iniciar_processamento)

    # ----------------------------------------------------------------- processamento

    def processar(self):
        """Botão "Processar": detecta o documento e extrai o texto."""
        if self.estado.imagem is None or self.processador.ocupado:
            return
        self._iniciar_processamento(None)

    def _limpar_resultados(self):
        """Esquece tudo que foi calculado a partir da imagem (a imagem fica)."""
        self.estado.limpar_resultados()
        self.painel.definir_resumo("Processe a imagem para ver a avaliação.")
        self.area.mostrar_texto("")
        self.area.limpar_imagens(CARTOES_PROCESSO, "Aguardando")
        self._atualizar_botoes()

    def _iniciar_processamento(self, cantos_manuais=None):
        """Prepara a tela e dispara o processamento em segundo plano.

        Com `cantos_manuais` (vindos de "Ajustar cantos") a detecção automática
        é pulada. Os resultados chegam depois pelos métodos `_ao_*` abaixo.
        """
        if self.estado.imagem is None or self.processador.ocupado:
            return

        self._limpar_resultados()
        self.area.mostrar("original", self.estado.imagem)
        self.painel.definir_status("Pré-processando a imagem…")
        self.painel.iniciar_progresso()
        self.processador.iniciar(self.estado.imagem.copy(), cantos_manuais)
        self._atualizar_botoes()  # já com o processador ocupado

    def _ao_preprocessamento(self, cinza, desfocada, binaria):
        """Chegaram as imagens do pré-processamento."""
        self.area.mostrar("cinza", cinza)
        self.area.mostrar("desfocada", desfocada)
        self.area.mostrar("binaria", binaria)

    def _ao_deteccao(self, cantos, encontrou, contorno):
        """Chegou o resultado da detecção do documento."""
        self.estado.cantos = cantos
        self.estado.documento_encontrado = encontrou
        self.area.mostrar("contorno", contorno)
        if not encontrou:
            self.painel.definir_status("Documento não detectado: a imagem inteira foi "
                                       "usada. Use Ajustar cantos.")

    def _ao_digitalizada(self, cor, pb):
        """Chegou o documento corrigido (colorido e com efeito de scanner)."""
        self.estado.digitalizada, self.estado.digitalizada_pb = cor, pb
        self.area.mostrar("digitalizada", cor)
        self.area.mostrar("pb", pb)

    def _ao_concluir(self, resultado):
        """O OCR terminou: mostra o texto, a avaliação e a mensagem final."""
        self.painel.encerrar_progresso()

        self.estado.texto_ocr = resultado["texto"]
        self._mostrar_avaliacao(resultado)
        self.area.mostrar_texto(self.estado.texto_ocr)
        self._atualizar_botoes()

        if not self.estado.texto_ocr.strip():
            self.painel.definir_status("Nenhum texto encontrado.")
            messagebox.showinfo("OCR", "Nenhum texto foi encontrado.")
        elif self.estado.documento_encontrado:
            self.painel.definir_status("Pronto. Você pode corrigir o texto e salvar.")
        else:
            self.painel.definir_status("Pronto, mas o documento não foi detectado com "
                                       "segurança. Confira com Ajustar cantos.")

    def _ao_erro(self, mensagem):
        """O processamento falhou em alguma etapa."""
        self.painel.encerrar_progresso()
        self.painel.definir_status("Falha ao processar. Confira a mensagem.")
        self.painel.definir_resumo("Avaliação indisponível.")
        self._atualizar_botoes()
        messagebox.showerror("Erro", mensagem)

    def _mostrar_avaliacao(self, resultado):
        """Escreve o cartão "Avaliação do OCR" com os números do resultado."""
        confianca = f"{resultado['confianca_media']:.1f}".replace(".", ",")
        self.painel.definir_resumo(
            f"Letras e números extraídos: {resultado['caracteres_total']}\n\n"
            f"Em palavras com confiança ≥ {CONFIANCA_MINIMA}: "
            f"{resultado['caracteres_confiaveis']}\n\n"
            f"Confiança média das palavras: {confianca} / 100"
        )

    # ------------------------------------------------------------------------ salvar

    def salvar_texto(self):
        """Salva o texto da caixa (com as correções do usuário) em um .txt."""
        texto = self.area.texto_atual()
        if not texto.strip():
            messagebox.showwarning("Aviso", "Não há texto para salvar.")
            return

        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo de texto", "*.txt")],
            initialfile="texto_extraido.txt",
        )
        if not caminho:
            return

        try:
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write(texto)
        except OSError as erro:
            messagebox.showerror("Erro", f"Não foi possível salvar o texto:\n{erro}")
            return

        messagebox.showinfo("Pronto", f"Texto salvo em:\n{caminho}")

    def salvar(self, versao="cor"):
        """Salva o documento digitalizado em PNG ("cor" ou "pb")."""
        imagem = self.estado.digitalizada if versao == "cor" else self.estado.digitalizada_pb
        if imagem is None:
            messagebox.showwarning("Aviso", "Processe a imagem antes de salvar.")
            return

        caminho = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialfile=f"scan_{'colorido' if versao == 'cor' else 'pb'}.png",
        )
        if not caminho:
            return

        Image.fromarray(para_rgb(imagem)).save(caminho, "PNG")
        messagebox.showinfo("Pronto", f"Salvo em:\n{caminho}")
