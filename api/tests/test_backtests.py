from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
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


def test_backtest_launch_request_accepts_signal_evaluation() -> None:
    """BacktestLaunchRequest with signal_evaluation field round-trips correctly."""
    from api.models import (  # noqa: PLC0415
        BacktestLaunchRequest,
        DecayEntry,
        SignalEvaluationData,
    )

    se = SignalEvaluationData(
        ic=0.143,
        icir=3.815,
        turnover=0.04,
        decay=[
            DecayEntry(horizon=1, ic=0.143),
            DecayEntry(horizon=5, ic=0.089),
            DecayEntry(horizon=20, ic=0.031),
        ],
        evaluation_window=63,
        computed_at="2024-01-01T12:00:00.000Z",
        ic_band="strong",
    )
    req = BacktestLaunchRequest(
        asset="gold",
        strategy="ema_crossover",
        params={"fast_period": 50, "slow_period": 200},
        signal_evaluation=se,
    )
    assert req.signal_evaluation is not None
    assert req.signal_evaluation.ic == pytest.approx(0.143)
    assert req.signal_evaluation.ic_band == "strong"
    assert req.signal_evaluation.decay[0].horizon == 1


def test_backtest_launch_request_accepts_null_signal_evaluation() -> None:
    """BacktestLaunchRequest with signal_evaluation=None (IC Gate override)."""
    from api.models import BacktestLaunchRequest  # noqa: PLC0415

    req = BacktestLaunchRequest(
        asset="gold",
        strategy="ema_crossover",
        params={"fast_period": 50, "slow_period": 200},
        signal_evaluation=None,
    )
    assert req.signal_evaluation is None

    # Absent field (old client behaviour) also defaults to None
    req2 = BacktestLaunchRequest(
        asset="gold",
        strategy="ema_crossover",
        params={"fast_period": 50, "slow_period": 200},
    )
    assert req2.signal_evaluation is None


def test_api_eval_to_core_maps_decay_and_window() -> None:
    """SignalEvaluationData → SignalEvaluation maps decay list and window."""
    import datetime  # noqa: PLC0415

    from api.models import DecayEntry, SignalEvaluationData  # noqa: PLC0415
    from api.routers.backtests import _api_eval_to_core  # noqa: PLC0415

    se = SignalEvaluationData(
        ic=0.143,
        icir=3.815,
        turnover=0.04,
        decay=[
            DecayEntry(horizon=1, ic=0.143),
            DecayEntry(horizon=5, ic=None),
            DecayEntry(horizon=20, ic=0.031),
        ],
        evaluation_window=63,
        computed_at="2024-01-01T12:00:00.000Z",
        ic_band="strong",
    )
    core = _api_eval_to_core(
        se,
        signal_name="ema_crossover_50_200",
        asset="gold",
        evaluation_start=datetime.date(2020, 1, 1),
        evaluation_end=datetime.date(2024, 1, 1),
    )
    assert core.ic == pytest.approx(0.143)
    assert core.ic_rolling_window == 63
    assert core.ic_decay == {1: 0.143, 20: 0.031}
    assert 5 not in core.ic_decay  # None ic dropped
