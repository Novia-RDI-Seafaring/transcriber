"""OpenAI Whisper API backend.

The verbose_json response with ``timestamp_granularities=["word"]`` returns
words *without* sentence punctuation, but the top-level ``text`` field has
all the punctuation. We re-attach trailing punctuation to each word by
walking the text alongside the word list. Without this step the segmenter
only sees the natural pauses, which produces a handful of huge multi-minute
segments instead of normal sentences.

Requires the ``openai`` extra: ``pip install transcriber[openai]``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transcriber._logging import get_logger
from transcriber.models import Word
from transcriber.transcribe.base import initial_prompt

log = get_logger(__name__)

_TRAILING_PUNCT = ".,?!;:—…"


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

        raw_words = _get(response, "words") or []
        full_text = _get(response, "text") or ""
        words = [_to_word(w) for w in raw_words]
        return _attach_punctuation(full_text, words)


def _to_word(w: Any) -> Word:
    text = _get(w, "word") or _get(w, "text") or ""
    return Word(
        text=str(text),
        start=float(_get(w, "start") or 0.0),
        end=float(_get(w, "end") or 0.0),
    )


def _get(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _attach_punctuation(text: str, words: list[Word]) -> list[Word]:
    """Walk ``words`` alongside ``text`` and reattach trailing punctuation.

    For each word we find its first occurrence in ``text`` starting from the
    last consumed position, then look at the immediately-following non-space
    characters: if any of them are sentence punctuation we append them to
    the word's text. This restores the period/?/! that Whisper strips when
    word-level timestamps are requested.
    """
    if not text or not words:
        return words

    out: list[Word] = []
    cursor = 0
    text_len = len(text)
    for w in words:
        wt = w.text
        idx = text.find(wt, cursor)
        if idx < 0:
            out.append(w)
            continue
        end = idx + len(wt)
        punct = ""
        j = end
        while j < text_len and text[j] in _TRAILING_PUNCT:
            punct += text[j]
            j += 1
        cursor = j
        out.append(Word(text=wt + punct, start=w.start, end=w.end) if punct else w)
    return out
