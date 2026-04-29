# transcriber

Transcribe interviews, identify speakers from voice embeddings, and
relabel them interactively in a React web UI.

The pipeline takes an audio file (or a YouTube URL), produces word-level
timestamps with Whisper, groups words into sentence segments, extracts a
short audio clip per segment, embeds each clip with NVIDIA NeMo TitaNet,
clusters the embeddings on a UMAP projection, and emits a transcript
labeled with `Speaker 1`, `Speaker 2`, …. The web UI lets you lasso a
cluster, rename it inline, hear individual segments, and search the
transcript — all synchronized across a UMAP scatter, a Gantt-style
timeline, and a continuous waveform with one region per segment.

## Install

```bash
uv pip install transcriber              # core only
uv pip install "transcriber[local]"     # + faster-whisper backend
uv pip install "transcriber[openai]"    # + OpenAI Whisper API backend
uv pip install "transcriber[cluster]"   # + scikit-learn / UMAP
uv pip install "transcriber[embed]"     # + NeMo TitaNet speaker embedder
uv pip install "transcriber[ui]"        # + (legacy) Dash UI
uv pip install "transcriber[api]"       # + FastAPI backend (powers the React UI)
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
uv pip install -e ".[dev,cluster,api,openai,embed,youtube]"
# build the React frontend once so `transcriber serve` can serve it
(cd web && pnpm install && pnpm build)
```

## CLI

```bash
# Run the full pipeline and emit a speaker-labeled .txt next to the audio
transcriber transcribe path/to/audio.mp3

# Specify number of speakers, language, output format
transcriber transcribe interview.mp3 --participants 3 --language sv --format vtt

# OpenAI Whisper API instead of the local model
transcriber transcribe interview.mp3 --backend openai

# Pull audio from YouTube
transcriber download https://www.youtube.com/watch?v=...

# Run pipeline + serve the React UI on http://127.0.0.1:8000
transcriber serve interview.mp3 --participants 3
transcriber serve "https://www.youtube.com/watch?v=..." --backend openai --participants 3

# Legacy Dash UI on http://127.0.0.1:8051 (still works)
transcriber ui interview.mp3 --participants 2
```

`transcriber serve` accepts the same `AUDIO_OR_URL` argument as
`transcribe`. URLs are downloaded once into `<work-dir>/youtube/<id>/`
and reused.

## Web UI

`transcriber serve` runs uvicorn + the FastAPI backend, and serves the
built React frontend from `web/dist`. The UI gives you:

- a UMAP scatter where each dot is one segment, colored by cluster;
- a continuous audio waveform with one **region** per segment, colored
  by speaker — click a region or scrub to play any part;
- a Gantt-style timeline with time ticks;
- a virtualized transcript with full-text search and colored speaker
  dots;
- inline-renameable speaker chips at the top (rename a chip → relabels
  every segment with that speaker, persisted server-side);
- lasso-select on the scatter → bulk rename to any name;
- TXT / VTT / SRT export buttons;
- keyboard navigation: ↑/↓ step segments, Space play/pause, `/` focus
  search, Esc clear selection.

For frontend development:

```bash
cd web
pnpm install
pnpm dev          # http://127.0.0.1:5173, proxies /api to :8000
# in another shell, run the API alone:
transcriber serve interview.mp3 --participants 3 --port 8000
```

For production-ish: `pnpm build` once, then `transcriber serve …` is
fully self-contained.

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

| Concern    | Default                                       | Override via                       |
|------------|-----------------------------------------------|-------------------------------------|
| Transcribe | `faster-whisper` large-v3                     | `--backend openai`                  |
| Embed      | `nvidia/speakerverification_en_titanet_large` | pass `embedder=` to `run_pipeline`  |
| Cluster    | UMAP(2) + KMeans + silhouette                 | pass a `ClusterConfig`              |
| YouTube    | `yt-dlp`                                      | replace `YouTubeDownloader`         |

All backends are Protocols — see `transcriber/transcribe/base.py`,
`transcriber/embed/base.py`. Tests use in-memory fakes.

## Tests

```bash
uv pip install -e ".[dev,cluster,api]"
pytest                  # core + clustering + api tests
pytest -m "not slow"    # skip heavy/network tests
```

`ffmpeg` is auto-detected; tests that need it skip cleanly when it is
absent. Tests that need NeMo or `faster-whisper` rely on injected fakes,
so the heavy models are not required to run the suite.

## License

MIT.
