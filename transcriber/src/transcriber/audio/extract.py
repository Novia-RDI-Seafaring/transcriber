"""High-level helpers built on :mod:`transcriber.audio.ffmpeg`."""

from __future__ import annotations

from pathlib import Path

from transcriber.audio.ffmpeg import extract_clip, pad_or_trim
from transcriber.models import Clip, Segment


def clip_for_segment(
    audio_path: Path,
    segment: Segment,
    output_dir: Path,
    *,
    index: int,
    sample_rate: int = 16_000,
) -> Clip:
    """Extract the audio for a single segment to ``output_dir/clip_<i>.wav``."""
    out = output_dir / f"clip_{index:05d}.wav"
    extract_clip(
        audio_path,
        out,
        start=segment.start,
        duration=segment.duration,
        sample_rate=sample_rate,
    )
    return Clip(path=out, start=segment.start, end=segment.end)


def clips_for_segments(
    audio_path: Path,
    segments: list[Segment],
    output_dir: Path,
    *,
    sample_rate: int = 16_000,
) -> list[Clip]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        clip_for_segment(audio_path, seg, output_dir, index=i, sample_rate=sample_rate)
        for i, seg in enumerate(segments)
    ]


def normalize_for_embedding(clip: Clip, output_dir: Path, *, target_seconds: float = 2.0) -> Path:
    """Produce a fixed-length, mono, 16 kHz WAV used as embedder input."""
    out = output_dir / f"{clip.path.stem}_emb.wav"
    return pad_or_trim(clip.path, out, target_seconds=target_seconds)
