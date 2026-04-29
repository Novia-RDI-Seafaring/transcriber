"""KMeans clustering on a 2-D projection of speaker embeddings.

Pipeline:

* If we have very few embeddings (< 4), do a 2-component PCA — UMAP is
  unhappy with such tiny inputs and the original code already had this
  fallback.
* Otherwise reduce to 2-D with UMAP. ``n_neighbors`` is computed from the
  data size, with a floor of 2 and a ceiling of 50.
* Pick ``k`` either from the user (``participants``) or by maximizing the
  silhouette score over ``range(2, max_clusters+1)``.
* Run KMeans for the chosen ``k`` and return labels + projection.

Requires the ``cluster`` extra: ``pip install transcriber[cluster]``.
"""

from __future__ import annotations

import numpy as np

from transcriber._logging import get_logger
from transcriber.models import ClusterResult

log = get_logger(__name__)


def cluster_embeddings(
    embeddings: np.ndarray,
    *,
    participants: int | None = None,
    max_clusters: int = 10,
    random_state: int = 0,
    umap_min_dist: float = 0.0,
) -> ClusterResult:
    """Reduce ``embeddings`` to 2-D and KMeans-cluster them."""
    if embeddings.ndim != 2:
        raise ValueError(f"expected 2-D embeddings, got shape {embeddings.shape}")
    n = embeddings.shape[0]
    if n == 0:
        raise ValueError("no embeddings to cluster")

    projection = _reduce(embeddings, participants=participants, random_state=random_state, min_dist=umap_min_dist)
    raw_labels, k = _kmeans_with_silhouette(
        projection,
        max_clusters=max_clusters,
        participants=participants,
        random_state=random_state,
    )
    labels = _label_speakers(raw_labels)
    return ClusterResult(labels=labels, raw_labels=raw_labels, projection=projection, n_clusters=k)


def _reduce(
    embeddings: np.ndarray,
    *,
    participants: int | None,
    random_state: int,
    min_dist: float,
) -> np.ndarray:
    n = embeddings.shape[0]
    if n < 4:
        from sklearn.decomposition import PCA  # type: ignore[import-not-found]

        log.info("only %d points; using PCA(2) instead of UMAP", n)
        n_components = min(2, n)
        return PCA(n_components=n_components).fit_transform(embeddings)

    import umap  # type: ignore[import-not-found]

    n_neighbors = max(2, participants or 0, min(n - 1, int(n * 0.1), 50))
    log.info("UMAP n_neighbors=%d for %d points", n_neighbors, n)
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        random_state=random_state,
        n_jobs=-1 if random_state is None else 1,
    )
    return reducer.fit_transform(embeddings)


def _kmeans_with_silhouette(
    data: np.ndarray,
    *,
    max_clusters: int,
    participants: int | None,
    random_state: int,
) -> tuple[np.ndarray, int]:
    from sklearn.cluster import KMeans  # type: ignore[import-not-found]
    from sklearn.metrics import silhouette_score  # type: ignore[import-not-found]

    n_samples = data.shape[0]
    if participants is not None:
        k = max(1, min(participants, n_samples))
        km = KMeans(n_clusters=k, random_state=random_state, n_init="auto").fit(data)
        return km.labels_, k

    cap = min(max_clusters, n_samples - 1)
    if cap < 2:
        return np.zeros(n_samples, dtype=int), 1

    best_k = 2
    best_score = -1.0
    best_labels: np.ndarray | None = None
    for k in range(2, cap + 1):
        km = KMeans(n_clusters=k, random_state=random_state, n_init="auto").fit(data)
        score = silhouette_score(data, km.labels_)
        log.debug("silhouette k=%d -> %.3f", k, score)
        if score > best_score:
            best_score = score
            best_k = k
            best_labels = km.labels_
    assert best_labels is not None
    return best_labels, best_k


def _label_speakers(raw_labels: np.ndarray) -> list[str]:
    """Map integer cluster ids to ``Speaker N`` labels in order of appearance."""
    seen: dict[int, str] = {}
    out: list[str] = []
    for label in raw_labels.tolist():
        name = seen.get(label)
        if name is None:
            name = f"Speaker {len(seen) + 1}"
            seen[label] = name
        out.append(name)
    return out
