"""``transcriber oip ...`` CLI sub-app.

Subcommands:

* ``install`` — write the manifest to <data-dir> and producers.d.
* ``ingest``  — run the pipeline and emit OIP artefacts.
* ``serve``   — run the MCP-stdio server (alias of ``transcriber-mcp``).
* ``manifest``— print the manifest payload (no writes).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from transcriber._logging import configure_logging, get_logger
from transcriber.oip.constants import PRODUCER_NAME, TOOLS_NAMESPACE
from transcriber.oip.ingest import ingest_source
from transcriber.oip.install import (
    install_manifest,
    manifest_payload,
    system_producers_dir,
)

log = get_logger(__name__)

app = typer.Typer(
    name="oip",
    help=(
        "Open Ingestion Protocol producer commands. "
        f"Namespace: {TOOLS_NAMESPACE}. Spec: oip spec."
    ),
    no_args_is_help=True,
    add_completion=False,
)


_DEFAULT_DATA_DIR = Path("./oip-data")


@app.command("install")
def install_command(
    data_dir: Annotated[
        Path,
        typer.Option(
            "--data-dir",
            help="Directory the producer owns. The manifest lands at <data-dir>/manifest.json.",
        ),
    ] = _DEFAULT_DATA_DIR,
    scope: Annotated[
        str,
        typer.Option("--scope", help="'system' or 'project'."),
    ] = "system",
    consumer_data_dir: Annotated[
        Path | None,
        typer.Option(
            "--consumer-data-dir",
            help="Required for --scope project: the consumer that should pin this producer.",
        ),
    ] = None,
    print_only: Annotated[
        bool,
        typer.Option("--print", help="Emit the manifest to stdout without writing anything."),
    ] = False,
) -> None:
    """Register this producer with the local OIP discovery directory."""
    configure_logging("INFO")
    if print_only:
        typer.echo(manifest_payload(data_dir), nl=False)
        return

    written = install_manifest(
        data_dir,
        scope=scope,
        consumer_data_dir=consumer_data_dir,
    )
    for label, path in written.items():
        typer.echo(f"{label:>10}: {path}")


@app.command("ingest")
def ingest_command(
    source: Annotated[
        str,
        typer.Argument(metavar="AUDIO_OR_URL", help="Local audio file or YouTube URL."),
    ],
    data_dir: Annotated[
        Path,
        typer.Option("--data-dir", help="OIP data directory."),
    ] = _DEFAULT_DATA_DIR,
    backend: Annotated[str, typer.Option(help="local or openai.")] = "local",
    language: Annotated[str, typer.Option(help="Language code.")] = "en",
    participants: Annotated[
        int | None, typer.Option(help="Number of speakers, if known.")
    ] = None,
    chunk_seconds: Annotated[int, typer.Option()] = 600,
    context: Annotated[str, typer.Option()] = "",
    no_cache: Annotated[bool, typer.Option(help="Disable per-stage cache.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Transcribe one source and write its artefacts under ``--data-dir``."""
    configure_logging("DEBUG" if verbose else "INFO")
    summary = ingest_source(
        source,
        data_dir=data_dir,
        backend=backend,
        language=language,
        participants=participants,
        chunk_seconds=chunk_seconds,
        context=context,
        use_cache=not no_cache,
    )
    typer.echo(
        f"slug={summary['slug']} regions={summary['region_count']} "
        f"speakers={summary.get('speaker_count')}"
    )
    typer.echo(f"document: {summary['document_path']}")
    typer.echo(f"regions:  {summary['regions_path']}")


@app.command("serve")
def serve_command(
    data_dir: Annotated[
        Path,
        typer.Option("--data-dir", help="OIP data directory."),
    ] = _DEFAULT_DATA_DIR,
) -> None:
    """Run the MCP-stdio server. Equivalent to the ``transcriber-mcp`` binary."""
    from transcriber.oip.mcp_server import main as mcp_main

    mcp_main(["--data-dir", str(data_dir)])


@app.command("manifest")
def manifest_command(
    data_dir: Annotated[
        Path,
        typer.Option("--data-dir"),
    ] = _DEFAULT_DATA_DIR,
) -> None:
    """Print the manifest payload to stdout."""
    typer.echo(manifest_payload(data_dir), nl=False)


@app.command("where")
def where_command() -> None:
    """Print the discovery paths the installer writes to."""
    typer.echo(f"system:  {system_producers_dir() / (PRODUCER_NAME + '.json')}")
    typer.echo(
        "project: <consumer-data-dir>/.oip/producers.d/"
        f"{PRODUCER_NAME}.json  (when --scope project)"
    )
