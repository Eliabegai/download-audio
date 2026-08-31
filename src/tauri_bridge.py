"""
CLI bridge called by Tauri desktop app.

Stdin: JSON body per invocation.
Stdout:
  - preview | search: single JSON object line (only JSON on stdout)
  - download: lines prefixed with TAURI_PROGRESS:{json}; stderr has errors
"""

from __future__ import annotations

import json
import os
import sys

from js_runtime_utils import youtube_compat_opts


def _repo_src_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _ensure_import_path() -> None:
    src_dir = _repo_src_dir()
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


def _looks_like_youtube_url(text: str) -> bool:
    t = text.lower()
    return "youtube.com" in t or "youtu.be" in t


def _cookies_path(data: dict) -> str | None:
    p = data.get("cookiesPath") or data.get("cookies_path")
    if not p:
        return None
    return str(p) if os.path.isfile(str(p)) else None


def _default_output_path() -> str:
    return os.path.join(os.path.expanduser("~"), "Downloads", "Musica")


def _emit_progress(payload: dict) -> None:
    line = json.dumps(payload, ensure_ascii=False)
    print(f"TAURI_PROGRESS:{line}", flush=True)


def cmd_preview(data: dict) -> dict:
    _ensure_import_path()
    import yt_dlp  # noqa: PLC0415

    raw_input = (data.get("input") or "").strip()
    if not raw_input:
        raise ValueError("input vazio")

    cookies = _cookies_path(data)
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
    }
    opts.update(youtube_compat_opts(cookies))

    with yt_dlp.YoutubeDL(opts) as ydl:
        if _looks_like_youtube_url(raw_input):
            info = ydl.extract_info(raw_input, download=False)
        else:
            info = ydl.extract_info(f"ytsearch1:{raw_input}", download=False)
            entries = info.get("entries") or []
            if entries:
                info = entries[0]

    thumb = info.get("thumbnail") or ""
    thumbs = info.get("thumbnails") or []
    if not thumb and thumbs:
        thumb = thumbs[-1].get("url") or thumbs[0].get("url") or ""

    return {
        "title": info.get("title") or "Sem título",
        "thumbnail": thumb or "",
    }


def cmd_search(data: dict) -> list:
    _ensure_import_path()
    import yt_dlp  # noqa: PLC0415

    query = (data.get("query") or "").strip()
    if len(query) < 2:
        raise ValueError("query muito curta")

    limit = int(data.get("limit") or 5)
    limit = max(1, min(limit, 5))

    cookies = _cookies_path(data)
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "ignoreerrors": True,
    }
    opts.update(youtube_compat_opts(cookies))

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

    entries = info.get("entries") or []
    out = []
    for entry in entries[:limit]:
        if not entry:
            continue
        url = entry.get("url") or entry.get("webpage_url") or ""
        vid = entry.get("id")
        if not url and vid:
            url = f"https://www.youtube.com/watch?v={vid}"
        title = entry.get("title") or "Sem título"
        thumbs = entry.get("thumbnails") or []
        thumb = (
            entry.get("thumbnail")
            or (thumbs[0].get("url") if thumbs else "")
            or ""
        )
        if url:
            out.append({"title": title, "url": url, "thumbnail": thumb})

    return out


def cmd_download(data: dict) -> None:
    _ensure_import_path()
    import yt_dlp  # noqa: PLC0415
    from bridge_hooks import bridge_progress_hook  # noqa: PLC0415
    from functions_download import (  # noqa: PLC0415
        downloadAudio,
        downloadPlaylist,
        downloadVideo,
    )

    mode = (data.get("mode") or "").strip().lower()
    profile_id = (data.get("profileId") or data.get("profile_id") or "").strip()
    url_or_term = (data.get("input") or "").strip()
    output_path = (data.get("outputPath") or data.get("output_path") or "").strip()
    cookies_arg = data.get("cookiesPath") or data.get("cookies_path")
    cookies = str(cookies_arg) if cookies_arg and os.path.isfile(str(cookies_arg)) else None

    if not url_or_term:
        raise ValueError("input vazio")
    if mode not in ("audio", "video", "playlist"):
        raise ValueError(f"mode inválido: {mode}")
    if not profile_id:
        raise ValueError("profileId vazio")

    target_dir = output_path if output_path else _default_output_path()
    os.makedirs(target_dir, exist_ok=True)

    started_title = url_or_term
    if mode != "playlist":
        info_opts = {
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "skip_download": True,
        }
        info_opts.update(youtube_compat_opts(cookies))
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url_or_term, download=False)
        started_title = info.get("title") or url_or_term

    _emit_progress({"kind": "started", "mode": mode, "title": started_title})

    if mode == "playlist":
        info_opts = {
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "extract_flat": "in_playlist",
        }
        info_opts.update(youtube_compat_opts(cookies))
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url_or_term, download=False)
        total = len(info.get("entries") or [])
        _emit_progress(
            {
                "kind": "playlist-meta",
                "playlistCount": total,
                "title": info.get("title") or "Playlist",
            }
        )

    hook = [bridge_progress_hook]

    if mode == "audio":
        downloadAudio(url_or_term, target_dir, cookies, profile_id, progress_hooks=hook)
    elif mode == "video":
        downloadVideo(url_or_term, target_dir, cookies, profile_id, progress_hooks=hook)
    else:
        downloadPlaylist(url_or_term, target_dir, cookies, profile_id, progress_hooks=hook)

    _emit_progress({"kind": "batch-finished"})


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: tauri_bridge.py <preview|search|download>", file=sys.stderr)
        return 2

    op = sys.argv[1].strip().lower()
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"JSON inválido: {exc}"}), file=sys.stderr)
        return 2

    try:
        if op == "preview":
            result = cmd_preview(data)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if op == "search":
            result = cmd_search(data)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if op == "download":
            cmd_download(data)
            return 0
        print(json.dumps({"error": f"op desconhecida: {op}"}), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
