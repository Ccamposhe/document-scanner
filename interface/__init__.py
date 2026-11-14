"""Interface gráfica (Tkinter) do scanner.

Este pacote só cuida de mostrar e coletar informações; o processamento de
imagem e o OCR vivem em `nucleo/`, que não conhece a interface.

Organização (cada arquivo tem uma responsabilidade):
    janela            AplicativoScanner: liga todas as peças e guarda o fluxo geral
    estado            Estado: os dados do documento atual (imagem, cantos, resultados)
    tema              cores, abas e títulos dos cartões
    widgets           botão padrão com estados ativado/desativado
    conversao         OpenCV (BGR) -> RGB, para exibir e salvar
    painel_lateral    barra da esquerda: arquivo, câmera, girar, status, avaliação do OCR
    area_principal    abas, grade de imagens, botões de ação e caixa de texto
    visualizacao      a grade de cartões com as imagens (redimensiona sozinha)
    camera            câmera ao vivo com prévia da detecção
    processamento     processamento em segundo plano (thread + fila)
    dialogo_cantos    janela "Ajustar cantos"
"""
