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


def _fake_result():
    import numpy as np

    from transcriber.models import Clip, ClusterResult, Segment, SpeakerSegment

    seg = SpeakerSegment(
        segment=Segment(text="Hi.", start=0.0, end=1.0),
        clip=Clip(path=Path("/tmp/x.wav"), start=0.0, end=1.0),
        speaker="Speaker 1",
    )

    class _R:
        segments = [seg]
        cluster = ClusterResult(
            labels=["Speaker 1"],
            raw_labels=np.array([0]),
            projection=np.zeros((1, 2)),
            n_clusters=1,
        )

    return _R()


def test_transcribe_json_to_stdout(tmp_path: Path):
    import json

    from typer.testing import CliRunner

    from transcriber.cli import app

    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"\x00")

    with patch("transcriber.cli.run_pipeline", return_value=_fake_result()):
        result = CliRunner().invoke(
            app, ["transcribe", str(audio), "--format", "json", "--output", "-"]
        )

    assert result.exit_code == 0, result.output
    doc = json.loads(result.stdout)
    assert doc["speakers"] == ["Speaker 1"]
    assert doc["segments"][0]["text"] == "Hi."


def test_version_flag():
    from typer.testing import CliRunner

    from transcriber import __version__
    from transcriber.cli import app

    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_env_file_loaded_from_cwd(tmp_path: Path, monkeypatch):
    import os

    from transcriber._env import load_env

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TRANSCRIBER_TEST_ENV_KEY", raising=False)
    monkeypatch.setenv("TRANSCRIBER_TEST_EXPORTED", "exported-wins")
    (tmp_path / ".env").write_text(
        "TRANSCRIBER_TEST_ENV_KEY=from-dotenv\nTRANSCRIBER_TEST_EXPORTED=from-dotenv\n"
    )

    load_env()

    assert os.environ["TRANSCRIBER_TEST_ENV_KEY"] == "from-dotenv"
    # an already-exported variable is never overridden by the file
    assert os.environ["TRANSCRIBER_TEST_EXPORTED"] == "exported-wins"
