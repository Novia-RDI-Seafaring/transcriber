"""End-to-end pipeline using fake backends and a generated silent WAV.

This test exercises segmentation + clipping + clustering together. The
clustering extra (sklearn / umap) is required.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from tests.conftest import needs_ffmpeg
from transcriber.config import ClusterConfig, PipelineConfig, TranscribeConfig
from transcriber.models import Word
from transcriber.pipeline import run_pipeline

pytest.importorskip("sklearn")


class _FakeTranscriber:
    def __init__(self, words: list[Word]) -> None:
        self._words = words

    def transcribe(self, audio_path: Path, *, language: str = "en", context: str = "") -> list[Word]:
        return list(self._words)


class _FakeEmbedder:
    """Returns one embedding per file, alternating between two centers."""

    def __init__(self) -> None:
        self.calls: list[Path] = []

    def embed_files(self, paths: Sequence[Path]) -> np.ndarray:
        self.calls.extend(paths)
        rng = np.random.default_rng(42)
        rows = []
        for i in range(len(paths)):
            base = np.array([0.0, 0.0, 0.0]) if i % 2 == 0 else np.array([5.0, 5.0, 5.0])
            rows.append(base + rng.normal(scale=0.05, size=3))
        return np.stack(rows, axis=0)


@needs_ffmpeg
def test_pipeline_runs_with_fakes(silent_wav: Path, tmp_path: Path):
    words = [
        Word("Hello.", 0.0, 0.5),
        Word("Hi.", 1.0, 1.5),
        Word("How", 2.0, 2.3),
        Word("are", 2.3, 2.5),
        Word("you?", 2.5, 2.8),
    ]
    cfg = PipelineConfig(
        transcribe=TranscribeConfig(backend="local", chunk_seconds=600),
        cluster=ClusterConfig(participants=2, clip_seconds=0.5),
        work_dir=tmp_path / "cache",
    )
    result = run_pipeline(
        silent_wav,
        config=cfg,
        transcriber=_FakeTranscriber(words),
        embedder=_FakeEmbedder(),
    )

    assert len(result.segments) >= 1
    assert result.cluster.n_clusters == 2
    assert result.embeddings.ndim == 2
    # Every speaker label is one of two values.
    assert set(result.speakers) <= {"Speaker 1", "Speaker 2"}


@needs_ffmpeg
def test_pipeline_caches_stages(silent_wav: Path, tmp_path: Path):
    words = [Word("One.", 0.0, 0.5), Word("Two.", 1.0, 1.5)]
    embedder = _FakeEmbedder()
    cfg = PipelineConfig(
        transcribe=TranscribeConfig(backend="local"),
        cluster=ClusterConfig(participants=2, clip_seconds=0.5),
        work_dir=tmp_path / "cache",
    )

    transcriber1 = _FakeTranscriber(words)
    run_pipeline(silent_wav, config=cfg, transcriber=transcriber1, embedder=embedder)
    n_calls_first = len(embedder.calls)

    # Second run with fresh fakes - embedder should not be called because the
    # cached numpy is reused.
    embedder2 = _FakeEmbedder()
    run_pipeline(silent_wav, config=cfg, transcriber=transcriber1, embedder=embedder2)
    assert embedder2.calls == [], "second run should hit the embedding cache"
    assert n_calls_first > 0
