"""NVIDIA NeMo TitaNet speaker-embedding backend.

Requires the ``embed`` extra: ``pip install transcriber[embed]``.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from transcriber._logging import get_logger

log = get_logger(__name__)

_DEFAULT_MODEL = "nvidia/speakerverification_en_titanet_large"


class NemoSpeakerEmbedder:
    """Wraps ``nemo_asr.models.EncDecSpeakerLabelModel`` (TitaNet)."""

    def __init__(self, *, model_name: str = _DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model: Any | None = None

    def _model_or_load(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            import nemo.collections.asr as nemo_asr  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "nemo_toolkit not installed. Run `pip install transcriber[embed]`."
            ) from exc
        log.info("loading nemo speaker model %s", self.model_name)
        self._model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained(self.model_name)
        return self._model

    def embed_files(self, paths: Sequence[Path]) -> np.ndarray:
        model = self._model_or_load()
        rows: list[np.ndarray] = []
        for p in paths:
            emb = model.get_embedding(str(p))
            arr = _to_numpy(emb).reshape(-1)
            rows.append(arr)
        return np.stack(rows, axis=0)


def _to_numpy(x: Any) -> np.ndarray:
    if hasattr(x, "detach"):
        x = x.detach().cpu().numpy()
    return np.asarray(x)
