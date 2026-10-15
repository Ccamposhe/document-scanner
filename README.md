# 📄 Scanner de Documentos

Projeto acadêmico desenvolvido para a disciplina de **Algorítmos de Processamento de Imagem**, com o objetivo de explorar técnicas de processamento de imagens aplicadas à digitalização e ao reconhecimento de documentos.

A aplicação utiliza Python, OpenCV e Tkinter para carregar imagens e visualizar diferentes etapas de pré-processamento em uma interface gráfica.

## ✨ Funcionalidades

- 🖼️ **Carregamento de imagens:** seleção de arquivos diretamente pelo computador.
- 🌑 **Escala de cinza:** conversão da imagem colorida para tons de cinza.
- 🌫️ **Gaussian Blur:** suavização da imagem para reduzir ruídos.
- ⚫ **Threshold:** binarização automática da imagem.
- 📐 **Canny Edge Detection:** detecção de bordas e contornos.
- 🖥️ **Interface gráfica:** visualização dos resultados lado a lado utilizando Tkinter.

## 🛠️ Tecnologias utilizadas

| Tecnologia | Finalidade |
|---|---|
| [Python](https://www.python.org/) | Linguagem de programação |
| [OpenCV](https://opencv.org/) | Processamento e análise de imagens |
| [NumPy](https://numpy.org/) | Operações com matrizes e dados numéricos |
| [Tkinter](https://docs.python.org/3/library/tkinter.html) | Construção da interface gráfica |
| [Pillow](https://python-pillow.org/) | Conversão e exibição de imagens |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | Motor de reconhecimento óptico de caracteres |
| [pytesseract](https://github.com/madmaze/pytesseract) | Integração do Tesseract com Python |

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
├── .venv/
├── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

- `main.py`: contém a interface gráfica e as funções de pré-processamento.
- `requirements.txt`: lista as dependências Python.
- `README.md`: documenta o projeto e suas instruções de uso.
- `.gitignore`: define os arquivos e diretórios que não devem ser enviados ao Git.
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

Essas técnicas permitem comparar diferentes representações da mesma imagem e compreender como o pré-processamento pode auxiliar em tarefas de análise e reconhecimento de documentos.

## 🗺️ Próximas etapas

- [ ] Implementar a detecção automática dos limites do documento.
- [ ] Aplicar transformação de perspectiva para corrigir documentos fotografados em ângulo.
- [ ] Integrar o Tesseract OCR para extrair texto das imagens.
- [ ] Permitir a visualização e exportação do texto reconhecido.
- [ ] Avaliar os resultados com documentos em diferentes condições de iluminação.

## 🎓 Objetivo acadêmico

O projeto busca aplicar conceitos de processamento digital de imagens em um problema prático: a digitalização de documentos.

Além de construir uma aplicação funcional, o trabalho permite estudar como diferentes técnicas de pré-processamento influenciam as etapas posteriores de análise e reconhecimento de texto.
