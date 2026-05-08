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
