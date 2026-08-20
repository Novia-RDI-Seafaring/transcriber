"""YouTube downloads via ``yt-dlp``.

We download the audio track directly (m4a/webm) and let ffmpeg transcode if
needed. ``yt-dlp`` is an optional dependency — install with
``pip install transcriber[youtube]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from transcriber._logging import get_logger

log = get_logger(__name__)


class YouTubeUnavailableError(RuntimeError):
    """Raised when ``yt-dlp`` is not installed."""


@dataclass(slots=True)
class DownloadResult:
    audio_path: Path
    title: str
    video_id: str


def _import_yt_dlp() -> Any:
    try:
        import yt_dlp  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise YouTubeUnavailableError(
            "yt-dlp is not installed. Install with `pip install transcriber[youtube]`."
        ) from exc
    return yt_dlp


class YouTubeDownloader:
    """Download a YouTube video's audio track to ``out_dir/<id>/<id>.mp3``."""

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str, *, use_cached: bool = True) -> DownloadResult:
        yt_dlp = _import_yt_dlp()
        info = yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}).extract_info(
            url, download=False
        )
        video_id = info["id"]
        title = info.get("title", video_id)
        target_dir = self.out_dir / video_id
        target_dir.mkdir(parents=True, exist_ok=True)
        audio_path = target_dir / f"{video_id}.mp3"

        if use_cached and audio_path.exists():
            log.info("using cached audio at %s", audio_path)
            return DownloadResult(audio_path=audio_path, title=title, video_id=video_id)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(target_dir / f"{video_id}.%(ext)s"),
            "quiet": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return DownloadResult(audio_path=audio_path, title=title, video_id=video_id)


def download_youtube(url: str, out_dir: Path, *, use_cached: bool = True) -> DownloadResult:
    """Convenience wrapper for one-shot use."""
    return YouTubeDownloader(out_dir).download(url, use_cached=use_cached)
