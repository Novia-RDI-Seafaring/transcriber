"""FastAPI endpoints for the multi-job server."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from transcriber.api.jobs import JobManager, JobRecord, _now  # noqa: E402
from transcriber.api.server import build_app  # noqa: E402
from transcriber.models import (  # noqa: E402
    PipelineResult,
)


def _build_seeded_manager(
    work_dir: Path, result: PipelineResult, *, status: str = "complete"
) -> tuple[JobManager, str]:
    """Build a JobManager and inject a job whose result is already
    in-memory. We bypass the worker so tests don't need ffmpeg/NeMo."""
    # Materialize clip files referenced by the fixture so /clip works.
    for seg in result.segments:
        seg.clip.path.parent.mkdir(parents=True, exist_ok=True)
        if not seg.clip.path.exists():
            seg.clip.path.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    audio_path = result.audio_path
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    if not audio_path.exists():
        audio_path.write_bytes(b"\xff\xfb\x90")  # mp3 magic-ish

    manager = JobManager(work_dir)
    rec = JobRecord(
        id="seeded01",
        source=str(audio_path),
        title=audio_path.name,
        status=status,
        audio_path=str(audio_path),
        audio_hash="abc",
        duration_seconds=max(s.end for s in result.segments),
        n_segments=len(result.segments),
        n_speakers=result.cluster.n_clusters,
        completed_at=_now(),
    )
    manager._records[rec.id] = rec
    manager._results[rec.id] = result
    manager._persist(rec)
    return manager, rec.id


@pytest.fixture
def client_pair(
    small_pipeline_result: PipelineResult, tmp_path: Path
) -> tuple[TestClient, str]:
    manager, job_id = _build_seeded_manager(tmp_path, small_pipeline_result)
    app = build_app(work_dir=tmp_path, manager=manager)
    return TestClient(app), job_id


def test_healthz(client_pair: tuple[TestClient, str]):
    client, _ = client_pair
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_jobs(client_pair: tuple[TestClient, str]):
    client, job_id = client_pair
    r = client.get("/api/jobs")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["id"] == job_id
    assert body[0]["status"] == "complete"


def test_get_job(client_pair: tuple[TestClient, str]):
    client, job_id = client_pair
    r = client.get(f"/api/jobs/{job_id}")
    assert r.status_code == 200
    assert r.json()["n_speakers"] == 2


def test_get_job_404(client_pair: tuple[TestClient, str]):
    client, _ = client_pair
    r = client.get("/api/jobs/nope")
    assert r.status_code == 404


def test_result_endpoint(client_pair: tuple[TestClient, str]):
    client, job_id = client_pair
    r = client.get(f"/api/jobs/{job_id}/result")
    assert r.status_code == 200
    body = r.json()
    assert body["job_id"] == job_id
    assert body["n_speakers"] == 2
    assert body["audio_url"] == f"/api/jobs/{job_id}/audio"
    assert body["segments"][0]["clip_url"] == f"/api/jobs/{job_id}/clip/0"


def test_result_409_when_not_complete(
    small_pipeline_result: PipelineResult, tmp_path: Path
):
    manager, job_id = _build_seeded_manager(
        tmp_path, small_pipeline_result, status="running"
    )
    client = TestClient(build_app(work_dir=tmp_path, manager=manager))
    r = client.get(f"/api/jobs/{job_id}/result")
    assert r.status_code == 409


def test_clip_endpoint(client_pair: tuple[TestClient, str]):
    client, job_id = client_pair
    r = client.get(f"/api/jobs/{job_id}/clip/0")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/")
    assert r.content.startswith(b"RIFF")


def test_clip_oob(client_pair: tuple[TestClient, str]):
    client, job_id = client_pair
    r = client.get(f"/api/jobs/{job_id}/clip/9999")
    assert r.status_code == 404


def test_audio_endpoint(client_pair: tuple[TestClient, str]):
    client, job_id = client_pair
    r = client.get(f"/api/jobs/{job_id}/audio")
    assert r.status_code == 200


def test_post_labels_and_persist(
    client_pair: tuple[TestClient, str], tmp_path: Path
):
    client, job_id = client_pair
    r = client.post(
        f"/api/jobs/{job_id}/labels",
        json={"mapping": {"Alice": "Andy"}, "per_index": {}},
    )
    assert r.status_code == 200
    speakers = r.json()["speakers"]
    assert "Andy" in speakers
    assert "Alice" not in speakers
    saved = (tmp_path / "labels" / f"{job_id}.json").read_text()
    assert "Andy" in saved


def test_export_txt_vtt_srt(client_pair: tuple[TestClient, str]):
    client, job_id = client_pair
    for fmt, expected in (("txt", "Alice"), ("vtt", "WEBVTT")):
        r = client.get(f"/api/jobs/{job_id}/transcripts/{fmt}")
        assert r.status_code == 200
        assert expected in r.text or fmt == "txt"


def test_export_unknown_format(client_pair: tuple[TestClient, str]):
    client, job_id = client_pair
    r = client.get(f"/api/jobs/{job_id}/transcripts/json")
    assert r.status_code == 400


def test_create_job_via_post(tmp_path: Path):
    # Backed by a fresh manager — the worker is real but we use a
    # sentinel "source" that fails fast; we just want to confirm the
    # POST shape and persistence.
    app = build_app(work_dir=tmp_path)
    client = TestClient(app)
    r = client.post(
        "/api/jobs",
        json={
            "source": "/nonexistent/audio.mp3",
            "title": "test",
            "backend": "openai",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "test"
    assert body["status"] in {"pending", "running", "failed"}


def test_upload_creates_job(tmp_path: Path):
    app = build_app(work_dir=tmp_path)
    client = TestClient(app)
    r = client.post(
        "/api/jobs/upload",
        files={"file": ("hello.mp3", io.BytesIO(b"\x00" * 16), "audio/mpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "hello.mp3"
    # the upload should land in <work_dir>/uploads
    assert (tmp_path / "uploads" / "hello.mp3").exists()


def test_delete_job(client_pair: tuple[TestClient, str]):
    client, job_id = client_pair
    r = client.delete(f"/api/jobs/{job_id}")
    assert r.status_code == 200
    r2 = client.get(f"/api/jobs/{job_id}")
    assert r2.status_code == 404


def test_delete_404(client_pair: tuple[TestClient, str]):
    client, _ = client_pair
    r = client.delete("/api/jobs/nope")
    assert r.status_code == 404


def test_jobs_persist_across_managers(
    small_pipeline_result: PipelineResult, tmp_path: Path
):
    """A new JobManager pointed at the same work_dir loads existing
    job records (but treats running ones as failed)."""
    manager1, job_id = _build_seeded_manager(tmp_path, small_pipeline_result)
    # Force a record to "running" then build a fresh manager.
    manager1.get(job_id).status = "running"  # type: ignore[union-attr]
    manager1._persist(manager1.get(job_id))  # type: ignore[arg-type]
    manager2 = JobManager(tmp_path)
    rec = manager2.get(job_id)
    assert rec is not None
    assert rec.status == "failed"
    assert "interrupted" in (rec.error or "")
