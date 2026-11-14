"""Câmera ao vivo com prévia da detecção do documento."""

import tkinter as tk

import cv2

from nucleo.configuracao import INDICE_CAMERA
from nucleo.deteccao import detectar_documento
from nucleo.geometria import transformar_perspectiva

# Intervalo entre quadros (ms). É contado DEPOIS do processamento do quadro,
# então quadros lentos não se acumulam em fila.
INTERVALO_QUADROS_MS = 40


class ControladorCamera:
    """Abre a câmera, lê quadros em intervalos e avisa a interface de cada um.

    O controlador não mexe em widgets. Quando algo acontece, chama as funções
    recebidas na criação:
        ao_quadro(quadro, cantos, previa)
            a cada quadro lido. `cantos` e `previa` (o documento já endireitado)
            são None quando nenhum documento foi detectado.
        ao_falha(titulo, mensagem)
            a câmera parou de funcionar DURANTE o uso (não enviou imagem ou o
            processamento do quadro falhou). Já foi encerrada quando esta função
            é chamada. Falhas ao ABRIR a câmera são devolvidas por `abrir`.

    A detecção da prévia usa só as passadas rápidas (baixo_contraste=False) para
    manter a imagem fluida; a análise completa roda quando o quadro é capturado.
    """

    def __init__(self, raiz, ao_quadro, ao_falha):
        """`raiz` é a janela do Tkinter (usada para agendar os próximos quadros)."""
        self._raiz = raiz
        self._ao_quadro = ao_quadro
        self._ao_falha = ao_falha
        self._camera = None          # objeto cv2.VideoCapture (None = desligada)
        self._agendamento = None     # id do próximo quadro agendado em raiz.after
        self.quadro_atual = None     # último quadro lido (para capturar)

    @property
    def ativa(self):
        """True se a câmera está ligada."""
        return self._camera is not None

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
        self.quadro_atual = None
        return None

    def iniciar_previa(self):
        """Começa o ciclo de leitura de quadros (chame depois de `abrir`)."""
        self._atualizar()

    def parar(self):
        """Cancela o próximo quadro e libera a câmera. Pode ser chamado várias vezes."""
        if self._agendamento is not None:
            try:
                self._raiz.after_cancel(self._agendamento)
            except tk.TclError:  # id já expirado ou janela fechando: não há o que cancelar
                pass
            self._agendamento = None

        camera = self._camera
        self._camera = None
        self.quadro_atual = None
        if camera is not None:
            camera.release()

    # ---------------------------------------------------------------- ciclo de leitura

    def _atualizar(self):
        """Lê um quadro, detecta o documento, avisa a interface e agenda o próximo."""
        self._agendamento = None
        if self._camera is None:
            return

        sucesso, quadro = self._camera.read()
        if not sucesso or quadro is None:
            self.parar()
            self._ao_falha("Falha na câmera",
                           "A câmera foi aberta, mas não foi possível receber a imagem.")
            return

        self.quadro_atual = quadro.copy()
        try:
            cantos, encontrou = detectar_documento(quadro, baixo_contraste=False)
            previa = transformar_perspectiva(quadro, cantos) if encontrou else None
        except Exception as erro:
            self.parar()
            self._ao_falha("Erro no processamento da câmera",
                           f"Não foi possível processar o quadro recebido:\n{erro}")
            return

        if encontrou and previa is not None:
            self._ao_quadro(quadro, cantos.copy(), previa)
        else:
            self._ao_quadro(quadro, None, None)

        # O intervalo é contado após o processamento, então quadros não se acumulam.
        self._agendamento = self._raiz.after(INTERVALO_QUADROS_MS, self._atualizar)
