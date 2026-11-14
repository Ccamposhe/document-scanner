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
