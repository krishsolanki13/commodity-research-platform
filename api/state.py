"""In-process task state for backtest and portfolio run lifecycle.

TD-F0-B: A crashed API process loses all in-flight tasks. Acceptable for a
local research tool where vectorized backtests complete in seconds. A task
queue (Redis/Celery) is the documented upgrade path for multi-user or
long-running portfolio batch runs.
"""

from __future__ import annotations

from threading import Lock
from typing import Any, Literal

TaskStatus = Literal["queued", "running", "persisting", "complete", "failed"]

_store: dict[str, dict[str, Any]] = {}
# Maps polling_run_id → actual artifact run_id (set after completion)
_artifact_map: dict[str, str] = {}
_lock = Lock()


def register(run_id: str) -> None:
    """Register a new task in the queued state."""
    with _lock:
        _store[run_id] = {"status": "queued", "error": None, "executed_at": None}


def update(
    run_id: str,
    status: TaskStatus,
    *,
    error: str | None = None,
    executed_at: str | None = None,
) -> None:
    """Update task status. No-op if run_id is not registered."""
    with _lock:
        if run_id not in _store:
            return
        _store[run_id]["status"] = status
        if error is not None:
            _store[run_id]["error"] = error
        if executed_at is not None:
            _store[run_id]["executed_at"] = executed_at


def get(run_id: str) -> dict[str, Any] | None:
    """Return a copy of the task state, or None if not registered."""
    with _lock:
        return dict(_store[run_id]) if run_id in _store else None


def set_artifact_id(polling_id: str, artifact_id: str) -> None:
    """Map polling id → on-disk artifact id.

    Also aliases the poll_-stripped form so GET /api/runs/{stripped} resolves
    when the frontend strips the prefix before the timestamps match.
    """
    stripped = polling_id.removeprefix("poll_")
    with _lock:
        _artifact_map[polling_id] = artifact_id
        if stripped != polling_id:
            _artifact_map[stripped] = artifact_id


def get_artifact_id(polling_id: str) -> str | None:
    with _lock:
        return _artifact_map.get(polling_id)
