import os
import yt_dlp
from hooks import status_downloading

def downloadAudio(url_download, output_path, return_filepath=False, path_cookies=None):

    audio_folder = os.path.join(output_path, 'audios')
    os.makedirs(audio_folder, exist_ok=True)
    downloaded_file = {'path': None}

    def capture_path_hook(d):
        if d['status'] == 'finished':
            downloaded_file['path'] = d['filename']

    ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(audio_folder, '%(title)s.%(ext)s'),
    'noplaylist': True,
    'cookies': path_cookies,
    'progress_hooks': [status_downloading],                    # Função de hook para monitorar progresso
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'nooverwrites': True,
    'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])
    
    print("Download e conversão concluídos!")

    if return_filepath:
        return downloaded_file['path']