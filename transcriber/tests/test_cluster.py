"""Speaker clustering."""

from __future__ import annotations

import numpy as np
import pytest

# scikit-learn / umap-learn live behind the cluster extra; if they're not
# installed we want a clean skip rather than an import error.
pytest.importorskip("sklearn")


from transcriber.cluster.kmeans import _label_speakers, cluster_embeddings  # noqa: E402


def test_label_speakers_assigns_in_order():
    labels = _label_speakers(np.array([2, 0, 0, 1, 2]))
    assert labels == ["Speaker 1", "Speaker 2", "Speaker 2", "Speaker 3", "Speaker 1"]


def test_cluster_with_known_participants(fake_embeddings: np.ndarray):
    """Two well-separated clusters should produce two distinct labels."""
    result = cluster_embeddings(fake_embeddings, participants=2, random_state=0)
    assert result.n_clusters == 2
    assert set(result.labels) == {"Speaker 1", "Speaker 2"}
    # First three points are one cluster, last three are another.
    assert len(set(result.labels[:3])) == 1
    assert len(set(result.labels[3:])) == 1
    assert result.labels[0] != result.labels[3]


def test_cluster_silhouette_picks_two(fake_embeddings: np.ndarray):
    """With clearly two clusters, silhouette should pick k=2."""
    result = cluster_embeddings(fake_embeddings, max_clusters=4, random_state=0)
    assert result.n_clusters == 2


def test_cluster_pca_fallback_for_small_n():
    rng = np.random.default_rng(0)
    embeddings = rng.normal(size=(3, 8))
    result = cluster_embeddings(embeddings, participants=2, random_state=0)
    assert result.projection.shape[0] == 3
    assert result.projection.shape[1] in (1, 2)


def test_cluster_rejects_empty():
    with pytest.raises(ValueError):
        cluster_embeddings(np.zeros((0, 4)))


def test_cluster_rejects_non_2d():
    with pytest.raises(ValueError):
        cluster_embeddings(np.zeros(8))
