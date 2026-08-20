"""Adapter from :class:`PipelineResult` to the OIP on-disk shape.

This module is the only place that knows about the OIP file layout. The
rest of the transcriber stays oblivious — invoke
:func:`write_artefacts` after a successful pipeline run and it will
materialise ``document.json`` + ``regions.json`` + per-region content
files under ``<data-dir>/artefacts/<slug>/``.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transcriber._logging import get_logger
from transcriber.cache import file_hash
from transcriber.models import PipelineResult, SpeakerSegment
from transcriber.oip.constants import (
    PRODUCER_NAME,
    PRODUCER_VERSION,
    REGION_KIND_TRANSCRIPT_SEGMENT,
    SOURCE_REF_KIND_AUDIO_TIMESTAMP,
)

log = get_logger(__name__)

# Roughly mirrors what the transcriber accepts. Keeps things deterministic
# regardless of whether ``mimetypes`` knows about the extension.
_EXT_TO_MIME = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/x-m4a",
    ".aac": "audio/mp4",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".flac": "audio/flac",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
}


def slug_for_audio(audio_path: Path, audio_hash: str | None = None) -> str:
    """Deterministic slug for ``audio_path``.

    ``"<sanitised stem>-<short content hash>"``. Same bytes → same slug,
    independent of where the file lives or when it was ingested.
    """
    if audio_hash is None:
        audio_hash = file_hash(audio_path)
    base = re.sub(r"[^a-z0-9]+", "-", audio_path.stem.lower()).strip("-") or "doc"
    return f"{base}-{audio_hash[:8]}"


def _content_filename(slug: str, start_ms: int, end_ms: int, ext: str) -> str:
    """Filename inside ``content/`` for a region, mirrors the spec example."""
    return f"{slug}_t{start_ms:08d}-{end_ms:08d}.{ext}"


def _region_id(slug: str, start_ms: int, end_ms: int) -> str:
    return f"{slug}:t{start_ms:08d}-{end_ms:08d}"


def _detect_source_kind(audio_path: Path) -> str:
    return _EXT_TO_MIME.get(audio_path.suffix.lower(), "audio/mpeg")


def _now_iso_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_title(seg: SpeakerSegment, max_chars: int = 80) -> str:
    text = seg.text.strip().replace("\n", " ")
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text or f"segment {seg.start:.1f}s"


def write_artefacts(
    result: PipelineResult,
    data_dir: Path,
    *,
    title: str | None = None,
    source_url: str | None = None,
    ingested_at: str | None = None,
    deterministic_timestamp: bool = False,
) -> dict[str, Any]:
    """Write OIP artefacts for ``result`` under ``data_dir``.

    Returns a small summary dict (``slug``, ``region_count``, ``paths``)
    suitable for echoing to a CLI or returning from an MCP tool.

    ``deterministic_timestamp`` writes a fixed ingested_at; useful for
    tests where re-ingestion must produce byte-identical artefacts.
    """
    data_dir = Path(data_dir).expanduser().resolve()
    audio_path = Path(result.audio_path).resolve()
    audio_hash: str = result.metadata.get("audio_hash") or file_hash(audio_path)
    slug = slug_for_audio(audio_path, audio_hash)

    art_dir = data_dir / "artefacts" / slug
    content_dir = art_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    if ingested_at is None:
        ingested_at = (
            "1970-01-01T00:00:00Z" if deterministic_timestamp else _now_iso_utc()
        )

    regions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for seg in result.segments:
        start_ms = max(0, int(round(seg.start * 1000)))
        end_ms = max(start_ms, int(round(seg.end * 1000)))
        rid = _region_id(slug, start_ms, end_ms)

        # Defensive uniqueness — extremely short / overlapping segments
        # could collide. Disambiguate by appending a content-derived
        # suffix that's still deterministic.
        if rid in seen_ids:
            disambig = hashlib.sha1(seg.text.encode("utf-8")).hexdigest()[:6]
            rid = f"{rid}-{disambig}"
        seen_ids.add(rid)

        text_filename = _content_filename(slug, start_ms, end_ms, "txt")
        text_path = content_dir / text_filename
        text_path.write_text(seg.text + "\n", encoding="utf-8")

        source_ref: dict[str, Any] = {
            "kind": SOURCE_REF_KIND_AUDIO_TIMESTAMP,
            "start_ms": start_ms,
            "end_ms": end_ms,
        }
        # The consumer needs a locator to play the audio. Use the URL if
        # we have one (the original ingestion source); otherwise fall
        # back to a file:// URI for the local audio.
        if source_url:
            source_ref["source_url"] = source_url
        else:
            source_ref["source_url"] = audio_path.as_uri()
        if seg.speaker:
            source_ref["speaker"] = seg.speaker

        regions.append(
            {
                "id": rid,
                "kind": REGION_KIND_TRANSCRIPT_SEGMENT,
                "title": _format_title(seg),
                "description": seg.text,
                "source_ref": source_ref,
                "content": {
                    "text": f"content/{text_filename}",
                },
            }
        )

    document: dict[str, Any] = {
        "slug": slug,
        "title": title or audio_path.stem or slug,
        "source_kind": _detect_source_kind(audio_path),
        "source_path": None,
        "source_url": source_url,
        "ingested_at": ingested_at,
        "ingested_by": f"{PRODUCER_NAME}/{PRODUCER_VERSION}",
        "size_units": {
            "duration_ms": int(round(_total_duration_ms(result))),
            "segment_count": len(result.segments),
        },
        "tags": [],
        "extras": {
            "speaker_count": result.cluster.n_clusters,
            "audio_sha256": audio_hash,
        },
    }

    document_path = art_dir / "document.json"
    regions_path = art_dir / "regions.json"
    _write_json(document_path, document)
    _write_json(regions_path, regions)

    log.info("wrote OIP artefacts for slug=%s (%d regions)", slug, len(regions))
    return {
        "slug": slug,
        "region_count": len(regions),
        "document_path": str(document_path),
        "regions_path": str(regions_path),
    }


def _total_duration_ms(result: PipelineResult) -> float:
    if not result.segments:
        return 0.0
    return result.segments[-1].end * 1000.0


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8")


# ----- read-side helpers (used by the MCP server) ----------------------


def list_documents(data_dir: Path) -> list[dict[str, Any]]:
    data_dir = Path(data_dir).expanduser().resolve()
    art_root = data_dir / "artefacts"
    if not art_root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for slug_dir in sorted(p for p in art_root.iterdir() if p.is_dir()):
        doc = slug_dir / "document.json"
        if doc.exists():
            try:
                out.append(json.loads(doc.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                log.warning("skipping corrupt %s: %s", doc, exc)
    return out


def get_document(data_dir: Path, slug: str) -> dict[str, Any]:
    path = Path(data_dir).expanduser().resolve() / "artefacts" / slug / "document.json"
    if not path.exists():
        raise FileNotFoundError(f"unknown slug: {slug}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_regions(
    data_dir: Path,
    slug: str,
    *,
    speaker: str | None = None,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> list[dict[str, Any]]:
    path = Path(data_dir).expanduser().resolve() / "artefacts" / slug / "regions.json"
    if not path.exists():
        raise FileNotFoundError(f"unknown slug: {slug}")
    regions: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    if speaker is not None:
        regions = [r for r in regions if r.get("source_ref", {}).get("speaker") == speaker]
    if start_ms is not None:
        regions = [r for r in regions if r.get("source_ref", {}).get("end_ms", 0) >= start_ms]
    if end_ms is not None:
        regions = [r for r in regions if r.get("source_ref", {}).get("start_ms", 0) <= end_ms]
    return regions


def get_region_content(data_dir: Path, region_id: str, fmt: str = "text") -> str:
    if ":" not in region_id:
        raise ValueError(f"region id must be '<slug>:<suffix>': {region_id!r}")
    slug = region_id.split(":", 1)[0]
    art_dir = Path(data_dir).expanduser().resolve() / "artefacts" / slug
    regions_path = art_dir / "regions.json"
    if not regions_path.exists():
        raise FileNotFoundError(f"unknown slug: {slug}")
    regions: list[dict[str, Any]] = json.loads(regions_path.read_text(encoding="utf-8"))
    region = next((r for r in regions if r.get("id") == region_id), None)
    if region is None:
        raise FileNotFoundError(f"unknown region id: {region_id}")
    key = "markdown" if fmt == "markdown" else "text"
    rel = region.get("content", {}).get(key)
    if not rel:
        raise FileNotFoundError(f"region {region_id} has no '{key}' content")
    payload_path = art_dir / rel
    if not payload_path.exists():
        raise FileNotFoundError(f"missing content file: {payload_path}")
    return payload_path.read_text(encoding="utf-8")


__all__ = [
    "get_document",
    "get_region_content",
    "get_regions",
    "list_documents",
    "slug_for_audio",
    "write_artefacts",
]
