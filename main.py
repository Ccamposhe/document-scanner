#Passos para ativar o ambiente virtual e instalar as bibliotecas
# 1.Criar o ambiente virtual
#python3 -m venv .venv

# 2.Ativar o ambiente
#source .venv/bin/activate

# 3.Instalar as dependências
#python -m pip install -r requirements.txt

import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
from PIL import Image, ImageTk


def scan_detector(image):
    # 1. Converter para escala de cinza
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 2. Aplicar Gaussian Blur
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # 3. Aplicar Threshold com Otsu
    _, threshold = cv2.threshold(
        blur,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Retornar os resultados para a interface
    return gray, blur, threshold


class ImagePreprocessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualizador de Pré-processamento")
        self.root.geometry("1000x750")

        # Botão pra selecionar uma imagem
        button = tk.Button(
            root,
            text="Selecionar imagem",
            command=self.load_image,
            font=("Arial", 12)
        )
        button.grid(row=0, column=0, columnspan=2, pady=12)

        # Criar os quatro painéis
        stages = [
            ("original", "1. Imagem original"),
            ("gray", "2. Escala de cinza"),
            ("blur", "3. Gaussian Blur"),
            ("threshold", "4. Threshold")
        ]

        self.image_labels = {}

        for index, (key, title) in enumerate(stages):
            row = (index // 2) + 1
            column = index % 2

            frame = tk.LabelFrame(
                root,
                text=title,
                padx=8,
                pady=8
            )

            frame.grid(
                row=row,
                column=column,
                padx=8,
                pady=8,
                sticky="nsew"
            )

            label = tk.Label(
                frame,
                text="Selecione uma imagem",
                anchor="center"
            )
            label.pack(fill="both", expand=True)

            self.image_labels[key] = label

        # Permitir que os painéis ocupem o espaço disponível
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(1, weight=1)
        root.grid_rowconfigure(2, weight=1)

    def load_image(self):
        path = filedialog.askopenfilename(
            title="Escolha uma imagem",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                ("Todos os arquivos", "*.*")
            ]
        )

        if not path:
            return

        # Leitura da imagem
        image = cv2.imread(path)

        if image is None:
            messagebox.showerror(
                "Erro",
                "Não foi possível abrir essa imagem."
            )
            return

        # Processamento da imagem
        gray, blur, threshold = scan_detector(image)

        # Dicionário dos painéis com o título e a devida imagem
        images = {
            "original": image,
            "gray": gray,
            "blur": blur,
            "threshold": threshold
        }

        for key, array in images.items():
            # OpenCV trabalha com imagens coloridas em BGR.
            # O Pillow utiliza RGB.
            if len(array.shape) == 2:
                pil_image = Image.fromarray(array)
            else:
                rgb = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb)

            # Limitar o tamanho sem distorcer a imagem
            pil_image.thumbnail(
                (450, 280),
                Image.Resampling.LANCZOS
            )

            # Converter para um formato exibível pelo Tkinter
            photo = ImageTk.PhotoImage(pil_image)

            label = self.image_labels[key]
            label.configure(image=photo, text="")

            # Manter uma referência para a imagem
            label.image = photo


if __name__ == "__main__":
    root = tk.Tk()
    app = ImagePreprocessorApp(root)
    root.mainloop()
