"""FastAPI app factory.

The API is organized around **jobs**: each job is a request to
transcribe one source. The server owns a :class:`JobManager` for the
lifecycle, and exposes:

* ``GET    /api/jobs``                       — list all jobs
* ``POST   /api/jobs``                       — create a job from a
  URL or local path
* ``POST   /api/jobs/upload``                — create a job from an
  uploaded file
* ``GET    /api/jobs/{id}``                  — single job record
* ``DELETE /api/jobs/{id}``                  — remove a job
* ``GET    /api/jobs/{id}/result``           — full DTO with segments
  + projection (only when ``status == 'complete'``)
* ``GET    /api/jobs/{id}/audio``            — full source audio
* ``GET    /api/jobs/{id}/clip/{idx}``       — per-segment WAV
* ``POST   /api/jobs/{id}/labels``           — apply a labels update
* ``GET    /api/jobs/{id}/transcripts/{fmt}`` — txt / vtt / srt
* ``GET    /healthz``                        — liveness

If a built React frontend exists at ``web_dist``, it is mounted at
``/`` so the same server serves both API and SPA.
"""

from __future__ import annotations

import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

try:
    from fastapi import (
        FastAPI,
        File,
        Form,
        HTTPException,
        UploadFile,
    )
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, PlainTextResponse, Response
    from fastapi.staticfiles import StaticFiles
except ImportError:  # pragma: no cover
    FastAPI = File = Form = HTTPException = UploadFile = None  # type: ignore[assignment]
    CORSMiddleware = FileResponse = PlainTextResponse = Response = StaticFiles = None  # type: ignore[assignment]

from transcriber._logging import get_logger
from transcriber.api.jobs import JobManager, JobRecord
from transcriber.api.schemas import (
    CreateJobRequest,
    JobDTO,
    LabelsState,
    LabelsUpdate,
    ResultDTO,
    SegmentDTO,
)
from transcriber.models import PipelineResult
from transcriber.render import render_srt, render_txt, render_vtt

log = get_logger(__name__)


def _require_fastapi() -> None:
    if FastAPI is None:  # pragma: no cover
        raise RuntimeError(
            "fastapi not installed. Run `pip install transcriber[api]`."
        )


def build_app(
    *,
    work_dir: Path,
    web_dist: Path | None = None,
    manager: JobManager | None = None,
) -> Any:
    """Build the FastAPI app.

    Parameters
    ----------
    work_dir:
        Cache + jobs directory.
    web_dist:
        Optional path to a built frontend (``index.html`` + assets).
    manager:
        Optional pre-built ``JobManager`` (tests use this to inject
        custom job state).
    """
    _require_fastapi()
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    job_manager = manager or JobManager(work_dir)

    app = FastAPI(
        title="transcriber",
        version="0.2.0",
        description="Multi-job transcription + speaker clustering API.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.job_manager = job_manager

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # ---------- jobs --------------------------------------------------

    @app.get("/api/jobs", response_model=list[JobDTO])
    def list_jobs() -> list[JobDTO]:
        return [_to_dto(r) for r in job_manager.list()]

    @app.post("/api/jobs", response_model=JobDTO)
    def create_job(req: CreateJobRequest) -> JobDTO:
        rec = job_manager.create(
            source=req.source,
            title=req.title,
            backend=req.backend,
            language=req.language,
            participants=req.participants,
        )
        return _to_dto(rec)

    @app.post("/api/jobs/upload", response_model=JobDTO)
    async def upload_job(
        file: Annotated[UploadFile, File()],
        backend: Annotated[str, Form()] = "openai",
        language: Annotated[str, Form()] = "en",
        participants: Annotated[int | None, Form()] = None,
    ) -> JobDTO:
        if not file.filename:
            raise HTTPException(status_code=400, detail="missing filename")
        target_dir = work_dir / "uploads"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / _safe_filename(file.filename)
        with target.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        rec = job_manager.create(
            source=str(target),
            title=file.filename,
            backend=backend,
            language=language,
            participants=participants,
        )
        return _to_dto(rec)

    @app.get("/api/jobs/{job_id}", response_model=JobDTO)
    def get_job(job_id: str) -> JobDTO:
        rec = _require_job(job_manager, job_id)
        return _to_dto(rec)

    @app.delete("/api/jobs/{job_id}")
    def delete_job(job_id: str) -> dict[str, str]:
        if not job_manager.delete(job_id):
            raise HTTPException(status_code=404, detail="job not found")
        return {"status": "deleted"}

    # ---------- per-job result, audio, clips, labels, exports ---------

    @app.get("/api/jobs/{job_id}/result", response_model=ResultDTO)
    def get_result(job_id: str) -> ResultDTO:
        rec = _require_job(job_manager, job_id)
        if rec.status != "complete":
            raise HTTPException(
                status_code=409,
                detail=f"job is {rec.status!r}, not complete",
            )
        result = job_manager.get_result(job_id)
        if result is None:
            raise HTTPException(
                status_code=500, detail="result missing on disk"
            )
        return _result_to_dto(rec, result)

    @app.get("/api/jobs/{job_id}/audio")
    def get_audio(job_id: str) -> Response:
        rec = _require_job(job_manager, job_id)
        if not rec.audio_path:
            raise HTTPException(
                status_code=404, detail="audio not available yet"
            )
        path = Path(rec.audio_path)
        if not path.exists():
            raise HTTPException(
                status_code=404, detail="audio file missing on disk"
            )
        media = "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/wav"
        return FileResponse(path, media_type=media)

    @app.get("/api/jobs/{job_id}/clip/{idx}")
    def get_clip(job_id: str, idx: int) -> Response:
        result = _require_complete(job_manager, job_id)
        if idx < 0 or idx >= len(result.segments):
            raise HTTPException(
                status_code=404, detail="segment out of range"
            )
        path = Path(result.segments[idx].clip.path)
        if not path.exists():
            raise HTTPException(
                status_code=404, detail="clip file missing on disk"
            )
        return FileResponse(path, media_type="audio/wav")

    @app.post("/api/jobs/{job_id}/labels", response_model=LabelsState)
    def update_labels(job_id: str, update: LabelsUpdate) -> LabelsState:
        result = _require_complete(job_manager, job_id)
        if update.mapping:
            for seg in result.segments:
                current = seg.speaker or "Unknown"
                if current in update.mapping:
                    seg.speaker = update.mapping[current]
        if update.per_index:
            for idx, name in update.per_index.items():
                if 0 <= idx < len(result.segments):
                    result.segments[idx].speaker = name
        speakers = [s.speaker or "Unknown" for s in result.segments]
        job_manager.update_labels(job_id, speakers)
        return LabelsState(speakers=speakers)

    @app.get("/api/jobs/{job_id}/transcripts/{fmt}")
    def export(job_id: str, fmt: str) -> Response:
        result = _require_complete(job_manager, job_id)
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
            raise HTTPException(
                status_code=400, detail="format must be txt, vtt, or srt"
            )
        return PlainTextResponse(content=body, media_type=media)

    # ---------- frontend ----------------------------------------------

    if web_dist is not None and web_dist.is_dir():
        log.info("serving frontend from %s", web_dist)
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="web")
    else:
        @app.get("/")
        def root() -> dict[str, str]:
            return {
                "message": (
                    "transcriber API. The React frontend is not built. "
                    "Run `pnpm install && pnpm build` in web/."
                ),
                "docs": "/docs",
            }

    return app


def run(
    *,
    work_dir: Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    web_dist: Path | None = None,
    starter_source: str | None = None,
    starter_backend: str = "openai",
    starter_language: str = "en",
    starter_participants: int | None = None,
) -> None:
    """Run uvicorn. If ``starter_source`` is given, enqueue it as the
    first job before the server begins handling requests."""
    try:
        import uvicorn  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "uvicorn not installed. Run `pip install transcriber[api]`."
        ) from exc
    app = build_app(work_dir=work_dir, web_dist=web_dist)
    if starter_source:
        manager: JobManager = app.state.job_manager
        manager.create(
            source=starter_source,
            backend=starter_backend,
            language=starter_language,
            participants=starter_participants,
        )
    log.info("API listening on http://%s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


# ------------ helpers --------------------------------------------------


def _to_dto(rec: JobRecord) -> JobDTO:
    return JobDTO(**{k: v for k, v in asdict(rec).items() if k in JobDTO.model_fields})


def _result_to_dto(rec: JobRecord, result: PipelineResult) -> ResultDTO:
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
            clip_url=f"/api/jobs/{rec.id}/clip/{i}",
        )
        for i, seg in enumerate(result.segments)
    ]
    duration = max((s.end for s in result.segments), default=0.0)
    return ResultDTO(
        job_id=rec.id,
        audio_name=Path(result.audio_path).name,
        audio_url=f"/api/jobs/{rec.id}/audio",
        duration=duration,
        n_speakers=result.cluster.n_clusters,
        speakers=[s.speaker or "Unknown" for s in result.segments],
        segments=segments,
    )


def _require_job(manager: JobManager, job_id: str) -> JobRecord:
    rec = manager.get(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="job not found")
    return rec


def _require_complete(manager: JobManager, job_id: str) -> PipelineResult:
    rec = _require_job(manager, job_id)
    if rec.status != "complete":
        raise HTTPException(
            status_code=409,
            detail=f"job is {rec.status!r}, not complete",
        )
    result = manager.get_result(job_id)
    if result is None:
        raise HTTPException(status_code=500, detail="result missing on disk")
    return result


def _safe_filename(name: str) -> str:
    # Strip directory components and any null bytes; keep extension.
    safe = Path(name).name.replace("\x00", "")
    return safe or "upload"
