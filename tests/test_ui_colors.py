"""UI color assignment is deterministic and palette-bounded."""

from __future__ import annotations

import pytest

pytest.importorskip("dash")

from transcriber.ui.colors import FALLBACK_COLOR, PALETTE, assign_colors  # noqa: E402


def test_assign_colors_in_order():
    mapping = assign_colors(["B", "A", "B", "C"])
    assert mapping["B"] == PALETTE[0]
    assert mapping["A"] == PALETTE[1]
    assert mapping["C"] == PALETTE[2]


def test_assign_colors_falls_back_after_palette_exhausted():
    labels = [f"S{i}" for i in range(len(PALETTE) + 3)]
    mapping = assign_colors(labels)
    assert mapping[labels[len(PALETTE)]] == FALLBACK_COLOR


def test_assign_colors_handles_empty():
    assert assign_colors([]) == {}
