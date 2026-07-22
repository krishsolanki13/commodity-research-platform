from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient


def _make_mock_port_report(total_pnl: float = 74_759.0):
    """Minimal mock PortfolioPerformanceReport."""
    report = MagicMock()
    report.strategy_name = "ema_crossover"
    report.assets = ["gold", "silver", "copper", "wti", "brent", "natural_gas"]
    report.skipped_assets = []
    report.initial_capital_per_asset = 1_000_000.0
    report.initial_capital_total = 6_000_000.0
    report.portfolio_date_range = ("2020-01-01", "2024-01-01")
    report.portfolio_metrics = {
        "total_return": total_pnl / 6_000_000.0,
        "cagr": 0.003,
        "sharpe": 0.12,
        "sortino": 0.15,
        "calmar": 0.05,
        "max_drawdown": -0.07,
        "portfolio_vol": 0.025,
        "n_trading_days": 1000.0,
    }
    report.absolute_pnl_by_asset = {a: total_pnl / 6 for a in report.assets}
    report.asset_contributions = {a: 1 / 6 for a in report.assets}
    report.per_asset_reports = {}
    return report


def _make_mock_corr_report():
    """Mock CorrelationReport with upper-triangle rolling only (TD-M17-A)."""
    report = MagicMock()
    assets = ["brent", "copper", "gold", "natural_gas", "silver", "wti"]
    report.correlation_matrix = {a: {b: 0.5 for b in assets} for a in assets}
    idx = pd.date_range("2021-01-01", periods=100, freq="D", tz="UTC")
    report.rolling_correlations_63 = {
        "gold": {"silver": pd.Series(0.65, index=idx)},
        "wti": {"brent": pd.Series(0.62, index=idx)},
    }
    report.rolling_correlations_126 = {
        "gold": {"silver": pd.Series(0.63, index=idx)},
    }
    report.realized_vol_by_asset = {a: 0.05 for a in assets}
    report.portfolio_realized_vol = 0.025
    report.avg_pairwise_correlation = 0.12
    report.most_correlated_pair = ("gold", "silver", 0.65)
    report.least_correlated_pair = ("natural_gas", "copper", -0.05)
    return report


def _make_mock_risk_report():
    report = MagicMock()
    report.portfolio_var_95 = 31_948.0
    report.portfolio_var_99 = 44_490.0
    report.portfolio_var_95_pct = 0.0053
    report.portfolio_var_99_pct = 0.0074
    report.portfolio_es_95 = 55_000.0
    report.portfolio_es_99 = 99_095.0
    report.asset_var_95 = {
        a: 8_000.0 for a in ["gold", "silver", "copper", "wti", "brent", "natural_gas"]
    }
    report.asset_var_99 = {
        a: 11_000.0 for a in ["gold", "silver", "copper", "wti", "brent", "natural_gas"]
    }
    report.avg_gross_notional_by_asset = {
        a: 100_000.0
        for a in ["gold", "silver", "copper", "wti", "brent", "natural_gas"]
    }
    report.avg_net_notional_by_asset = {
        a: 50_000.0 for a in ["gold", "silver", "copper", "wti", "brent", "natural_gas"]
    }
    report.total_avg_gross_notional = 600_000.0
    report.total_avg_net_notional = 300_000.0
    report.portfolio_diversification_benefit = 2.23
    return report


def _inject_complete_task(
    polling_id: str,
    port_report=None,
    corr_report=None,
    risk_report=None,
    multi_result=None,
) -> None:
    """Directly inject a complete task into state for testing detail endpoints."""
    import api.state as _s

    _s.register(polling_id)
    with _s._lock:
        _s._store[polling_id]["status"] = "complete"
        _s._store[polling_id]["executed_at"] = "2024-01-01T12:00:00Z"
        if port_report is not None:
            _s._store[polling_id]["port_report"] = port_report
        if corr_report is not None:
            _s._store[polling_id]["corr_report"] = corr_report
        if risk_report is not None:
            _s._store[polling_id]["risk_report"] = risk_report
        if multi_result is not None:
            _s._store[polling_id]["multi_result"] = multi_result


def test_launch_portfolio_returns_202(client: TestClient) -> None:
    """POST /api/portfolio/run returns 202 with portfolio-format run_id."""
    with patch("api.routers.portfolio._run_portfolio_task"):
        response = client.post(
            "/api/portfolio/run",
            json={
                "strategy": "ema_crossover",
                "params": {"fast_period": 50, "slow_period": 200},
            },
        )
    assert response.status_code == 202
    data = response.json()
    assert "portfolio" in data["run_id"]
    assert data["status"] == "queued"


def test_portfolio_summary_contributions_null_when_small_pnl(
    client: TestClient,
) -> None:
    """asset_contributions must be None when |total_pnl/capital| < 1%."""
    port_report = _make_mock_port_report(total_pnl=5_000.0)
    polling_id = "test_contrib_null_001"
    _inject_complete_task(polling_id, port_report=port_report)

    response = client.get(f"/api/portfolio/{polling_id}/summary")
    assert response.status_code == 200
    assert response.json()["asset_contributions"] is None


def test_correlation_rolling_symmetrized(client: TestClient) -> None:
    """rolling_correlations_63 must contain both [gold][silver] and [silver][gold]."""
    corr_report = _make_mock_corr_report()
    polling_id = "test_corr_symm_001"
    _inject_complete_task(polling_id, corr_report=corr_report)

    response = client.get(f"/api/portfolio/{polling_id}/correlation")
    assert response.status_code == 200
    data = response.json()
    rc63 = data["rolling_correlations_63"]
    assert "gold" in rc63.get("silver", {}), "silver→gold symmetrization missing"
    assert "framing_note" in data
    assert len(data["framing_note"]) > 10


def test_risk_var_is_positive(client: TestClient) -> None:
    """VaR values must be positive loss magnitudes, not negative."""
    risk_report = _make_mock_risk_report()
    polling_id = "test_risk_var_001"
    _inject_complete_task(polling_id, risk_report=risk_report)

    response = client.get(f"/api/portfolio/{polling_id}/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["portfolio_var_99"] is not None
    assert (
        data["portfolio_var_99"] > 0
    ), f"VaR must be positive, got {data['portfolio_var_99']}"
    assert data["methodology"] == "historical_simulation"


def test_portfolio_assets_returns_200_with_asset_metrics(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/portfolio/{run_id}/assets → 200 with asset_metrics dict."""
    run_id = "20260101_000000_portfolio_ema_crossover"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    summary = {
        "run_id": run_id,
        "strategy_name": "ema_crossover",
        "assets": ["gold", "silver"],
        "skipped_assets": [],
        "initial_capital_per_asset": 1_000_000.0,
        "initial_capital_total": 2_000_000.0,
        "portfolio_date_range": ["2020-01-01", "2026-07-01"],
        "portfolio_metrics": {"sharpe": 0.42, "max_drawdown": -0.05},
        "asset_contributions": {"gold": 0.6, "silver": 0.4},
        "absolute_pnl_by_asset": {"gold": 12000.0, "silver": 8000.0},
        "per_asset_metrics": {
            "gold": {
                "sharpe": 0.55,
                "max_drawdown": -0.04,
                "total_return": 0.012,
            },
            "silver": {
                "sharpe": 0.31,
                "max_drawdown": -0.06,
                "total_return": 0.008,
            },
        },
    }
    (run_dir / "portfolio_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )

    import api.routers.portfolio as portfolio_router

    monkeypatch.setattr(portfolio_router, "RUNS_DIR", tmp_path)
    response = client.get(f"/api/portfolio/{run_id}/assets")

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert set(data["assets"]) == {"gold", "silver"}
    assert "asset_metrics" in data
    assert "gold" in data["asset_metrics"]
    assert data["asset_metrics"]["gold"]["sharpe"] == pytest.approx(0.55)


def test_portfolio_assets_pre_fix_run_returns_404_with_rerun_message(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/portfolio/{run_id}/assets → 404 when per_asset_metrics absent."""
    run_id = "20200101_000000_portfolio_ema_crossover"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    summary = {
        "run_id": run_id,
        "strategy_name": "ema_crossover",
        "assets": ["gold"],
        "portfolio_metrics": {"sharpe": 0.1},
        "asset_contributions": {"gold": 1.0},
        "absolute_pnl_by_asset": {"gold": 5000.0},
    }
    (run_dir / "portfolio_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )

    import api.routers.portfolio as portfolio_router

    monkeypatch.setattr(portfolio_router, "RUNS_DIR", tmp_path)
    response = client.get(f"/api/portfolio/{run_id}/assets")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "RUN_NOT_FOUND"
    assert "Re-run" in detail["message"] or "re-run" in detail["message"].lower()


def test_portfolio_assets_returns_asset_run_ids(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/portfolio/{run_id}/assets → asset_run_ids present and
    values match expected run_id format YYYYMMDD_HHMMSS_{strategy}_{asset}."""
    import re

    run_id = "20260722_120000_portfolio_ema_crossover"
    gold_run_id = "20260722_120000_ema_crossover_gold"
    silver_run_id = "20260722_120001_ema_crossover_silver"

    summary = {
        "run_id": run_id,
        "strategy_name": "ema_crossover",
        "assets": ["gold", "silver"],
        "skipped_assets": [],
        "initial_capital_per_asset": 1_000_000.0,
        "initial_capital_total": 2_000_000.0,
        "portfolio_date_range": ["2020-01-01", "2026-07-01"],
        "portfolio_metrics": {"sharpe": 0.42},
        "asset_contributions": {"gold": 0.6, "silver": 0.4},
        "absolute_pnl_by_asset": {"gold": 12000.0, "silver": 8000.0},
        "per_asset_metrics": {
            "gold": {"sharpe": 0.55, "max_drawdown": -0.04},
            "silver": {"sharpe": 0.31, "max_drawdown": -0.06},
        },
        "asset_run_ids": {
            "gold": gold_run_id,
            "silver": silver_run_id,
        },
    }

    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "portfolio_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )

    import api.routers.portfolio as portfolio_router

    monkeypatch.setattr(portfolio_router, "RUNS_DIR", tmp_path)
    response = client.get(f"/api/portfolio/{run_id}/assets")

    assert response.status_code == 200
    data = response.json()
    assert "asset_run_ids" in data, "asset_run_ids missing from /assets response"
    assert data["asset_run_ids"].get("gold") == gold_run_id
    assert data["asset_run_ids"].get("silver") == silver_run_id

    # Run IDs must match expected format
    run_id_pattern = re.compile(r"^\d{8}_\d{6}_\w+_\w+$")
    for asset, rid in data["asset_run_ids"].items():
        if rid is not None:
            assert run_id_pattern.match(rid), (
                f"asset_run_ids[{asset}] = '{rid}' does not match "
                f"YYYYMMDD_HHMMSS_strategy_asset format"
            )


def test_portfolio_assets_pre_fix_run_returns_empty_asset_run_ids(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/portfolio/{run_id}/assets with a pre-fix portfolio_summary.json
    that lacks asset_run_ids returns 200 with asset_run_ids == {} not a 404."""
    run_id = "20200101_000000_portfolio_ema_crossover"

    # Pre-fix summary: has per_asset_metrics but no asset_run_ids
    summary = {
        "run_id": run_id,
        "strategy_name": "ema_crossover",
        "assets": ["gold"],
        "skipped_assets": [],
        "initial_capital_total": 1_000_000.0,
        "portfolio_metrics": {"sharpe": 0.1},
        "asset_contributions": {"gold": 1.0},
        "absolute_pnl_by_asset": {"gold": 5000.0},
        "per_asset_metrics": {"gold": {"sharpe": 0.15}},
        # asset_run_ids deliberately absent (pre-fix run)
    }

    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "portfolio_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )

    import api.routers.portfolio as portfolio_router

    monkeypatch.setattr(portfolio_router, "RUNS_DIR", tmp_path)
    response = client.get(f"/api/portfolio/{run_id}/assets")

    assert response.status_code == 200, (
        f"Pre-fix run must return 200, not 404. Got {response.status_code}: "
        f"{response.json()}"
    )
    data = response.json()
    # asset_run_ids absent in JSON → default {} in response (graceful)
    asset_run_ids = data.get("asset_run_ids", {})
    assert (
        asset_run_ids == {} or asset_run_ids is None
    ), f"Pre-fix run should return empty asset_run_ids, got: {asset_run_ids}"


def test_summary_resolves_poll_prefix(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/portfolio/poll_{id}/summary → 200 (poll_ prefix stripped)."""
    run_id = "20260722_110000_portfolio_ema_crossover"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    summary = {
        "run_id": run_id,
        "strategy_name": "ema_crossover",
        "assets": ["gold"],
        "skipped_assets": [],
        "initial_capital_per_asset": 1_000_000.0,
        "initial_capital_total": 1_000_000.0,
        "portfolio_date_range": ["2020-01-01", "2026-07-01"],
        "portfolio_metrics": {
            "sharpe": 0.42,
            "max_drawdown": -0.05,
            "total_return": 0.02,
            "cagr": 0.001,
            "portfolio_vol": 0.025,
            "n_trading_days": 1500,
        },
        "asset_contributions": {"gold": 1.0},
        "absolute_pnl_by_asset": {"gold": 20000.0},
        "per_asset_metrics": {"gold": {"sharpe": 0.42}},
        "asset_run_ids": {"gold": "20260722_110000_ema_crossover_gold"},
    }
    (run_dir / "portfolio_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    import api.routers.portfolio as pr

    monkeypatch.setattr(pr, "RUNS_DIR", tmp_path)
    r = client.get(f"/api/portfolio/poll_{run_id}/summary")
    assert (
        r.status_code == 200
    ), f"poll_ prefix not resolved for /summary: {r.status_code} {r.json()}"


def test_equity_resolves_poll_prefix(client: TestClient) -> None:
    """GET /api/portfolio/poll_{id}/equity → 200 (poll_ prefix resolved via state).

    Equity is served from in-memory multi_result (not disk). Resolution is via
    _get_task_or_404 trying poll_ and bare artifact ids.
    """
    run_id = "20260722_110001_portfolio_ema_crossover"
    poll_id = f"poll_{run_id}"
    idx = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    multi = MagicMock()
    multi.portfolio_equity_curve = pd.Series(
        [1_000_000.0, 1_000_100.0, 1_000_200.0, 1_000_150.0, 1_000_300.0],
        index=idx,
    )
    multi.portfolio_pnl_series = pd.Series([0.0, 100.0, 100.0, -50.0, 150.0], index=idx)
    _inject_complete_task(poll_id, multi_result=multi)
    # Also register bare→poll artifact map like a real completed launch
    import api.state as _s

    _s.set_artifact_id(poll_id, run_id)

    r = client.get(f"/api/portfolio/{poll_id}/equity")
    assert (
        r.status_code == 200
    ), f"poll_ prefix not resolved for /equity: {r.status_code} {r.json()}"


def test_risk_resolves_poll_prefix(client: TestClient) -> None:
    """GET /api/portfolio/poll_{id}/risk → 200 (poll_ prefix resolved via state)."""
    run_id = "20260722_110002_portfolio_ema_crossover"
    poll_id = f"poll_{run_id}"
    _inject_complete_task(poll_id, risk_report=_make_mock_risk_report())
    import api.state as _s

    _s.set_artifact_id(poll_id, run_id)

    r = client.get(f"/api/portfolio/{poll_id}/risk")
    assert (
        r.status_code == 200
    ), f"poll_ prefix not resolved for /risk: {r.status_code} {r.json()}"


def test_correlation_resolves_poll_prefix(client: TestClient) -> None:
    """GET /api/portfolio/poll_{id}/correlation → 200 (poll_ prefix resolved)."""
    run_id = "20260722_110003_portfolio_ema_crossover"
    poll_id = f"poll_{run_id}"
    _inject_complete_task(poll_id, corr_report=_make_mock_corr_report())
    import api.state as _s

    _s.set_artifact_id(poll_id, run_id)

    r = client.get(f"/api/portfolio/{poll_id}/correlation")
    assert (
        r.status_code == 200
    ), f"poll_ prefix not resolved for /correlation: {r.status_code} {r.json()}"


def test_assets_still_resolves_poll_prefix_regression(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/portfolio/poll_{id}/assets → 200 (regression: 141f6e8 intact)."""
    run_id = "20260722_110004_portfolio_ema_crossover"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    summary = {
        "run_id": run_id,
        "strategy_name": "ema_crossover",
        "assets": ["gold"],
        "skipped_assets": [],
        "initial_capital_total": 1_000_000.0,
        "portfolio_metrics": {"sharpe": 0.10},
        "asset_contributions": {"gold": 1.0},
        "absolute_pnl_by_asset": {"gold": 3000.0},
        "per_asset_metrics": {"gold": {"sharpe": 0.10, "max_drawdown": -0.02}},
        "asset_run_ids": {"gold": "20260722_110004_ema_crossover_gold"},
    }
    (run_dir / "portfolio_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    import api.routers.portfolio as pr

    monkeypatch.setattr(pr, "RUNS_DIR", tmp_path)
    r = client.get(f"/api/portfolio/poll_{run_id}/assets")
    assert (
        r.status_code == 200
    ), f"Regression — 141f6e8 fix broken: {r.status_code} {r.json()}"
    assert "asset_metrics" in r.json()


def test_portfolio_runs_returns_200_with_list(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/portfolio/runs → 200 with runs list from disk."""
    run_id = "20260722_120000_portfolio_ema_crossover"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    summary = {
        "run_id": run_id,
        "strategy_name": "ema_crossover",
        "assets": ["gold", "silver"],
        "skipped_assets": [],
        "initial_capital_total": 2_000_000.0,
        "portfolio_date_range": ["2020-01-01", "2026-07-01"],
        "portfolio_metrics": {
            "sharpe": 0.42,
            "max_drawdown": -0.05,
            "total_return": 0.02,
            "cagr": 0.001,
            "portfolio_vol": 0.025,
            "n_trading_days": 1500,
        },
        "asset_contributions": {"gold": 0.6, "silver": 0.4},
        "absolute_pnl_by_asset": {"gold": 12000.0, "silver": 8000.0},
        "per_asset_metrics": {"gold": {"sharpe": 0.55}},
        "asset_run_ids": {},
    }
    (run_dir / "portfolio_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )

    import api.routers.portfolio as pr

    monkeypatch.setattr(pr, "RUNS_DIR", tmp_path)

    response = client.get("/api/portfolio/runs")
    assert (
        response.status_code == 200
    ), f"GET /api/portfolio/runs → {response.status_code}: {response.json()}"
    data = response.json()
    assert "runs" in data, "Response must have 'runs' key"
    assert "total" in data, "Response must have 'total' key"
    assert isinstance(data["runs"], list)
    assert data["total"] >= 1

    run_item = next((r for r in data["runs"] if r["run_id"] == run_id), None)
    assert run_item is not None, f"Expected run_id {run_id} in response"
    assert run_item["strategy_name"] == "ema_crossover"
    assert "gold" in run_item["assets"]
    assert run_item["sharpe"] == pytest.approx(0.42)


def test_portfolio_runs_returns_empty_list_when_no_runs(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/portfolio/runs → 200 with empty list when no runs on disk."""
    import api.routers.portfolio as pr

    monkeypatch.setattr(pr, "RUNS_DIR", tmp_path)

    response = client.get("/api/portfolio/runs")
    assert response.status_code == 200
    data = response.json()
    assert data["runs"] == []
    assert data["total"] == 0
