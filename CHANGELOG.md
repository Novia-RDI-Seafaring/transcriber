# Changelog

Notable changes to dialogue-transcriber. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow
[SemVer](https://semver.org/).

## [0.1.2] - 2026-08-20

### Changed
- `transcriber serve` now picks its default backend automatically: `openai`
  when an `OPENAI_API_KEY` is available, otherwise `local`. Previously it
  defaulted to `openai` unconditionally and failed without a key.
  (`transcriber transcribe` still defaults to `local` — audio is never sent
  to a third party unless you opt in.)
- `--no-cache` no longer renders a spurious `--no-no-cache` negation in
  `--help`.

### Added
- README section on where data lives (cache, outputs, model weights);
  rewritten `web/README.md`; CONTRIBUTING.md and this changelog.

## [0.1.1] - 2026-08-20

### Added
- `OPENAI_API_KEY` (and other variables) can live in a project `.env` file:
  the CLI and MCP server load `.env` from the working directory or nearest
  parent. Exported environment variables always take precedence.

## [0.1.0] - 2026-08-20

First public release.

### Added
- Pipeline: Whisper word-level transcription (local faster-whisper or OpenAI
  API) → sentence segments → per-segment clips → TitaNet speaker embeddings
  → UMAP + KMeans clustering → speaker-labeled transcript. Content-hash
  caching per stage.
- CLI: `transcribe` (txt/vtt/srt/json, `--output -` for stdout), `download`
  (YouTube via yt-dlp), `serve` (FastAPI + React review UI), `ui` (legacy
  Dash UI), `oip` (Open Ingestion Protocol producer), `--version`.
- Web review UI: cluster scatter with lasso rename, waveform regions,
  speaker timeline, searchable transcript, multi-job sidebar, TXT/VTT/SRT
  export; bundled into release wheels.
- OIP producer + MCP server (`transcriber-mcp`).
- Claude Code skill / plugin marketplace in-repo.

[0.1.2]: https://github.com/Novia-RDI-Seafaring/transcriber/releases/tag/v0.1.2
[0.1.1]: https://github.com/Novia-RDI-Seafaring/transcriber/releases/tag/v0.1.1
[0.1.0]: https://github.com/Novia-RDI-Seafaring/transcriber/releases/tag/v0.1.0
