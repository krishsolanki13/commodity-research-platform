"""API tests for POST /api/validation/run, GET /status, GET /report.

6 tests. Uses TestClient (synchronous). State setup uses the router's
_register/_update helpers to match the module's own state management pattern.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# ── Shared fixtures ───────────────────────────────────────────────────────────

_LAUNCH_PAYLOAD = {
    "asset": "gold",
    "strategy_name": "ema_crossover",
    "parameters": {"fast_period": 50, "slow_period": 200},
    "n_splits": 2,
    "embargo_bars": 5,
}

_MINIMAL_REPORT = {
    "validation_run_id": "20240101_120000_validation_gold_ema_crossover",
    "asset": "gold",
    "strategy_name": "ema_crossover",
    "parameters": {"fast_period": 50, "slow_period": 200},
    "n_splits": 2,
    "embargo_bars": 5,
    "computation_date": "2024-01-01",
    "folds": [],
    "insample_sharpe": 0.42,
    "outsample_sharpe": 0.18,
    "insample_return": 0.15,
    "outsample_return": 0.06,
    "overfitting_ratio": 0.43,
    "sharpe_se": 0.22,
    "psr": 0.72,
    "n_trials": 47,
    "sr_benchmark": 1.85,
    "dsr": 0.23,
    "is_significant": False,
    "dsr_threshold": 0.95,
}


# ── Test 1: POST /run returns 202 ─────────────────────────────────────────────


def test_validation_launch_returns_202_with_run_id() -> None:
    """POST /api/validation/run returns 202 Accepted with a validation_run_id."""
    response = client.post("/api/validation/run", json=_LAUNCH_PAYLOAD)
    assert response.status_code == 202, response.text
    data = response.json()
    assert "validation_run_id" in data, f"Missing validation_run_id in {data}"
    assert "status" in data
    assert "gold" in data["validation_run_id"]
    assert "ema_crossover" in data["validation_run_id"]


# ── Test 2: GET /status returns queued ───────────────────────────────────────


def test_validation_status_returns_queued_immediately_after_launch() -> None:
    """GET /status returns 'queued' for a task in queued state."""
    import api.routers.validation as val_router

    test_run_id = "20240101_000000_validation_gold_ema_crossover_statustest"
    val_router._register(test_run_id)

    try:
        response = client.get(f"/api/validation/{test_run_id}/status")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "queued"
        assert data["validation_run_id"] == test_run_id
    finally:
        val_router._validation_tasks.pop(test_run_id, None)


# ── Test 3: GET /report returns 409 before complete ──────────────────────────


def test_validation_report_returns_409_before_complete() -> None:
    """GET /report returns 409 when the run exists but is not yet complete."""
    import api.routers.validation as val_router

    test_run_id = "20240101_000000_validation_gold_ema_crossover_409test"
    val_router._register(test_run_id)
    val_router._update(test_run_id, "running")

    try:
        response = client.get(f"/api/validation/{test_run_id}/report")
        assert response.status_code == 409, response.text
        detail = response.json().get("detail", {})
        assert detail.get("code") == "VALIDATION_NOT_COMPLETE"
    finally:
        val_router._validation_tasks.pop(test_run_id, None)


# ── Test 4: GET /report returns 200 from disk ────────────────────────────────


def test_validation_report_returns_200_from_disk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /report reads from disk and returns 200 with correct fields."""
    import api.routers.validation as val_router

    run_id = _MINIMAL_REPORT["validation_run_id"]
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "validation_report.json").write_text(
        json.dumps(_MINIMAL_REPORT), encoding="utf-8"
    )

    monkeypatch.setattr(val_router, "_VALIDATION_DIR", tmp_path)
    # Ensure run is NOT in memory (pure disk path)
    val_router._validation_tasks.pop(run_id, None)

    response = client.get(f"/api/validation/{run_id}/report")
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["validation_run_id"] == run_id
    assert data["asset"] == "gold"
    assert data["dsr"] == pytest.approx(0.23)
    assert data["is_significant"] is False
    assert data["n_trials"] == 47
    assert isinstance(data["folds"], list)


# ── Test 5: GET /status returns complete for disk-backed run ─────────────────


def test_validation_status_returns_complete_for_disk_backed_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /status returns 'complete' when artifact is on disk but not in memory."""
    import api.routers.validation as val_router

    run_id = "20240202_090000_validation_gold_ema_crossover_disktest"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "validation_report.json").write_text(
        json.dumps({**_MINIMAL_REPORT, "validation_run_id": run_id}),
        encoding="utf-8",
    )

    monkeypatch.setattr(val_router, "_VALIDATION_DIR", tmp_path)
    val_router._validation_tasks.pop(run_id, None)  # simulate post-restart state

    response = client.get(f"/api/validation/{run_id}/status")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "complete"


# ── Test 6: Unknown run returns 404 ──────────────────────────────────────────


def test_validation_unknown_run_returns_404(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /status and GET /report both return 404 for an entirely unknown run_id."""
    import api.routers.validation as val_router

    monkeypatch.setattr(val_router, "_VALIDATION_DIR", tmp_path)  # empty dir

    fake_id = "99991231_235959_validation_nonexistent_run"
    val_router._validation_tasks.pop(fake_id, None)

    status_resp = client.get(f"/api/validation/{fake_id}/status")
    assert status_resp.status_code == 404, status_resp.text
    assert status_resp.json()["detail"]["code"] == "VALIDATION_NOT_FOUND"

    report_resp = client.get(f"/api/validation/{fake_id}/report")
    assert report_resp.status_code == 404, report_resp.text
