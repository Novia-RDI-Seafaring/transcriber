"""Chunked transcription wraps a backend and shifts word timings."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from transcriber.models import Word
from transcriber.transcribe.chunking import transcribe_chunked


class _FakeTranscriber:
    """Returns one word per call, located at t=0.0..0.5 within the chunk."""

    def __init__(self) -> None:
        self.calls: list[Path] = []

    def transcribe(self, audio_path: Path, *, language: str = "en", context: str = "") -> list[Word]:
        self.calls.append(audio_path)
        return [Word(text=f"chunk{len(self.calls)}", start=0.0, end=0.5)]


def test_short_audio_skips_chunking():
    backend = _FakeTranscriber()
    with patch("transcriber.transcribe.chunking.probe_duration", return_value=30.0):
        words = transcribe_chunked(backend, Path("/tmp/x.mp3"), chunk_seconds=600)
    assert len(backend.calls) == 1
    assert words == [Word("chunk1", 0.0, 0.5)]


def test_long_audio_is_split_and_offsets_applied():
    backend = _FakeTranscriber()
    with (
        patch("transcriber.transcribe.chunking.probe_duration", return_value=1500.0),
        patch("transcriber.transcribe.chunking.extract_clip", return_value=Path("/tmp/c.mp3")),
    ):
        words = transcribe_chunked(backend, Path("/tmp/x.mp3"), chunk_seconds=600)

    # 1500s / 600s = 3 chunks.
    assert len(backend.calls) == 3
    starts = [w.start for w in words]
    # Each chunk word starts at 0.0 in chunk-local time -> 0, 600, 1200 globally.
    assert starts == [0.0, 600.0, 1200.0]
    ends = [w.end for w in words]
    assert ends == [0.5, 600.5, 1200.5]
