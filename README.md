# Downloader Pro (Tauri + Python bridge)

Aplicativo desktop para download de YouTube com:

- áudio
- vídeo
- playlist (áudio)
- busca direta no app (limitada a 5 resultados)
- preview com título e thumbnail

Motor de download usa `yt-dlp` via bridge Python.
Interface usa `React + TypeScript + Tauri v2`.

---

## Requisitos

- Node.js 18+ (recomendado 20+)
- npm
- Rust (toolchain estável) + Cargo
- Python 3.9+
- FFmpeg no `PATH`

### Instalação do FFmpeg (exemplos)

- **Windows**

  ```bash
  winget install "FFmpeg (Essentials Build)"
  ```

- **macOS**

  ```bash
  brew install ffmpeg
  ```

- **Linux (Debian/Ubuntu)**

  ```bash
  sudo apt update
  sudo apt install ffmpeg
  ```

---

## Setup rápido (novo ambiente)

No diretório raiz do projeto:

```bash
pip install -r requirements.txt
npm run desktop:install
```

Isso instala dependências Python e frontend desktop.

---

## Comandos principais (raiz do projeto)

Sem `--prefix` manual:

```bash
npm run dev
npm run build
npm run preview
npm run tauri:dev
npm run tauri:build
```

### O que cada comando faz

- `npm run dev`: sobe somente Vite (frontend web local)
- `npm run tauri:dev`: abre app desktop Tauri com hot reload
- `npm run build`: build frontend (`apps/desktop/dist`)
- `npm run tauri:build`: gera build desktop empacotado

---

## Build no Windows

### Pré-requisitos

- [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/) com o workload **"Desenvolvimento para desktop com C++"** (fornece o linker `link.exe` exigido pelo Rust MSVC). Instalação via PowerShell como administrador:

  ```powershell
  winget install Microsoft.VisualStudio.2022.BuildTools --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
  ```

  Depois da instalação, feche e reabra o terminal.

- Node.js 22+ ou Deno (o `yt-dlp` precisa de um runtime JS para baixar do YouTube).
- FFmpeg (`winget install "FFmpeg (Essentials Build)"`).

### Criar o ambiente Python

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
npm run desktop:install
```

### Atualizar dependências e gerar o build

O YouTube muda com frequência; atualize o `yt-dlp` no `requirements.txt` (ou reinstale no `.venv`) antes de cada build:

```powershell
.venv\Scripts\activate
python -m pip install -U --pre "yt-dlp[default]" yt-dlp-ejs
npm run tauri:build
```

`npm run tauri:build` monta um runtime portátil (Python, `yt-dlp`, FFmpeg, Node.js e os scripts de `src/`) e o grava dentro do executável. O outro computador não precisa ter Python, FFmpeg nem Node instalados.

Para usar sem instalador, copie este arquivo:

`apps/desktop/src-tauri/target/release/bundle/portable/Downloader Pro.exe`

Na primeira abertura ele extrai o runtime para `%LOCALAPPDATA%\Downloader Pro\runtime`. O `.exe` solto em `target/release/downloader_pro_desktop.exe`, copiado sem esse empacotamento, procura uma pasta `resources` ao lado dele e falha em outro PC.

O instalador continua em `apps/desktop/src-tauri/target/release/bundle/` (`msi/` e `nsis/`).

### Observações

- O modo de desenvolvimento (`npm run tauri:dev`) continua usando o `.venv` desta pasta.
- Atualizar o `yt-dlp` do `.venv` não atualiza o app já instalado. É preciso gerar o instalador de novo e reinstalá-lo.
- Se downloads falharem com `Requested format is not available` ou uma playlist terminar sem baixar nada, atualize o `yt-dlp` e gere um novo build.

---

## Fluxo de uso

1. Abrir app em dev:

   ```bash
   npm run tauri:dev
   ```

2. Informar URL YouTube ou termo.
3. Fazer preview ou busca.
4. Selecionar modo (`Audio`, `Video`, `Playlist Audio`).
5. Escolher pasta de saída (opcional).
6. Clicar em `Baixar`.

Durante download:

- spinner de loading
- barra de progresso
- velocidade/ETA
- contador de itens (playlist)
- logs de andamento

Após concluir:

- campo de entrada e resultados são limpos
- pasta de saída é mantida

---

## Cookies (opcional)

Se quiser melhorar compatibilidade com conteúdos restritos, adicione `cookies.txt` na raiz do projeto.
O bridge tenta usar esse arquivo automaticamente quando presente.

---

## Estrutura relevante

- `apps/desktop/` -> frontend e shell Tauri
- `apps/desktop/src-tauri/` -> comandos Rust
- `src/tauri_bridge.py` -> bridge Python para preview/search/download
- `src/functions_download.py` -> motor yt-dlp
- `src/format_profiles.py` -> perfis de formato

---

## Changelog da refatoração atual

Veja `CHANGELOG.md` para lista completa das mudanças feitas nesta migração/refino.
