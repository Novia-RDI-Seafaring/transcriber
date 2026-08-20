"""Plotly scatter for the speaker embedding projection."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from transcriber.models import SpeakerSegment
from transcriber.ui.colors import assign_colors

HOVER_TEXT_LIMIT = 17


def _hover_text(text: str) -> str:
    return text[:HOVER_TEXT_LIMIT] + "..."


def make_scatter(
    projection: np.ndarray,
    segments: list[SpeakerSegment],
    speaker_labels: list[str],
    selected_indices: list[int] | None = None,
) -> go.Figure:
    """Build the lasso-enabled scatter mirroring ``get_scatter_figure`` in the
    original ``app.py``.

    ``selected_indices`` enlarges those markers and adds a black outline; the
    same indices are passed to Plotly as ``selectedpoints`` so the lasso state
    is reflected visually on re-render.
    """
    color_map = assign_colors(speaker_labels)
    colors = [color_map[label] for label in speaker_labels]

    n_points = len(segments)
    if selected_indices:
        selected_set = set(selected_indices)
        sizes = [15 if i in selected_set else 10 for i in range(n_points)]
        line_widths = [3 if i in selected_set else 0 for i in range(n_points)]
    else:
        sizes = 10
        line_widths = 0

    marker = {
        "size": sizes,
        "opacity": 0.8,
        "color": colors,
        "line": {"width": line_widths, "color": "black"},
    }

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=projection[:, 0],
            y=projection[:, 1],
            hovertext=[_hover_text(seg.text) for seg in segments],
            hoverinfo="text",
            mode="markers",
            marker=marker,
            selectedpoints=selected_indices,
            showlegend=False,
            unselected={"marker": {"opacity": 1}},
        )
    )
    fig.update_xaxes(showticklabels=False, automargin=False, showgrid=False)
    fig.update_yaxes(showticklabels=False, automargin=False, showgrid=False)
    fig.update_layout(
        dragmode="lasso",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
    )
    return fig
