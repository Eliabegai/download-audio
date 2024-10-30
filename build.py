import os
import platform
import subprocess

def build_executable():
    sistema = platform.system()
    
    if sistema == "Windows":
        print("Gerando executável para Windows...")
        subprocess.run([
            "pyinstaller", "--onefile", "src/main.py",
            "--name", "meu_projeto_windows"
        ])
    elif sistema == "Darwin":  # macOS
        print("Gerando executável para macOS...")
        subprocess.run([
            "pyinstaller", "--onefile", "src/main.py",
            "--name", "meu_projeto_mac"
        ])
    else:
        print("Sistema operacional não suportado para build automatizado.")

if __name__ == "__main__":
    build_executable()