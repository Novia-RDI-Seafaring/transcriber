"""CLI input dispatch — local path vs YouTube URL."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from transcriber.cli import _is_url, _resolve_audio
from transcriber.download.youtube import DownloadResult


def test_is_url_recognizes_http_and_https():
    assert _is_url("https://www.youtube.com/watch?v=foo")
    assert _is_url("http://example.com/a.mp3")
    assert not _is_url("/tmp/a.mp3")
    assert not _is_url("audio.mp3")


def test_resolve_audio_passes_through_existing_path(tmp_path: Path):
    p = tmp_path / "a.mp3"
    p.write_bytes(b"\x00")
    assert _resolve_audio(str(p), work_dir=tmp_path) == p


def test_resolve_audio_rejects_missing_path(tmp_path: Path):
    with pytest.raises(typer.BadParameter):
        _resolve_audio(str(tmp_path / "nope.mp3"), work_dir=tmp_path)


def test_resolve_audio_downloads_for_url(tmp_path: Path):
    expected = tmp_path / "youtube" / "abc" / "abc.mp3"
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"\x00")

    with patch("transcriber.download.youtube.download_youtube") as mock_dl:
        mock_dl.return_value = DownloadResult(
            audio_path=expected, title="Demo", video_id="abc"
        )
        out = _resolve_audio("https://youtu.be/abc", work_dir=tmp_path)

    assert out == expected
    mock_dl.assert_called_once()
    call_args = mock_dl.call_args
    assert call_args.kwargs["use_cached"] is True
    assert call_args.args[0] == "https://youtu.be/abc"
    assert call_args.args[1] == tmp_path / "youtube"
