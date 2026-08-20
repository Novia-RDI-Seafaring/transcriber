"""SRT subtitle rendering."""

from __future__ import annotations

from collections.abc import Sequence

from transcriber.models import SpeakerSegment


def _srt_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    millis_total = int(round(seconds * 1000))
    h, rem = divmod(millis_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def render_srt(segments: Sequence[SpeakerSegment]) -> str:
    blocks: list[str] = []
    for i, seg in enumerate(segments, start=1):
        text = f"{seg.speaker}: {seg.text}" if seg.speaker else seg.text
        blocks.append(
            f"{i}\n{_srt_timestamp(seg.start)} --> {_srt_timestamp(seg.end)}\n{text}\n"
        )
    return "\n".join(blocks)
