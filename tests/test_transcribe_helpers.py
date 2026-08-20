"""Backend-agnostic transcription helpers."""

from __future__ import annotations

from transcriber.transcribe.base import initial_prompt


def test_initial_prompt_includes_language_phrase():
    assert "transcription" in initial_prompt("en", "")


def test_initial_prompt_falls_back_to_english_for_unknown_language():
    assert initial_prompt("xx", "") == initial_prompt("en", "")


def test_initial_prompt_appends_context():
    prompt = initial_prompt("en", "Discussion about AI policy.")
    assert prompt.endswith("Discussion about AI policy.")
    assert "transcription" in prompt
