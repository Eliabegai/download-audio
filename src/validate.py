import yt_dlp
import re

def validar_url(url, path_cookies=None):
    global total_videos
    url_pattern = re.compile(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$')
    if not url_pattern.match(url):
        print("URL inválida: não corresponde ao formato esperado.")
        return False
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'cookies': path_cookies,
        'extract_flat': 'in_playlist'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            titulo = info.get("title", "Título desconhecido")
            print("URL válida! Título:",titulo)
            if 'entries' in info:
                total_videos = len(info['entries'])
                print(f"Total de vídeos na playlist: {total_videos}")
            return True, titulo
        except yt_dlp.utils.DownloadError:
            print("URL inválida ou conteúdo indisponível.")
            return False