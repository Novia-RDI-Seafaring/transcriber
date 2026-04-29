"""Layout for the relabeling UI.

All UI state is held in ``dcc.Store`` components; nothing in this module
references global state. Re-rendering is driven by callbacks registered in
:mod:`transcriber.ui.callbacks`.
"""

from __future__ import annotations

from dash import dcc, html

from transcriber.models import PipelineResult
from transcriber.ui.figure import make_scatter
from transcriber.ui.timeline import make_timeline

TIMELINE_HEIGHT = 110


def build_layout(result: PipelineResult, *, height: int = 300) -> html.Div:
    """Return the root layout for the Dash app."""
    speaker_labels = list(result.cluster.labels)
    initial_scatter = make_scatter(
        result.cluster.projection,
        result.segments,
        speaker_labels,
    )
    initial_timeline = make_timeline(
        result.segments,
        speaker_labels,
        height=TIMELINE_HEIGHT,
    )

    left_pane = html.Div(
        [
            html.Div(
                [
                    dcc.Graph(
                        id="scatter-plot",
                        config={"displayModeBar": False},
                        figure=initial_scatter,
                    )
                ],
                style={
                    "width": "100%",
                    "display": "inline-block",
                    "height": f"{height}px",
                    "marginTop": "-30px",
                },
            ),
            html.Div(
                [
                    dcc.Graph(
                        id="timeline",
                        config={"displayModeBar": False},
                        figure=initial_timeline,
                    )
                ],
                style={
                    "width": "100%",
                    "display": "inline-block",
                    "height": f"{TIMELINE_HEIGHT}px",
                },
            ),
            html.Div(
                id="dynamic-content",
                children="",
                style={
                    "zIndex": "100",
                    "verticalAlign": "top",
                    "padding": "10px 30px",
                    "width": "450px",
                },
            ),
            html.Div(
                id="bottom-ui1",
                children="",
                style={
                    "verticalAlign": "top",
                    "padding": "10px 30px",
                    "width": "90%",
                },
            ),
        ],
        style={
            "width": "50%",
            "display": "inline-block",
            "height": "100vh",
            "verticalAlign": "top",
        },
    )

    right_pane = html.Div(
        [
            html.H2(children="Transcript"),
            html.Div(id="transcript", children="", style={"verticalAlign": "top"}),
        ],
        style={
            "width": "50%",
            "height": "90vh",
            "display": "inline-block",
            "verticalAlign": "top",
            "overflowY": "scroll",
        },
    )

    return html.Div(
        [
            left_pane,
            right_pane,
            dcc.Store(id="speaker-labels", data=speaker_labels),
            dcc.Store(id="selected-clip", data=None),
            dcc.Store(id="selected-speakers", data=None),
            dcc.Store(id="selected-data", data=None),
            dcc.Store(id="highlighted-point", data=None),
        ],
        style={"backgroundColor": "white"},
    )
