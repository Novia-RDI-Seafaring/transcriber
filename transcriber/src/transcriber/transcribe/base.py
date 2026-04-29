"""Transcriber protocol and shared helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from transcriber.models import Word


class Transcriber(Protocol):
    """Strategy interface for any speech-to-text backend.

    Implementations must return a flat list of :class:`Word` records covering
    the entire audio file, in order.
    """

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str = "en",
        context: str = "",
    ) -> list[Word]: ...


_PROMPTS: dict[str, str] = {
    "en": "This is a transcription.",
    "da": "Dette er en transskription.",
    "sv": "Detta är en transkription.",
    "no": "Dette er en transkripsjon.",
    "nn": "Dette er ei transkripsjon.",
    "fi": "Tämä on transkriptio.",
    "is": "Þetta er þýðing.",
    "et": "See on transkriptsioon.",
    "de": "Das ist eine Transkription.",
    "fr": "Ceci est une transcription.",
    "es": "Esto es una transcripción.",
    "it": "Questa è una trascrizione.",
}


def initial_prompt(language: str, context: str = "") -> str:
    base = _PROMPTS.get(language, _PROMPTS["en"])
    return f"{base} {context}".strip()
