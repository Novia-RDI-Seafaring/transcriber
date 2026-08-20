"""Word-to-sentence segmentation."""

from __future__ import annotations

from transcriber.models import Word
from transcriber.segment import group_words_into_segments, merge_short_segments


def test_groups_by_terminator(words_simple: list[Word]):
    segs = group_words_into_segments(words_simple)
    assert len(segs) == 2
    assert segs[0].text == "Hello there."
    assert segs[1].text == "How are you?"


def test_breaks_on_long_pause(words_with_pause: list[Word]):
    segs = group_words_into_segments(words_with_pause, pause_seconds=1.0)
    assert len(segs) == 2
    assert segs[0].text == "First clause"
    assert segs[1].text == "Second clause."


def test_segment_timings_track_words(words_simple: list[Word]):
    segs = group_words_into_segments(words_simple)
    assert segs[0].start == 0.0
    assert segs[0].end == 1.0
    assert segs[1].start == 1.2
    assert segs[1].end == 2.0


def test_collapses_extra_whitespace():
    words = [Word("  Hello", 0.0, 0.4), Word("  world.  ", 0.4, 1.0)]
    segs = group_words_into_segments(words)
    assert segs[0].text == "Hello world."


def test_handles_no_terminator():
    words = [Word("trailing", 0.0, 0.5), Word("words", 0.5, 1.0)]
    segs = group_words_into_segments(words)
    assert len(segs) == 1
    assert segs[0].text == "trailing words"


def test_merge_short_segments_combines_with_previous():
    from transcriber.models import Segment

    segs = [
        Segment(text="long enough.", start=0.0, end=1.5),
        Segment(text="tiny", start=1.5, end=1.6),
        Segment(text="ok also long.", start=1.7, end=3.0),
    ]
    merged = merge_short_segments(segs, min_seconds=0.5)
    assert len(merged) == 2
    assert merged[0].text == "long enough. tiny"
    assert merged[0].end == 1.6


def test_merge_keeps_first_short_segment():
    """A short first segment has nothing to merge with."""
    from transcriber.models import Segment

    segs = [Segment(text="hi", start=0.0, end=0.1), Segment(text="bye", start=0.5, end=1.0)]
    merged = merge_short_segments(segs, min_seconds=0.3)
    assert len(merged) == 2  # first stays, second is long enough
