"""Project ``.env`` support.

A harness or script driving the CLI from inside a project often keeps
secrets (e.g. ``OPENAI_API_KEY``) in a ``.env`` file rather than the
process environment. Every entry point calls :func:`load_env` so those
just work.
"""

from __future__ import annotations

from dotenv import find_dotenv, load_dotenv


def load_env() -> None:
    """Load a ``.env`` from the working directory or nearest parent.

    Variables already present in the environment always win — an
    explicitly exported key is never overridden by a project file.
    """
    path = find_dotenv(usecwd=True)
    if path:
        load_dotenv(path, override=False)
