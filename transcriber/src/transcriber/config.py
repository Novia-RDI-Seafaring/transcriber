"""Pipeline configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class TranscribeConfig:
    """Settings for the transcription stage."""

    backend: Literal["openai", "local"] = "local"
    language: str = "en"
    context: str = ""
    """Free-form context passed as initial prompt to Whisper."""
    chunk_seconds: int = 600
    """Long-audio chunk size. Each chunk is transcribed independently."""
    local_model: str = "large-v3"
    openai_model: str = "whisper-1"


@dataclass(slots=True)
class ClusterConfig:
    """Settings for the speaker clustering stage."""

    participants: int | None = None
    """If known, the number of speakers. Otherwise selected via silhouette."""
    max_clusters: int = 10
    clip_seconds: float = 2.0
    """Length of audio fed to the speaker embedder per segment."""
    random_state: int = 0
    umap_min_dist: float = 0.0


@dataclass(slots=True)
class PipelineConfig:
    """Top-level configuration for an end-to-end run."""

    transcribe: TranscribeConfig = field(default_factory=TranscribeConfig)
    cluster: ClusterConfig = field(default_factory=ClusterConfig)
    work_dir: Path = field(default_factory=lambda: Path(".transcriber-cache"))
    use_cache: bool = True
