"""Câmera ao vivo com prévia da detecção do documento.

Por que a prévia usa threads
----------------------------
Ler a câmera, detectar a folha e desenhar na tela são tarefas com ritmos
diferentes. Se tudo rodasse na thread da janela, uma leitura lenta (câmera com
pouca luz, câmera que demora a "esquentar") congelaria a interface, e os
quadros ficariam velhos: o OpenCV guarda quadros num buffer e, se o programa
demora a lê-los, entrega imagens antigas. Por isso o trabalho é dividido:

    thread de LEITURA    só lê a câmera, sem parar, guardando o quadro MAIS
                         RECENTE (quadros que ninguém viu são descartados);
    thread de ANÁLISE    pega o quadro mais recente e roda as etapas do
                         processamento em versão leve (detecção da folha, cinza,
                         desfoque, threshold, contorno, documento endireitado e
                         efeito de scanner), no máximo ~8 vezes por segundo;
    thread da JANELA     a cada ~33 ms mostra o quadro mais recente com o
                         contorno da última análise e, quando uma análise
                         termina, atualiza os cartões das etapas. Só ela mexe
                         em widgets (regra do Tkinter).

Resultado: o quadro aparece sempre, em tempo real, e as demais etapas se
atualizam simultaneamente, mesmo que a análise seja lenta, e a janela continua
responsiva. O OCR não roda ao vivo (leva vários segundos por quadro): ele só
roda quando o quadro é capturado.
"""

import tkinter as tk
from threading import Event, Lock, Thread

import cv2

from nucleo.analise_rapida import analisar_quadro
from nucleo.configuracao import INDICE_CAMERA, INTERVALO_ANALISE_S, INTERVALO_EXIBICAO_MS


class ControladorCamera:
    """Abre a câmera e avisa a interface do que aparece nela.

    O controlador não mexe em widgets. Funções recebidas na criação (sempre
    chamadas na thread da janela):
        ao_quadro(quadro, cantos)
            quando há um quadro novo para mostrar. `cantos` são os da última
            análise (ou None se nenhuma folha foi achada ainda).
        ao_etapas(etapas)
            quando uma análise termina: dicionário com a imagem de cada etapa
            ("contorno", "cinza", "desfocada", "binaria", "digitalizada",
            "pb"). "digitalizada" e "pb" são None se nenhuma folha foi achada.
        ao_falha(titulo, mensagem)
            a câmera parou de funcionar DURANTE o uso (não enviou imagem, a
            análise falhou ou a própria prévia deu erro). Já foi encerrada
            quando esta função é chamada. Falhas ao ABRIR a câmera são
            devolvidas por `abrir`.

    A análise usa versões leves das etapas (ver nucleo/analise_rapida.py); o
    processamento completo, com OCR, roda quando o quadro é capturado.
    """

    def __init__(self, raiz, ao_quadro, ao_etapas, ao_falha):
        """`raiz` é a janela do Tkinter (usada para agendar a atualização da tela)."""
        self._raiz = raiz
        self._ao_quadro = ao_quadro
        self._ao_etapas = ao_etapas
        self._ao_falha = ao_falha

        self._camera = None          # cv2.VideoCapture (None = desligada)
        self._agendamento = None     # id da próxima atualização de tela em raiz.after
        self._parar = Event()        # pedido de encerramento das threads
        self._threads = []

        # Dados compartilhados entre as threads (sempre acessados com _trava).
        self._trava = Lock()
        self._quadro = None          # quadro mais recente lido da câmera
        self._numero_quadro = 0      # conta quadros lidos (para saber se há novidade)
        self._novo_quadro = Event()  # sinaliza à detecção que há quadro novo
        self._resultado = None       # (id, cantos|None, etapas) da última análise
        self._falha = None           # (titulo, mensagem) se algo deu errado numa thread

        # Controle da thread da janela: o que ela já mostrou.
        self._ultimo_quadro_exibido = 0
        self._ultimo_resultado_avisado = 0

    @property
    def ativa(self):
        """True se a câmera está ligada."""
        return self._camera is not None

    @property
    def quadro_atual(self):
        """Cópia do quadro mais recente (para capturar), ou None se ainda não chegou."""
        with self._trava:
            return None if self._quadro is None else self._quadro.copy()

    # --------------------------------------------------------------- ligar/desligar

    def abrir(self):
        """Tenta abrir a câmera (sem iniciar a prévia).

        Retorna None se conseguiu, ou o texto do erro (para a interface exibir)
        se a câmera não pôde ser acessada.
        """
        camera = cv2.VideoCapture(INDICE_CAMERA)
        if not camera.isOpened():
            camera.release()
            return ("Não foi possível acessar a câmera. Verifique se ela está conectada, "
                    "se as permissões estão habilitadas e se outro programa não está "
                    "usando-a.")

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._camera = camera
        return None

    def iniciar_previa(self):
        """Inicia as threads de leitura e de análise e o ciclo de atualização da tela."""
        with self._trava:
            self._quadro = None
            self._numero_quadro = 0
            self._resultado = None
            self._falha = None
        self._novo_quadro.clear()
        self._parar.clear()
        self._ultimo_quadro_exibido = 0
        self._ultimo_resultado_avisado = 0

        self._threads = [
            Thread(target=self._ler_continuamente, args=(self._camera,), daemon=True),
            Thread(target=self._analisar_continuamente, daemon=True),
        ]
        for thread in self._threads:
            thread.start()
        self._atualizar_tela()

    def parar(self):
        """Encerra as threads e libera a câmera. Pode ser chamado várias vezes."""
        if self._agendamento is not None:
            try:
                self._raiz.after_cancel(self._agendamento)
            except tk.TclError:  # id já expirado ou janela fechando: não há o que cancelar
                pass
            self._agendamento = None

        self._parar.set()
        self._novo_quadro.set()   # acorda a thread de análise para ela perceber o pedido
        for thread in self._threads:
            thread.join(timeout=2.0)
        self._threads = []

        self._camera = None  # a thread de leitura já liberou o dispositivo ao terminar
        with self._trava:
            self._quadro = None

    # ----------------------------------------------------- thread de leitura (câmera)

    def _ler_continuamente(self, camera):
        """Lê a câmera sem parar e guarda só o quadro mais recente.

        Ler o tempo todo esvazia o buffer do driver, então o quadro guardado é
        sempre "de agora" (sem atraso). Esta thread é a dona da câmera e a
        libera ao terminar.
        """
        try:
            while not self._parar.is_set():
                sucesso, quadro = camera.read()
                if not sucesso or quadro is None:
                    self._registrar_falha("Falha na câmera",
                                          "A câmera foi aberta, mas não foi possível "
                                          "receber a imagem.")
                    return
                with self._trava:
                    self._quadro = quadro
                    self._numero_quadro += 1
                self._novo_quadro.set()
        finally:
            camera.release()

    # ---------------------------------------------------- thread de análise (etapas)

    def _analisar_continuamente(self):
        """Roda as etapas no quadro mais recente, no máximo ~8 vezes por segundo."""
        identificador = 0
        ultimo_analisado = 0
        while not self._parar.is_set():
            # Dorme até haver um quadro novo (acorda sozinha de vez em quando).
            self._novo_quadro.wait(timeout=0.5)
            self._novo_quadro.clear()
            if self._parar.is_set():
                return
            with self._trava:
                quadro, numero = self._quadro, self._numero_quadro
            if quadro is None or numero == ultimo_analisado:
                continue
            ultimo_analisado = numero

            try:
                cantos, etapas = analisar_quadro(quadro)
            except Exception as erro:
                self._registrar_falha("Erro no processamento da câmera",
                                      f"Não foi possível processar o quadro recebido:\n{erro}")
                return

            identificador += 1
            with self._trava:
                self._resultado = (identificador, cantos, etapas)

            # Limita a taxa de análises: poupa processador sem prejudicar a tela.
            self._parar.wait(INTERVALO_ANALISE_S)

    def _registrar_falha(self, titulo, mensagem):
        """Uma thread de trabalho avisa a thread da janela de que algo falhou."""
        with self._trava:
            if self._falha is None:
                self._falha = (titulo, mensagem)

    # ------------------------------------------------- ciclo da thread da janela (tela)

    def _atualizar_tela(self):
        """Mostra o quadro mais recente e avisa a interface (roda na thread da janela)."""
        self._agendamento = None
        if self._camera is None:
            return

        try:
            with self._trava:
                falha = self._falha
                quadro, numero = self._quadro, self._numero_quadro
                resultado = self._resultado

            if falha is not None:
                self.parar()
                self._ao_falha(*falha)
                return

            # Cantos da última análise concluída (None enquanto nenhuma achou a folha).
            cantos = resultado[1] if resultado is not None else None

            # Análise nova: atualiza os cartões das etapas.
            if resultado is not None and resultado[0] != self._ultimo_resultado_avisado:
                self._ultimo_resultado_avisado = resultado[0]
                self._ao_etapas(resultado[2])

            # Quadro novo: troca a imagem da tela. Sem novidade, não gasta processamento.
            if quadro is not None and numero != self._ultimo_quadro_exibido:
                self._ultimo_quadro_exibido = numero
                self._ao_quadro(quadro, cantos)
        except Exception as erro:
            # Qualquer erro na prévia encerra a câmera COM aviso (em vez de a
            # imagem congelar em silêncio, que parece "a câmera não funciona").
            self.parar()
            self._ao_falha("Erro na prévia da câmera",
                           f"Não foi possível atualizar a imagem da câmera:\n{erro}")
            return

        # O intervalo é contado após o trabalho, então atualizações não se acumulam.
        self._agendamento = self._raiz.after(INTERVALO_EXIBICAO_MS, self._atualizar_tela)
