import os
import shutil
import sys
from functools import lru_cache


def _project_root() -> str:
    # Este arquivo vive em <root>/src
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _exe_name() -> str:
    return "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"


def _platform_dir() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _bundled_candidates() -> list[str]:
    root = _project_root()
    exe = _exe_name()
    return [
        os.path.join(root, "bin", exe),
        os.path.join(root, "bin", _platform_dir(), exe),
    ]


def _system_candidates() -> list[str]:
    # Apps GUI no macOS não herdam o PATH do shell, então checamos os
    # diretórios usuais de instalação manualmente.
    exe = _exe_name()
    if sys.platform == "darwin":
        dirs = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
    elif sys.platform.startswith("win"):
        dirs = []
    else:
        dirs = ["/usr/bin", "/usr/local/bin", "/bin"]
    return [os.path.join(d, exe) for d in dirs]


@lru_cache(maxsize=1)
def find_ffmpeg() -> str | None:
    """Localiza o binário do FFmpeg, retornando o caminho absoluto ou None."""
    # 1) Override explícito via variável de ambiente (arquivo ou diretório)
    env = os.environ.get("FFMPEG_LOCATION")
    if env:
        if os.path.isdir(env):
            cand = os.path.join(env, _exe_name())
            if os.path.isfile(cand):
                return cand
        elif os.path.isfile(env):
            return env

    # 2) Binário empacotado junto ao projeto (bin/ ou bin/<plataforma>/)
    for cand in _bundled_candidates():
        if os.path.isfile(cand):
            return cand

    # 3) PATH do processo
    found = shutil.which("ffmpeg")
    if found:
        return found

    # 4) Locais comuns de instalação (fallback p/ apps GUI)
    for cand in _system_candidates():
        if os.path.isfile(cand):
            return cand

    return None


def ffmpeg_installed() -> bool:
    return find_ffmpeg() is not None


def ffmpeg_location_for_ydl() -> str | None:
    """Caminho para passar em ydl_opts['ffmpeg_location'] (aceita arquivo ou dir)."""
    return find_ffmpeg()


def ensure_ffmpeg_for_profile(profile_id: str, requires_ffmpeg: bool) -> None:
    if requires_ffmpeg and not ffmpeg_installed():
        raise RuntimeError(
            f"Formato '{profile_id}' requer FFmpeg, mas FFmpeg não foi encontrado no sistema."
        )
