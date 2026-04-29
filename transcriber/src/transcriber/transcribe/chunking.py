"""Chunked transcription for long audio.

Long inputs (interviews, podcasts) are sliced into fixed-length pieces, each
transcribed independently, then word timings are shifted back into the global
timeline.

This replaces the original ``transcribe()`` chunk loop, which mutated state via
text-substitution on VTT strings.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from transcriber._logging import get_logger
from transcriber.audio.ffmpeg import extract_clip, probe_duration
from transcriber.models import Word
from transcriber.transcribe.base import Transcriber

log = get_logger(__name__)


def transcribe_chunked(
    transcriber: Transcriber,
    audio_path: Path,
    *,
    language: str = "en",
    context: str = "",
    chunk_seconds: int = 600,
) -> list[Word]:
    """Transcribe a long audio file in fixed-length chunks.

    The chunk audio is written to a temp directory and cleaned up on exit.
    """
    duration = probe_duration(audio_path)
    if duration <= chunk_seconds:
        return transcriber.transcribe(audio_path, language=language, context=context)

    n_chunks = int(duration // chunk_seconds) + (1 if duration % chunk_seconds else 0)
    log.info("chunking %.1fs audio into %d × %ds pieces", duration, n_chunks, chunk_seconds)

    words: list[Word] = []
    with TemporaryDirectory(prefix="transcriber-chunk-") as tmp:
        tmp_path = Path(tmp)
        for i in range(n_chunks):
            start = i * chunk_seconds
            length = min(chunk_seconds, duration - start)
            # WAV (PCM 16-bit, 16 kHz mono) keeps the chunk frame-accurate
            # via re-encode (-ss is honored exactly) and stays well under
            # OpenAI Whisper's 25 MB upload cap for a 10 min chunk
            # (600 s × 32 kB/s ≈ 19 MB). Earlier versions named the file
            # ``.mp3`` which clashes with the PCM codec we ask for.
            chunk_file = tmp_path / f"chunk_{i:03d}.wav"
            extract_clip(
                audio_path,
                chunk_file,
                start=start,
                duration=length,
                sample_rate=16_000,
                channels=1,
            )
            chunk_words = transcriber.transcribe(
                chunk_file, language=language, context=context
            )
            offset = float(start)
            words.extend(
                Word(text=w.text, start=w.start + offset, end=w.end + offset)
                for w in chunk_words
            )
    return words
