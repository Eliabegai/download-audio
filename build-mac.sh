#!/bin/bash

# Compila o script com PyInstaller
pyinstaller --onefile --name=baixar-audio-mac --distpath dist/mac/2_1 ./src/baixar_audio.py

# Aplica a permissão de execução ao arquivo gerado
chmod +x dist/mac/2_1/baixar-audio-mac