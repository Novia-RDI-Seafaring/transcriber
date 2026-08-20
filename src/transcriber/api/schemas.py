"""JSON shapes returned by the API."""

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
    job_id: str
    audio_name: str
    audio_url: str | None
    duration: float
    n_speakers: int
    speakers: list[str]
    segments: list[SegmentDTO]


class LabelsUpdate(BaseModel):
    """Partial update of speaker labels.

    ``mapping`` renames every segment whose current speaker matches the
    key — i.e. it's a cluster-wide rename. ``per_index`` overrides
    individual segments.
    """

    mapping: dict[str, str] = {}
    per_index: dict[int, str] = {}


class LabelsState(BaseModel):
    speakers: list[str]


class JobDTO(BaseModel):
    id: str
    source: str
    title: str
    backend: str
    language: str
    participants: int | None
    status: str
    stage: str | None
    error: str | None
    duration_seconds: float | None
    n_segments: int | None
    n_speakers: int | None
    created_at: str
    updated_at: str
    completed_at: str | None


class CreateJobRequest(BaseModel):
    source: str
    title: str | None = None
    backend: str = "openai"
    language: str = "en"
    participants: int | None = None
