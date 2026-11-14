"""Geometria dos cantos e retas: o que o resto do programa usa como "régua".

Convenção usada em todo o projeto:
    - um ponto é (x, y), com x para a direita e y para BAIXO (coordenadas de imagem);
    - os quatro cantos de uma folha são guardados em um array 4x2 e, quando
      "ordenados", seguem a ordem: superior-esquerdo, superior-direito,
      inferior-direito, inferior-esquerdo.

Duas formas de representar uma reta aparecem aqui:
    - cartesiana  a·x + b·y = c        (reta_por_dois_pontos / intersecao_de_retas)
    - polar       x·cos(θ) + y·sen(θ) = ρ   (intersecao_polar)
"""

import cv2
import numpy as np


def ordenar_cantos(pontos):
    """Ordena 4 pontos como: superior-esquerdo, superior-direito,
    inferior-direito, inferior-esquerdo.

    Truque clássico: somando x + y, o canto superior-esquerdo dá a MENOR soma
    e o inferior-direito dá a MAIOR. Calculando y - x, o superior-direito dá a
    menor diferença e o inferior-esquerdo dá a maior.
    """
    ordenados = np.zeros((4, 2), dtype="float32")

    # Menor soma = superior-esquerdo; maior soma = inferior-direito.
    soma = pontos.sum(axis=1)
    ordenados[0] = pontos[np.argmin(soma)]
    ordenados[2] = pontos[np.argmax(soma)]

    # np.diff devolve (y - x): menor = superior-direito; maior = inferior-esquerdo.
    diferenca = np.diff(pontos, axis=1)
    ordenados[1] = pontos[np.argmin(diferenca)]
    ordenados[3] = pontos[np.argmax(diferenca)]

    return ordenados


def transformar_perspectiva(imagem, pontos):
    """"Endireita" o documento: leva os 4 cantos a um retângulo, como se a foto
    tivesse sido tirada exatamente de cima.

    Retorna a imagem recortada e corrigida, ou None se os cantos formarem uma
    área pequena demais para ser um documento.
    """
    # 1) Cantos na ordem canônica (superior-esquerdo, superior-direito, ...).
    cantos = ordenar_cantos(pontos)
    superior_esquerdo, superior_direito, inferior_direito, inferior_esquerdo = cantos

    # 2) Tamanho do retângulo de saída: a maior largura e a maior altura entre
    #    lados opostos (a foto em perspectiva deixa um lado maior que o outro).
    largura_a = np.linalg.norm(inferior_direito - inferior_esquerdo)
    largura_b = np.linalg.norm(superior_direito - superior_esquerdo)
    altura_a = np.linalg.norm(superior_direito - inferior_direito)
    altura_b = np.linalg.norm(superior_esquerdo - inferior_esquerdo)

    largura_maxima = int(max(largura_a, largura_b))
    altura_maxima = int(max(altura_a, altura_b))

    if largura_maxima < 2 or altura_maxima < 2:
        return None

    # 3) Cantos do retângulo de destino, na mesma ordem dos cantos de origem.
    destino = np.array(
        [
            [0, 0],
            [largura_maxima - 1, 0],
            [largura_maxima - 1, altura_maxima - 1],
            [0, altura_maxima - 1],
        ],
        dtype="float32",
    )

    # 4) Matriz de transformação projetiva (homografia) origem -> destino,
    #    aplicada sobre a imagem ORIGINAL colorida (sem perder qualidade).
    matriz = cv2.getPerspectiveTransform(cantos, destino)
    return cv2.warpPerspective(imagem, matriz, (largura_maxima, altura_maxima))


def afastar_do_centro(cantos, pixels):
    """Afasta cada canto do centro do quadrilátero.

    Usado para compensar a borda engrossada pela dilatação das máscaras: sem
    isso o quadrilátero ficaria alguns pixels "para dentro" da folha. O fator
    1,41 (√2) vem do deslocamento na diagonal de um quadrado.
    """
    direcao = cantos - cantos.mean(axis=0)
    direcao /= np.linalg.norm(direcao, axis=1, keepdims=True)
    return (cantos + direcao * pixels * 1.41).astype(np.float32)


def reta_por_dois_pontos(p, q):
    """Reta no formato a·x + b·y = c que passa pelos pontos p e q."""
    a, b = q[1] - p[1], p[0] - q[0]
    return a, b, a * p[0] + b * p[1]


def intersecao_de_retas(r1, r2):
    """Ponto onde duas retas cartesianas (a, b, c) se cruzam, ou None se forem
    paralelas. Resolve o sistema 2x2 pela regra de Cramer."""
    a1, b1, c1 = r1
    a2, b2, c2 = r2
    determinante = a1 * b2 - a2 * b1
    if abs(determinante) < 1e-6:
        return None  # retas paralelas: não se cruzam
    return np.array([(c1 * b2 - c2 * b1) / determinante,
                     (a1 * c2 - a2 * c1) / determinante], np.float32)


def intersecao_polar(r1, r2):
    """Ponto onde duas retas polares (rho, theta) se cruzam (regra de Cramer),
    ou None se forem quase paralelas.

    Na forma polar a reta é  x·cos(θ) + y·sen(θ) = ρ.  O determinante do
    sistema é sen(θ2 − θ1); abaixo de 0,2 (≈ 11,5°) as retas são paralelas
    demais para que a interseção seja confiável.
    """
    (rho1, theta1), (rho2, theta2) = r1, r2
    c1, s1, c2, s2 = np.cos(theta1), np.sin(theta1), np.cos(theta2), np.sin(theta2)
    determinante = c1 * s2 - s1 * c2
    if abs(determinante) < 0.2:  # quase paralelas
        return None
    return np.array([(rho1 * s2 - s1 * rho2) / determinante,
                     (c1 * rho2 - rho1 * c2) / determinante], np.float32)
