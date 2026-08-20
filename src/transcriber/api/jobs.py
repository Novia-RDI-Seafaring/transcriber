"""Multi-job pipeline runner.

Each job is a request to transcribe one source (URL, local path, or
uploaded file). The manager owns the lifecycle: persistence, queueing,
serial execution in a worker thread, and in-memory caching of the
resulting :class:`PipelineResult`.

JSON state lives at ``<work_dir>/jobs/<id>.json``; pipeline outputs live
in the regular content-hashed cache so re-running a completed job is
free.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from transcriber._logging import get_logger
from transcriber.config import ClusterConfig, PipelineConfig, TranscribeConfig
from transcriber.models import PipelineResult
from transcriber.pipeline import run_pipeline

log = get_logger(__name__)

_TERMINAL = {"complete", "failed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return secrets.token_urlsafe(8)


@dataclass
class JobRecord:
    """Persisted job metadata. Pipeline outputs are not in here — they
    live in the content-hashed cache and the in-memory result map."""

    id: str
    source: str
    title: str
    backend: str = "openai"
    language: str = "en"
    participants: int | None = None
    status: str = "pending"  # pending | running | complete | failed
    stage: str | None = None
    error: str | None = None
    audio_path: str | None = None
    audio_hash: str | None = None
    duration_seconds: float | None = None
    n_segments: int | None = None
    n_speakers: int | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    completed_at: str | None = None


class JobManager:
    """Owns all jobs.

    Single worker thread runs jobs serially. Results from completed jobs
    are cached in memory and re-built lazily on first request after a
    server restart.
    """

    def __init__(self, work_dir: Path) -> None:
        self.work_dir = Path(work_dir)
        self.jobs_dir = self.work_dir / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, JobRecord] = {}
        self._results: dict[str, PipelineResult] = {}
        self._futures: dict[str, Future[None]] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="transcriber-job"
        )
        self._load_existing()

    # ----- persistence ----------------------------------------------------

    def _record_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.json"

    def _load_existing(self) -> None:
        for p in sorted(self.jobs_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text())
                rec = JobRecord(**data)
            except (OSError, json.JSONDecodeError, TypeError):
                log.exception("ignoring corrupt job file %s", p)
                continue
            # Anything left "running" from a previous run is treated as
            # interrupted; the caller can retry it.
            if rec.status == "running":
                rec.status = "failed"
                rec.error = "interrupted (server restart)"
                rec.updated_at = _now()
            self._records[rec.id] = rec
        if self._records:
            log.info("loaded %d jobs from %s", len(self._records), self.jobs_dir)

    def _persist(self, rec: JobRecord) -> None:
        rec.updated_at = _now()
        path = self._record_path(rec.id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(rec), indent=2))
        tmp.replace(path)

    # ----- public API ----------------------------------------------------

    def list(self) -> list[JobRecord]:
        with self._lock:
            return sorted(
                self._records.values(),
                key=lambda r: r.created_at,
                reverse=True,
            )

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._records.get(job_id)

    def get_result(self, job_id: str) -> PipelineResult | None:
        """Return the cached result, building it from the on-disk cache
        if necessary. Returns ``None`` if the job has not completed."""
        with self._lock:
            rec = self._records.get(job_id)
            if rec is None or rec.status != "complete":
                return None
            cached = self._results.get(job_id)
            if cached is not None:
                return cached
            audio = rec.audio_path
        if audio is None:
            return None
        # All pipeline stages are cached on disk under work_dir, so this
        # is fast even though we call run_pipeline().
        try:
            result = run_pipeline(Path(audio), config=self._config_for(rec))
        except Exception:
            log.exception("failed to rebuild result for job %s", job_id)
            return None
        with self._lock:
            self._results[job_id] = result
        return result

    def create(
        self,
        *,
        source: str,
        title: str | None = None,
        backend: str = "openai",
        language: str = "en",
        participants: int | None = None,
    ) -> JobRecord:
        rec = JobRecord(
            id=_new_id(),
            source=source,
            title=title or _default_title(source),
            backend=backend,
            language=language,
            participants=participants,
        )
        with self._lock:
            self._records[rec.id] = rec
            self._persist(rec)
        future = self._executor.submit(self._run_job, rec.id)
        self._futures[rec.id] = future
        return rec

    def delete(self, job_id: str) -> bool:
        with self._lock:
            rec = self._records.pop(job_id, None)
            self._results.pop(job_id, None)
        if rec is None:
            return False
        try:
            self._record_path(job_id).unlink(missing_ok=True)
        except OSError:
            log.exception("failed to delete %s", self._record_path(job_id))
        return True

    def update_labels(self, job_id: str, speakers: list[str]) -> None:
        """Persist the latest speaker labels back into the cache file
        adjacent to the result, so the React frontend's renames survive
        a server restart."""
        with self._lock:
            rec = self._records.get(job_id)
        if rec is None:
            return
        labels_path = self.work_dir / "labels" / f"{job_id}.json"
        labels_path.parent.mkdir(parents=True, exist_ok=True)
        labels_path.write_text(json.dumps({"speakers": speakers}))

    def restore_labels(self, job_id: str, result: PipelineResult) -> None:
        """If a labels file exists for ``job_id``, apply it to ``result``."""
        labels_path = self.work_dir / "labels" / f"{job_id}.json"
        if not labels_path.exists():
            return
        try:
            data = json.loads(labels_path.read_text())
        except (OSError, json.JSONDecodeError):
            return
        for i, name in enumerate(data.get("speakers", [])):
            if i < len(result.segments) and name:
                result.segments[i].speaker = name

    # ----- worker --------------------------------------------------------

    def _config_for(self, rec: JobRecord) -> PipelineConfig:
        return PipelineConfig(
            transcribe=TranscribeConfig(
                backend=rec.backend,  # type: ignore[arg-type]
                language=rec.language,
            ),
            cluster=ClusterConfig(participants=rec.participants),
            work_dir=self.work_dir,
        )

    def _set_stage(self, job_id: str, stage: str) -> None:
        with self._lock:
            rec = self._records.get(job_id)
            if rec is None:
                return
            rec.stage = stage
            rec.status = "running"
            self._persist(rec)

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            rec = self._records.get(job_id)
        if rec is None:
            return
        try:
            self._set_stage(job_id, "preparing")
            audio = self._resolve_source(rec)
            self._set_stage(job_id, "running pipeline")
            result = run_pipeline(audio, config=self._config_for(rec))
            self.restore_labels(job_id, result)
            with self._lock:
                self._results[job_id] = result
                rec.status = "complete"
                rec.stage = None
                rec.audio_path = str(audio)
                rec.audio_hash = str(result.metadata.get("audio_hash"))
                rec.duration_seconds = max(
                    (s.end for s in result.segments), default=0.0
                )
                rec.n_segments = len(result.segments)
                rec.n_speakers = result.cluster.n_clusters
                rec.completed_at = _now()
                if rec.title in {_default_title(rec.source), rec.source}:
                    rec.title = audio.name
                self._persist(rec)
            log.info("job %s complete (%d segments)", job_id, rec.n_segments)
        except Exception as exc:
            log.exception("job %s failed", job_id)
            with self._lock:
                rec.status = "failed"
                rec.stage = None
                rec.error = f"{type(exc).__name__}: {exc}"
                self._persist(rec)

    def _resolve_source(self, rec: JobRecord) -> Path:
        src = rec.source
        if src.startswith(("http://", "https://")):
            self._set_stage(rec.id, "downloading")
            from transcriber.download.youtube import download_youtube

            target = self.work_dir / "youtube"
            result = download_youtube(src, target, use_cached=True)
            with self._lock:
                if rec.title in {_default_title(rec.source), rec.source}:
                    rec.title = result.title
                self._persist(rec)
            return result.audio_path
        path = Path(src)
        if not path.exists():
            raise FileNotFoundError(f"source not found: {src}")
        return path

    # ----- shutdown -------------------------------------------------------

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


def _default_title(source: str) -> str:
    if source.startswith(("http://", "https://")):
        return source
    return Path(source).name


# Convenience used by tests.
def wait_for(
    manager: JobManager,
    job_id: str,
    *,
    timeout: float = 30.0,
    poll: float = 0.05,
    predicate: Callable[[JobRecord], bool] | None = None,
) -> JobRecord:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rec = manager.get(job_id)
        if rec is None:
            raise KeyError(job_id)
        done = (
            predicate(rec)
            if predicate is not None
            else rec.status in _TERMINAL
        )
        if done:
            return rec
        time.sleep(poll)
    raise TimeoutError(f"job {job_id} did not finish in {timeout}s")
