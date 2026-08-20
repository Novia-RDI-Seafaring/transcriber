"""Core data model.

Stages of the pipeline produce and consume these typed records. They are
intentionally plain dataclasses (no pydantic) so they remain cheap to
construct and trivial to serialize.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class Word:
    """A single transcribed word with start/end times in seconds."""

    text: str
    start: float
    end: float


@dataclass(slots=True)
class Segment:
    """A sentence-level segment built from contiguous words."""

    text: str
    start: float
    end: float
    words: list[Word] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(slots=True)
class Clip:
    """An audio clip extracted from a segment, on disk."""

    path: Path
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(slots=True)
class SpeakerSegment:
    """A segment with a clip and (after clustering) a speaker label."""

    segment: Segment
    clip: Clip
    speaker: str | None = None

    @property
    def text(self) -> str:
        return self.segment.text

    @property
    def start(self) -> float:
        return self.segment.start

    @property
    def end(self) -> float:
        return self.segment.end


@dataclass(slots=True)
class ClusterResult:
    """Output of the clustering stage.

    ``labels`` is the per-segment speaker label string (e.g. "Speaker 1"),
    aligned with the input segments. ``raw_labels`` is the integer cluster
    id from KMeans. ``projection`` is a 2-D array used for UI scatter plots.
    """

    labels: list[str]
    raw_labels: np.ndarray
    projection: np.ndarray
    n_clusters: int


@dataclass(slots=True)
class PipelineResult:
    """The final composite result that the UI consumes."""

    audio_path: Path
    segments: list[SpeakerSegment]
    embeddings: np.ndarray
    cluster: ClusterResult
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def speakers(self) -> list[str]:
        return [s.speaker or "Unknown" for s in self.segments]
