# Web frontend

The React (Vite + TypeScript) review UI served by `transcriber serve`:
a UMAP cluster scatter, a waveform with one region per segment, a
Gantt-style speaker timeline, a searchable virtualized transcript, and
inline speaker renaming. It talks to the FastAPI backend under `/api`.

## Development

```bash
pnpm install
pnpm dev        # http://127.0.0.1:5173, proxies /api to :8000
```

Run the backend in another shell:

```bash
transcriber serve interview.mp3 --port 8000
```

## Production build

```bash
pnpm build      # outputs to dist/
```

`transcriber serve` looks for the build in two places: `web/dist` in a
development checkout, or `transcriber/web/dist` inside an installed wheel.
Release wheels bundle the build automatically — `.github/workflows/release.yml`
runs `pnpm build` and copies `dist/` into the package before `uv build`.

## Layout

- `src/App.tsx` — layout and top-level state wiring
- `src/store.ts` — client state (zustand)
- `src/api.ts` / `src/types.ts` — backend API client and shared types
- `src/components/` — Scatter, Timeline, Transcript, AudioPlayer, SpeakerChips,
  Sidebar/JobsList (multi-job manager), NewJobDialog
- `src/hooks/useKeyboardNav.ts` — ↑/↓ segment stepping, Space play/pause,
  `/` search focus
