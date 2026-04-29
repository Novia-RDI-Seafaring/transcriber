"""JSON shapes returned by the API.

These are plain dataclass-like models; we use FastAPI's automatic
serialization with ``response_model`` so the frontend gets a stable
schema. Keeping ``pydantic`` here is fine because FastAPI already pulls
it in.
"""

from __future__ import annotations

from pydantic import BaseModel


class SegmentDTO(BaseModel):
    index: int
    start: float
    end: float
    text: str
    speaker: str
    x: float
    y: float
    clip_url: str


class ResultDTO(BaseModel):
    audio_name: str
    audio_url: str | None
    duration: float
    n_speakers: int
    speakers: list[str]
    segments: list[SegmentDTO]


class LabelsUpdate(BaseModel):
    """A partial update of speaker labels.

    ``mapping`` renames every segment whose current speaker matches the
    key — i.e. it's a cluster-wide rename. ``per_index`` overrides
    individual segments.
    """

    mapping: dict[str, str] = {}
    per_index: dict[int, str] = {}


class LabelsState(BaseModel):
    speakers: list[str]
