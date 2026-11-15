"""Constantes que controlam a detecção da folha e a câmera.

Ficam todas aqui para que seja fácil ajustar o comportamento do programa sem
procurar números espalhados pelo código. Cada constante explica o efeito de
aumentar ou diminuir o seu valor.
"""

# Lado maior (em pixels) usado na detecção da folha. Reduzir a imagem deixa a
# detecção rápida e ignora detalhes pequenos (textura da mesa, letras). O
# recorte final é feito na imagem original, sem perder qualidade.
LADO_DETECCAO = 500

# Índice da câmera padrão. Se houver mais de uma câmera, teste 1, 2 etc.
INDICE_CAMERA = 0

# --- Prévia da câmera ao vivo -------------------------------------------------
# A prévia é dividida em duas tarefas independentes, para a janela nunca travar:
#   exibição  troca o quadro da câmera na tela. É barata (alguns ms por quadro).
#   análise   roda as etapas do processamento (detecção da folha, cinza,
#             desfoque, threshold, contorno, documento endireitado e efeito de
#             scanner) sobre o quadro mais recente. É mais cara, então roda menos
#             vezes por segundo; as etapas na tela são as da última análise.

# Intervalo (ms) entre atualizações da imagem na tela. 33 ms = no máximo ~30
# quadros por segundo. Aumente (ex.: 50 ou 66) se a máquina for lenta.
INTERVALO_EXIBICAO_MS = 33

# Intervalo mínimo (s) entre duas análises. 0,12 s = no máximo ~8 por segundo.
# Aumentar economiza processador (as etapas atualizam menos vezes); diminuir
# deixa o contorno e as etapas mais "coladas" na folha em movimento.
INTERVALO_ANALISE_S = 0.12

# Tamanho máximo (px do maior lado) das imagens das ETAPAS na prévia ao vivo.
# Os cartões mostram miniaturas, então não vale gastar processador com imagens
# maiores. Isso reduz muito o custo (o efeito P&B cai de ~116 ms para ~9 ms).
# O processamento ao CAPTURAR continua usando a imagem em tamanho completo.
LADO_ETAPAS_AO_VIVO = 640

# O documento precisa ocupar pelo menos 15% da foto. Isso evita escolher um
# retângulo pequeno, como a foto 3x4 dentro de uma identidade.
AREA_MINIMA_RELATIVA = 0.15

# Pelo menos metade do contorno precisa estar sobre bordas reais da imagem.
# Aumentar deixa a detecção mais exigente (menos falsos positivos, mais
# fotos em que nada é encontrado); diminuir faz o contrário.
APOIO_MINIMO = 0.5

# Cada lado do contorno (fora da margem da foto) precisa ter pelo menos esta
# fração apoiada em bordas reais. Evita aceitar um lado "inventado", por
# exemplo uma diagonal cortando a folha, mesmo que os outros três lados sejam
# fortes e puxem a média para cima.
LADO_MINIMO = 0.2
