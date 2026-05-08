from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormatProfile:
    profile_id: str
    output_group: str
    yt_dlp_format: str
    requires_ffmpeg: bool
    merge_output_format: str | None = None
    postprocessor: dict | None = None


FORMAT_PROFILES: dict[str, FormatProfile] = {
    "audio_mp3": FormatProfile(
        profile_id="audio_mp3",
        output_group="audios",
        yt_dlp_format="bestaudio/best",
        requires_ffmpeg=True,
        postprocessor={
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        },
    ),
    "audio_m4a": FormatProfile(
        profile_id="audio_m4a",
        output_group="audios",
        yt_dlp_format="bestaudio[ext=m4a]/bestaudio/best",
        requires_ffmpeg=False,
    ),
    "video_mp4": FormatProfile(
        profile_id="video_mp4",
        output_group="video",
        yt_dlp_format="bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bestvideo+bestaudio/best",
        requires_ffmpeg=True,
        merge_output_format="mp4",
    ),
    "video_webm": FormatProfile(
        profile_id="video_webm",
        output_group="video",
        yt_dlp_format="bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]",
        requires_ffmpeg=False,
        merge_output_format="webm",
    ),
}


def get_profile(profile_id: str) -> FormatProfile:
    if profile_id not in FORMAT_PROFILES:
        available = ", ".join(sorted(FORMAT_PROFILES.keys()))
        raise ValueError(
            f"Formato '{profile_id}' não suportado. Formatos disponíveis: {available}"
        )

    return FORMAT_PROFILES[profile_id]
