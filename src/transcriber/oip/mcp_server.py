"""MCP-stdio server for the transcriber OIP producer.

Tools are unprefixed inside the server (``ingest``, ``list_documents``,
``get_document``, ``get_regions``, ``get_region_content``). The
consumer prefixes them with ``manifest.invocation.tools_namespace``
(``transcribe``) when surfacing to its own clients.

This module is invoked by the ``transcriber-mcp`` entry point or via
``transcriber oip serve``. The data directory is configurable via
``--data-dir`` and falls back to ``$TRANSCRIBER_OIP_DATA_DIR`` or
``./oip-data``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from transcriber._logging import get_logger
from transcriber.oip.adapter import (
    get_document,
    get_region_content,
    get_regions,
    list_documents,
)
from transcriber.oip.constants import PRODUCER_NAME, TOOLS_NAMESPACE
from transcriber.oip.ingest import ingest_source

log = get_logger(__name__)

_DEFAULT_DATA_DIR_ENV = "TRANSCRIBER_OIP_DATA_DIR"


def _configure_stderr_logging(level: str = "INFO") -> None:
    """Configure logging to go to stderr (stdout is the JSON-RPC channel)."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def _default_data_dir() -> Path:
    env = os.environ.get(_DEFAULT_DATA_DIR_ENV)
    if env:
        return Path(env).expanduser().resolve()
    return Path("./oip-data").resolve()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="transcriber-mcp",
        description="OIP MCP-stdio server for the transcriber producer.",
    )
    p.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="OIP data directory (default: $TRANSCRIBER_OIP_DATA_DIR or ./oip-data).",
    )
    return p.parse_args(argv)


# ---- tool implementations ---------------------------------------------


def _tool_ingest(data_dir: Path, args: dict[str, Any]) -> dict[str, Any]:
    source = args.get("source") or args.get("path") or args.get("url")
    if not source:
        raise ValueError("ingest requires 'source' (path or URL)")
    return ingest_source(
        source,
        data_dir=data_dir,
        backend=args.get("backend", "local"),
        language=args.get("language", "en"),
        participants=args.get("participants"),
        chunk_seconds=int(args.get("chunk_seconds", 600)),
        context=args.get("context", ""),
        use_cache=bool(args.get("use_cache", True)),
    )


def _tool_list_documents(data_dir: Path, _args: dict[str, Any]) -> list[dict[str, Any]]:
    return list_documents(data_dir)


def _tool_get_document(data_dir: Path, args: dict[str, Any]) -> dict[str, Any]:
    return get_document(data_dir, args["slug"])


def _tool_get_regions(data_dir: Path, args: dict[str, Any]) -> list[dict[str, Any]]:
    return get_regions(
        data_dir,
        args["slug"],
        speaker=args.get("speaker"),
        start_ms=args.get("start_ms"),
        end_ms=args.get("end_ms"),
    )


def _tool_get_region_content(data_dir: Path, args: dict[str, Any]) -> dict[str, Any]:
    text = get_region_content(data_dir, args["region_id"], fmt=args.get("format", "text"))
    return {"region_id": args["region_id"], "format": args.get("format", "text"), "content": text}


# Tool descriptors — a single source for `tools/list` and dispatching.
_TOOLS: list[dict[str, Any]] = [
    {
        "name": "ingest",
        "description": (
            "Transcribe an audio file or URL and write OIP artefacts. "
            "Returns slug, region_count, audio_hash, speaker_count."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Local audio path or YouTube URL."},
                "backend": {"type": "string", "enum": ["local", "openai"], "default": "local"},
                "language": {"type": "string", "default": "en"},
                "participants": {"type": ["integer", "null"]},
                "chunk_seconds": {"type": "integer", "default": 600},
                "context": {"type": "string"},
                "use_cache": {"type": "boolean", "default": True},
            },
            "required": ["source"],
        },
        "handler": _tool_ingest,
    },
    {
        "name": "list_documents",
        "description": "List every document.json under the data dir.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_list_documents,
    },
    {
        "name": "get_document",
        "description": "Return one document.json by slug.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
        "handler": _tool_get_document,
    },
    {
        "name": "get_regions",
        "description": "Return regions for one document, optionally filtered by speaker / time.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "speaker": {"type": ["string", "null"]},
                "start_ms": {"type": ["integer", "null"]},
                "end_ms": {"type": ["integer", "null"]},
            },
            "required": ["slug"],
        },
        "handler": _tool_get_regions,
    },
    {
        "name": "get_region_content",
        "description": "Return the text/markdown payload for a single region.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "region_id": {"type": "string"},
                "format": {"type": "string", "enum": ["text", "markdown"], "default": "text"},
            },
            "required": ["region_id"],
        },
        "handler": _tool_get_region_content,
    },
]


def _public_tool_descriptors() -> list[dict[str, Any]]:
    return [{k: v for k, v in t.items() if k != "handler"} for t in _TOOLS]


def _dispatch(name: str, data_dir: Path, args: dict[str, Any]) -> Any:
    for tool in _TOOLS:
        if tool["name"] == name:
            return tool["handler"](data_dir, args)
    raise ValueError(f"unknown tool: {name}")


# ---- MCP server wiring ------------------------------------------------


async def _serve_mcp(data_dir: Path) -> None:
    """Speak MCP over stdio. Imports ``mcp`` lazily so the rest of the
    package is usable without the optional dependency."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError as exc:  # pragma: no cover
        print(
            "transcriber-mcp: the 'mcp' package is not installed. "
            "Install with: pip install 'transcriber[oip]'",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    server = Server(PRODUCER_NAME)

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"])
            for t in _public_tool_descriptors()
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            result = _dispatch(name, data_dir, arguments or {})
        except FileNotFoundError as exc:
            payload = {"error": str(exc), "kind": "not_found"}
        except ValueError as exc:
            payload = {"error": str(exc), "kind": "invalid_argument"}
        except Exception as exc:  # noqa: BLE001 — surface unexpected errors as JSON
            log.exception("tool %s failed", name)
            payload = {"error": f"{type(exc).__name__}: {exc}", "kind": "internal"}
        else:
            payload = result
        return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]

    async with stdio_server() as (read_stream, write_stream):
        log.info(
            "transcriber-mcp ready: namespace=%s data_dir=%s",
            TOOLS_NAMESPACE,
            data_dir,
        )
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``transcriber-mcp`` console script."""
    args = _parse_args(argv)
    # Logs MUST go to stderr — stdout is the JSON-RPC channel. The
    # project's configure_logging() routes to stderr by default
    # (basicConfig with no stream arg), but force it explicitly so a
    # future change can't silently break MCP framing.
    _configure_stderr_logging("INFO")
    data_dir = (args.data_dir or _default_data_dir()).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        asyncio.run(_serve_mcp(data_dir))
    except KeyboardInterrupt:  # pragma: no cover
        log.info("transcriber-mcp interrupted")


if __name__ == "__main__":  # pragma: no cover
    main()
