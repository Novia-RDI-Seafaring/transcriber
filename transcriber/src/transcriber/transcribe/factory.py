"""Build a transcriber from a :class:`TranscribeConfig`."""

from __future__ import annotations

from transcriber.config import TranscribeConfig
from transcriber.transcribe.base import Transcriber


def build_transcriber(cfg: TranscribeConfig) -> Transcriber:
    if cfg.backend == "openai":
        from transcriber.transcribe.openai import OpenAIWhisperTranscriber

        return OpenAIWhisperTranscriber(model=cfg.openai_model)
    if cfg.backend == "local":
        from transcriber.transcribe.local import FasterWhisperTranscriber

        return FasterWhisperTranscriber(model=cfg.local_model)
    raise ValueError(f"unknown transcribe backend: {cfg.backend!r}")
