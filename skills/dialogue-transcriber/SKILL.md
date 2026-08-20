---
name: dialogue-transcriber
description: >
  Transcribe audio or video of conversations — interviews, panel discussions,
  meetings, podcasts, YouTube videos — and identify who said what (speaker
  diarization) using the `transcriber` CLI. Use this skill whenever the user
  wants a transcript of multi-speaker audio, asks "who said what", wants
  speakers labeled or separated in a recording, wants subtitles (VTT/SRT) with
  speaker names, wants to transcribe a YouTube link, or wants to review and
  relabel speakers in a web UI — even if they don't use the words
  "diarization" or "transcription" (e.g. "turn this panel recording into
  text", "get me quotes per person from this interview").
compatibility: Requires ffmpeg/ffprobe on PATH. Uses `uv`/`uvx` to run the dialogue-transcriber package.
---

# Dialogue Transcriber

`transcriber` runs a pipeline: Whisper word-level transcription → sentence
segments → per-segment audio clips → TitaNet speaker embeddings → UMAP +
KMeans clustering → a transcript where every line is attributed to
`Speaker 1`, `Speaker 2`, …

## Setup

Check availability first; prefer an existing install:

```bash
transcriber --version || uv tool install "dialogue-transcriber[all]"
ffmpeg -version >/dev/null || echo "ffmpeg missing — install it (e.g. brew install ffmpeg)"
```

One-off runs also work without installing: `uvx --from "dialogue-transcriber[all]" transcriber …`

Pick a transcription backend:

- `--backend local` (default) — faster-whisper on this machine. No API key,
  but downloads a large model on first use and is slow without a GPU.
- `--backend openai` — OpenAI Whisper API. Fast and light; requires
  `OPENAI_API_KEY`, read from the environment or from a `.env` file in the
  working directory (or a parent — exported variables win over the file).
  Prefer this when the key is available and the audio is not sensitive; ask
  the user if unsure.

## Transcribe (the main task)

```bash
# Local file or YouTube URL; writes <audio>.txt next to the input
transcriber transcribe interview.mp3
transcriber transcribe "https://www.youtube.com/watch?v=..." --backend openai

# Useful options
#   --participants 3      number of speakers, if known (improves clustering)
#   --language sv         audio language (default en)
#   --format txt|vtt|srt|json
#   --context "..."       names/jargon hint passed to Whisper
#   --output PATH | -     output file, or '-' for stdout
```

Pass `--participants` whenever the user tells you (or the content implies)
how many people are speaking — clustering is noticeably better with it.

For your own consumption, use JSON on stdout — parse it instead of scraping
the human-readable formats:

```bash
transcriber transcribe interview.mp3 --format json --output -
```

```json
{
  "speakers": ["Speaker 1", "Speaker 2"],
  "n_segments": 42,
  "duration": 512.3,
  "segments": [
    {"speaker": "Speaker 1", "start": 0.0, "end": 4.2, "text": "..."}
  ]
}
```

Every stage is cached under `.transcriber-cache/` keyed on audio content +
config, so re-running with different output formats or a corrected
`--participants` is cheap — never avoid a re-run out of cost concern, and
don't delete the cache between runs on the same file.

Speaker labels are anonymous (`Speaker 1`, …). To map them to real names,
read the JSON and infer names from the dialogue itself (people address each
other), from `--context` the user gave, or ask the user — then post-process
your output accordingly.

## Review UI (offer this to the user)

Automatic clustering is good but not perfect. When the user cares about
correctness of the speaker labels, launch the web UI and let them inspect
and relabel — it shows a cluster scatter, a per-speaker timeline, a
waveform, and click-to-play segments, and exports TXT/VTT/SRT:

```bash
transcriber serve interview.mp3 --participants 3   # http://127.0.0.1:8000
```

The command blocks; run it in the background and tell the user the URL.
Renames made in the UI are persisted server-side in the work dir.

## Ingest into a knowledge base (OIP)

The package is an Open Ingestion Protocol producer. When the user wants
transcripts inside an OIP consumer (e.g. Anchor):

```bash
transcriber oip install --data-dir <dir>              # register producer
transcriber oip ingest audio.mp3 --data-dir <dir>     # transcript → OIP regions
transcriber oip serve                                 # MCP server (also: transcriber-mcp)
```

## Troubleshooting

- `ffmpeg` errors → it must be on PATH; install via the system package manager.
- Local backend very slow → suggest `--backend openai`, or accept the wait.
- Wrong speaker count → re-run with explicit `--participants N` (cached
  stages make this fast), or hand the user the review UI.
- Long files → chunked automatically (`--chunk-seconds`, default 600).
