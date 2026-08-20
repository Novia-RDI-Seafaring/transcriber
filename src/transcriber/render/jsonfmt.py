"""Machine-readable JSON transcript output.

The shape is stable and intended for programmatic consumers (scripts,
agents piping ``transcriber transcribe --format json --output -``):

.. code-block:: json

    {
      "speakers": ["Speaker 1", "Speaker 2"],
      "n_segments": 42,
      "duration": 512.3,
      "segments": [
        {"speaker": "Speaker 1", "start": 0.0, "end": 4.2, "text": "..."}
      ]
    }
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from transcriber.models import SpeakerSegment


def render_json(segments: Sequence[SpeakerSegment], *, unknown: str = "Unknown") -> str:
    """Render segments as a JSON document (see module docstring for the shape)."""
    speakers: list[str] = []
    for seg in segments:
        speaker = seg.speaker or unknown
        if speaker not in speakers:
            speakers.append(speaker)
    doc = {
        "speakers": speakers,
        "n_segments": len(segments),
        "duration": round(max((s.end for s in segments), default=0.0), 3),
        "segments": [
            {
                "speaker": seg.speaker or unknown,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text,
            }
            for seg in segments
        ],
    }
    return json.dumps(doc, ensure_ascii=False, indent=2)
