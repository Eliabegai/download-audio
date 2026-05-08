import shutil


def ffmpeg_installed() -> bool:
    return shutil.which("ffmpeg") is not None


def ensure_ffmpeg_for_profile(profile_id: str, requires_ffmpeg: bool) -> None:
    if requires_ffmpeg and not ffmpeg_installed():
        raise RuntimeError(
            f"Formato '{profile_id}' requer FFmpeg, mas FFmpeg não foi encontrado no sistema."
        )
