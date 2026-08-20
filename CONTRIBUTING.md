# Contributing

Thanks for your interest! Issues and pull requests are welcome at
[Novia-RDI-Seafaring/transcriber](https://github.com/Novia-RDI-Seafaring/transcriber).

## Development setup

Requirements: Python ≥ 3.10, [uv](https://docs.astral.sh/uv/), `ffmpeg`/`ffprobe`
on PATH, and [pnpm](https://pnpm.io/) for the frontend.

```bash
git clone https://github.com/Novia-RDI-Seafaring/transcriber
cd transcriber
uv venv
uv pip install -e ".[dev,cluster,api,openai,embed,youtube]"
(cd web && pnpm install && pnpm build)
```

## Checks

CI runs these on every PR; run them locally first:

```bash
pytest -m "not slow"     # heavy models are faked; ffmpeg-needing tests skip cleanly
ruff check src tests
(cd web && pnpm build)
```

Add tests for behavior changes. The transcription/embedding backends are
Protocols with in-memory fakes in `tests/conftest.py`, so most pipeline
behavior is testable without downloading models.

## Pull requests

- Keep PRs focused; one topic per PR.
- Match the surrounding code style (ruff enforces the basics).
- Update `CHANGELOG.md` under an "Unreleased" heading if your change is
  user-visible.

## Releases (maintainers)

1. Bump `version` in `pyproject.toml`, `__version__` in
   `src/transcriber/__init__.py`, and `.claude-plugin/plugin.json`.
2. Move the changelog's Unreleased notes under the new version.
3. Push, then publish a GitHub release tagged `vX.Y.Z` —
   `.github/workflows/release.yml` builds the frontend, bundles it into the
   wheel, and publishes to PyPI via trusted publishing.
