"""FastAPI backend for the React frontend.

Multi-job server: every transcription request is a Job that runs in a
worker thread, with state persisted under ``<work_dir>/jobs``. Install
via the ``[api]`` extra.
"""

from transcriber.api.jobs import JobManager, JobRecord
from transcriber.api.server import build_app, run

__all__ = ["JobManager", "JobRecord", "build_app", "run"]
