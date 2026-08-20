"""Write ``manifest.json`` to the data dir and to the discovery dir."""

from __future__ import annotations

import json
import os
from pathlib import Path

from transcriber._logging import get_logger
from transcriber.oip.constants import PRODUCER_NAME
from transcriber.oip.manifest import build_manifest

log = get_logger(__name__)


def system_producers_dir() -> Path:
    """``${XDG_CONFIG_HOME:-~/.config}/oip/producers.d``."""
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base).expanduser() / "oip" / "producers.d"


def project_producers_dir(consumer_data_dir: Path) -> Path:
    """``<consumer-data-dir>/.oip/producers.d`` for per-project pinning."""
    return Path(consumer_data_dir).expanduser().resolve() / ".oip" / "producers.d"


def install_manifest(
    data_dir: Path,
    *,
    scope: str = "system",
    consumer_data_dir: Path | None = None,
) -> dict[str, Path]:
    """Write the manifest to the data dir and the producers.d dir.

    ``scope`` is ``"system"`` (default) or ``"project"``. ``project``
    requires ``consumer_data_dir`` — the consumer that should pin this
    producer.
    """
    data_dir = Path(data_dir).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(data_dir)
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"

    written: dict[str, Path] = {}
    data_manifest = data_dir / "manifest.json"
    data_manifest.write_text(payload, encoding="utf-8")
    written["data_dir"] = data_manifest

    if scope == "system":
        prod_dir = system_producers_dir()
    elif scope == "project":
        if consumer_data_dir is None:
            raise ValueError("scope='project' requires consumer_data_dir")
        prod_dir = project_producers_dir(consumer_data_dir)
    else:
        raise ValueError(f"unknown scope: {scope!r}")
    prod_dir.mkdir(parents=True, exist_ok=True)
    discovery_path = prod_dir / f"{PRODUCER_NAME}.json"
    discovery_path.write_text(payload, encoding="utf-8")
    written["discovery"] = discovery_path

    log.info("installed OIP manifest: %s", " ".join(str(p) for p in written.values()))
    return written


def manifest_payload(data_dir: Path) -> str:
    """Manifest as a JSON string — for the ``--print`` dry-run mode."""
    return json.dumps(build_manifest(data_dir), indent=2, ensure_ascii=False) + "\n"


__all__ = [
    "install_manifest",
    "manifest_payload",
    "project_producers_dir",
    "system_producers_dir",
]
