
# Passos para ativar o ambiente virtual e instalar as bibliotecas
# 1. Criar o ambiente virtual:
# python3 -m venv .venv

# 2. Ativar o ambiente:
# source .venv/bin/activate

# 3. Instalar as dependências:
# python -m pip install -r requirements.txt

import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
from PIL import Image, ImageTk

IMAGEM_TESTE = "./assets/identidade-mc-lovin.jpg"

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

    # 4. Aplicar Canny pra detecção de bordas
    edged = cv2.Canny(blur, 75, 200)

    # Retornar todas as etapas do processamento
    return gray, blur, threshold, edged


class ImagePreprocessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualizador de Pré-processamento")
        self.root.geometry("1200x760")

        # Botão para selecionar uma imagem
        button = tk.Button(
            root,
            text="Selecionar imagem",
            command=self.load_image,
            font=("Arial", 12)
        )
        button.grid(
            row=0,
            column=0,
            columnspan=3,
            pady=12
        )

        # Etapas do processamento
        stages = [
            ("original", "1. Imagem original"),
            ("gray", "2. Escala de cinza"),
            ("blur", "3. Gaussian Blur"),
            ("threshold", "4. Threshold"),
            ("edged", "5. Canny - detecção de bordas")
        ]

        self.image_labels = {}

        # Criar os painéis em três colunas
        for index, (key, title) in enumerate(stages):
            row = (index // 3) + 1
            column = index % 3

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

        # Distribuir igualmente o espaço entre as colunas
        for column in range(3):
            root.grid_columnconfigure(column, weight=1)

        # Distribuir o espaço entre as duas linhas de imagens
        root.grid_rowconfigure(1, weight=1)
        root.grid_rowconfigure(2, weight=1)

    def load_image(self):
        # Escolha de imagem desativada temporariamente pra usar a IMAGEM_TESTE como imagem padrão.
        # Pra reativar: tirar os comentários e comentar/remover a linha logo abaixo, onde tem path = IMAGEM_TESTE
        #path = filedialog.askopenfilename(
        #    title="Escolha uma imagem",
        #    filetypes=[
        #        (
        #            "Imagens",
        #            "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"
        #        ),
        #        ("Todos os arquivos", "*.*")
        #    ]
        #)

        path = IMAGEM_TESTE

        if not path:
            return

        # Ler a imagem
        image = cv2.imread(path)

        if image is None:
            messagebox.showerror(
                "Erro",
                "Não foi possível abrir essa imagem."
            )
            return

        # Executar o pré-processamento
        gray, blur, threshold, edged = scan_detector(image)

        # Relacionar cada resultado ao seu painel
        images = {
            "original": image,
            "gray": gray,
            "blur": blur,
            "threshold": threshold,
            "edged": edged
        }

        for key, array in images.items():
            # Converter a imagem para o formato aceito pelo Pillow
            if len(array.shape) == 2:
                # Imagem em escala de cinza
                pil_image = Image.fromarray(array)
            else:
                # Converter BGR para RGB
                rgb = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb)

            # Redimensionar sem distorcer a proporção
            pil_image.thumbnail(
                (350, 230),
                Image.Resampling.LANCZOS
            )

            # Converter para exibição no Tkinter
            photo = ImageTk.PhotoImage(pil_image)

            label = self.image_labels[key]
            label.configure(image=photo, text="")

            # Impedir que a imagem seja removida da memória
            label.image = photo


if __name__ == "__main__":
    root = tk.Tk()
    app = ImagePreprocessorApp(root)
    root.mainloop()
