"""Audio helpers (require ffmpeg)."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import needs_ffmpeg
from transcriber.audio.extract import clip_for_segment
from transcriber.audio.ffmpeg import extract_clip, pad_or_trim, probe_duration
from transcriber.models import Segment


@needs_ffmpeg
def test_probe_duration(silent_wav: Path):
    duration = probe_duration(silent_wav)
    assert 2.9 < duration < 3.1


@needs_ffmpeg
def test_extract_clip(silent_wav: Path, tmp_path: Path):
    out = extract_clip(
        silent_wav,
        tmp_path / "clip.wav",
        start=0.5,
        duration=1.0,
    )
    assert out.exists()
    assert 0.9 < probe_duration(out) < 1.1


@needs_ffmpeg
def test_clip_for_segment(silent_wav: Path, tmp_path: Path):
    seg = Segment(text="hi", start=0.0, end=1.0)
    clip = clip_for_segment(silent_wav, seg, tmp_path, index=0)
    assert clip.path.exists()
    assert clip.start == 0.0
    assert clip.end == 1.0


@needs_ffmpeg
def test_pad_or_trim_pads_short(silent_wav: Path, tmp_path: Path):
    short = tmp_path / "short.wav"
    extract_clip(silent_wav, short, start=0.0, duration=0.5)
    padded = pad_or_trim(short, tmp_path / "padded.wav", target_seconds=2.0)
    assert 1.95 < probe_duration(padded) < 2.05


@needs_ffmpeg
def test_pad_or_trim_trims_long(silent_wav: Path, tmp_path: Path):
    trimmed = pad_or_trim(silent_wav, tmp_path / "trimmed.wav", target_seconds=1.0)
    assert 0.95 < probe_duration(trimmed) < 1.05
