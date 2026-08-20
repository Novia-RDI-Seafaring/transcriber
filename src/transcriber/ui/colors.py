"""Deterministic speaker -> color mapping.

A fixed 30-color palette is consumed in label-encounter order so the same
sequence of labels always yields the same colors. Labels beyond the palette
fall back to black.
"""

from __future__ import annotations

PALETTE: list[str] = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
    "#bcbd22",  # yellow-green
    "#17becf",  # cyan
    "#aec7e8",  # light blue
    "#ffbb78",  # light orange
    "#98df8a",  # light green
    "#ff9896",  # light red
    "#c5b0d5",  # light purple
    "#c49c94",  # light brown
    "#f7b6d2",  # light pink
    "#c7c7c7",  # light gray
    "#dbdb8d",  # pale yellow-green
    "#9edae5",  # pale cyan
    "#393b79",  # dark blue
    "#8c6d31",  # dark yellow-brown
    "#b5cf6b",  # yellow-green
    "#5254a3",  # dark purple
    "#6b6ecf",  # medium purple
    "#9c9ede",  # light purple
    "#8ca252",  # olive green
    "#bd9e39",  # gold
    "#e7ba52",  # yellow-gold
    "#ad494a",  # deep red
]

FALLBACK_COLOR: str = "#000000"


def assign_colors(labels: list[str]) -> dict[str, str]:
    """Return a stable label -> color mapping.

    Colors are assigned in the order labels are first encountered. The mapping
    is therefore deterministic for any fixed input order.
    """
    mapping: dict[str, str] = {}
    next_index = 0
    for label in labels:
        if label in mapping:
            continue
        if next_index < len(PALETTE):
            mapping[label] = PALETTE[next_index]
            next_index += 1
        else:
            mapping[label] = FALLBACK_COLOR
    return mapping
