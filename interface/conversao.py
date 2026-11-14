"""Conversões entre o formato do OpenCV e o que a interface precisa."""

import cv2


def para_rgb(array):
    """Converte uma imagem BGR do OpenCV para RGB (o que o Pillow espera).

    Imagens em tons de cinza (2 dimensões) já servem e são devolvidas como estão.
    """
    if array.ndim == 3:
        return cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
    return array
