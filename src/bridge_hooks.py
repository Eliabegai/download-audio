"""Progress hook for Tauri bridge: one JSON object per line prefixed for Rust parsing."""

from __future__ import annotations

import json


def bridge_progress_hook(progress_dict):
    info = progress_dict.get("info_dict") or {}
    playlist_index = info.get("playlist_index")
    playlist_count = info.get("playlist_count") or info.get("n_entries")
    title = info.get("title") or progress_dict.get("filename")

    status = progress_dict.get("status")

    if status == "downloading":
        total = progress_dict.get("total_bytes") or progress_dict.get(
            "total_bytes_estimate"
        )
        downloaded = progress_dict.get("downloaded_bytes") or 0
        progress = (downloaded / total) if total else None
        payload = {
            "kind": "downloading",
            "progress": progress,
            "percentStr": progress_dict.get("_percent_str"),
            "speedStr": progress_dict.get("_speed_str"),
            "etaStr": progress_dict.get("_eta_str"),
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

    line = json.dumps(payload, ensure_ascii=False)
    print(f"TAURI_PROGRESS:{line}", flush=True)
