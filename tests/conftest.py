"""Shared pytest fixtures."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from transcriber.models import Clip, ClusterResult, PipelineResult, Segment, SpeakerSegment, Word


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


needs_ffmpeg = pytest.mark.skipif(
    not _ffmpeg_available(), reason="ffmpeg/ffprobe not installed"
)


@pytest.fixture
def words_simple() -> list[Word]:
    """A short word stream with two sentences."""
    return [
        Word("Hello", 0.0, 0.5),
        Word("there.", 0.5, 1.0),
        Word("How", 1.2, 1.5),
        Word("are", 1.5, 1.7),
        Word("you?", 1.7, 2.0),
    ]


@pytest.fixture
def words_with_pause() -> list[Word]:
    """Word stream where a long silence forces a segment break."""
    return [
        Word("First", 0.0, 0.3),
        Word("clause", 0.3, 0.7),
        Word("Second", 5.0, 5.3),
        Word("clause.", 5.3, 5.8),
    ]


@pytest.fixture
def segments_two_speakers() -> list[Segment]:
    return [
        Segment(text="Hi.", start=0.0, end=1.0),
        Segment(text="Hello.", start=1.2, end=2.0),
        Segment(text="How are you?", start=2.5, end=3.5),
    ]


@pytest.fixture
def speaker_segments(segments_two_speakers: list[Segment], tmp_path: Path) -> list[SpeakerSegment]:
    out: list[SpeakerSegment] = []
    for i, seg in enumerate(segments_two_speakers):
        clip = Clip(path=tmp_path / f"c{i}.wav", start=seg.start, end=seg.end)
        speaker = "Alice" if i % 2 == 0 else "Bob"
        out.append(SpeakerSegment(segment=seg, clip=clip, speaker=speaker))
    return out


@pytest.fixture
def fake_embeddings() -> np.ndarray:
    """Two well-separated clusters of 3-D vectors (6 points)."""
    rng = np.random.default_rng(0)
    a = rng.normal(loc=[0.0, 0.0, 0.0], scale=0.05, size=(3, 3))
    b = rng.normal(loc=[5.0, 5.0, 5.0], scale=0.05, size=(3, 3))
    return np.vstack([a, b])


@pytest.fixture
def small_pipeline_result(
    speaker_segments: list[SpeakerSegment], fake_embeddings: np.ndarray, tmp_path: Path
) -> PipelineResult:
    cluster = ClusterResult(
        labels=[s.speaker or "?" for s in speaker_segments],
        raw_labels=np.array([0, 1, 0]),
        projection=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]),
        n_clusters=2,
    )
    return PipelineResult(
        audio_path=tmp_path / "audio.mp3",
        segments=speaker_segments,
        embeddings=fake_embeddings[: len(speaker_segments)],
        cluster=cluster,
    )


@pytest.fixture
def silent_wav(tmp_path: Path) -> Path:
    """Generate a 3-second silent 16 kHz mono WAV with ffmpeg, if available."""
    if not _ffmpeg_available():
        pytest.skip("ffmpeg required to generate audio fixture")
    out = tmp_path / "silent.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=mono:sample_rate=16000",
            "-t",
            "3",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return out
