"""Dash application factory and entry point."""

from __future__ import annotations

import dash

from transcriber._logging import get_logger
from transcriber.models import PipelineResult
from transcriber.ui.callbacks import register_callbacks
from transcriber.ui.layout import build_layout

log = get_logger(__name__)


def build_app(result: PipelineResult) -> dash.Dash:
    """Construct the Dash app for ``result`` with layout and callbacks wired."""
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    app.title = "Transcriber"
    app.layout = build_layout(result)
    register_callbacks(app, result)
    return app


def launch(result: PipelineResult, *, port: int = 8051, debug: bool = False) -> None:
    """Build the app and start the development server."""
    app = build_app(result)
    log.info("Launching UI on http://127.0.0.1:%d", port)
    app.run(debug=debug, port=port)
