import cv2
import numpy as np
import pytesseract


def extrair_texto(imagem, idioma="por"):
    """Aplica threshold adaptativo e extrai o texto em português por padrão."""
    if imagem is None or (isinstance(imagem, np.ndarray) and imagem.size == 0):
        raise ValueError("A imagem está vazia.")
    if not isinstance(imagem, np.ndarray) or imagem.dtype != np.uint8:
        raise ValueError("Use uma imagem NumPy com pixels do tipo uint8.")
    if imagem.ndim not in (2, 3):
        raise ValueError("Use uma imagem em cinza, BGR ou BGRA.")
    if not isinstance(idioma, str) or not idioma.strip():
        raise ValueError("Informe um idioma, como 'por' ou 'eng'.")

    if imagem.ndim == 3:
        if imagem.shape[2] not in (3, 4):
            raise ValueError("A imagem colorida deve ter 3 ou 4 canais.")
        imagem = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    
    #Aplicando o threshold adaptativo para quando for extrair o texto ficar mais legivel

    blur = cv2.GaussianBlur(imagem, (3, 3), 0)
    threshold = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    resultado = threshold

    return pytesseract.image_to_string(
        resultado,
        lang=idioma,
        timeout=30,
    ).strip()
