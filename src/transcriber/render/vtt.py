"""WebVTT subtitle rendering."""

from __future__ import annotations

from collections.abc import Sequence

from transcriber.models import SpeakerSegment


def _vtt_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    millis_total = int(round(seconds * 1000))
    h, rem = divmod(millis_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def render_vtt(segments: Sequence[SpeakerSegment], *, include_speaker: bool = True) -> str:
    cues: list[str] = ["WEBVTT", ""]
    for seg in segments:
        cue_text = (
            f"<v {seg.speaker}>{seg.text}" if include_speaker and seg.speaker else seg.text
        )
        cues.append(f"{_vtt_timestamp(seg.start)} --> {_vtt_timestamp(seg.end)}")
        cues.append(cue_text)
        cues.append("")
    return "\n".join(cues).rstrip() + "\n"
