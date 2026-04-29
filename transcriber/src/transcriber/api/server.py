"""FastAPI app factory.

Creates an app that owns a :class:`PipelineResult` (mutable on the
``speaker`` fields only) and exposes:

* ``GET /api/result`` — full DTO of segments + projection + speakers
* ``GET /api/clip/{idx}`` — streams the WAV for segment ``idx``
* ``POST /api/labels`` — apply a labels update (cluster rename + per-index)
* ``GET /api/transcripts/{fmt}`` — txt | vtt | srt rendering of the
  current labels
* ``GET /healthz`` — liveness

If a built React app exists at ``<repo>/web/dist``, it is mounted at
``/`` so the same server serves both API and SPA.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from transcriber._logging import get_logger
from transcriber.api.schemas import LabelsState, LabelsUpdate, ResultDTO, SegmentDTO
from transcriber.models import PipelineResult
from transcriber.render import render_srt, render_txt, render_vtt

log = get_logger(__name__)


def _import_fastapi() -> Any:
    try:
        import fastapi  # noqa: F401
        import fastapi.responses  # noqa: F401
        import fastapi.staticfiles  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "fastapi not installed. Run `pip install transcriber[api]`."
        ) from exc
    return fastapi


def build_app(
    result: PipelineResult,
    *,
    web_dist: Path | None = None,
    labels_path: Path | None = None,
    audio_url: str | None = None,
) -> Any:
    """Build the FastAPI app for ``result``.

    Parameters
    ----------
    result:
        The pipeline result to expose. Speaker labels on its segments
        are mutated in place by ``POST /api/labels``.
    web_dist:
        Optional path to a built frontend (``index.html`` + assets).
        If provided, mounted at ``/``.
    labels_path:
        Optional path where labels are persisted on every update. If
        the file exists at startup, labels are restored from it.
    """
    fastapi = _import_fastapi()
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, PlainTextResponse, Response
    from fastapi.staticfiles import StaticFiles

    if labels_path and labels_path.exists():
        try:
            saved = json.loads(labels_path.read_text())
            for i, name in enumerate(saved.get("speakers", [])):
                if i < len(result.segments) and name:
                    result.segments[i].speaker = name
            log.info("restored speaker labels from %s", labels_path)
        except (OSError, json.JSONDecodeError):
            log.exception("failed to load labels from %s", labels_path)

    app = FastAPI(
        title="transcriber",
        version="0.1.0",
        description="Interview transcription + speaker clustering API.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/result", response_model=ResultDTO)
    def get_result() -> ResultDTO:
        projection = result.cluster.projection
        segments = [
            SegmentDTO(
                index=i,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                speaker=seg.speaker or "Unknown",
                x=float(projection[i, 0]),
                y=float(projection[i, 1]),
                clip_url=f"/api/clip/{i}",
            )
            for i, seg in enumerate(result.segments)
        ]
        duration = max((s.end for s in result.segments), default=0.0)
        # Always advertise our /api/audio endpoint; it 404s if the source
        # file is gone, which the frontend tolerates.
        full_url = audio_url or "/api/audio"
        return ResultDTO(
            audio_name=result.audio_path.name,
            audio_url=full_url,
            duration=duration,
            n_speakers=result.cluster.n_clusters,
            speakers=[s.speaker or "Unknown" for s in result.segments],
            segments=segments,
        )

    @app.get("/api/audio")
    def get_audio() -> Response:
        path = Path(result.audio_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="audio file missing on disk")
        media = "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/wav"
        return FileResponse(path, media_type=media)

    @app.get("/api/clip/{idx}")
    def get_clip(idx: int) -> Response:
        if idx < 0 or idx >= len(result.segments):
            raise HTTPException(status_code=404, detail="segment out of range")
        path = Path(result.segments[idx].clip.path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="clip file missing on disk")
        return FileResponse(path, media_type="audio/wav")

    @app.post("/api/labels", response_model=LabelsState)
    def update_labels(update: LabelsUpdate) -> LabelsState:
        if update.mapping:
            for seg in result.segments:
                current = seg.speaker or "Unknown"
                if current in update.mapping:
                    seg.speaker = update.mapping[current]
        if update.per_index:
            for idx_str, name in update.per_index.items():
                # FastAPI/pydantic delivers int keys when the schema says int
                idx = int(idx_str)
                if 0 <= idx < len(result.segments):
                    result.segments[idx].speaker = name
        speakers = [s.speaker or "Unknown" for s in result.segments]
        if labels_path:
            labels_path.parent.mkdir(parents=True, exist_ok=True)
            labels_path.write_text(json.dumps({"speakers": speakers}))
        return LabelsState(speakers=speakers)

    @app.get("/api/transcripts/{fmt}")
    def export_transcript(fmt: str) -> Response:
        if fmt == "txt":
            body = render_txt(result.segments)
            media = "text/plain"
        elif fmt == "vtt":
            body = render_vtt(result.segments)
            media = "text/vtt"
        elif fmt == "srt":
            body = render_srt(result.segments)
            media = "application/x-subrip"
        else:
            raise HTTPException(status_code=400, detail="format must be txt, vtt, or srt")
        return PlainTextResponse(content=body, media_type=media)

    if web_dist is not None and web_dist.is_dir():
        log.info("serving frontend from %s", web_dist)
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="web")
    else:
        @app.get("/")
        def root() -> dict[str, str]:
            return {
                "message": (
                    "transcriber API. The React frontend is not built. "
                    "Run `pnpm install && pnpm build` in the web/ directory, "
                    "or use the dev server with --web-dev."
                ),
                "docs": "/docs",
            }

    return app


def run(
    result: PipelineResult,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    web_dist: Path | None = None,
    labels_path: Path | None = None,
) -> None:
    """Run uvicorn with a built app. Blocking."""
    try:
        import uvicorn  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "uvicorn not installed. Run `pip install transcriber[api]`."
        ) from exc
    app = build_app(result, web_dist=web_dist, labels_path=labels_path)
    log.info("API listening on http://%s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
