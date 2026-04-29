"""FastAPI backend for the React frontend.

The API is intentionally tiny: it serves a single PipelineResult plus a
mutable speaker-labels store and audio clips. The React app does the
rest. Install via the ``[api]`` extra.
"""

from transcriber.api.server import build_app, run

__all__ = ["build_app", "run"]
