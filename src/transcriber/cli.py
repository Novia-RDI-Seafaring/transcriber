"""``transcriber`` command-line entry point.

Subcommands:

* ``transcribe`` — run the full pipeline, write a transcript file.
* ``download`` — fetch audio from a YouTube URL.
* ``ui`` — launch the interactive Dash UI for relabeling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from transcriber import __version__
from transcriber._env import load_env
from transcriber._logging import configure_logging, get_logger
from transcriber.config import ClusterConfig, PipelineConfig, TranscribeConfig
from transcriber.pipeline import run_pipeline
from transcriber.render import render_json, render_srt, render_txt, render_vtt

app = typer.Typer(
    name="transcriber",
    help="Transcribe dialogues and identify who said what.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"transcriber {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Print version and exit."
        ),
    ] = False,
) -> None:
    """Transcribe dialogues and identify who said what."""
    load_env()

# OIP (Open Ingestion Protocol) producer commands. See `transcriber oip --help`.
from transcriber.oip.cli import app as _oip_app  # noqa: E402

app.add_typer(_oip_app, name="oip")

log = get_logger(__name__)


def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def _resolve_backend(explicit: str | None) -> str:
    """Pick a transcription backend when none was given explicitly.

    Prefer the OpenAI API when a key is available (fast everywhere),
    otherwise fall back to the local faster-whisper model.
    """
    import os

    if explicit is not None:
        return explicit
    backend = "openai" if os.environ.get("OPENAI_API_KEY") else "local"
    log.info("no --backend given; using %s", backend)
    return backend


def _resolve_audio(source: str, *, work_dir: Path) -> Path:
    """Return a local audio path for ``source``.

    A URL is downloaded into ``work_dir/youtube`` (cached on the YouTube
    video id); a local path is validated to exist.
    """
    if _is_url(source):
        from transcriber.download.youtube import download_youtube

        download_dir = work_dir / "youtube"
        log.info("downloading %s into %s", source, download_dir)
        result = download_youtube(source, download_dir, use_cached=True)
        log.info("audio: %s (%s)", result.audio_path, result.title)
        return result.audio_path
    path = Path(source)
    if not path.exists():
        raise typer.BadParameter(f"audio file does not exist: {path}")
    return path


def _build_config(
    *,
    backend: str,
    language: str,
    participants: int | None,
    chunk_seconds: int,
    work_dir: Path,
    no_cache: bool,
    context: str,
) -> PipelineConfig:
    return PipelineConfig(
        transcribe=TranscribeConfig(
            backend=backend,  # type: ignore[arg-type]
            language=language,
            chunk_seconds=chunk_seconds,
            context=context,
        ),
        cluster=ClusterConfig(participants=participants),
        work_dir=work_dir,
        use_cache=not no_cache,
    )


@app.command()
def transcribe(
    source: Annotated[
        str,
        typer.Argument(
            metavar="AUDIO_OR_URL",
            help="Local audio file (mp3/wav/m4a/...) or a YouTube URL.",
        ),
    ],
    output: Annotated[
        str | None,
        typer.Option(
            "--output",
            "-o",
            help="Where to write the transcript ('-' for stdout). Default: <audio>.<format>",
        ),
    ] = None,
    backend: Annotated[
        str, typer.Option(help="Transcription backend: openai or local.")
    ] = "local",
    language: Annotated[str, typer.Option(help="Language code (e.g. en, sv).")] = "en",
    participants: Annotated[
        int | None, typer.Option(help="Number of speakers, if known.")
    ] = None,
    chunk_seconds: Annotated[
        int, typer.Option(help="Chunk size for long audio.")
    ] = 600,
    fmt: Annotated[
        str, typer.Option("--format", help="Output format: txt, vtt, srt, or json.")
    ] = "txt",
    work_dir: Annotated[
        Path, typer.Option(help="Cache directory.")
    ] = Path(".transcriber-cache"),
    no_cache: Annotated[
        bool, typer.Option("--no-cache", help="Disable caching of stage outputs.")
    ] = False,
    context: Annotated[
        str, typer.Option(help="Free-form context passed to Whisper as initial prompt.")
    ] = "",
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Run the full pipeline on ``AUDIO_OR_URL`` and write a transcript."""
    configure_logging("DEBUG" if verbose else "INFO")
    audio = _resolve_audio(source, work_dir=work_dir)
    cfg = _build_config(
        backend=backend,
        language=language,
        participants=participants,
        chunk_seconds=chunk_seconds,
        work_dir=work_dir,
        no_cache=no_cache,
        context=context,
    )
    result = run_pipeline(audio, config=cfg)

    renderers = {"txt": render_txt, "vtt": render_vtt, "srt": render_srt, "json": render_json}
    if fmt not in renderers:
        raise typer.BadParameter(f"unknown format: {fmt}")
    text = renderers[fmt](result.segments)

    summary = f"{result.cluster.n_clusters} speakers, {len(result.segments)} segments"
    if output == "-":
        typer.echo(text)
        typer.echo(summary, err=True)
    else:
        out = Path(output) if output else audio.with_suffix(f".{fmt}")
        out.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {out}  ({summary})")


@app.command()
def download(
    url: Annotated[str, typer.Argument(help="YouTube URL.")],
    out_dir: Annotated[
        Path, typer.Option("--out-dir", "-o", help="Where to store downloaded audio.")
    ] = Path(".transcriber-cache/youtube"),
    no_cache: Annotated[
        bool, typer.Option("--no-cache", help="Re-download even if cached.")
    ] = False,
) -> None:
    """Download a YouTube video's audio track."""
    configure_logging()
    from transcriber.download.youtube import download_youtube

    result = download_youtube(url, out_dir, use_cached=not no_cache)
    typer.echo(f"{result.title}\n{result.audio_path}")


@app.command("serve")
def serve_command(
    source: Annotated[
        str | None,
        typer.Argument(
            metavar="AUDIO_OR_URL",
            help="Optional starter job: a local audio file or a YouTube URL.",
        ),
    ] = None,
    backend: Annotated[
        str | None,
        typer.Option(
            help="local or openai. Default: openai if an OPENAI_API_KEY is available, else local."
        ),
    ] = None,
    language: Annotated[str, typer.Option()] = "en",
    participants: Annotated[int | None, typer.Option()] = None,
    host: Annotated[str, typer.Option(help="Bind address.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="HTTP port.")] = 8000,
    work_dir: Annotated[Path, typer.Option()] = Path(".transcriber-cache"),
    web_dist: Annotated[
        Path | None,
        typer.Option(
            "--web-dist",
            help="Path to a built React frontend (web/dist). Default: transcriber/web/dist alongside the source tree.",
        ),
    ] = None,
) -> None:
    """Serve the FastAPI + React frontend.

    With no argument, the server starts empty and you add jobs through
    the sidebar. With a URL or path, it enqueues that as the first job.
    """
    configure_logging("INFO")
    from transcriber.api.server import run as run_api

    dist = web_dist or _default_web_dist()
    run_api(
        work_dir=work_dir,
        host=host,
        port=port,
        web_dist=dist,
        starter_source=source,
        starter_backend=_resolve_backend(backend),
        starter_language=language,
        starter_participants=participants,
    )


def _default_web_dist() -> Path | None:
    """Locate the built React app.

    In a development checkout it lives at ``<repo>/web/dist`` (three
    levels up from this file: transcriber -> src -> repo root); in an
    installed wheel it is bundled at ``transcriber/web/dist``.
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parent / "web" / "dist",  # installed wheel
        here.parent.parent.parent / "web" / "dist",  # development checkout
    ]
    for c in candidates:
        if c.is_dir():
            log.info("serving frontend from %s", c)
            return c
    log.warning("no built frontend found; tried: %s", [str(c) for c in candidates])
    return None


@app.command("ui")
def ui_command(
    source: Annotated[
        str,
        typer.Argument(
            metavar="AUDIO_OR_URL",
            help="Local audio file or a YouTube URL.",
        ),
    ],
    backend: Annotated[str, typer.Option(help="local or openai.")] = "local",
    language: Annotated[str, typer.Option()] = "en",
    participants: Annotated[int | None, typer.Option()] = None,
    port: Annotated[int, typer.Option()] = 8051,
    work_dir: Annotated[Path, typer.Option()] = Path(".transcriber-cache"),
    debug: Annotated[bool, typer.Option()] = False,
) -> None:
    """Run the pipeline (cached) and launch the interactive Dash UI."""
    configure_logging("DEBUG" if debug else "INFO")
    audio = _resolve_audio(source, work_dir=work_dir)
    cfg = _build_config(
        backend=backend,
        language=language,
        participants=participants,
        chunk_seconds=600,
        work_dir=work_dir,
        no_cache=False,
        context="",
    )
    result = run_pipeline(audio, config=cfg)
    from transcriber.ui.app import launch

    launch(result, port=port, debug=debug)


if __name__ == "__main__":  # pragma: no cover
    app()
