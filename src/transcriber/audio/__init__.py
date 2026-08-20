"""Audio I/O: probing, slicing, normalization, video-to-audio."""

from transcriber.audio.ffmpeg import (
    ensure_ffmpeg,
    extract_audio_from_video,
    extract_clip,
    pad_or_trim,
    probe_duration,
)

__all__ = [
    "ensure_ffmpeg",
    "extract_audio_from_video",
    "extract_clip",
    "pad_or_trim",
    "probe_duration",
]
