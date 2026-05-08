# Changelog

Todas mudanças abaixo feitas nesta sessão de refatoração para Tauri desktop.

## [Unreleased]

### Added

- Base desktop criada em `apps/desktop` com React + TypeScript + Tauri v2.
- Scripts de workspace na raiz (`package.json`) para rodar sem `--prefix`:

  - `npm run dev`
  - `npm run build`
  - `npm run preview`
  - `npm run tauri:dev`
  - `npm run tauri:build`
  - `npm run desktop:install`

- Backend Tauri com comandos:

  - `preview_url`
  - `search_youtube`
  - `start_download`
  - `pick_output_folder`

- Bridge Python em `src/tauri_bridge.py` para ligar Tauri com engine Python/yt-dlp.
- Hook dedicado de progresso em `src/bridge_hooks.py`.
- Suporte inicial a perfis de formato em `src/format_profiles.py`:

  - `audio_mp3`
  - `audio_m4a`
  - `video_mp4`
  - `video_webm`

- Utilitário de FFmpeg em `src/ffmpeg_utils.py`.
- Painel de progresso no frontend:

  - barra de progresso
  - velocidade
  - ETA
  - contador por item/playlist
  - log de eventos recentes

- Loading visual com spinner para busca e download.

### Changed

- `src/functions_download.py` refatorado:

  - centralização de opções yt-dlp
  - `progress_hooks` opcional
  - validação de FFmpeg por perfil
  - nome de arquivo mais seguro (`trim_file_name`, `windowsfilenames`, template reduzido)
  - configuração de `js_runtimes` em formato compatível com yt-dlp.

- Fluxo de download no Tauri atualizado para emitir eventos contínuos ao frontend.
- UI do app desktop melhorada:

  - modo selecionado destacado (Audio/Video/Playlist)
  - resultado de busca selecionado destacado
  - thumbnails na lista de resultados
  - layout `Preview` e `Resultados` lado a lado
  - espaçamentos e legibilidade ajustados
  - limpeza de campos após download concluído (mantém pasta de saída)
  - ao alterar input, limpa preview/resultados antigos para evitar confusão.

- Seleção de pasta movida para plugin frontend (`@tauri-apps/plugin-dialog`) para reduzir travamento percebido na UI.

### Fixed

- Erro Python 3.9: `unsupported operand type(s) for |: 'type' and 'NoneType'`

  - corrigido com `from __future__ import annotations` em `src/format_profiles.py`.

- Erro yt-dlp: `Invalid js_runtimes format`

  - corrigido para formato esperado `{runtime: {config}}`.

- Título em download único não mostrava nome real

  - bridge agora extrai metadado antes do início e envia título.

- Progresso/finalização inconsistentes

  - adição de eventos `started`, `playlist-meta`, `post-process`, `batch-finished` e fallback de 100% na conclusão.

### Tooling / Project hygiene

- `.gitignore` atualizado para ignorar artefatos locais relevantes:

  - `venv/`
  - `.cargo-local/`
  - `apps/**/node_modules/`
  - `apps/**/dist/`
  - `apps/**/src-tauri/target/`
