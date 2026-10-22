import tkinter as tk
from tkinter import filedialog, messagebox

from ocr import extrair_texto

import cv2
from PIL import Image, ImageTk

IMAGEM_TESTE = "./assets/identidade-mc-lovin.jpg"

def scan_detector(image):
    # Converter para escala de cinza
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Aplicar Gaussian Blur
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Aplicar Threshold com Otsu
    _, threshold = cv2.threshold(
        blur,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Retornar todas as etapas do processamento
    return gray, blur, threshold


class ImagePreprocessorApp:
    #Etapas do pipeline (chave interna, título)
    ETAPAS = [
        ("original", "Entrada"),
        ("gray", "Escala de cinza"),
        ("blur", "Gaussian Blur"),
        ("threshold", "Threshold"),
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Scanner de Documentos")
        self.root.geometry("1200x760")

        self.imagem = None
        self.resultado = None
        self.texto_ocr = ""
        self.fotos = {}
        self.labels = {}

        #Barra lateral
        barra = tk.Frame(root, padx=20, pady=20)
        barra.pack(side="left", fill="y")

        #Botoes
        #command=self.carregar
        tk.Button(barra, text="Escolher arquivo", command=self.carregar,
                  font=("Arial", 11, "bold")).pack(fill="x")

        #command=self.processar
        self.btn = tk.Button(barra, text="Processar", command=self.processar,
                             font=("Arial", 11, "bold"), state="disabled")
        self.btn.pack(fill="x", pady=12)

        #command=self.salvar
        self.btn_salvar = tk.Button(barra, text="Salvar", command=self.salvar,
                                    font=("Arial", 11, "bold"),
                                    bg="#215041", fg="white")
        self.btn_salvar.pack(fill="x")
        
        #command=self.OCR
        self.btn_ocr = tk.Button(
            barra,
            text="Extrair texto (OCR)",
            command=self.executar_ocr,
            font=("Arial", 11, "bold"),
        )
        self.btn_ocr.pack(fill="x", pady=12)

        self.btn_salvar_texto = tk.Button(
            barra,
            text="Salvar texto (.txt)",
            command=self.salvar_texto,
            font=("Arial", 11, "bold"),
            state="disabled",
        )
        self.btn_salvar_texto.pack(fill="x")

        #Área principal
        grade = tk.Frame(root, padx=10, pady=10)
        grade.pack(side="left", fill="both", expand=True)

        #Organizado em grade de 3 colunas
        for i, (chave, titulo) in enumerate(self.ETAPAS):
            quadro = tk.LabelFrame(grade, text=titulo, padx=6, pady=6)
            quadro.grid(row=i // 3, column=i % 3, padx=6, pady=6, sticky="nsew")


            self.labels[chave] = tk.Label(quadro, text="Aguardando")
            self.labels[chave].pack()

        #Define o tamanho de colunas e linhas de acordo com a janela
        for c in range(3):
            grade.grid_columnconfigure(c, weight=1)
        for r in range(2):
            grade.grid_rowconfigure(r, weight=1)

    def carregar(self):

      #Askopenfilename
      #askopenfilename abre a janela nativa do sistema para escolher um arquivo
      #O filtro Imagens mostra só os formatos de imagem suportados
      #Todos os arquivos permite ver qualquer arquivo se o usuário precisar
        caminho = filedialog.askopenfilename(
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                       ("Todos os arquivos", "*.*")]
        )
        if not caminho:
            return

        imagem = cv2.imread(caminho)
        if imagem is None:
            messagebox.showerror("Erro", "Não foi possível abrir essa imagem.")
            return

        self.imagem = imagem
        self.resultado = None
        self.texto_ocr = ""
        self.btn_salvar_texto.config(state="disabled")
        self.btn.config(state="normal")
        self.mostrar("original", imagem)

        for chave, _ in self.ETAPAS[1:]:
            self.labels[chave].config(image="", text="Aguardando")

    def processar(self):
        if self.imagem is None:
            return

        #scan_detector devolve as quatro imagens 
        gray, blur, threshold = scan_detector(self.imagem)

        for chave, img in zip(("gray", "blur", "threshold"),
                              (gray, blur, threshold)):
            self.mostrar(chave, img)

        #Define a escala de cinza como arquivo que sera salvo
        self.resultado = gray
        self.texto_ocr = ""
        self.btn_salvar_texto.config(state="disabled")

    def executar_ocr(self):
        if self.resultado is None:
            messagebox.showwarning(
                "Aviso", "Processe a imagem antes de extrair o texto."
            )
            return

        self.texto_ocr = ""
        self.btn_salvar_texto.config(state="disabled")
        texto = extrair_texto(self.resultado)

        if not texto:
            messagebox.showinfo("OCR", "Nenhum texto foi encontrado.")
            return

        self.texto_ocr = texto
        self.btn_salvar_texto.config(state="normal")
        messagebox.showinfo("Texto extraído", texto)

    def salvar_texto(self):
        if not self.texto_ocr.strip():
            messagebox.showwarning("Aviso", "Extraia o texto com OCR antes de salvar.")
            return

        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo de texto", "*.txt")],
            initialfile="texto_extraido.txt",
        )
        if not caminho:
            return

        try:
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write(self.texto_ocr)
        except OSError as erro:
            messagebox.showerror("Erro", f"Não foi possível salvar o texto:\n{erro}")
            return

        messagebox.showinfo("Pronto", f"Texto salvo em:\n{caminho}")

    def salvar(self):
        if self.resultado is None:
            messagebox.showwarning("Aviso", "Processe a imagem antes de salvar.")
            return

        #Asksaveasfilename
        #Escolhe onde salvar o arquivo
        caminho = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialfile="scan_resultado.png",
        )
        if not caminho:
            return

        array = self.resultado
        if len(array.shape) == 3:
            array = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)

        #Fromarray e .save
        #fromarray cria um objeto PIL Image a partir do array NumPy
        #save grava esse objeto no caminho escolhido, forçando o formato PNG
        Image.fromarray(array).save(caminho, "PNG")
        
        #Mostra uma confirmação com o local onde o arquivo foi salvo
        messagebox.showinfo("Pronto", f"Salvo em:\n{caminho}")

    def mostrar(self, chave, array):
        if len(array.shape) == 3:
            array = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(array)

        #Thumbnail 
        #Reduz para caber no quadro sem alterar a imagem original
        pil.thumbnail((300, 220))

        self.fotos[chave] = ImageTk.PhotoImage(pil)
        self.labels[chave].config(image=self.fotos[chave], text="")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImagePreprocessorApp(root)
    root.mainloop()
