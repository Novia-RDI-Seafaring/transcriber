# transcriber

Transcribe interviews, identify speakers from voice embeddings, and
relabel them interactively.

The pipeline takes an audio file (or a YouTube URL), produces word-level
timestamps with Whisper, groups words into sentence segments, extracts a
short audio clip per segment, embeds each clip with NVIDIA NeMo TitaNet,
clusters the embeddings on a UMAP projection, and emits a transcript
labeled with `Speaker 1`, `Speaker 2`, …. A Dash UI lets you lasso-select
points in the projection and rename clusters with the speakers' real
names.

## Install

```bash
uv pip install transcriber              # core only
uv pip install "transcriber[local]"     # + faster-whisper backend
uv pip install "transcriber[openai]"    # + OpenAI Whisper API backend
uv pip install "transcriber[cluster]"   # + scikit-learn / UMAP
uv pip install "transcriber[embed]"     # + NeMo TitaNet speaker embedder
uv pip install "transcriber[ui]"        # + Dash UI
uv pip install "transcriber[youtube]"   # + yt-dlp downloader
uv pip install "transcriber[all]"       # everything
```

`ffmpeg` and `ffprobe` must be on `PATH`. On macOS:

```bash
brew install ffmpeg
```

For local development:

```bash
git clone <repo>
cd transcriber
uv venv
uv pip install -e ".[dev,cluster,ui]"
```

## CLI

```bash
# Run the full pipeline and emit a speaker-labeled .txt next to the audio
transcriber transcribe path/to/audio.mp3

# Specify number of speakers, language, output format
transcriber transcribe interview.mp3 --participants 3 --language sv --format vtt

# Use the OpenAI API instead of the local model
transcriber transcribe interview.mp3 --backend openai

# Pull audio from YouTube
transcriber download https://www.youtube.com/watch?v=...

# Launch the relabeling UI on http://127.0.0.1:8051
transcriber ui interview.mp3 --participants 2
```

## Library use

```python
from transcriber.config import ClusterConfig, PipelineConfig, TranscribeConfig
from transcriber.pipeline import run_pipeline
from transcriber.render import render_txt

cfg = PipelineConfig(
    transcribe=TranscribeConfig(backend="local", language="en"),
    cluster=ClusterConfig(participants=2),
)
result = run_pipeline("interview.mp3", config=cfg)
print(render_txt(result.segments))
```

`PipelineResult.segments` is a list of `SpeakerSegment` records with the
sentence text, time range, the on-disk clip, and the assigned speaker.
`PipelineResult.cluster.projection` is the 2-D UMAP for plotting.

## Pipeline stages

```
audio  ──►  transcribe  ──►  segment  ──►  extract_clips  ──►  embed  ──►  cluster
              (Whisper)        (sentence-       (ffmpeg)       (TitaNet)    (UMAP +
                               level)                                       KMeans +
                                                                            silhouette)
```

Each stage's output is cached under `--work-dir` (default
`.transcriber-cache`), keyed on the audio's content hash plus the
relevant config. Re-running with the same inputs is free; changing one
stage's config invalidates only that stage and its dependents.

## Backends

| Concern    | Default                                   | Override via                 |
|------------|-------------------------------------------|------------------------------|
| Transcribe | `faster-whisper` large-v3                 | `--backend openai`           |
| Embed      | `nvidia/speakerverification_en_titanet_large` | pass `embedder=` to `run_pipeline` |
| Cluster    | UMAP(2) + KMeans + silhouette             | pass a `ClusterConfig`        |
| YouTube    | `yt-dlp`                                  | replace `YouTubeDownloader`   |

All backends are protocols — see `transcriber/transcribe/base.py`,
`transcriber/embed/base.py`. Tests use in-memory fakes.

## Tests

```bash
uv pip install -e ".[dev,cluster]"
pytest                  # core + clustering tests
pytest -m "not slow"    # skip heavy/network tests
```

`ffmpeg` is auto-detected; tests that need it skip cleanly when it is
absent. Tests that need NeMo or `faster-whisper` rely on injected fakes,
so the heavy models are not required to run the suite.

## License

MIT.
