"""Round-trip tests for the OIP adapter.

We don't run the full pipeline here — instead we hand-build a
``PipelineResult`` (via the existing fixtures) and exercise the
adapter / installer / read helpers directly.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from transcriber.oip.adapter import (
    get_document,
    get_region_content,
    get_regions,
    list_documents,
    slug_for_audio,
    write_artefacts,
)
from transcriber.oip.constants import (
    OIP_VERSION,
    PRODUCER_NAME,
    REGION_KIND_TRANSCRIPT_SEGMENT,
    SOURCE_REF_KIND_AUDIO_TIMESTAMP,
    TOOLS_NAMESPACE,
)
from transcriber.oip.install import install_manifest, manifest_payload
from transcriber.oip.manifest import build_manifest

# ---- manifest --------------------------------------------------------


def test_manifest_required_fields(tmp_path: Path):
    manifest = build_manifest(tmp_path)
    assert manifest["oip_version"] == OIP_VERSION
    assert manifest["producer"]["name"] == PRODUCER_NAME
    assert manifest["data_dir"] == str(tmp_path.resolve())
    assert manifest["produces"]["region_kinds"] == [REGION_KIND_TRANSCRIPT_SEGMENT]
    assert SOURCE_REF_KIND_AUDIO_TIMESTAMP in manifest["produces"]["source_ref_kinds"]
    assert manifest["invocation"]["tools_namespace"] == TOOLS_NAMESPACE
    assert manifest["invocation"]["kind"] == "mcp-stdio"


def test_manifest_payload_is_pure_json(tmp_path: Path):
    payload = manifest_payload(tmp_path)
    parsed = json.loads(payload)
    assert parsed == build_manifest(tmp_path)


def test_install_writes_both_locations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    written = install_manifest(tmp_path / "data", scope="system")
    assert written["data_dir"].read_text().startswith("{")
    assert written["discovery"].name == f"{PRODUCER_NAME}.json"
    # bit-for-bit identical
    assert written["data_dir"].read_text() == written["discovery"].read_text()


def test_install_project_scope(tmp_path: Path):
    consumer = tmp_path / "consumer"
    written = install_manifest(
        tmp_path / "data", scope="project", consumer_data_dir=consumer
    )
    assert written["discovery"].parent == consumer.resolve() / ".oip" / "producers.d"


# ---- adapter round-trip ----------------------------------------------


def test_slug_is_deterministic(tmp_path: Path):
    audio = tmp_path / "MyClip 01.mp3"
    audio.write_bytes(b"hello world")
    s1 = slug_for_audio(audio)
    s2 = slug_for_audio(audio)
    assert s1 == s2
    assert s1.startswith("myclip-01-")
    assert len(s1.split("-")[-1]) == 8


def _seed_audio(path: Path) -> None:
    path.write_bytes(b"fake-audio-bytes-for-test")


def test_write_artefacts_round_trip(tmp_path, small_pipeline_result):
    audio_path = tmp_path / "audio.mp3"
    _seed_audio(audio_path)
    # rebind the result to a real on-disk audio so file_hash works
    small_pipeline_result.audio_path = audio_path
    data_dir = tmp_path / "data"

    summary = write_artefacts(
        small_pipeline_result, data_dir, deterministic_timestamp=True
    )
    assert summary["region_count"] == len(small_pipeline_result.segments)
    slug = summary["slug"]

    # files exist
    art_dir = data_dir / "artefacts" / slug
    assert (art_dir / "document.json").exists()
    assert (art_dir / "regions.json").exists()
    content_files = list((art_dir / "content").iterdir())
    assert len(content_files) == len(small_pipeline_result.segments)

    # document is valid
    doc = json.loads((art_dir / "document.json").read_text())
    assert doc["slug"] == slug
    assert doc["source_kind"].startswith("audio/")
    assert doc["ingested_by"].startswith(PRODUCER_NAME + "/")
    assert "duration_ms" in doc["size_units"]

    # regions reference content with relative paths
    regions = json.loads((art_dir / "regions.json").read_text())
    for r in regions:
        assert r["kind"] == REGION_KIND_TRANSCRIPT_SEGMENT
        assert r["source_ref"]["kind"] == SOURCE_REF_KIND_AUDIO_TIMESTAMP
        assert "start_ms" in r["source_ref"]
        rel = r["content"]["text"]
        assert not Path(rel).is_absolute()
        assert (art_dir / rel).exists()


def test_write_artefacts_is_idempotent(tmp_path, small_pipeline_result):
    audio_path = tmp_path / "audio.mp3"
    _seed_audio(audio_path)
    small_pipeline_result.audio_path = audio_path
    data_dir = tmp_path / "data"

    s1 = write_artefacts(small_pipeline_result, data_dir, deterministic_timestamp=True)
    art = Path(s1["regions_path"])
    snapshot = art.read_text()
    s2 = write_artefacts(small_pipeline_result, data_dir, deterministic_timestamp=True)

    assert s1["slug"] == s2["slug"]
    assert art.read_text() == snapshot


def test_read_helpers(tmp_path, small_pipeline_result):
    audio_path = tmp_path / "audio.mp3"
    _seed_audio(audio_path)
    small_pipeline_result.audio_path = audio_path
    data_dir = tmp_path / "data"

    summary = write_artefacts(
        small_pipeline_result, data_dir, deterministic_timestamp=True
    )
    slug = summary["slug"]

    docs = list_documents(data_dir)
    assert len(docs) == 1
    assert docs[0]["slug"] == slug

    doc = get_document(data_dir, slug)
    assert doc["slug"] == slug

    regions = get_regions(data_dir, slug)
    assert len(regions) == len(small_pipeline_result.segments)

    alice_regions = get_regions(data_dir, slug, speaker="Alice")
    assert all(r["source_ref"].get("speaker") == "Alice" for r in alice_regions)

    text = get_region_content(data_dir, regions[0]["id"], fmt="text")
    assert small_pipeline_result.segments[0].text in text


# ---- end-to-end validation via the `oip` CLI -------------------------


@pytest.mark.skipif(shutil.which("oip") is None, reason="oip CLI not installed")
def test_validate_passes(tmp_path, small_pipeline_result):
    audio_path = tmp_path / "audio.mp3"
    _seed_audio(audio_path)
    small_pipeline_result.audio_path = audio_path
    data_dir = tmp_path / "data"

    install_manifest(
        data_dir,
        scope="system",
        consumer_data_dir=None,
    )
    write_artefacts(small_pipeline_result, data_dir, deterministic_timestamp=True)

    result = subprocess.run(
        ["oip", "validate", str(data_dir)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"oip validate failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
