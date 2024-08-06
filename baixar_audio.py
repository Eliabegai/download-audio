import os
import sys
from yt_dlp import YoutubeDL

def download_and_convert(url, output_path):

    # Cria a pasta "audios" se não existir
    audio_folder = os.path.join(output_path, 'audios')
    os.makedirs(audio_folder, exist_ok=True)

    # Define as opções para yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(audio_folder, '%(title)s.%(ext)s'),
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            },
            {
                'key': 'FFmpegMetadata',
            },
        ],
        'retries': 4,
    }

    # Baixa o áudio do YouTube
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    print("Download e conversão concluídos.")
    print(f"Arquivos salvos na pasta: {audio_folder}")

# Exemplo de uso
if __name__ == "__main__":
    url = input("Digite a URL do vídeo do YouTube: ")
    output_path = os.getcwd()  # Obtém o diretório atual
    download_and_convert(url, output_path)
