import os
import shutil
import yt_dlp
from hooks import status_downloading, reset_and_set_total
from format_profiles import get_profile
from ffmpeg_utils import ensure_ffmpeg_for_profile, ffmpeg_location_for_ydl

def _available_js_runtimes():
    runtimes = {}
    if shutil.which('node'):
        runtimes['node'] = {}
    if shutil.which('deno'):
        runtimes['deno'] = {}
    return runtimes

def _base_opts(target_folder, profile, path_cookies, noplaylist=True, progress_hooks=None):
    hooks = progress_hooks if progress_hooks is not None else [status_downloading]
    # Keep filename shorter/stable to avoid filesystem rename failures.
    file_template = '%(title).140B [%(id)s].%(ext)s'

    opts = {
        'format': profile.yt_dlp_format,
        'outtmpl': os.path.join(target_folder, file_template),
        'noplaylist': noplaylist,
        'cookies': path_cookies,
        'cookies-from-browser': ['chrome', 'firefox', 'edge', 'brave'],
        'progress_hooks': hooks,
        'nooverwrites': True,
        'windowsfilenames': True,
        'trim_file_name': 140,
        'quiet': True,
        'nowarnings': True,
        'verbose': False,
    }

    ffmpeg_loc = ffmpeg_location_for_ydl()
    if ffmpeg_loc:
        opts['ffmpeg_location'] = ffmpeg_loc

    js_runtimes = _available_js_runtimes()
    if js_runtimes:
        # yt-dlp API expects dict: {runtime: {config}}
        opts['js_runtimes'] = js_runtimes

    if profile.postprocessor:
        opts['postprocessors'] = [profile.postprocessor]

    if profile.merge_output_format:
        opts['merge_output_format'] = profile.merge_output_format

    return opts

def downloadAudio(url_download, output_path, path_cookies=None, profile_id='audio_mp3', progress_hooks=None):

    reset_and_set_total(1)
    profile = get_profile(profile_id)
    ensure_ffmpeg_for_profile(profile.profile_id, profile.requires_ffmpeg)
    
    audio_folder = os.path.join(output_path, profile.output_group)
    os.makedirs(audio_folder, exist_ok=True)

    ydl_opts = _base_opts(audio_folder, profile, path_cookies, noplaylist=True, progress_hooks=progress_hooks)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])
        
    return audio_folder


def downloadVideo(url_download, output_path, path_cookies=None, profile_id='video_mp4', progress_hooks=None):

    reset_and_set_total(1)
    profile = get_profile(profile_id)
    ensure_ffmpeg_for_profile(profile.profile_id, profile.requires_ffmpeg)
    
    video_folder = os.path.join(output_path, profile.output_group)
    os.makedirs(video_folder, exist_ok=True)
    
    ydl_opts = _base_opts(video_folder, profile, path_cookies, noplaylist=True, progress_hooks=progress_hooks)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])
    
    return video_folder

def downloadPlaylist(url_download, output_path, path_cookies=None, profile_id='audio_mp3', progress_hooks=None):
    profile = get_profile(profile_id)
    ensure_ffmpeg_for_profile(profile.profile_id, profile.requires_ffmpeg)

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
    
    ydl_opts = _base_opts(playlist_folder, profile, path_cookies, noplaylist=False, progress_hooks=progress_hooks)
    ydl_opts['ignoreerrors'] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])
    
    return playlist_folder

def baixar_por_titulo(titulo, output_path, path_cookies=None, profile_id='audio_mp3', progress_hooks=None):
    
    reset_and_set_total(1)
    profile = get_profile(profile_id)
    ensure_ffmpeg_for_profile(profile.profile_id, profile.requires_ffmpeg)
    
    audio_folder = os.path.join(output_path, profile.output_group)
    os.makedirs(audio_folder, exist_ok=True)
    
    ydl_opts = _base_opts(audio_folder, profile, path_cookies, noplaylist=True, progress_hooks=progress_hooks)
    ydl_opts['default_search'] = 'ytsearch'
    ydl_opts['ignoreerrors'] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([titulo])
        
    return audio_folder 
