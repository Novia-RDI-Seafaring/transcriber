"""Project logging setup. Library code uses ``logging.getLogger(__name__)``;
applications opt into formatting via :func:`configure_logging`."""

from __future__ import annotations

import logging
import os


def configure_logging(level: int | str | None = None) -> None:
    """Configure root-level logging once. Idempotent.

    Level resolution: explicit arg > ``TRANSCRIBER_LOG_LEVEL`` env > INFO.
    """
    if level is None:
        level = os.environ.get("TRANSCRIBER_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
