"""Open Ingestion Protocol (OIP) producer.

This subpackage is a thin, additive layer on top of :mod:`transcriber`. It
adapts a :class:`~transcriber.models.PipelineResult` into the OIP
on-disk shape (`manifest.json`, `artefacts/<slug>/document.json`,
`artefacts/<slug>/regions.json`, `content/...`) and exposes the
producer's operations as MCP-stdio tools.

The OIP spec lives at https://github.com/Novia-RDI-Seafaring/OIP and is
also available locally via ``oip spec`` / ``oip schema`` after
``uv tool install`` of the ``oip`` package.
"""

from transcriber.oip.constants import (
    OIP_VERSION,
    PRODUCER_NAME,
    PRODUCER_VERSION,
    REGION_KIND_TRANSCRIPT_SEGMENT,
    REGION_KINDS,
    SOURCE_KINDS,
    SOURCE_REF_KINDS,
    TOOLS_NAMESPACE,
)

__all__ = [
    "OIP_VERSION",
    "PRODUCER_NAME",
    "PRODUCER_VERSION",
    "REGION_KIND_TRANSCRIPT_SEGMENT",
    "REGION_KINDS",
    "SOURCE_KINDS",
    "SOURCE_REF_KINDS",
    "TOOLS_NAMESPACE",
]
