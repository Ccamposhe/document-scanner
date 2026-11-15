"""Núcleo do scanner: tudo que NÃO depende de interface gráfica.

Este pacote contém o processamento de imagem (detecção da folha, correção de
perspectiva, efeito de scanner) e o OCR. Nenhum módulo aqui importa o Tkinter,
então todo o conteúdo pode ser testado e usado pelo terminal, sem abrir janela.

Organização:
    configuracao  constantes que ajustam o comportamento do programa
    geometria     cantos, retas e transformação de perspectiva
    deteccao/     como a folha é encontrada na foto (3 passadas)
    imagem        pré-processamento, efeito de scanner e desenho do contorno
    analise_rapida  as etapas em versão leve, para a prévia da câmera ao vivo
    ocr           leitura do texto com o Tesseract
"""
