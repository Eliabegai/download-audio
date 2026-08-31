"""Localiza runtimes JS para o yt-dlp resolver desafios do YouTube.

Apps GUI (Tauri) no macOS não herdam o PATH do shell, então Node instalado
via nvm/fnm/Homebrew não aparece em shutil.which('node'). Sem runtime, o
yt-dlp não consegue assinar as URLs e o YouTube responde 403.
"""

from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache


_RUNTIME_NAMES = ("deno", "node", "bun")


def _home() -> str:
    return os.path.expanduser("~")


def _exe(name: str) -> str:
    return f"{name}.exe" if sys.platform.startswith("win") else name


def _is_executable(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)


def _common_bin_dirs() -> list[str]:
    home = _home()
    dirs: list[str] = []

    if sys.platform == "darwin":
        dirs.extend(["/opt/homebrew/bin", "/usr/local/bin"])
    elif sys.platform.startswith("win"):
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        dirs.append(os.path.join(program_files, "nodejs"))
    else:
        dirs.extend(["/usr/local/bin", "/usr/bin"])

    dirs.extend(
        [
            os.path.join(home, ".local", "bin"),
            os.path.join(home, ".deno", "bin"),
            os.path.join(home, ".volta", "bin"),
            os.path.join(home, ".asdf", "shims"),
            os.path.join(home, ".fnm", "aliases", "default", "bin"),
            os.path.join(home, ".local", "share", "fnm", "aliases", "default", "bin"),
        ]
    )
    return dirs


def _nvm_node_bins() -> list[str]:
    nvm_dir = os.environ.get("NVM_DIR") or os.path.join(_home(), ".nvm")
    versions_dir = os.path.join(nvm_dir, "versions", "node")
    bins: list[str] = []

    alias_file = os.path.join(nvm_dir, "alias", "default")
    if os.path.isfile(alias_file):
        try:
            with open(alias_file, encoding="utf-8") as fh:
                ver = fh.read().strip()
        except OSError:
            ver = ""
        if ver:
            if not ver.startswith("v"):
                ver = f"v{ver}"
            bins.append(os.path.join(versions_dir, ver, "bin", _exe("node")))

    if os.path.isdir(versions_dir):
        try:
            versions = sorted(os.listdir(versions_dir), reverse=True)
        except OSError:
            versions = []
        for ver in versions:
            bins.append(os.path.join(versions_dir, ver, "bin", _exe("node")))

    return bins


def _candidate_paths(name: str) -> list[str]:
    exe = _exe(name)
    candidates: list[str] = []

    found = shutil.which(name)
    if found:
        candidates.append(found)

    for directory in _common_bin_dirs():
        candidates.append(os.path.join(directory, exe))

    if name == "node":
        candidates.extend(_nvm_node_bins())

    # Dedup preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for path in candidates:
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        unique.append(path)
    return unique


def _find_runtime(name: str) -> str | None:
    for path in _candidate_paths(name):
        if _is_executable(path):
            return path
    return None


def ensure_gui_path() -> None:
    """Inclui diretórios usuais de Node/Deno no PATH deste processo."""
    extra: list[str] = []
    for name in _RUNTIME_NAMES:
        found = _find_runtime(name)
        if found:
            extra.append(os.path.dirname(found))
    extra.extend(_common_bin_dirs())

    current = os.environ.get("PATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    prepended = [d for d in extra if d and d not in parts and os.path.isdir(d)]
    if prepended:
        os.environ["PATH"] = os.pathsep.join(prepended + parts)


@lru_cache(maxsize=1)
def available_js_runtimes() -> dict:
    """Dict no formato da API do yt-dlp: {runtime: {path: abs}}."""
    ensure_gui_path()
    runtimes = {}
    for name in _RUNTIME_NAMES:
        path = _find_runtime(name)
        if path:
            runtimes[name] = {"path": path}
    return runtimes


def require_js_runtime() -> dict:
    runtimes = available_js_runtimes()
    if not runtimes:
        raise RuntimeError(
            "Nenhum runtime JavaScript encontrado (Node.js 22+ ou Deno). "
            "O YouTube exige isso para baixar. Instale Node.js 22+ ou Deno e tente de novo."
        )
    return runtimes


def youtube_compat_opts(cookies_path: str | None = None) -> dict:
    """Opções yt-dlp necessárias para extração atual do YouTube."""
    opts: dict = {
        "js_runtimes": require_js_runtime(),
        "remote_components": {"ejs:github"},
        "extractor_args": {
            "youtube": {
                # android_vr/android_sdkless devolvem URLs que o YouTube recusa com 403.
                "player_client": [
                    "default",
                    "-android_vr",
                    "-android_sdkless",
                ],
            }
        },
        # Poucas tentativas no mesmo cliente: falha rápido e o fallback troca de client.
        "retries": 2,
        "fragment_retries": 3,
        "extractor_retries": 3,
    }
    if cookies_path:
        opts["cookiefile"] = cookies_path
    return opts
