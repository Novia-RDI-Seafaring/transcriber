"""Run the transcription pipeline and write OIP artefacts.

The CLI and the MCP server both call :func:`ingest_source`. It wraps the
existing pipeline (so it benefits from the regular per-stage cache) and
then emits the OIP shape via the adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transcriber._logging import get_logger
from transcriber.config import ClusterConfig, PipelineConfig, TranscribeConfig
from transcriber.models import PipelineResult
from transcriber.oip.adapter import write_artefacts
from transcriber.pipeline import run_pipeline

log = get_logger(__name__)


def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def _resolve(source: str, work_dir: Path) -> tuple[Path, str | None, str | None]:
    """Return (audio_path, source_url, title) for ``source``."""
    if _is_url(source):
        from transcriber.download.youtube import download_youtube

        result = download_youtube(source, work_dir / "youtube", use_cached=True)
        return result.audio_path, source, result.title
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"audio file does not exist: {path}")
    return path, None, None


def ingest_source(
    source: str,
    *,
    data_dir: Path,
    work_dir: Path | None = None,
    backend: str = "local",
    language: str = "en",
    participants: int | None = None,
    chunk_seconds: int = 600,
    context: str = "",
    use_cache: bool = True,
) -> dict[str, Any]:
    """Transcribe ``source`` and write OIP artefacts under ``data_dir``.

    ``source`` is a local audio path or a YouTube URL. Returns the
    summary dict from :func:`write_artefacts`, augmented with the
    pipeline's audio hash and detected speaker count.
    """
    data_dir = Path(data_dir).expanduser().resolve()
    work_dir = Path(work_dir or data_dir / "_work").expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    audio_path, source_url, title = _resolve(source, work_dir)

    cfg = PipelineConfig(
        transcribe=TranscribeConfig(
            backend=backend,  # type: ignore[arg-type]
            language=language,
            chunk_seconds=chunk_seconds,
            context=context,
        ),
        cluster=ClusterConfig(participants=participants),
        work_dir=work_dir,
        use_cache=use_cache,
    )
    result: PipelineResult = run_pipeline(audio_path, config=cfg)

    summary = write_artefacts(
        result,
        data_dir,
        title=title,
        source_url=source_url,
    )
    summary.setdefault("audio_hash", result.metadata.get("audio_hash"))
    summary["speaker_count"] = result.cluster.n_clusters
    return summary


__all__ = ["ingest_source"]
