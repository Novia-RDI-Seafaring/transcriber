"""Content-hashed cache for stage outputs.

Each cache entry lives at ``<work_dir>/<stage>/<key>.<ext>``. The key is the
sha256 of the inputs that uniquely determine the output (e.g. an audio file's
content hash plus the relevant config).

Numpy arrays go through ``np.save``/``np.load``; plain Python objects use
``pickle``. We accept pickle here because the cache is local-only and never
network-trusted.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

_CHUNK = 1 << 20


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def stable_hash(*parts: Any) -> str:
    """sha256 over a stable JSON encoding of ``parts``."""
    payload = json.dumps(parts, default=_json_default, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    raise TypeError(f"not json-serializable: {type(obj)}")


class Cache:
    """Filesystem cache rooted at ``work_dir``."""

    def __init__(self, work_dir: Path, *, enabled: bool = True) -> None:
        self.work_dir = Path(work_dir)
        self.enabled = enabled
        if enabled:
            self.work_dir.mkdir(parents=True, exist_ok=True)

    def path(self, stage: str, key: str, ext: str) -> Path:
        d = self.work_dir / stage
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{key}.{ext}"

    # ------- pickle -------
    def get_pickle(self, stage: str, key: str) -> Any | None:
        if not self.enabled:
            return None
        p = self.path(stage, key, "pkl")
        if not p.exists():
            return None
        with p.open("rb") as f:
            return pickle.load(f)

    def put_pickle(self, stage: str, key: str, value: Any) -> Path:
        p = self.path(stage, key, "pkl")
        with p.open("wb") as f:
            pickle.dump(value, f)
        return p

    # ------- numpy -------
    def get_npy(self, stage: str, key: str) -> np.ndarray | None:
        if not self.enabled:
            return None
        p = self.path(stage, key, "npy")
        if not p.exists():
            return None
        return np.load(p)

    def put_npy(self, stage: str, key: str, value: np.ndarray) -> Path:
        p = self.path(stage, key, "npy")
        np.save(p, value)
        return p

    def cached(self, stage: str, key: str, exts: Iterable[str] = ("pkl",)) -> bool:
        return self.enabled and any(self.path(stage, key, e).exists() for e in exts)
