"""Layout for the relabeling UI.

All UI state is held in ``dcc.Store`` components; nothing in this module
references global state. Re-rendering is driven by callbacks registered in
:mod:`transcriber.ui.callbacks`.
"""

from __future__ import annotations

from dash import dcc, html

from transcriber.models import PipelineResult
from transcriber.ui.figure import make_scatter


def build_layout(result: PipelineResult, *, height: int = 300) -> html.Div:
    """Return the root layout for the Dash app."""
    speaker_labels = list(result.cluster.labels)
    initial_figure = make_scatter(
        result.cluster.projection,
        result.segments,
        speaker_labels,
    )

    left_pane = html.Div(
        [
            html.Div(
                [
                    dcc.Graph(
                        id="scatter-plot",
                        config={"displayModeBar": False},
                        figure=initial_figure,
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
                id="dynamic-content",
                children="",
                style={
                    "zIndex": "100",
                    "height": "50px",
                    "verticalAlign": "top",
                    "position": "absolute",
                    "padding": "30px",
                    "width": "450px",
                    "left": "50px",
                    "top": f"{height + 50}px",
                },
            ),
            html.Div(
                id="bottom-ui1",
                children="",
                style={
                    "height": f"{height - 50}px",
                    "verticalAlign": "top",
                    "padding": "30px",
                    "position": "absolute",
                    "top": f"{height + 100}px",
                    "left": "50px",
                    "width": "70%",
                },
            ),
        ],
        style={
            "width": "50%",
            "display": "inline-block",
            "height": "100vh",
            "position": "relative",
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
