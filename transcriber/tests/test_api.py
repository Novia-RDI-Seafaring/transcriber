"""FastAPI endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from transcriber.api.server import build_app  # noqa: E402
from transcriber.models import PipelineResult  # noqa: E402


@pytest.fixture
def client(small_pipeline_result: PipelineResult, tmp_path: Path) -> TestClient:
    # Materialize the clip files referenced by the fixture so /api/clip works.
    for seg in small_pipeline_result.segments:
        seg.clip.path.parent.mkdir(parents=True, exist_ok=True)
        seg.clip.path.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    app = build_app(small_pipeline_result, labels_path=tmp_path / "labels.json")
    return TestClient(app)


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_result_endpoint_shape(client: TestClient):
    r = client.get("/api/result")
    assert r.status_code == 200
    body = r.json()
    assert body["n_speakers"] == 2
    assert len(body["segments"]) == len(body["speakers"])
    seg = body["segments"][0]
    assert {"index", "start", "end", "text", "speaker", "x", "y", "clip_url"} <= set(seg)
    assert seg["clip_url"] == "/api/clip/0"


def test_clip_endpoint_streams_file(client: TestClient):
    r = client.get("/api/clip/0")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/")
    assert r.content.startswith(b"RIFF")


def test_clip_404_for_oob(client: TestClient):
    r = client.get("/api/clip/9999")
    assert r.status_code == 404


def test_post_labels_renames_cluster(client: TestClient):
    r = client.post("/api/labels", json={"mapping": {"Alice": "Andy"}, "per_index": {}})
    assert r.status_code == 200
    speakers = r.json()["speakers"]
    assert "Andy" in speakers
    assert "Alice" not in speakers
    # Bob is untouched.
    assert "Bob" in speakers


def test_post_labels_per_index(client: TestClient):
    r = client.post("/api/labels", json={"mapping": {}, "per_index": {"0": "Hawk"}})
    assert r.status_code == 200
    assert r.json()["speakers"][0] == "Hawk"


def test_post_labels_persists(client: TestClient, tmp_path: Path):
    client.post("/api/labels", json={"mapping": {}, "per_index": {"0": "Persisted"}})
    saved = (tmp_path / "labels.json").read_text()
    assert "Persisted" in saved


def test_transcripts_txt(client: TestClient):
    r = client.get("/api/transcripts/txt")
    assert r.status_code == 200
    assert "Alice:" in r.text or "Bob:" in r.text


def test_transcripts_vtt(client: TestClient):
    r = client.get("/api/transcripts/vtt")
    assert r.status_code == 200
    assert r.text.startswith("WEBVTT")


def test_transcripts_unknown_format(client: TestClient):
    r = client.get("/api/transcripts/json")
    assert r.status_code == 400
