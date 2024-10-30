import os
import platform
import subprocess
import urllib.request
import zipfile

def instalar_ffmpeg():
    sistema = platform.system()
    
    if sistema == "Windows":
        print("Baixando e instalando FFmpeg para Windows...")
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        ffmpeg_zip = "ffmpeg.zip"
        
        # Baixa o arquivo zip
        urllib.request.urlretrieve(url, ffmpeg_zip)

        # Extrai o binário e define o PATH
        with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
            zip_ref.extractall("ffmpeg")
        ffmpeg_path = os.path.join("ffmpeg", "ffmpeg-*-essentials_build", "bin")
        os.environ["PATH"] += os.pathsep + os.path.abspath(ffmpeg_path)

        # Limpa o arquivo zip
        os.remove(ffmpeg_zip)
        print("FFmpeg instalado com sucesso para Windows.")

    elif sistema == "Darwin":  # macOS
        print("Instalando FFmpeg para macOS...")
        subprocess.run(["brew", "install", "ffmpeg"])
        
    elif sistema == "Linux":
        print("Instalando FFmpeg para Linux...")
        subprocess.run(["sudo", "apt", "update"])
        subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"])
        
    else:
        print(f"Sistema operacional '{sistema}' não suportado para instalação automática.")