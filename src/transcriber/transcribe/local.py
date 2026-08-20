"""Local ``faster-whisper`` backend.

Requires the ``local`` extra: ``pip install transcriber[local]``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transcriber._logging import get_logger
from transcriber.models import Word
from transcriber.transcribe.base import initial_prompt

log = get_logger(__name__)


class FasterWhisperTranscriber:
    """Wraps ``faster_whisper.WhisperModel`` and yields :class:`Word` records."""

    def __init__(self, *, model: str = "large-v3", device: str = "auto") -> None:
        self.model_size = model
        self.device = device
        self._model: Any | None = None

    def _model_or_load(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "faster-whisper not installed. Run `pip install transcriber[local]`."
            ) from exc
        log.info("loading faster-whisper model %s on %s", self.model_size, self.device)
        self._model = WhisperModel(self.model_size, device=self.device)
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str = "en",
        context: str = "",
    ) -> list[Word]:
        model = self._model_or_load()
        log.info("local transcribing %s (lang=%s)", audio_path, language)
        segments, _info = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            beam_size=5,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt(language, context),
            language=language,
        )

        words: list[Word] = []
        for seg in segments:
            for w in (seg.words or []):
                words.append(
                    Word(
                        text=str(w.word).strip(),
                        start=float(w.start),
                        end=float(w.end),
                    )
                )
        return words
