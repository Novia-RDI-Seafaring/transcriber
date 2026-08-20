"""Identifiers this producer advertises in its manifest.

Kept in one place so the manifest, the adapter, the MCP server, and the
installer never disagree.
"""

from __future__ import annotations

from transcriber import __version__ as PRODUCER_VERSION

OIP_VERSION = "0.1"
PRODUCER_NAME = "transcriber"
PRODUCER_DISPLAY_NAME = "Audio/Video Transcriber"
PRODUCER_HOMEPAGE = "https://github.com/anthropics/transcriber"
TOOLS_NAMESPACE = "transcribe"

SOURCE_KINDS: tuple[str, ...] = (
    "audio/wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/x-m4a",
    "audio/ogg",
    "audio/flac",
    "video/mp4",
    "video/webm",
)

REGION_KIND_TRANSCRIPT_SEGMENT = "transcript_segment"
REGION_KINDS: tuple[str, ...] = (REGION_KIND_TRANSCRIPT_SEGMENT,)

SOURCE_REF_KIND_AUDIO_TIMESTAMP = "audio-timestamp"
SOURCE_REF_KINDS: tuple[str, ...] = (SOURCE_REF_KIND_AUDIO_TIMESTAMP,)

MCP_BINARY_NAME = "transcriber-mcp"

__all__ = [
    "MCP_BINARY_NAME",
    "OIP_VERSION",
    "PRODUCER_DISPLAY_NAME",
    "PRODUCER_HOMEPAGE",
    "PRODUCER_NAME",
    "PRODUCER_VERSION",
    "REGION_KIND_TRANSCRIPT_SEGMENT",
    "REGION_KINDS",
    "SOURCE_KINDS",
    "SOURCE_REF_KIND_AUDIO_TIMESTAMP",
    "SOURCE_REF_KINDS",
    "TOOLS_NAMESPACE",
]
