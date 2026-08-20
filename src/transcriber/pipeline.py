"""End-to-end pipeline that turns an audio file into a :class:`PipelineResult`.

Stages, in order:

1. Transcribe (chunked) → ``list[Word]``
2. Group into sentence segments → ``list[Segment]``
3. Extract one WAV clip per segment
4. Embed each clip
5. Cluster embeddings to assign speaker labels
6. Assemble :class:`PipelineResult`

Each stage is cached individually under ``config.work_dir`` keyed on the
audio's content hash + the relevant config slice.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np

from transcriber._logging import get_logger
from transcriber.audio.extract import clips_for_segments, normalize_for_embedding
from transcriber.audio.ffmpeg import ensure_ffmpeg
from transcriber.cache import Cache, file_hash, stable_hash
from transcriber.cluster.kmeans import cluster_embeddings
from transcriber.config import PipelineConfig
from transcriber.embed.base import SpeakerEmbedder
from transcriber.models import (
    Clip,
    PipelineResult,
    Segment,
    SpeakerSegment,
    Word,
)
from transcriber.segment.sentences import group_words_into_segments, merge_short_segments
from transcriber.transcribe.base import Transcriber
from transcriber.transcribe.chunking import transcribe_chunked
from transcriber.transcribe.factory import build_transcriber

log = get_logger(__name__)


def run_pipeline(
    audio_path: Path,
    *,
    config: PipelineConfig | None = None,
    transcriber: Transcriber | None = None,
    embedder: SpeakerEmbedder | None = None,
) -> PipelineResult:
    """Run the full pipeline. ``transcriber`` and ``embedder`` are optional
    overrides — useful for tests and notebooks."""
    cfg = config or PipelineConfig()
    audio_path = Path(audio_path).resolve()
    ensure_ffmpeg()

    cache = Cache(cfg.work_dir, enabled=cfg.use_cache)
    audio_hash = file_hash(audio_path)
    log.info("audio %s sha256=%s", audio_path.name, audio_hash[:12])

    words = _stage_transcribe(audio_path, audio_hash, cfg, cache, transcriber)
    segments = _stage_segment(words, audio_hash, cache)
    clips = _stage_clips(audio_path, segments, audio_hash, cfg, cache)
    embeddings = _stage_embed(clips, audio_hash, cfg, cache, embedder)
    cluster = cluster_embeddings(
        embeddings,
        participants=cfg.cluster.participants,
        max_clusters=cfg.cluster.max_clusters,
        random_state=cfg.cluster.random_state,
        umap_min_dist=cfg.cluster.umap_min_dist,
    )

    speaker_segments = [
        SpeakerSegment(segment=seg, clip=clip, speaker=label)
        for seg, clip, label in zip(segments, clips, cluster.labels, strict=True)
    ]
    return PipelineResult(
        audio_path=audio_path,
        segments=speaker_segments,
        embeddings=embeddings,
        cluster=cluster,
        metadata={"audio_hash": audio_hash},
    )


# ----- stages ------------------------------------------------------------


def _stage_transcribe(
    audio_path: Path,
    audio_hash: str,
    cfg: PipelineConfig,
    cache: Cache,
    transcriber: Transcriber | None,
) -> list[Word]:
    key = stable_hash(audio_hash, asdict(cfg.transcribe))
    cached = cache.get_pickle("transcribe", key)
    if cached is not None:
        log.info("cache hit: transcribe (%d words)", len(cached))
        return cached
    impl = transcriber or build_transcriber(cfg.transcribe)
    words = transcribe_chunked(
        impl,
        audio_path,
        language=cfg.transcribe.language,
        context=cfg.transcribe.context,
        chunk_seconds=cfg.transcribe.chunk_seconds,
    )
    cache.put_pickle("transcribe", key, words)
    return words


def _stage_segment(
    words: list[Word],
    audio_hash: str,
    cache: Cache,
) -> list[Segment]:
    key = stable_hash(audio_hash, "segment-v1", len(words))
    cached = cache.get_pickle("segment", key)
    if cached is not None:
        log.info("cache hit: segment (%d segments)", len(cached))
        return cached
    raw = group_words_into_segments(words)
    segments = merge_short_segments(raw, min_seconds=0.5)
    cache.put_pickle("segment", key, segments)
    return segments


def _stage_clips(
    audio_path: Path,
    segments: list[Segment],
    audio_hash: str,
    cfg: PipelineConfig,
    cache: Cache,
) -> list[Clip]:
    out_dir = cfg.work_dir / "clips" / audio_hash[:16]
    key = stable_hash(audio_hash, "clips-v1", len(segments))
    cached = cache.get_pickle("clip-meta", key)
    if cached is not None and all(Path(c.path).exists() for c in cached):
        log.info("cache hit: clips (%d files)", len(cached))
        return cached
    log.info("extracting %d clips into %s", len(segments), out_dir)
    clips = clips_for_segments(audio_path, segments, out_dir)
    cache.put_pickle("clip-meta", key, clips)
    return clips


def _stage_embed(
    clips: list[Clip],
    audio_hash: str,
    cfg: PipelineConfig,
    cache: Cache,
    embedder: SpeakerEmbedder | None,
) -> np.ndarray:
    key = stable_hash(audio_hash, "embed-v1", len(clips), cfg.cluster.clip_seconds)
    cached_npy = cache.get_npy("embed", key)
    if cached_npy is not None:
        log.info("cache hit: embed shape=%s", cached_npy.shape)
        return cached_npy

    if embedder is None:
        from transcriber.embed.nemo import NemoSpeakerEmbedder

        embedder = NemoSpeakerEmbedder()

    norm_dir = cfg.work_dir / "clips_norm" / audio_hash[:16]
    norm_dir.mkdir(parents=True, exist_ok=True)
    norm_paths = [
        normalize_for_embedding(c, norm_dir, target_seconds=cfg.cluster.clip_seconds) for c in clips
    ]
    embeddings = embedder.embed_files(norm_paths)
    cache.put_npy("embed", key, embeddings)
    return embeddings
