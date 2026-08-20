"""Build the OIP ``manifest.json`` payload for this producer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transcriber.oip.constants import (
    MCP_BINARY_NAME,
    OIP_VERSION,
    PRODUCER_DISPLAY_NAME,
    PRODUCER_HOMEPAGE,
    PRODUCER_NAME,
    PRODUCER_VERSION,
    REGION_KINDS,
    SOURCE_KINDS,
    SOURCE_REF_KINDS,
    TOOLS_NAMESPACE,
)


def build_manifest(data_dir: Path) -> dict[str, Any]:
    """Return the manifest dict for ``data_dir``.

    The dict is the source of truth — both the on-disk ``manifest.json``
    and the MCP server's self-description build from this.
    """
    data_dir_abs = str(Path(data_dir).expanduser().resolve())
    return {
        "oip_version": OIP_VERSION,
        "producer": {
            "name": PRODUCER_NAME,
            "display_name": PRODUCER_DISPLAY_NAME,
            "version": PRODUCER_VERSION,
            "homepage": PRODUCER_HOMEPAGE,
        },
        "data_dir": data_dir_abs,
        "produces": {
            "source_kinds": list(SOURCE_KINDS),
            "region_kinds": list(REGION_KINDS),
            "source_ref_kinds": list(SOURCE_REF_KINDS),
        },
        "invocation": {
            "kind": "mcp-stdio",
            "command": MCP_BINARY_NAME,
            "args": ["--data-dir", data_dir_abs],
            "tools_namespace": TOOLS_NAMESPACE,
        },
        "ui_hints": {
            "node_types": [
                {
                    "name": f"{TOOLS_NAMESPACE}:segment",
                    "renders": (
                        "card with speaker label, timestamp range, "
                        "inline text + audio scrub"
                    ),
                }
            ],
            "edge_styles": {},
            "source_ref_handlers": {
                "audio-timestamp": "play the audio from start_ms to end_ms",
            },
        },
    }


__all__ = ["build_manifest"]
