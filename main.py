"""Ponto de entrada do Scanner de Documentos.

Execute com:  python main.py
"""

import tkinter as tk

from interface.janela import AplicativoScanner


def main():
    """Cria a janela do Tkinter e entrega o controle ao aplicativo."""
    raiz = tk.Tk()
    AplicativoScanner(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
