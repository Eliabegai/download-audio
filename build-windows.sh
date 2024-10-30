#!/bin/bash

# Compila o script com PyInstaller
python -m PyInstaller --onefile --name=baixar-audio-windows --distpath dist/windows/2_1 ./src/baixar_audio.py