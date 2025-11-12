import os
import yt_dlp
from hooks import status_downloading, reset_and_set_total

def downloadAudio(url_download, output_path, path_cookies=None):

    reset_and_set_total(1)
    
    audio_folder = os.path.join(output_path, 'audios')
    os.makedirs(audio_folder, exist_ok=True)

    ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(audio_folder, '%(title)s.%(ext)s'),
    'noplaylist': True,
    'cookies': path_cookies,
    'cookies-from-browser': ['chrome', 'firefox', 'edge', 'brave'],
    'progress_hooks': [status_downloading],
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'nooverwrites': True,
    'quiet': True,
    'nowarnings': True,
    'verbose': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])
        
    return audio_folder


def downloadVideo(url_download, output_path, path_cookies=None):

    reset_and_set_total(1)
    
    video_folder = os.path.join(output_path, 'video')
    os.makedirs(video_folder, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(video_folder, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'cookies': path_cookies,
        'cookies-from-browser': ['chrome', 'firefox', 'edge', 'brave'],
        'merge_output_format': 'mp4',
        'progress_hooks': [status_downloading],
        'nooverwrites': True,
        'quiet': True,
        'nowarnings': True,
        'verbose': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])
    
    return video_folder

def downloadPlaylist(url_download, output_path, path_cookies=None):

    info_opts = {
        'noplaylist': False,
        'cookies': path_cookies,
        'cookies-from-browser': ['chrome', 'firefox', 'edge', 'brave'],
        'ignoreerrors': True,
        'extract_flat': 'in_playlist',
        'nowarnings': True,
        'quiet': True,
        'verbose': False,
    }
    
    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url_download, download=False)
    
    playlist_title = info.get('title', 'Playlist_Desconhecida')
    safe_title = "".join(c for c in playlist_title if c.isalnum() or c in (' ', '_')).rstrip()
    
    playlist_folder = os.path.join(output_path, 'playlist', safe_title)
    os.makedirs(playlist_folder, exist_ok=True)
    
    total_videos_na_playlist = len(info.get('entries', []))

    reset_and_set_total(total_videos_na_playlist)
    
    ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(playlist_folder, '%(title)s.%(ext)s'),
    'noplaylist': False,
    'cookies': path_cookies,
    'cookies-from-browser': ['chrome', 'firefox', 'edge', 'brave'],
    'extractaudio': True,
    'progress_hooks': [status_downloading],
    'ignoreerrors': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'nooverwrites': True,
    'quiet': True,
    'nowarnings': True,
    'verbose': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])
    
    return playlist_folder

def baixar_por_titulo(titulo, output_path, path_cookies=None):
    
    reset_and_set_total(1)
    
    audio_folder = os.path.join(output_path, 'audios')
    os.makedirs(audio_folder, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(audio_folder, '%(title)s.%(ext)s'),
        'default_search': 'ytsearch',
        'noplaylist': True,
        'ignoreerrors':True,
        'progress_hooks': [status_downloading],
        'cookies': path_cookies,
        'cookies-from-browser': ['chrome', 'firefox', 'edge', 'brave'],
        'nowarnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'nooverwrites': True,
        'quiet': True,
        'verbose': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([titulo])
        
    return audio_folder 
