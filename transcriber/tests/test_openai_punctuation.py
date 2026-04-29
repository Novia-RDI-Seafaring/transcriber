"""Punctuation re-attachment for the OpenAI Whisper backend."""

from __future__ import annotations

from transcriber.models import Word
from transcriber.transcribe.openai import _attach_punctuation


def test_attaches_period():
    text = "Hello world. How are you?"
    words = [
        Word("Hello", 0.0, 0.3),
        Word("world", 0.3, 0.7),
        Word("How", 1.0, 1.2),
        Word("are", 1.2, 1.4),
        Word("you", 1.4, 1.7),
    ]
    out = _attach_punctuation(text, words)
    assert [w.text for w in out] == ["Hello", "world.", "How", "are", "you?"]


def test_preserves_timing():
    words = [Word("Hi", 1.5, 2.0)]
    out = _attach_punctuation("Hi.", words)
    assert out[0].start == 1.5
    assert out[0].end == 2.0
    assert out[0].text == "Hi."


def test_handles_repeated_words():
    """Each word is matched in order from the cursor, not the first match."""
    text = "Yes, yes, yes!"
    words = [Word("Yes", 0.0, 0.2), Word("yes", 0.3, 0.5), Word("yes", 0.6, 0.8)]
    out = _attach_punctuation(text, words)
    assert [w.text for w in out] == ["Yes,", "yes,", "yes!"]


def test_handles_missing_text():
    """Falls back to the originals if text is empty."""
    words = [Word("hi", 0.0, 0.1)]
    out = _attach_punctuation("", words)
    assert [w.text for w in out] == ["hi"]


def test_handles_word_not_in_text():
    """Words that don't appear in text are passed through unchanged."""
    text = "completely different transcript."
    words = [Word("orphan", 0.0, 0.5)]
    out = _attach_punctuation(text, words)
    assert out[0].text == "orphan"


def test_handles_ellipsis_and_dash():
    text = "Wait — really…"
    words = [Word("Wait", 0.0, 0.3), Word("really", 0.5, 1.0)]
    out = _attach_punctuation(text, words)
    assert out[0].text == "Wait"  # space before — is consumed by the cursor walk
    assert out[1].text == "really…"
