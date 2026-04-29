"""Thin wrappers over the system ``ffmpeg`` / ``ffprobe`` binaries.

We shell out rather than depending on a python wrapper to keep the install
footprint small. The original code did the same — this version tightens the
parameters and surfaces errors.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from transcriber._logging import get_logger

log = get_logger(__name__)


class FfmpegError(RuntimeError):
    """Raised when an ffmpeg/ffprobe invocation fails."""


def ensure_ffmpeg() -> None:
    """Raise :class:`FfmpegError` if ``ffmpeg`` or ``ffprobe`` is missing."""
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise FfmpegError(
                f"`{tool}` not found on PATH. Install via Homebrew (`brew install ffmpeg`) "
                "or your distro's package manager."
            )


def _run(cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
    log.debug("running: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise FfmpegError(
            f"command failed ({' '.join(cmd[:2])}…): "
            f"{proc.stderr.decode(errors='replace').strip()}"
        )
    return proc


def probe_duration(path: Path) -> float:
    """Return the duration of an audio/video file in seconds."""
    proc = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    return float(proc.stdout.decode().strip())


def extract_audio_from_video(video_path: Path, audio_path: Path) -> Path:
    """Extract the audio track of a video as MP3."""
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-q:a",
            "0",
            "-map",
            "a",
            str(audio_path),
        ]
    )
    return audio_path


def extract_clip(
    audio_path: Path,
    out_path: Path,
    *,
    start: float,
    duration: float,
    sample_rate: int = 16_000,
    channels: int = 1,
) -> Path:
    """Slice ``[start, start+duration]`` from ``audio_path`` to a 16-bit PCM WAV.

    16 kHz mono is the canonical input shape for the NeMo speaker embedder.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(audio_path),
            "-t",
            f"{duration:.3f}",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            str(out_path),
        ]
    )
    return out_path


def pad_or_trim(
    in_path: Path,
    out_path: Path,
    *,
    target_seconds: float,
    sample_rate: int = 16_000,
    channels: int = 1,
) -> Path:
    """Trim or zero-pad an audio file to exactly ``target_seconds``.

    Speaker embedders behave better when fed a fixed-length window.
    """
    duration = probe_duration(in_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if abs(duration - target_seconds) < 1e-3:
        # already the right length — re-encode anyway to normalize sample rate / channels
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(in_path),
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(sample_rate),
                "-ac",
                str(channels),
                str(out_path),
            ]
        )
        return out_path

    if duration > target_seconds:
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(in_path),
                "-t",
                f"{target_seconds:.3f}",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(sample_rate),
                "-ac",
                str(channels),
                str(out_path),
            ]
        )
    else:
        pad_seconds = target_seconds - duration
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(in_path),
                "-af",
                f"apad=pad_dur={pad_seconds:.3f}",
                "-t",
                f"{target_seconds:.3f}",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(sample_rate),
                "-ac",
                str(channels),
                str(out_path),
            ]
        )
    return out_path
