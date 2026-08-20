"""Build sentence-level :class:`Segment` records from word-level timestamps.

Replaces the original ``ExtendableSegment`` + ``combine_subtitle_lines`` logic
with a straight, testable pass that doesn't depend on VTT round-tripping.
"""

from __future__ import annotations

from collections.abc import Iterable

from transcriber.models import Segment, Word

_TERMINATORS: tuple[str, ...] = (".", "?", "!", ";", ":", "—", "...")


def _ends_sentence(text: str) -> bool:
    text = text.rstrip()
    return bool(text) and text.endswith(_TERMINATORS)


def group_words_into_segments(
    words: Iterable[Word],
    *,
    pause_seconds: float = 1.0,
) -> list[Segment]:
    """Group a flat word stream into sentence segments.

    A new segment starts when the previous one ended with a sentence terminator
    *or* there is a silence longer than ``pause_seconds`` between two words.
    The resulting segment text is whitespace-joined and stripped of double
    spaces.
    """
    segments: list[Segment] = []
    current: list[Word] = []

    for word in words:
        if current and (word.start - current[-1].end) > pause_seconds:
            segments.append(_finalize(current))
            current = []
        current.append(word)
        if _ends_sentence(word.text):
            segments.append(_finalize(current))
            current = []

    if current:
        segments.append(_finalize(current))

    return segments


def _finalize(words: list[Word]) -> Segment:
    text = " ".join(w.text.strip() for w in words if w.text.strip())
    text = " ".join(text.split())  # collapse whitespace
    return Segment(text=text, start=words[0].start, end=words[-1].end, words=list(words))


def merge_short_segments(segments: list[Segment], *, min_seconds: float = 0.5) -> list[Segment]:
    """Merge any segment shorter than ``min_seconds`` into the previous one.

    Useful when a speaker-embedding model needs a minimum amount of audio.
    """
    if not segments:
        return []
    merged: list[Segment] = [segments[0]]
    for seg in segments[1:]:
        if seg.duration < min_seconds and merged:
            prev = merged[-1]
            prev.text = (prev.text + " " + seg.text).strip()
            prev.end = seg.end
            prev.words.extend(seg.words)
        else:
            merged.append(seg)
    return merged
