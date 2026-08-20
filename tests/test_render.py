"""Transcript renderers."""

from __future__ import annotations

from pathlib import Path

from transcriber.models import Clip, Segment, SpeakerSegment
from transcriber.render import render_srt, render_txt, render_vtt


def _make(text: str, start: float, end: float, speaker: str) -> SpeakerSegment:
    return SpeakerSegment(
        segment=Segment(text=text, start=start, end=end),
        clip=Clip(path=Path("/tmp/x.wav"), start=start, end=end),
        speaker=speaker,
    )


def test_txt_merges_consecutive_same_speaker():
    segs = [
        _make("Hi.", 0.0, 1.0, "Alice"),
        _make("How are you?", 1.0, 2.0, "Alice"),
        _make("Good.", 2.0, 3.0, "Bob"),
    ]
    out = render_txt(segs)
    assert out == "Alice: Hi. How are you?\n\nBob: Good."


def test_txt_unknown_speaker_label():
    seg = SpeakerSegment(
        segment=Segment(text="Hi.", start=0, end=1),
        clip=Clip(path=Path("/tmp/x.wav"), start=0, end=1),
        speaker=None,
    )
    out = render_txt([seg], unknown="???")
    assert out.startswith("???: ")


def test_txt_empty_segments():
    assert render_txt([]) == ""


def test_vtt_has_header_and_cues():
    segs = [_make("hi", 0.0, 1.0, "Alice")]
    out = render_vtt(segs)
    assert out.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:01.000" in out
    assert "<v Alice>hi" in out


def test_vtt_timestamps_use_three_digit_millis():
    segs = [_make("x", 0.0, 12.345, "Bob")]
    out = render_vtt(segs)
    assert "00:00:12.345" in out


def test_srt_uses_comma_separator_and_indices():
    segs = [
        _make("first", 0.0, 1.0, "A"),
        _make("second", 1.0, 2.5, "B"),
    ]
    out = render_srt(segs)
    assert out.startswith("1\n00:00:00,000 --> 00:00:01,000\nA: first\n")
    assert "2\n00:00:01,000 --> 00:00:02,500\nB: second\n" in out


def test_json_shape():
    import json

    segs = [
        _make("Hi.", 0.0, 1.5, "Alice"),
        _make("Hello.", 1.5, 3.25, "Bob"),
        _make("Bye.", 3.25, 4.0, "Alice"),
    ]
    from transcriber.render import render_json

    doc = json.loads(render_json(segs))
    assert doc["speakers"] == ["Alice", "Bob"]
    assert doc["n_segments"] == 3
    assert doc["duration"] == 4.0
    assert doc["segments"][1] == {
        "speaker": "Bob",
        "start": 1.5,
        "end": 3.25,
        "text": "Hello.",
    }


def test_json_empty_and_unknown():
    import json

    from transcriber.render import render_json

    assert json.loads(render_json([])) == {
        "speakers": [],
        "n_segments": 0,
        "duration": 0.0,
        "segments": [],
    }
    seg = SpeakerSegment(
        segment=Segment(text="Hi.", start=0, end=1),
        clip=Clip(path=Path("/tmp/x.wav"), start=0, end=1),
        speaker=None,
    )
    doc = json.loads(render_json([seg], unknown="???"))
    assert doc["speakers"] == ["???"]
    assert doc["segments"][0]["speaker"] == "???"
