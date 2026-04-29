"""Properties of the core data classes."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from transcriber.models import (
    Clip,
    ClusterResult,
    PipelineResult,
    Segment,
    SpeakerSegment,
    Word,
)


def test_word_is_frozen():
    w = Word("hi", 0.0, 0.5)
    try:
        w.text = "x"  # type: ignore[misc]
    except (AttributeError, Exception):
        return
    raise AssertionError("Word should be frozen")


def test_segment_duration():
    seg = Segment(text="hi", start=1.0, end=3.5)
    assert seg.duration == 2.5


def test_clip_duration(tmp_path: Path):
    clip = Clip(path=tmp_path / "x.wav", start=2.0, end=2.5)
    assert clip.duration == 0.5


def test_speaker_segment_proxies_segment(tmp_path: Path):
    seg = Segment(text="hello", start=0.0, end=1.0)
    clip = Clip(path=tmp_path / "x.wav", start=0.0, end=1.0)
    sp = SpeakerSegment(segment=seg, clip=clip, speaker="Alice")
    assert sp.text == "hello"
    assert sp.start == 0.0
    assert sp.end == 1.0


def test_pipeline_result_speakers():
    seg = Segment(text="hi", start=0.0, end=1.0)
    clip = Clip(path=Path("/tmp/x.wav"), start=0.0, end=1.0)
    speakers = [
        SpeakerSegment(segment=seg, clip=clip, speaker="Alice"),
        SpeakerSegment(segment=seg, clip=clip, speaker=None),
    ]
    cluster = ClusterResult(
        labels=["Alice", "Speaker 2"],
        raw_labels=np.array([0, 1]),
        projection=np.zeros((2, 2)),
        n_clusters=2,
    )
    result = PipelineResult(
        audio_path=Path("/tmp/a.mp3"),
        segments=speakers,
        embeddings=np.zeros((2, 4)),
        cluster=cluster,
    )
    assert result.speakers == ["Alice", "Unknown"]
