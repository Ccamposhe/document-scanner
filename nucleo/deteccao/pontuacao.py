"""Como um quadrilátero candidato é "pontuado" na detecção.

Um bom candidato tem os quatro lados em cima de bordas REAIS da foto. Um
candidato errado corta o meio da folha ou do fundo, onde não existe borda.
As funções deste módulo medem isso e são usadas pelas passadas 1 e 2.
"""

import cv2
import numpy as np


def medir_apoio_nas_bordas(cantos, bordas):
    """Mede quanto do contorno do quadrilátero passa sobre bordas reais.

    Devolve (apoio_medio, apoio_do_pior_lado), ambos entre 0 e 1:
        apoio_medio       fração total do contorno sobre bordas (média ponderada
                          pelo comprimento: lados longos pesam mais);
        apoio_do_pior_lado  apoio do lado MENOS apoiado. Antes só a média era
                          avaliada, e um lado inventado (uma diagonal, por
                          exemplo) passava se os outros três fossem fortes.

    Trechos colados na margem da foto são ignorados: lá a borda da folha pode
    simplesmente estar fora do quadro, então não dá para saber.
    """
    margem = 4  # faixa (em pixels) da borda da foto que não conta
    apoios_por_lado, acertos, totais = [], 0, 0
    for k in range(4):
        # Desenha só o lado k numa imagem vazia e apaga a faixa da margem.
        linha = np.zeros(bordas.shape, np.uint8)
        cv2.line(linha, tuple(int(v) for v in cantos[k]),
                 tuple(int(v) for v in cantos[(k + 1) % 4]), 255, 1)
        linha[:margem, :] = 0
        linha[-margem:, :] = 0
        linha[:, :margem] = 0
        linha[:, -margem:] = 0

        total = cv2.countNonZero(linha)
        comprimento = float(np.linalg.norm(cantos[(k + 1) % 4] - cantos[k]))
        if total < 0.25 * comprimento:
            continue  # lado quase todo na margem: não dá para medir

        # Quantos pixels do lado caem em cima de uma borda detectada.
        sobre_borda = cv2.countNonZero(cv2.bitwise_and(linha, bordas))
        apoios_por_lado.append(sobre_borda / total)
        acertos += sobre_borda
        totais += total

    if not apoios_por_lado:
        return 0.0, 0.0
    return acertos / totais, float(min(apoios_por_lado))


def tem_lado_na_margem(cantos, altura, largura, margem=4):
    """True se algum lado do quadrilátero está colado numa borda da foto.

    É um sinal de alerta: pode ser que a folha realmente passe do enquadramento,
    ou que a borda daquele lado simplesmente não tenha sido vista (folha clara
    em fundo claro). O pipeline usa isso para pedir uma "segunda opinião".
    """
    for k in range(4):
        p, q = cantos[k], cantos[(k + 1) % 4]
        # Os dois extremos do lado estão na mesma borda da foto?
        if ((p[0] <= margem and q[0] <= margem)
                or (p[0] >= largura - 1 - margem and q[0] >= largura - 1 - margem)
                or (p[1] <= margem and q[1] <= margem)
                or (p[1] >= altura - 1 - margem and q[1] >= altura - 1 - margem)):
            return True
    return False
