"""Filesystem cache."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from transcriber.cache import Cache, file_hash, stable_hash


def test_file_hash_stable(tmp_path: Path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"abc")
    h = file_hash(p)
    assert h == file_hash(p)
    assert len(h) == 64


def test_file_hash_changes_with_content(tmp_path: Path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"abc")
    h1 = file_hash(p)
    p.write_bytes(b"abd")
    assert file_hash(p) != h1


def test_stable_hash_order_independent_within_object():
    a = stable_hash({"a": 1, "b": 2})
    b = stable_hash({"b": 2, "a": 1})
    assert a == b


def test_pickle_roundtrip(tmp_path: Path):
    cache = Cache(tmp_path)
    cache.put_pickle("stage", "k1", {"x": [1, 2, 3]})
    assert cache.get_pickle("stage", "k1") == {"x": [1, 2, 3]}


def test_pickle_miss_returns_none(tmp_path: Path):
    cache = Cache(tmp_path)
    assert cache.get_pickle("stage", "nope") is None


def test_npy_roundtrip(tmp_path: Path):
    cache = Cache(tmp_path)
    arr = np.arange(12).reshape(3, 4).astype(np.float32)
    cache.put_npy("emb", "k", arr)
    out = cache.get_npy("emb", "k")
    assert out is not None
    np.testing.assert_array_equal(out, arr)


def test_disabled_cache_never_writes(tmp_path: Path):
    cache = Cache(tmp_path, enabled=False)
    cache.put_pickle("stage", "k", {"a": 1})
    assert cache.get_pickle("stage", "k") is None
