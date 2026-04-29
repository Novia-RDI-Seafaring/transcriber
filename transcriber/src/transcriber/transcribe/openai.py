"""OpenAI Whisper API backend.

Requires the ``openai`` extra: ``pip install transcriber[openai]``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transcriber._logging import get_logger
from transcriber.models import Word
from transcriber.transcribe.base import initial_prompt

log = get_logger(__name__)


class OpenAIWhisperTranscriber:
    """Calls the OpenAI Whisper API with word-level timestamps."""

    def __init__(self, *, model: str = "whisper-1", client: Any | None = None) -> None:
        self.model = model
        self._client = client

    def _client_or_default(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "openai not installed. Run `pip install transcriber[openai]`."
            ) from exc
        self._client = OpenAI()
        return self._client

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str = "en",
        context: str = "",
    ) -> list[Word]:
        client = self._client_or_default()
        log.info("openai transcribing %s (lang=%s)", audio_path, language)
        with audio_path.open("rb") as f:
            response = client.audio.transcriptions.create(
                model=self.model,
                file=f,
                response_format="verbose_json",
                prompt=initial_prompt(language, context),
                language=language,
                timestamp_granularities=["word"],
            )

        # Response contains either .words attribute (typed) or dict-style.
        raw_words = getattr(response, "words", None)
        if raw_words is None and isinstance(response, dict):
            raw_words = response.get("words", [])
        return [_to_word(w) for w in raw_words or []]


def _to_word(w: Any) -> Word:
    text = _get(w, "word") or _get(w, "text") or ""
    return Word(text=str(text), start=float(_get(w, "start") or 0.0), end=float(_get(w, "end") or 0.0))


def _get(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
