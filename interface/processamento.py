"""Processamento do documento em segundo plano.

Detecção, correção de perspectiva, efeito de scanner e OCR podem levar alguns
segundos. Se rodassem na thread da interface, a janela travaria. Por isso o
trabalho roda numa thread separada, e os resultados voltam por uma fila
(`Queue`) que a interface consulta de tempos em tempos.

Regra do Tkinter: só a thread principal pode mexer nos widgets. A thread de
trabalho NUNCA chama a interface; ela só coloca mensagens na fila. É o método
`_acompanhar`, executado pela thread principal, que lê a fila e chama os
`ao_*` recebidos.
"""

from queue import Empty, Queue
from threading import Thread

from nucleo.deteccao import detectar_documento
from nucleo.geometria import transformar_perspectiva
from nucleo.imagem import desenhar_contorno, efeito_scanner, preprocessamento
from nucleo.ocr import extrair_texto

# De quanto em quanto tempo (ms) a fila é consultada.
INTERVALO_CONSULTA_MS = 80


class ProcessadorDocumento:
    """Roda o fluxo completo de um documento e avisa a interface a cada etapa.

    Funções recebidas na criação (todas chamadas na thread principal):
        ao_etapa(texto)                            texto de andamento
        ao_preprocessamento(cinza, desfocada, binaria)   imagens do pré-processamento
        ao_deteccao(cantos, encontrou, contorno)   resultado da detecção
        ao_digitalizada(cor, pb)                   documento corrigido (cor e P&B)
        ao_concluir(resultado)                     OCR pronto (dicionário de extrair_texto)
        ao_erro(mensagem)                          algo falhou; o processamento terminou
    """

    def __init__(self, raiz, ao_etapa, ao_preprocessamento, ao_deteccao, ao_digitalizada,
                 ao_concluir, ao_erro):
        """Guarda as funções de aviso (veja a classe) e prepara a fila de mensagens."""
        self._raiz = raiz
        self._ao_etapa = ao_etapa
        self._ao_preprocessamento = ao_preprocessamento
        self._ao_deteccao = ao_deteccao
        self._ao_digitalizada = ao_digitalizada
        self._ao_concluir = ao_concluir
        self._ao_erro = ao_erro
        self._fila = Queue()   # mensagens (tipo, dados) da thread de trabalho
        self.ocupado = False   # True enquanto há um processamento em andamento

    def iniciar(self, imagem, cantos_manuais=None):
        """Começa o processamento de `imagem` em segundo plano.

        Com `cantos_manuais` (escolhidos em "Ajustar cantos"), a detecção
        automática é pulada e esses cantos são usados.
        """
        self.ocupado = True
        manual = cantos_manuais is not None
        cantos_entrada = cantos_manuais.copy() if manual else None

        def trabalho():
            """Executado na thread separada: só calcula e coloca mensagens na fila."""
            try:
                # 1) Pré-processamento (as imagens didáticas).
                cinza, desfocada, binaria = preprocessamento(imagem)
                self._fila.put(("pre", (cinza, desfocada, binaria)))

                # 2) Detecção do documento (ou cantos informados à mão).
                if manual:
                    cantos, encontrou = cantos_entrada, True
                else:
                    self._fila.put(("etapa", "Detectando o documento…"))
                    cantos, encontrou = detectar_documento(imagem)
                contorno = desenhar_contorno(imagem, cantos) if encontrou else imagem
                self._fila.put(("deteccao", (cantos, encontrou, contorno)))

                # 3) Correção de perspectiva e efeito de scanner.
                digitalizada = transformar_perspectiva(imagem, cantos)
                if digitalizada is None:
                    raise ValueError("Não foi possível aplicar a transformação de perspectiva.")
                self._fila.put(("digitalizada", (digitalizada, efeito_scanner(digitalizada))))

                # 4) OCR sobre a versão colorida (o P&B forte piorou a leitura).
                resultado = extrair_texto(
                    digitalizada,
                    progresso=lambda etapa, _img: self._fila.put(("etapa", etapa)),
                    retornar_detalhes=True,
                )
                self._fila.put(("resultado", resultado))
            except Exception as erro:
                self._fila.put(("erro", str(erro)))

        Thread(target=trabalho, daemon=True).start()
        self._raiz.after(INTERVALO_CONSULTA_MS, self._acompanhar)

    def _acompanhar(self):
        """Lê a fila (na thread principal) e repassa cada mensagem à interface."""
        try:
            while True:
                tipo, dados = self._fila.get_nowait()

                if tipo == "etapa":
                    self._ao_etapa(dados)
                    continue
                if tipo == "pre":
                    self._ao_preprocessamento(*dados)
                    continue
                if tipo == "deteccao":
                    self._ao_deteccao(*dados)
                    continue
                if tipo == "digitalizada":
                    self._ao_digitalizada(*dados)
                    continue

                # Daqui em diante o processamento terminou (resultado ou erro).
                self.ocupado = False
                if tipo == "erro":
                    self._ao_erro(dados)
                else:
                    self._ao_concluir(dados)
                return
        except Empty:
            # Fila vazia: se ainda há trabalho, consulta de novo daqui a pouco.
            if self.ocupado:
                self._raiz.after(INTERVALO_CONSULTA_MS, self._acompanhar)
