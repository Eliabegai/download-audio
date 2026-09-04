import os
import yt_dlp
from yt_dlp.utils import DownloadError
from hooks import status_downloading, reset_and_set_total
from format_profiles import get_profile
from ffmpeg_utils import ensure_ffmpeg_for_profile, ffmpeg_location_for_ydl
from js_runtime_utils import youtube_compat_opts
from bridge_hooks import bridge_progress_hook, emit_progress

# Clientes extras quando o conjunto padrão ainda devolve 403 / formato indisponível.
_FALLBACK_PLAYER_CLIENTS = (
    ["android", "web_embedded", "web_safari"],
    ["mweb", "web_safari"],
    ["web_embedded", "web_safari"],
    ["android"],
)


def _is_retryable_download_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "403",
            "forbidden",
            "unable to download video data",
            "requested format is not available",
            "only images are available",
        )
    )


def _with_player_clients(opts: dict, clients: list[str]) -> dict:
    merged = dict(opts)
    extractor_args = dict(merged.get("extractor_args") or {})
    youtube = dict(extractor_args.get("youtube") or {})
    youtube["player_client"] = clients
    extractor_args["youtube"] = youtube
    merged["extractor_args"] = extractor_args
    return merged


def _with_format(opts: dict, fmt: str) -> dict:
    merged = dict(opts)
    merged["format"] = fmt
    return merged


def _permissive_formats(ydl_opts: dict) -> list[str]:
    """Formatos mais permissivos quando o seletor do perfil não casa com o cliente."""
    original = str(ydl_opts.get("format") or "")
    has_audio_pp = any(
        isinstance(pp, dict) and pp.get("key") == "FFmpegExtractAudio"
        for pp in (ydl_opts.get("postprocessors") or [])
    )
    if has_audio_pp or "bestaudio" in original:
        candidates = ["bestaudio/best", "best"]
    else:
        candidates = ["bv*+ba/b", "bestvideo+bestaudio/best", "best"]

    return [fmt for fmt in candidates if fmt != original]


def _uses_bridge_hooks(ydl_opts: dict) -> bool:
    return bridge_progress_hook in (ydl_opts.get("progress_hooks") or [])


def _download_with_fallback(url_download, ydl_opts):
    base_attempts = [ydl_opts]
    for fmt in _permissive_formats(ydl_opts):
        base_attempts.append(_with_format(ydl_opts, fmt))

    attempts = []
    for base in base_attempts:
        attempts.append(base)
        attempts.extend(
            _with_player_clients(base, clients) for clients in _FALLBACK_PLAYER_CLIENTS
        )

    notify = _uses_bridge_hooks(ydl_opts)

    last_error = None
    for index, opts in enumerate(attempts):
        if notify and index > 0:
            emit_progress({
                "kind": "retrying",
                "title": url_download,
                "attempt": index + 1,
            })
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url_download])
            return
        except DownloadError as exc:
            last_error = exc
            if not _is_retryable_download_error(exc):
                raise

    if last_error:
        raise last_error


def _base_opts(target_folder, profile, path_cookies, noplaylist=True, progress_hooks=None):
    hooks = progress_hooks if progress_hooks is not None else [status_downloading]
    # Keep filename shorter/stable to avoid filesystem rename failures.
    file_template = '%(title).140B [%(id)s].%(ext)s'

    opts = {
        'format': profile.yt_dlp_format,
        'outtmpl': os.path.join(target_folder, file_template),
        'noplaylist': noplaylist,
        'progress_hooks': hooks,
        'nooverwrites': True,
        'windowsfilenames': True,
        'trim_file_name': 140,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'verbose': False,
    }
    opts.update(youtube_compat_opts(path_cookies))

    ffmpeg_loc = ffmpeg_location_for_ydl()
    if ffmpeg_loc:
        opts['ffmpeg_location'] = ffmpeg_loc

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
    _download_with_fallback(url_download, ydl_opts)
    return audio_folder


def downloadVideo(url_download, output_path, path_cookies=None, profile_id='video_mp4', progress_hooks=None):

    reset_and_set_total(1)
    profile = get_profile(profile_id)
    ensure_ffmpeg_for_profile(profile.profile_id, profile.requires_ffmpeg)
    
    video_folder = os.path.join(output_path, profile.output_group)
    os.makedirs(video_folder, exist_ok=True)
    
    ydl_opts = _base_opts(video_folder, profile, path_cookies, noplaylist=True, progress_hooks=progress_hooks)
    _download_with_fallback(url_download, ydl_opts)
    return video_folder

def downloadPlaylist(url_download, output_path, path_cookies=None, profile_id='audio_mp3', progress_hooks=None):
    profile = get_profile(profile_id)
    ensure_ffmpeg_for_profile(profile.profile_id, profile.requires_ffmpeg)

    info_opts = {
        'noplaylist': False,
        'ignoreerrors': True,
        'extract_flat': 'in_playlist',
        'no_warnings': True,
        'quiet': True,
        'verbose': False,
    }
    info_opts.update(youtube_compat_opts(path_cookies))
    
    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url_download, download=False)

    if not info:
        raise DownloadError(f"Não foi possível obter a playlist: {url_download}")

    playlist_title = info.get('title', 'Playlist_Desconhecida')
    safe_title = "".join(c for c in playlist_title if c.isalnum() or c in (' ', '_')).rstrip()
    
    playlist_folder = os.path.join(output_path, 'playlist', safe_title)
    os.makedirs(playlist_folder, exist_ok=True)
    
    total_videos_na_playlist = len(info.get('entries') or [])

    reset_and_set_total(total_videos_na_playlist)
    
    ydl_opts = _base_opts(playlist_folder, profile, path_cookies, noplaylist=False, progress_hooks=progress_hooks)
    ydl_opts['ignoreerrors'] = True
    _download_with_fallback(url_download, ydl_opts)
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
    _download_with_fallback(titulo, ydl_opts)
    return audio_folder 
