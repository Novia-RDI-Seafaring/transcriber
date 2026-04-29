"""Gantt-style speaker timeline.

A horizontal strip where each segment is a colored bar spanning
``[start, end]`` on a time axis. Shares the same selection model as the
scatter view: clicking or lasso-selecting a bar surfaces the segment in
the transcript and audio player.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from transcriber.models import SpeakerSegment
from transcriber.ui.colors import assign_colors


def _hms(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def make_timeline(
    segments: list[SpeakerSegment],
    speaker_labels: list[str],
    selected_indices: list[int] | None = None,
    *,
    height: int = 110,
) -> go.Figure:
    """Render a clickable timeline strip for ``segments``.

    Each segment becomes a horizontal bar from ``start`` to ``end``,
    colored by speaker. Selected segments get a black outline matching
    the scatter view.
    """
    color_map = assign_colors(speaker_labels)
    colors = [color_map[label] for label in speaker_labels]

    starts = np.array([seg.start for seg in segments], dtype=float)
    durations = np.array([max(seg.end - seg.start, 0.05) for seg in segments], dtype=float)
    selected_set = set(selected_indices or ())
    line_widths = [2 if i in selected_set else 0 for i in range(len(segments))]

    hover = [
        f"<b>{speaker_labels[i]}</b><br>"
        f"{_hms(seg.start)} → {_hms(seg.end)}<br>"
        f"{seg.text[:80]}{'…' if len(seg.text) > 80 else ''}"
        for i, seg in enumerate(segments)
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=["timeline"] * len(segments),
            x=durations,
            base=starts,
            orientation="h",
            marker={
                "color": colors,
                "line": {"color": "black", "width": line_widths},
            },
            customdata=list(range(len(segments))),
            hovertext=hover,
            hoverinfo="text",
            showlegend=False,
        )
    )
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 10, "b": 30},
        bargap=0,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        dragmode="select",
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        ticksuffix="s",
        rangemode="tozero",
    )
    fig.update_yaxes(showgrid=False, showticklabels=False, zeroline=False)
    return fig
