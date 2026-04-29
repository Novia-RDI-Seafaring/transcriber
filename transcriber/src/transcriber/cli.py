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

from transcriber._logging import configure_logging, get_logger
from transcriber.config import ClusterConfig, PipelineConfig, TranscribeConfig
from transcriber.pipeline import run_pipeline
from transcriber.render import render_srt, render_txt, render_vtt

app = typer.Typer(
    name="transcriber",
    help="Transcribe interviews and identify speakers.",
    no_args_is_help=True,
    add_completion=False,
)

log = get_logger(__name__)


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
    audio: Annotated[Path, typer.Argument(help="Audio file to transcribe (mp3/wav/m4a/...).")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Where to write the transcript. Default: <audio>.txt"),
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
        str, typer.Option("--format", help="Output format: txt, vtt, or srt.")
    ] = "txt",
    work_dir: Annotated[
        Path, typer.Option(help="Cache directory.")
    ] = Path(".transcriber-cache"),
    no_cache: Annotated[bool, typer.Option(help="Disable caching of stage outputs.")] = False,
    context: Annotated[
        str, typer.Option(help="Free-form context passed to Whisper as initial prompt.")
    ] = "",
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Run the full pipeline on ``AUDIO`` and write a transcript."""
    configure_logging("DEBUG" if verbose else "INFO")
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

    if fmt == "txt":
        text = render_txt(result.segments)
    elif fmt == "vtt":
        text = render_vtt(result.segments)
    elif fmt == "srt":
        text = render_srt(result.segments)
    else:
        raise typer.BadParameter(f"unknown format: {fmt}")

    out = output or audio.with_suffix(f".{fmt}")
    out.write_text(text, encoding="utf-8")
    typer.echo(f"wrote {out}  ({result.cluster.n_clusters} speakers, {len(result.segments)} segments)")


@app.command()
def download(
    url: Annotated[str, typer.Argument(help="YouTube URL.")],
    out_dir: Annotated[
        Path, typer.Option("--out-dir", "-o", help="Where to store downloaded audio.")
    ] = Path("data/audio/youtube"),
    no_cache: Annotated[bool, typer.Option(help="Re-download even if cached.")] = False,
) -> None:
    """Download a YouTube video's audio track."""
    configure_logging()
    from transcriber.download.youtube import download_youtube

    result = download_youtube(url, out_dir, use_cached=not no_cache)
    typer.echo(f"{result.title}\n{result.audio_path}")


@app.command("ui")
def ui_command(
    audio: Annotated[Path, typer.Argument(help="Audio file (or path to a YouTube-downloaded mp3).")],
    backend: Annotated[str, typer.Option(help="local or openai.")] = "local",
    language: Annotated[str, typer.Option()] = "en",
    participants: Annotated[int | None, typer.Option()] = None,
    port: Annotated[int, typer.Option()] = 8051,
    work_dir: Annotated[Path, typer.Option()] = Path(".transcriber-cache"),
    debug: Annotated[bool, typer.Option()] = False,
) -> None:
    """Run the pipeline (cached) and launch the interactive Dash UI."""
    configure_logging("DEBUG" if debug else "INFO")
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
