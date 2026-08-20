"""Timeline figure construction."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("dash")
pytest.importorskip("plotly")

from transcriber.models import Clip, Segment, SpeakerSegment  # noqa: E402
from transcriber.ui.timeline import make_timeline  # noqa: E402


def _seg(text: str, start: float, end: float, speaker: str) -> SpeakerSegment:
    return SpeakerSegment(
        segment=Segment(text=text, start=start, end=end),
        clip=Clip(path=Path("/tmp/x.wav"), start=start, end=end),
        speaker=speaker,
    )


def test_make_timeline_one_bar_per_segment():
    segs = [
        _seg("a", 0.0, 1.0, "Alice"),
        _seg("b", 1.0, 2.0, "Bob"),
        _seg("c", 2.0, 3.5, "Alice"),
    ]
    fig = make_timeline(segs, ["Alice", "Bob", "Alice"])
    bar = fig.data[0]
    assert len(bar.x) == 3
    assert list(bar.base) == [0.0, 1.0, 2.0]
    assert list(bar.x) == [1.0, 1.0, 1.5]
    assert list(bar.customdata) == [0, 1, 2]


def test_make_timeline_colors_mirror_scatter():
    """The timeline must reuse the same color map as the scatter."""
    from transcriber.ui.colors import assign_colors

    segs = [_seg("a", 0.0, 1.0, "Alice"), _seg("b", 1.0, 2.0, "Bob")]
    labels = ["Alice", "Bob"]
    fig = make_timeline(segs, labels)
    expected = list(assign_colors(labels).values())
    assert list(fig.data[0].marker.color) == expected


def test_make_timeline_outline_selected():
    segs = [_seg("a", 0.0, 1.0, "A"), _seg("b", 1.0, 2.0, "B")]
    fig = make_timeline(segs, ["A", "B"], selected_indices=[1])
    line_widths = list(fig.data[0].marker.line.width)
    assert line_widths == [0, 2]


def test_make_timeline_handles_zero_duration():
    """A segment with end == start should still get a positive bar width."""
    segs = [_seg("blip", 5.0, 5.0, "A")]
    fig = make_timeline(segs, ["A"])
    assert list(fig.data[0].x)[0] > 0
