"""Speaker-embedder protocol."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import numpy as np


class SpeakerEmbedder(Protocol):
    """Strategy interface for any speaker-embedding model.

    ``embed_files`` returns a 2-D ndarray of shape (n_clips, embedding_dim).
    """

    def embed_files(self, paths: Sequence[Path]) -> np.ndarray: ...
