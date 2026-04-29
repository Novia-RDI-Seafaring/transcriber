"""Callback wiring for the relabeling UI.

Mirrors the behavior of the original ``app.py``:

* lasso selection on the scatter stores selected points;
* clicking a point highlights it;
* a name input + submit button assigns a label to the current selection;
* the right-hand transcript reflects current labels and the highlighted point;
* clicking a transcript paragraph promotes it to the highlighted point;
* the highlighted segment renders an audio player on the bottom-left.

Audio is embedded as a base64 ``data:`` URL so the app does not depend on
Dash's static asset folder.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import dash
from dash import ALL, Input, Output, State, dcc, html

from transcriber._logging import get_logger
from transcriber.models import PipelineResult
from transcriber.ui.colors import assign_colors
from transcriber.ui.figure import make_scatter

log = get_logger(__name__)

_AUDIO_MIME_TYPES: dict[str, str] = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".flac": "audio/flac",
}


def _audio_mime(path: Path) -> str:
    return _AUDIO_MIME_TYPES.get(path.suffix.lower(), "audio/mpeg")


def _encode_audio(path: Path) -> str:
    """Return a ``data:`` URL with base64-encoded audio for ``path``."""
    mime = _audio_mime(path)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def register_callbacks(app: dash.Dash, result: PipelineResult) -> None:
    """Register all interactive callbacks against ``app``.

    The ``result`` is captured by closure; segments and the projection are
    treated as immutable. Speaker labels live in the ``speaker-labels`` store
    so relabeling is fully reactive and free of module-level state.
    """
    segments = result.segments
    projection = result.cluster.projection

    @app.callback(
        Output("selected-data", "data"),
        Input("scatter-plot", "selectedData"),
        prevent_initial_call=True,
    )
    def store_selected_data(selected_data: dict[str, Any] | None) -> dict[str, Any] | None:
        return selected_data

    @app.callback(
        Output("highlighted-point", "data"),
        Input("scatter-plot", "clickData"),
        prevent_initial_call=True,
    )
    def store_highlighted_point(click_data: dict[str, Any] | None) -> list[int] | None:
        if click_data:
            point_index = click_data["points"][0]["pointIndex"]
            return [point_index]
        return None

    @app.callback(
        Output("dynamic-content", "children"),
        Output("selected-speakers", "data"),
        Input("selected-data", "data"),
        Input("highlighted-point", "data"),
        prevent_initial_call=True,
    )
    def update_ui_for_naming(
        selected_data: dict[str, Any] | None,
        highlighted_point: list[int] | None,
    ) -> tuple[Any, dict[str, Any] | None]:
        no_lasso_points = (
            selected_data is None
            or ("points" in selected_data and len(selected_data["points"]) == 0)
        )
        if no_lasso_points and highlighted_point is not None:
            selected_data = {"points": [{"pointIndex": highlighted_point[0]}]}

        if selected_data and "points" in selected_data:
            naming_form = html.Div(
                [
                    dcc.Input(
                        id="name-input",
                        type="text",
                        placeholder="Enter name...",
                        value="",
                    ),
                    html.Button("Submit", id="submit-button", n_clicks=0),
                ]
            )
            return naming_form, selected_data
        return "No points selected.", selected_data

    @app.callback(
        Output("speaker-labels", "data"),
        Output("scatter-plot", "figure", allow_duplicate=True),
        Output("highlighted-point", "data", allow_duplicate=True),
        Input("submit-button", "n_clicks"),
        State("speaker-labels", "data"),
        State("selected-speakers", "data"),
        State("name-input", "value"),
        State("highlighted-point", "data"),
        prevent_initial_call=True,
    )
    def handle_name_submission(
        n_clicks: int,
        speakers: list[str],
        selected_data: dict[str, Any] | None,
        name: str | None,
        highlighted_point: list[int] | None,
    ) -> tuple[list[str], Any, Any]:
        if name and selected_data:
            indices = [point["pointIndex"] for point in selected_data["points"]]
            for idx in indices:
                speakers[idx] = name
            cleared_highlight = None
            figure = make_scatter(
                projection,
                segments,
                speakers,
                selected_indices=cleared_highlight,
            )
            return speakers, figure, cleared_highlight
        return speakers, dash.no_update, dash.no_update

    @app.callback(
        Output("transcript", "children"),
        Output("bottom-ui1", "children"),
        Output("highlighted-point", "data", allow_duplicate=True),
        Output("scatter-plot", "figure", allow_duplicate=True),
        Input("speaker-labels", "data"),
        Input("highlighted-point", "data"),
        Input({"type": "transcript-p", "index": ALL}, "n_clicks"),
        State("scatter-plot", "selectedData"),
        State({"type": "transcript-p", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def update_transcript_and_audio(
        speakers: list[str],
        highlighted_point: list[int] | None,
        n_clicks: list[int],
        selected_data: dict[str, Any] | None,
        ids: list[dict[str, Any]],
    ) -> tuple[Any, Any, Any, Any]:
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

        if (
            selected_data is not None
            and "points" in selected_data
            and len(selected_data["points"]) > 0
        ):
            return dash.no_update, None, dash.no_update, dash.no_update

        triggered_prop_id = ctx.triggered[0]["prop_id"]
        color_map = assign_colors(speakers)

        if (
            "highlighted-point.data" in triggered_prop_id
            or "speaker-labels.data" in triggered_prop_id
        ):
            selected_indices = highlighted_point
            point_index = highlighted_point[0] if highlighted_point else None
        elif "transcript-p" in triggered_prop_id:
            clicked_id = triggered_prop_id.split(".")[0]
            point_index = int(json.loads(clicked_id)["index"])
            selected_indices = [point_index]
        elif "scatter-plot.selectedData" in triggered_prop_id and selected_data:
            selected_indices = [
                point["pointIndex"] for point in selected_data["points"]
            ]
            point_index = selected_indices[0] if selected_indices else None
        else:
            selected_indices = None
            point_index = None

        transcript_children = _build_transcript(
            segments=segments,
            speakers=speakers,
            color_map=color_map,
            point_index=point_index,
        )

        if point_index is not None:
            audio_player = _build_audio_player(
                segment=segments[point_index],
                point_index=point_index,
            )
            figure = make_scatter(
                projection,
                segments,
                speakers,
                selected_indices=selected_indices,
            )
            return transcript_children, audio_player, selected_indices, figure

        return transcript_children, dash.no_update, dash.no_update, dash.no_update

    app.clientside_callback(
        """
        function (n_clicks) {
            if (n_clicks === 0) return window.dash_clientside.no_update;

            var highlightedElements = document.querySelectorAll('[id^="highlighted-"]');
            if (highlightedElements.length === 0) return window.dash_clientside.no_update;

            var highlighted = highlightedElements[highlightedElements.length - 1];
            var scrollableDiv = document.getElementById('transcript');

            if (!highlighted || !scrollableDiv) return window.dash_clientside.no_update;

            var scrollTop = highlighted.offsetTop - scrollableDiv.offsetTop
                - (scrollableDiv.clientHeight / 2)
                + (highlighted.clientHeight / 2);

            scrollableDiv.scrollTop = scrollTop;

            return window.dash_clientside.no_update;
        }
        """,
        Output("selected-clip", "data", allow_duplicate=True),
        Input("highlight", "n_clicks"),
        prevent_initial_call=True,
    )


def _build_transcript(
    *,
    segments: list,
    speakers: list[str],
    color_map: dict[str, str],
    point_index: int | None,
) -> list[Any]:
    transcript: list[Any] = []
    paragraph_style = {"cursor": "pointer", "margin": "0px", "padding": "10px"}
    for index, segment in enumerate(segments):
        background_color = color_map.get(speakers[index], "#000000")
        ball_style = {
            "display": "inline-block",
            "width": "10px",
            "height": "10px",
            "backgroundColor": background_color,
            "borderRadius": "50%",
            "marginRight": "10px",
        }
        ball_span = html.Span(style=ball_style)
        body_text = f"{speakers[index]}: {segment.text}"
        if point_index is not None and index == point_index:
            body = html.B(body_text, id=f"highlighted-{index}")
        else:
            body = html.Span(body_text)
        transcript.append(
            html.P(
                [ball_span, body],
                style=paragraph_style,
                id={"type": "transcript-p", "index": index},
                n_clicks=0,
            )
        )
    return transcript


def _build_audio_player(*, segment, point_index: int) -> list[Any]:
    clip_path = Path(segment.clip.path)
    encoded_sound = _encode_audio(clip_path)
    return [
        html.H3(f"Listen to {point_index}"),
        html.Audio(
            id="audio_player",
            src=encoded_sound,
            controls=True,
            autoPlay=True,
        ),
        html.P([html.Strong("Clip: "), str(clip_path)]),
        html.P([html.Strong("Text: "), segment.text]),
        html.Button("Highlight text", id="highlight", n_clicks=0),
    ]
