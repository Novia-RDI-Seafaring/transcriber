"""Transcribe audio to word-level timestamps."""

from transcriber.transcribe.base import Transcriber
from transcriber.transcribe.factory import build_transcriber

__all__ = ["Transcriber", "build_transcriber"]
