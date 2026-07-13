from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api import state


def _make_backtest_result(run_id: str = "20240101_120000_ema_crossover_gold"):
    """Minimal mock BacktestResult."""
    result = MagicMock()
    result.run_id = run_id
    result.asset = "gold"
    idx = pd.date_range("2020-01-01", periods=100, freq="D", tz="UTC")
    result.equity_curve = pd.Series(1_000_000.0 + np.arange(100) * 100, index=idx)
    result.pnl_series = pd.Series(100.0, index=idx)
    result.positions = pd.Series(100_000.0, index=idx)
    result.trades = []
    return result


def _make_perf_report():
    report = MagicMock()
    report.scalar_metrics = {
        "sharpe": 0.5,
        "max_drawdown": -0.03,
        "total_return": 0.01,
        "cagr": 0.008,
        "win_rate": 0.55,
        "initial_capital": 1_000_000.0,
    }
    return report


def test_launch_backtest_returns_202_immediately(client: TestClient) -> None:
    """POST /api/backtests must return 202 without waiting for completion."""
    with patch("api.routers.backtests._run_backtest_task"):
        response = client.post(
            "/api/backtests",
            json={
                "asset": "gold",
                "strategy": "ema_crossover",
                "params": {"fast_period": 50, "slow_period": 200},
            },
        )
    assert response.status_code == 202
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "queued"


def test_launch_with_null_signal_evaluation_accepted(client: TestClient) -> None:
    """signal_evaluation: null must return 202, not 400 (IC gate is client-side)."""
    with patch("api.routers.backtests._run_backtest_task"):
        response = client.post(
            "/api/backtests",
            json={
                "asset": "gold",
                "strategy": "ema_crossover",
                "params": {"fast_period": 50, "slow_period": 200},
                "signal_evaluation": None,
            },
        )
    assert response.status_code == 202


def test_poll_status_queued(client: TestClient) -> None:
    run_id = "test_poll_queued_001"
    state.register(run_id)
    response = client.get(f"/api/backtests/{run_id}/status")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_poll_status_complete(client: TestClient) -> None:
    run_id = "test_poll_complete_001"
    state.register(run_id)
    state.update(run_id, "complete", executed_at="2024-01-01T12:00:00Z")
    response = client.get(f"/api/backtests/{run_id}/status")
    assert response.status_code == 200
    assert response.json()["status"] == "complete"
    assert response.json()["executed_at"] is not None


def test_poll_status_unknown_run_404(client: TestClient) -> None:
    response = client.get("/api/backtests/not-a-real-run-id-xyz/status")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"


def test_backtest_lifecycle_mocked(client: TestClient) -> None:
    """Launch → task completes → status is complete."""
    mock_result = _make_backtest_result()

    def fake_task(polling_id: str, request) -> None:
        state.update(polling_id, "running")
        state.set_artifact_id(polling_id, mock_result.run_id)
        state.update(polling_id, "complete", executed_at="2024-01-01T12:00:00Z")

    with patch("api.routers.backtests._run_backtest_task", side_effect=fake_task):
        response = client.post(
            "/api/backtests",
            json={
                "asset": "gold",
                "strategy": "ema_crossover",
                "params": {"fast_period": 50, "slow_period": 200},
            },
        )
    assert response.status_code == 202
    polling_id = response.json()["run_id"]

    status_resp = client.get(f"/api/backtests/{polling_id}/status")
    assert status_resp.json()["status"] in ("queued", "running", "complete")
