from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient


def _write_fake_run(base_dir: Path, run_id: str, n_trades: int = 5) -> Path:
    """Write a minimal run artifact directory for testing."""
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True)

    params = {
        "asset": "gold",
        "strategy_name": "ema_crossover",
        "data_start": "2020-01-01",
        "data_end": "2024-01-01",
        "executed_at": "2024-01-01T12:00:00Z",
        "git_sha": "abcd1234ef567890",
        "dirty_flag": False,
        "package_versions": {"pandas": "2.3.3"},
    }
    (run_dir / "params.json").write_text(json.dumps(params))

    metrics = {
        "scalar_metrics": {
            "sharpe": 0.5,
            "max_drawdown": -0.03,
            "total_return": 0.01,
            "cagr": 0.008,
            "win_rate": 0.55,
            "avg_trade_duration_bars": 12.5,
            "avg_win": 500.0,
            "avg_loss": -300.0,
            "largest_win": 2000.0,
            "largest_loss": -1500.0,
        },
        "trade_statistics": {"n_trades": float(n_trades)},
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics))

    idx = pd.date_range("2020-01-01", periods=100, freq="D", tz="UTC")
    ec = pd.DataFrame({"equity": 1_000_000.0 + np.arange(100) * 100.0}, index=idx)
    ec.to_parquet(run_dir / "equity_curve.parquet")

    pnl = pd.DataFrame({"pnl": 100.0 * np.ones(100)}, index=idx)
    pnl.to_parquet(run_dir / "pnl_series.parquet")

    pos = pd.DataFrame({"position": 100_000.0 * np.ones(100)}, index=idx)
    pos.to_parquet(run_dir / "positions.parquet")

    trades_data = {
        "direction": ["long"] * n_trades,
        "entry_date": ["2020-01-10"] * n_trades,
        "exit_date": ["2020-02-10"] * n_trades,
        "entry_price": [1800.0] * n_trades,
        "exit_price": [1850.0] * n_trades,
        "duration_bars": [31] * n_trades,
        "gross_pnl": [5000.0] * n_trades,
        "transaction_cost": [10.0] * n_trades,
        "net_pnl": [4990.0] * n_trades,
        "return_pct": [0.027] * n_trades,
        "force_closed": [False] * n_trades,
    }
    pd.DataFrame(trades_data).to_parquet(run_dir / "trades.parquet")

    return run_dir


def _patch_runs_dir(tmp: Path):
    """Context manager patch that redirects _runs_dir() to tmp."""
    return patch("api.routers.runs._runs_dir", return_value=tmp)


def test_list_runs_empty(client: TestClient) -> None:
    with tempfile.TemporaryDirectory() as tmp, _patch_runs_dir(Path(tmp)):
        response = client.get("/api/runs")
    assert response.status_code == 200
    assert response.json()["runs"] == []
    assert response.json()["total"] == 0


def test_list_runs_happy_path(client: TestClient) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_fake_run(base, "20240101_120000_ema_crossover_gold")
        _write_fake_run(base, "20240102_120000_ema_crossover_silver")
        with _patch_runs_dir(base):
            response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all("run_id" in r for r in data["runs"])
    assert all("sharpe" in r for r in data["runs"])


def test_get_run_detail_happy_path(client: TestClient) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        run_id = "20240101_120000_ema_crossover_gold"
        _write_fake_run(base, run_id)
        with _patch_runs_dir(base):
            response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["provenance"]["git_sha"] == "abcd1234"
    assert "pandas" in data["provenance"]["package_versions"]
    assert data["asset"] == "gold"
    assert data["signal_evaluation"] is None


def test_get_run_detail_returns_persisted_signal_evaluation(
    client: TestClient,
) -> None:
    """signal_evaluation written into params.json is returned by run detail."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        run_id = "20240101_120000_ema_crossover_gold"
        run_dir = _write_fake_run(base, run_id)
        params = json.loads((run_dir / "params.json").read_text())
        params["signal_evaluation"] = {
            "ic": 0.143,
            "icir": 3.815,
            "turnover": 0.04,
            "decay": [
                {"horizon": 1, "ic": 0.143},
                {"horizon": 5, "ic": 0.089},
                {"horizon": 20, "ic": 0.031},
            ],
            "evaluation_window": 63,
            "computed_at": "2024-01-01T12:00:00.000Z",
            "ic_band": "strong",
        }
        (run_dir / "params.json").write_text(json.dumps(params))
        with _patch_runs_dir(base):
            response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    se = response.json()["signal_evaluation"]
    assert se is not None
    assert se["ic"] == pytest.approx(0.143)
    assert se["ic_band"] == "strong"
    assert se["decay"][0]["horizon"] == 1


def test_get_run_series_equity_curve(client: TestClient) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        run_id = "20240101_120000_ema_crossover_gold"
        _write_fake_run(base, run_id)
        with _patch_runs_dir(base):
            response = client.get(f"/api/runs/{run_id}/series/equity_curve")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["index"]) == 100
    assert data["data"]["index"][0] > 1_000_000_000_000


def test_get_run_trades_pagination(client: TestClient) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        run_id = "20240101_120000_ema_crossover_gold"
        _write_fake_run(base, run_id, n_trades=150)
        with _patch_runs_dir(base):
            resp1 = client.get(f"/api/runs/{run_id}/trades?page=1&page_size=100")
            resp2 = client.get(f"/api/runs/{run_id}/trades?page=2&page_size=100")
    assert resp1.status_code == 200
    assert len(resp1.json()["trades"]) == 100
    assert resp2.status_code == 200
    assert len(resp2.json()["trades"]) == 50
    assert resp1.json()["total"] == 150


def test_compare_runs_aligned_series(client: TestClient) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        id1 = "20240101_120000_ema_crossover_gold"
        id2 = "20240102_120000_ema_crossover_gold"
        _write_fake_run(base, id1)
        _write_fake_run(base, id2)
        with _patch_runs_dir(base):
            response = client.post("/api/runs/compare", json={"ids": [id1, id2]})
    assert response.status_code == 200
    data = response.json()
    assert len(data["runs"]) == 2
    assert data["intersection_bars"] is not None
    assert data["intersection_bars"] > 0


def test_delete_run_calls_run_manager(client: TestClient) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        run_id = "20240101_120000_ema_crossover_gold"
        _write_fake_run(base, run_id)
        with (
            _patch_runs_dir(base),
            patch("src.backtesting.run_manager.RunManager") as mock_rm,
        ):
            mock_rm.return_value.delete_run = MagicMock()
            response = client.delete(f"/api/runs/{run_id}")
            mock_rm.return_value.delete_run.assert_called_once_with(run_id)
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_trades_direction_serialized_as_string(client: TestClient) -> None:
    """Trade direction values must be 'long'/'short' strings, not int 1/-1.

    Root cause of bug: parquet stores direction as int64; filter compared
    against strings → 0 results. Fix: normalize at serialization time.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        run_id = "20240101_120000_ema_crossover_gold"
        run_dir = _write_fake_run(base, run_id, n_trades=4)
        # Production parquet stores direction as int64 (1/-1), not strings.
        trades_df = pd.read_parquet(run_dir / "trades.parquet")
        trades_df["direction"] = [1, -1, 1, -1]
        trades_df.to_parquet(run_dir / "trades.parquet")

        with _patch_runs_dir(base):
            response = client.get(f"/api/runs/{run_id}/trades")
            assert response.status_code == 200
            data = response.json()
            trades = data.get("trades", data) if isinstance(data, dict) else data
            assert trades

            for trade in trades:
                d = trade.get("direction")
                if d is not None:
                    assert isinstance(d, str), (
                        f"Trade direction must be string, got {type(d).__name__}: {d!r}. "
                        "Parquet stores int64 (1/-1); normalize to long/short at serialization."
                    )
                    assert d in (
                        "long",
                        "short",
                        "flat",
                    ), f"Trade direction must be long/short/flat, got: {d!r}"

            r_long = client.get(f"/api/runs/{run_id}/trades?direction=long")
            assert r_long.status_code == 200
            long_trades = r_long.json()["trades"]
            assert len(long_trades) == 2
            assert all(t["direction"] == "long" for t in long_trades)
