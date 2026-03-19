<h1 align="center">🎵 YouTube to MP3 Converter</h1>

<p align="center">
  Uma aplicação web moderna, rápida e responsiva para converter e baixar vídeos do YouTube como arquivos de áudio MP3, construída com FastAPI e HTMX.
</p>

## 💡 Visão Geral

Este projeto oferece uma solução robusta e amigável para converter vídeos do YouTube em arquivos de áudio MP3. Utilizando o poder do FastAPI para um backend de alta performance e o HTMX para um frontend dinâmico e leve em JavaScript, ele proporciona atualizações de progresso em tempo real e uma experiência de usuário fluida e intuitiva.

---

## ✨ Funcionalidades

- **Conversão Direta:** Cola o link, converte e baixa. Simples assim.
- **Interface Moderna:** Tema dark com detalhes em azul, focado na experiência do usuário.
- **Progresso em Tempo Real:** Acompanhamento do download e conversão ao vivo sem recarregar a página (via HTMX + Idiomorph).
- **Download Simultâneo:** Suporte para múltiplas conversões em fila.
- **Código Limpo:** Orientado a testes (TDD) e boas práticas.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python 3.11+, FastAPI, `yt-dlp`, `asyncio`
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla), HTMX, Idiomorph
- **Testes:** `pytest`, `pytest-asyncio`
- **Mídia:** FFmpeg

---

## ⚙️ Pré-requisitos e FFmpeg

Para que o `yt-dlp` consiga extrair o áudio e convertê-lo para `.mp3`, o **FFmpeg** é estritamente necessário.

### Configuração Recomendada (Usada neste projeto)
A configuração atual do backend aponta diretamente para um caminho fixo no Windows. Siga os passos:

1. Baixe a build do FFmpeg para Windows: yt-dlp/FFmpeg-Builds.
2. Baixe o arquivo `ffmpeg-master-latest-win64-gpl.zip`.
3. Extraia o conteúdo na raiz do seu disco `C:\`, de forma que o caminho do executável fique exatamente como:
   `C:\ffmpeg\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe`

> **Nota:** Esta configuração garante isolamento e evita conflitos com outras versões do FFmpeg instaladas no sistema.

### Outras Configurações Possíveis

Se você preferir usar o FFmpeg global do sistema ou estiver no Linux/macOS:

1. Instale o FFmpeg via gerenciador de pacotes (`apt install ffmpeg`, `brew install ffmpeg` ou via `winget` no Windows).
2. Adicione-o ao `PATH` do sistema.
3. Edite o arquivo `backend/app/converter.py` e **remova** a linha `"ffmpeg_location": r"..."` ou aponte-a para seu executável global.

---

## 🚀 Instalação e Execução

### 1. Clonar o Repositório
```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd youtube-mp3-converter
```

### 2. Configurar o Ambiente Python (Backend)
Recomenda-se o uso de um ambiente virtual para isolar as dependências.

```bash
cd backend

# Criar ambiente virtual
python -m venv venv

# Ativar (Windows)
venv\Scripts\activate
# Ativar (Linux/Mac)
# source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Iniciar o Servidor
Com o ambiente ativado e as dependências instaladas, inicie o servidor da API e Frontend com o Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

Acesse no seu navegador: **http://localhost:8000**

---

## 🧪 Executando Testes

O projeto foi construído utilizando a metodologia TDD. Para garantir que tudo está funcionando perfeitamente:

```bash
cd backend

# Executar todos os testes
pytest -v

# Executar testes com relatório de cobertura (coverage)
pytest --cov=app --cov-report=html
```

---

## 📁 Estrutura do Projeto

```text
├── backend/                 # API Python/FastAPI
│   ├── app/                 # Regras de negócio, serviços e rotas
│   ├── tests/               # Casos de uso e testes unitários
│   └── requirements.txt     # Dependências do Python
├── frontend/                # Interface visual servida estaticamente
│   ├── css/                 # Estilização (Dark Theme)
│   ├── js/                  # Interatividade (transição p/ HTMX)
│   └── index.html           # Arquivo principal
└── README.md
```