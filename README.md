# 📄 Scanner de Documentos

Projeto acadêmico desenvolvido para a disciplina de **Algoritmos de Processamento de Imagem**, com o objetivo de explorar técnicas de processamento de imagens aplicadas à digitalização e ao reconhecimento de documentos.

A aplicação utiliza Python, OpenCV e Tkinter para carregar imagens e visualizar diferentes etapas de pré-processamento em uma interface gráfica.

## ✨ Funcionalidades

- 🖼️ **Carregamento de imagens:** seleção de arquivos diretamente pelo computador.
- 🌑 **Escala de cinza:** conversão da imagem colorida para tons de cinza.
- 🌫️ **Gaussian Blur:** suavização da imagem para reduzir ruídos.
- ⚫ **Threshold:** binarização automática da imagem.
- 📐 **Canny Edge Detection:** detecção de bordas e contornos.
- 🔲 **Detecção do documento:** encontra os quatro cantos da folha e mostra o contorno sobre a foto, inclusive quando a folha e o fundo têm cores parecidas.
- 📄 **Transformação de perspectiva:** "endireita" documentos fotografados em ângulo.
- ⏹️ **Ajuste manual dos quatro cantos** dá a opção de ajustar os cantos da imagem manualmente, caso o documento não seja detectado.
- 🔤 **OCR com Tesseract:** extrai o texto testando versões da imagem e modos de leitura.
- 🔄 **Girar a imagem:** botões de 90° e 180° para fotos de cabeça para baixo ou de lado.
- 📷 **Câmera ao vivo:** enquanto a câmera filma, todas as etapas (contorno, cinza, blur, threshold, documento digitalizado e P&B) aparecem **simultaneamente** nos cartões. A leitura e a análise rodam em threads separadas, então a janela não trava (ritmos ajustáveis em `nucleo/configuracao.py`). O OCR roda ao capturar o quadro.
- 🖥️ **Interface gráfica:** abas para ver as etapas do processamento, imagens que acompanham o tamanho da janela e caixa de texto editável.

## 🧭 Como usar

1. **Entrada da imagem:** clique em **Escolher arquivo** ou em **Câmera ao vivo** (a prévia mostra o contorno da folha; use **Capturar quadro** para congelar a imagem).
2. Se a foto estiver de cabeça para baixo ou de lado, use **Girar imagem** (90° esq., 180°, 90° dir.). Os resultados anteriores são limpos.
3. Clique em **Processar**. O documento é detectado, corrigido e lido pelo OCR em segundo plano, com a barra de progresso na lateral.
   - Se o contorno estiver errado (ou não aparecer), clique em **Ajustar cantos** e arraste os 4 círculos até os cantos da folha.
4. Use as **abas** para escolher o que ver: _Original + pré-processamento_, _Original + digitalizada_ ou _Todos os processos_.
5. Corrija o texto na caixa **Texto extraído**, se precisar, e use **Salvar imagem (cor)**, **Salvar imagem (P&B)** ou **Salvar texto (.txt)**.

## 🛠️ Tecnologias utilizadas

| Tecnologia                                                  | Finalidade                                   |
| ----------------------------------------------------------- | -------------------------------------------- |
| [Python](https://www.python.org/)                           | Linguagem de programação                     |
| [OpenCV](https://opencv.org/)                               | Processamento e análise de imagens           |
| [NumPy](https://numpy.org/)                                 | Operações com matrizes e dados numéricos     |
| [Tkinter](https://docs.python.org/3/library/tkinter.html)   | Construção da interface gráfica              |
| [Pillow](https://python-pillow.org/)                        | Conversão e exibição de imagens              |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | Motor de reconhecimento óptico de caracteres |
| [pytesseract](https://github.com/madmaze/pytesseract)       | Integração do Tesseract com Python           |

## 🚀 Instalação

Escolha abaixo as instruções correspondentes ao seu sistema operacional. Os comandos devem ser executados no terminal, dentro da pasta do projeto quando indicado.

### 🐧 Xubuntu / Linux (Debian e Ubuntu)

#### 1. Instale os componentes do sistema

Abra o terminal e execute:

```bash
sudo apt update

sudo apt install \
    python3 \
    python3-venv \
    python3-pip \
    python3-tk \
    tesseract-ocr \
    tesseract-ocr-por \
    tesseract-ocr-eng
```

Esses pacotes fornecem o Python, o suporte a ambientes virtuais, a interface Tkinter e o motor Tesseract com dados para português e inglês.

#### 2. Clone o repositório

Se estiver obtendo o projeto pelo Git:

```bash
git clone <URL_DO_REPOSITORIO>
cd <PASTA_DO_PROJETO>
```

Substitua os valores pelos dados do seu repositório. Se você já possui os arquivos do projeto, entre diretamente na pasta correspondente.

#### 3. Crie e ative o ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 4. Instale as dependências Python

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

#### 5. Execute a aplicação

```bash
python main.py
```

### 🪟 Windows

#### 1. Instale o Python

Baixe uma versão compatível do Python pelo [site oficial](https://www.python.org/downloads/windows/) ou instale o Python Install Manager conforme as instruções do [Python.org](https://docs.python.org/3/using/windows.html).

Durante a instalação, siga as instruções apresentadas pelo instalador. Depois, feche e reabra o terminal ou o VS Code.

Verifique a instalação no PowerShell ou no Prompt de Comando:

```powershell
py --version
```

O Tkinter normalmente é incluído na distribuição padrão do Python para Windows. Teste-o com:

```powershell
py -m tkinter
```

Uma pequena janela de demonstração deve aparecer. Se isso não acontecer, confira a instalação do Python e seus componentes Tcl/Tk.

#### 2. Instale o Tesseract OCR

O Tesseract é um programa separado e não é instalado pelo `requirements.txt`. Uma opção comum para Windows é o instalador disponibilizado pela [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).

Durante a instalação, inclua os dados de idioma para português (`por`) e inglês (`eng`), quando disponíveis. Se necessário, adicione a pasta de instalação do Tesseract à variável de ambiente `PATH` do Windows para que o comando `tesseract` seja reconhecido no terminal.

Verifique a instalação:

```powershell
tesseract --version
tesseract --list-langs
```

Na lista de idiomas, confira se aparecem `por` e `eng`.

#### 3. Clone o repositório e entre na pasta

Se estiver usando Git:

```powershell
git clone <URL_DO_REPOSITORIO>
cd <PASTA_DO_PROJETO>
```

Se já tiver os arquivos, abra o terminal na pasta do projeto.

#### 4. Crie e ative o ambiente virtual

No PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação por causa da política de execução, você pode usar o Prompt de Comando (`cmd.exe`) no lugar dele. Nesse caso, o comando de ativação é:

```bat
.venv\Scripts\activate.bat
```

#### 5. Instale as dependências Python

Com o ambiente virtual ativado, execute:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

#### 6. Execute a aplicação

```powershell
python main.py
```

### 🍎 macOS

#### 1. Instale o Python

Baixe e instale uma versão compatível do Python pelo [site oficial](https://www.python.org/downloads/macos/). O instalador oficial inclui suporte ao Tkinter nas versões atuais. Depois da instalação, abra um novo terminal e verifique:

```bash
python3 --version
python3 -m tkinter
```

O segundo comando deve abrir uma pequena janela de demonstração do Tkinter.

#### 2. Instale o Homebrew

O Homebrew é um gerenciador de pacotes para macOS. Caso ainda não o tenha instalado, siga as instruções oficiais em [brew.sh](https://brew.sh/). Depois, instale o Tesseract:

```bash
brew install tesseract
brew install tesseract-lang
```

O segundo comando instala dados de idiomas adicionais. Confira se o Tesseract está disponível e se os idiomas desejados aparecem na lista:

```bash
tesseract --version
tesseract --list-langs
```

Confirme que a lista inclui `por` e `eng`.

#### 3. Clone o repositório e entre na pasta

Se estiver usando Git:

```bash
git clone <URL_DO_REPOSITORIO>
cd <PASTA_DO_PROJETO>
```

Se já tiver os arquivos, abra o terminal na pasta do projeto.

#### 4. Crie e ative o ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 5. Instale as dependências Python

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

#### 6. Execute a aplicação

```bash
python main.py
```

## 📦 Dependências Python

O arquivo `requirements.txt` deve conter:

```txt
numpy
opencv-python
Pillow
pytesseract
```

Essas bibliotecas são instaladas dentro do ambiente virtual. **Tkinter e o programa Tesseract OCR não são instalados pelo `requirements.txt`**: o Tkinter é fornecido junto ao Python em muitas distribuições (no Xubuntu, instale o pacote `python3-tk` se necessário), enquanto o Tesseract deve ser instalado separadamente no sistema operacional.

## ✅ Verificação da instalação

Com o ambiente virtual ativado, verifique as dependências Python:

```bash
python -m pip check
```

Para verificar o Tesseract e os idiomas disponíveis:

```bash
tesseract --version
tesseract --list-langs
```

Para confirmar que o Tkinter funciona:

```bash
python -m tkinter
```

No Windows, se o comando `python` não estiver disponível, tente `py -m tkinter`.

## 📁 Estrutura do projeto

```text
scanner-documentos/
├── main.py                       # ponto de entrada: só cria a janela
├── nucleo/                       # processamento: NÃO depende de interface gráfica
│   ├── configuracao.py           # constantes ajustáveis (cada uma comentada)
│   ├── geometria.py              # ordenar cantos, perspectiva, retas e interseções
│   ├── imagem.py                 # pré-processamento, efeito scanner, contorno
│   ├── analise_rapida.py         # as etapas em versão leve (prévia da câmera)
│   ├── ocr.py                    # leitura do texto com o Tesseract
│   └── deteccao/
│       ├── pipeline.py           # detectar_documento(): orquestra as 3 passadas
│       ├── candidatos.py         # passadas 1 e 2 (Otsu, Canny, Hough, CLAHE)
│       ├── pontuacao.py          # nota de cada candidato
│       └── baixo_contraste.py    # passada 3: croma, LSD, retas, texto
├── interface/                    # interface gráfica (Tkinter)
│   ├── janela.py                 # AplicativoScanner: liga as peças
│   ├── estado.py                 # dados do documento atual
│   ├── tema.py                   # cores, abas, títulos
│   ├── widgets.py                # botão padrão
│   ├── conversao.py              # BGR -> RGB
│   ├── painel_lateral.py         # barra da esquerda
│   ├── area_principal.py         # abas, ações e texto
│   ├── visualizacao.py           # grade de imagens
│   ├── camera.py                 # câmera ao vivo
│   ├── processamento.py          # thread + fila
│   └── dialogo_cantos.py         # "Ajustar cantos"
├── assets/                       # imagens de teste
├── requirements.txt
├── README.md
└── .gitignore
```

- **`nucleo/`** não importa o Tkinter: pode ser usado e testado pelo terminal. A interface só o _usa_, nunca o contrário.
- **`interface/`** só mostra e coleta informações. `janela.py` é o único arquivo que conhece todas as peças.
- `assets/`: imagens usadas para testar o scanner.
- `.venv/`: ambiente virtual local, que não deve ser versionado.

## 🔬 Etapas do pré-processamento

### 1. Imagem original

A imagem selecionada é carregada pelo OpenCV e utilizada como entrada das operações seguintes.

### 2. Conversão para escala de cinza

A função `cv2.cvtColor()` converte a imagem do espaço de cores BGR para tons de cinza, simplificando as operações posteriores.

### 3. Gaussian Blur

A função `cv2.GaussianBlur()` suaviza a imagem utilizando um kernel de `5 × 5` pixels, ajudando a reduzir ruídos e pequenas variações de intensidade.

### 4. Threshold

A função `cv2.threshold()` transforma a imagem em uma representação binária, permitindo separar pixels em primeiro plano e fundo de acordo com um limiar de intensidade.

### 5. Canny Edge Detection

A função `cv2.Canny()` identifica as bordas presentes na imagem a partir dos limiares configurados no código.

### 6. Contorno detectado

A função `detectar_documento()` (em `nucleo/deteccao/pipeline.py`) procura os quatro cantos da folha:

1. **Reduz a foto** para 500 px no maior lado. Fica rápido (cerca de 20 ms) e ignora detalhes pequenos, como a textura da mesa.
2. **Apaga o texto** com fechamento morfológico (`cv2.morphologyEx` com `MORPH_CLOSE`). A folha fica lisa e sobram só as bordas grandes.
3. **Usa dois canais:** o cinza comum e a **"brancura"** (brilho menos saturação do HSV). Papel é claro e sem cor, enquanto madeira e tecido têm cor. Isso separa a folha de fundos claros.
4. **Gera vários candidatos** com Otsu e Canny. Nas bordas do Canny, usa o contorno _de dentro_ (`RETR_LIST`), que continua certo mesmo quando a borda da folha encosta em outra linha (tábua, outra folha).
5. **Encaixa os lados nas retas reais** (`cv2.HoughLinesP`). Quando uma sombra "come" um canto, o lado é corrigido pela reta da borda e o canto é recalculado pela interseção.
6. **Dá uma nota** a cada candidato: quanto do contorno passa sobre bordas reais e o tamanho da área. Fica o melhor.

Se nada for encontrado, uma 2ª passada usa **CLAHE** (contraste local) para revelar bordas fracas, exigindo mais apoio nas bordas (75%). Ela não é usada sempre porque também realça texturas, como madeira e piso.

**3ª passada: folha e fundo de cores parecidas.** Quando a folha tem quase o mesmo brilho do fundo (papel branco em parede branca, folha cinza em mesa cinza), as passadas acima falham por três motivos: o fechamento morfológico apaga a linha fina que marca a borda do papel, o limiar do Canny vem da mediana do brilho (alto demais em fotos escuras ou sem contraste) e só o brilho era comparado. A 3ª passada (`passada_baixo_contraste`, em `nucleo/deteccao/baixo_contraste.py`) resolve assim:

1. **Croma (Lab):** mede a distância da cor ao cinza neutro, `√((a−128)² + (b−128)²)`. Papel é neutro; parede, madeira e tecido quase sempre têm algum tom. A folha se separa do fundo mesmo com brilho igual.
2. **LSD (Line Segment Detector):** acha segmentos de reta pela coerência da direção do gradiente, sem limiar de borda, então detecta lados muito fracos desde que sejam retos. Roda no brilho e no croma.
3. **Retas e quadrilátero:** os segmentos quase colineares são somados em retas, e o programa testa combinações de 2 retas "horizontais" + 2 "verticais". Cada candidato ganha nota = apoio nos segmentos × √área, e todos os lados medidos precisam de apoio mínimo.
4. **O texto como âncora:** uma máscara de texto (blackhat + junção das letras em blocos) garante que a folha **contenha** o texto. Um lado que corta as letras nunca é borda de papel.

Essa passada também é uma "segunda opinião": se o resultado das anteriores encosta na margem da foto (a borda daquele lado pode não ter sido vista), ela confere se existe um quadrilátero com os 4 lados visíveis. Além disso, a nota da 1ª passada agora exige que **nenhum lado** fique sem borda (`LADO_MINIMO`, em `nucleo/configuracao.py`), e não só a média, o que evita aceitar diagonais inventadas.

A câmera ao vivo usa só as passadas rápidas (`baixo_contraste=False`); ao **Capturar**, o quadro congelado é analisado com todas.

Se nenhum candidato for confiável, a imagem inteira é usada e a interface sugere **Ajustar cantos**. **Dica:** mesmo com a 3ª passada, fotografe com a borda da folha visível e, se puder, sobre um fundo de tom diferente do papel.

### 7. Documento digitalizado

`transformar_perspectiva()` (em `nucleo/geometria.py`) usa `cv2.getPerspectiveTransform()` e `cv2.warpPerspective()` para transformar os quatro cantos encontrados em um retângulo, como se a foto tivesse sido tirada de cima.

### 8. Efeito scanner (P&B)

`efeito_scanner()` (em `nucleo/imagem.py`) deixa a imagem com cara de escaneada:

1. Amplia para ~2200 px, para as letras ficarem lisas.
2. Estima o fundo do papel (fechamento morfológico + mediana) e divide a imagem por ele, removendo sombras.
3. Aplica nitidez (_unsharp mask_).
4. Usa uma curva de tons: o quase branco vira branco puro e o texto escurece, mantendo as bordas das letras suaves.

O OCR continua lendo a versão colorida: nos testes, o P&B forte "engrossou" letras pequenas e piorou um pouco a leitura.

### 9. OCR

O `nucleo/ocr.py` prepara a imagem e chama o Tesseract:

- corta uma margem fina (1,5%) para remover restos do fundo, que viram caracteres falsos;
- amplia letras pequenas e corrige sombras dividindo a imagem pelo seu "fundo" borrado;
- usa os idiomas `por+eng` e o motor LSTM (`--oem 1`);
- faz quatro leituras **em paralelo**, combinando versões da imagem com modos de layout (PSM 6, 3 e 11). Uma das versões usa CLAHE e nitidez;
- escolhe a leitura com melhor confiança média, sem perder muito texto.

O PSM 6 (página como um bloco único) é o mais importante em folhas inteiras. O PSM 3 tenta achar colunas e, ao lado de logotipos, "picotava" as linhas.

O painel de texto mostra a confiança média e quantos caracteres têm confiança ≥ 40. A confiança é uma estimativa do Tesseract, não uma porcentagem de acertos.

> As etapas 2 a 5 acontecem internamente; a interface mostra apenas a imagem original e o resultado final.

Essas técnicas permitem comparar diferentes representações da mesma imagem e compreender como o pré-processamento pode auxiliar em tarefas de análise e reconhecimento de documentos.

## 🎓 Objetivo acadêmico

O projeto busca aplicar conceitos de processamento digital de imagens em um problema prático: a digitalização de documentos.

Além de construir uma aplicação funcional, o trabalho permite estudar como diferentes técnicas de pré-processamento influenciam as etapas posteriores de análise e reconhecimento de texto.
