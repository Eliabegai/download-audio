"""Progress hook for Tauri bridge: one JSON object per line prefixed for Rust parsing."""

from __future__ import annotations

import json
import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_PERCENT_RE = re.compile(r"([\d.]+)")


def emit_progress(payload: dict) -> None:
    try:
        line = json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return
    print(f"TAURI_PROGRESS:{line}", flush=True)


def _plain(value) -> str | None:
    if value is None:
        return None
    text = _ANSI_RE.sub("", str(value)).strip()
    return text or None


def _ratio_from_percent_str(raw) -> float | None:
    text = _plain(raw)
    if not text:
        return None
    match = _PERCENT_RE.search(text)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    if 0 <= value <= 100:
        return value / 100.0
    return None


def _download_ratio(progress_dict: dict) -> float | None:
    percent = progress_dict.get("_percent")
    if isinstance(percent, (int, float)):
        return max(0.0, min(float(percent) / 100.0, 1.0))

    total = progress_dict.get("total_bytes") or progress_dict.get("total_bytes_estimate")
    downloaded = progress_dict.get("downloaded_bytes") or 0
    if total:
        return max(0.0, min(downloaded / total, 1.0))

    fragments = progress_dict.get("fragment_count")
    index = progress_dict.get("fragment_index")
    if fragments and index:
        return max(0.0, min(index / fragments, 1.0))

    return _ratio_from_percent_str(progress_dict.get("_percent_str"))


def bridge_progress_hook(progress_dict):
    try:
        _emit_hook_payload(progress_dict)
    except Exception:
        return


def _emit_hook_payload(progress_dict):
    info = progress_dict.get("info_dict") or {}
    playlist_index = info.get("playlist_index")
    playlist_count = info.get("playlist_count") or info.get("n_entries")
    raw_title = info.get("title") or progress_dict.get("filename")
    title = None if raw_title is None else str(raw_title)

    status = progress_dict.get("status")

    if status == "downloading":
        progress = _download_ratio(progress_dict)
        payload = {
            "kind": "downloading",
            "progress": progress,
            "percent": round(progress * 100) if progress is not None else None,
            "percentStr": _plain(progress_dict.get("_percent_str")),
            "speedStr": _plain(progress_dict.get("_speed_str")),
            "etaStr": _plain(progress_dict.get("_eta_str")),
            "title": title,
            "playlistIndex": playlist_index,
            "playlistCount": playlist_count,
        }
    elif status == "finished":
        payload = {
            "kind": "finished",
            "title": title,
            "playlistIndex": playlist_index,
            "playlistCount": playlist_count,
        }
    elif status == "error":
        payload = {
            "kind": "error",
            "title": title,
            "playlistIndex": playlist_index,
            "playlistCount": playlist_count,
        }
    elif status == "post_process":
        payload = {
            "kind": "post-process",
            "title": title,
            "playlistIndex": playlist_index,
            "playlistCount": playlist_count,
        }
    else:
        return

    emit_progress(payload)
