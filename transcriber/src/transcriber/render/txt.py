"""Plain-text speaker-labeled transcript output."""

from __future__ import annotations

from collections.abc import Sequence

from transcriber.models import SpeakerSegment


def render_txt(segments: Sequence[SpeakerSegment], *, unknown: str = "Unknown") -> str:
    """Render segments as ``Speaker: text`` blocks, merging consecutive same-speaker turns."""
    if not segments:
        return ""
    lines: list[str] = []
    current_speaker: str | None = None
    buffer: list[str] = []

    for seg in segments:
        speaker = seg.speaker or unknown
        if speaker != current_speaker:
            if current_speaker is not None:
                lines.append(f"{current_speaker}: {' '.join(buffer)}")
            current_speaker = speaker
            buffer = [seg.text]
        else:
            buffer.append(seg.text)

    if current_speaker is not None:
        lines.append(f"{current_speaker}: {' '.join(buffer)}")
    return "\n\n".join(lines)
