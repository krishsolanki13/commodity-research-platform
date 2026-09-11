"""Provenance (git_sha, dirty_flag, package_versions) on non-single-asset artifacts.

Single-asset backtests already persist these via BacktestMetadata / params.json.
These tests cover the four newly-wired write paths: sweep, validation,
regime-attribution (per-asset + portfolio), and portfolio summary.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _assert_provenance(data: dict) -> None:
    """git_sha, dirty_flag, package_versions present and non-null."""
    assert "git_sha" in data
    assert data["git_sha"] is not None
    assert isinstance(data["git_sha"], str)
    assert data["git_sha"] != ""
    assert "dirty_flag" in data
    assert isinstance(data["dirty_flag"], bool)
    assert data["dirty_flag"] is not None
    pv = data.get("package_versions")
    assert pv is not None
    assert isinstance(pv, dict)
    assert len(pv) > 0


def test_capture_schema_matches_single_asset_contract() -> None:
    """Shared capture() returns the same three fields as params.json."""
    from src.core.provenance import capture

    snap = capture()
    assert set(snap.keys()) == {"git_sha", "dirty_flag", "package_versions"}
    assert isinstance(snap["git_sha"], str)
    assert isinstance(snap["dirty_flag"], bool)
    assert isinstance(snap["package_versions"], dict)
    assert "pandas" in snap["package_versions"]


def test_sweep_result_json_includes_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_save_sweep_result writes git_sha/dirty_flag/package_versions once per sweep."""
    import api.routers.sweeps as sweeps
    from src.core.provenance import capture
    from src.core.types import SweepResult

    monkeypatch.setattr(sweeps, "_SWEEPS_DIR", tmp_path)
    prov = capture()
    result = SweepResult(
        sweep_id="provenance_test_sweep",
        asset="gold",
        strategy_name="ema_crossover",
        param_grid={"fast_period": [20, 50], "slow_period": [200]},
        n_combinations=2,
        n_complete=2,
        n_failed=0,
        computation_date=datetime.date.today(),
        runs=[],
        git_sha=prov["git_sha"],
        dirty_flag=prov["dirty_flag"],
        package_versions=prov["package_versions"],
    )
    sweeps._save_sweep_result("provenance_test_sweep", result)

    data = json.loads(
        (tmp_path / "provenance_test_sweep" / "sweep_result.json").read_text(
            encoding="utf-8"
        )
    )
    _assert_provenance(data)
    assert data["git_sha"] == prov["git_sha"]
    assert data["dirty_flag"] == prov["dirty_flag"]
    assert data["package_versions"] == prov["package_versions"]


def test_sweep_runner_attaches_provenance_once_per_sweep() -> None:
    """SweepRunner.run_sweep() stamps provenance on the SweepResult object."""
    from src.backtesting.sweep_runner import SweepRunner
    from src.core.types import SweepRunSummary

    dummy = SweepRunSummary(
        sweep_id="s",
        run_id="r",
        parameters={},
        status="complete",
    )
    runner = SweepRunner(MagicMock())
    with (
        patch("src.data.loader.DataLoader") as loader_cls,
        patch.object(runner, "_run_single", return_value=dummy),
    ):
        loader_cls.return_value.load.return_value = pd.DataFrame()
        result = runner.run_sweep(
            asset="gold",
            strategy_name="ema_crossover",
            param_grid={"fast_period": [20, 50], "slow_period": [200]},
            sweep_id="provenance_test_sweep",
        )

    _assert_provenance(
        {
            "git_sha": result.git_sha,
            "dirty_flag": result.dirty_flag,
            "package_versions": result.package_versions,
        }
    )


def test_validation_report_json_includes_provenance(tmp_path: Path) -> None:
    """_save_validation_report writes git_sha/dirty_flag/package_versions."""
    from api.routers.validation import _save_validation_report
    from src.core.provenance import capture
    from src.core.types import ValidationReport

    prov = capture()
    report = ValidationReport(
        validation_run_id="20240101_120000_validation_gold_ema_crossover",
        asset="gold",
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
        n_splits=2,
        embargo_bars=5,
        computation_date=datetime.date.today(),
        folds=[],
        insample_sharpe=0.42,
        outsample_sharpe=0.18,
        insample_return=0.15,
        outsample_return=0.05,
        overfitting_ratio=0.43,
        sharpe_se=0.1,
        psr=0.8,
        n_trials=10,
        sr_benchmark=0.5,
        dsr=0.6,
        is_significant=False,
        dsr_threshold=0.95,
        git_sha=prov["git_sha"],
        dirty_flag=prov["dirty_flag"],
        package_versions=prov["package_versions"],
    )
    _save_validation_report(report, tmp_path)

    data = json.loads((tmp_path / "validation_report.json").read_text(encoding="utf-8"))
    _assert_provenance(data)
    assert data["git_sha"] == prov["git_sha"]
    assert data["package_versions"] == prov["package_versions"]


def test_regime_attribution_result_json_includes_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per-asset _save_regime_result writes provenance onto result.json."""
    import api.routers.regime_attribution as ra
    from src.analytics.regime_attribution import RegimeAttributionEngine

    monkeypatch.setattr(ra, "_REGIME_DIR", tmp_path)

    mock_result = MagicMock()
    mock_result.run_id = "test_run"
    mock_result.strategy_name = "ema_crossover"
    n = 100
    dates = pd.bdate_range("2024-01-02", periods=n, freq="B", tz="UTC")
    mock_result.pnl_series = pd.Series([100.0] * n, index=dates, name="pnl")

    engine = RegimeAttributionEngine(config=MagicMock())
    with patch(
        "src.commodity.curve.FuturesCurveBuilder.available_assets",
        return_value=["gold"],
    ):
        report = engine.compute(
            backtest_result=mock_result,
            asset="silver",
            n_contracts=4,
        )

    _assert_provenance(
        {
            "git_sha": report.git_sha,
            "dirty_flag": report.dirty_flag,
            "package_versions": report.package_versions,
        }
    )

    ra._save_regime_result("prov_regime_job", report)
    data = json.loads(
        (tmp_path / "prov_regime_job" / "result.json").read_text(encoding="utf-8")
    )
    _assert_provenance(data)


def test_portfolio_regime_result_json_includes_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_save_portfolio_regime_result writes provenance onto result.json."""
    import api.routers.regime_attribution as ra
    from src.core.provenance import capture
    from src.core.types import PortfolioRegimeAttributionReport

    monkeypatch.setattr(ra, "_REGIME_DIR", tmp_path)
    prov = capture()
    report = PortfolioRegimeAttributionReport(
        portfolio_run_id="20240101_000000_portfolio_ema_crossover",
        n_assets_computed=0,
        git_sha=prov["git_sha"],
        dirty_flag=prov["dirty_flag"],
        package_versions=prov["package_versions"],
    )
    ra._save_portfolio_regime_result("prov_port_regime_job", report)

    data = json.loads(
        (tmp_path / "prov_port_regime_job" / "result.json").read_text(encoding="utf-8")
    )
    _assert_provenance(data)
    assert data["git_sha"] == prov["git_sha"]
    assert data["package_versions"] == prov["package_versions"]


def test_portfolio_summary_json_includes_provenance(tmp_path: Path) -> None:
    """save_portfolio_summary writes provenance; risk/corr files do not duplicate it."""
    from src.core.types import PortfolioPerformanceReport
    from src.performance.portfolio import save_portfolio_summary

    report = PortfolioPerformanceReport(
        strategy_name="ema_crossover",
        run_id="20260101_000000_portfolio_ema_crossover",
        assets=["gold", "silver"],
        skipped_assets=[],
        initial_capital_per_asset=1_000_000.0,
        initial_capital_total=2_000_000.0,
        portfolio_date_range=(datetime.date(2023, 1, 2), datetime.date(2024, 12, 31)),
        portfolio_metrics={"sharpe": 0.3},
        asset_contributions={"gold": 0.3, "silver": 0.7},
        absolute_pnl_by_asset={"gold": 6000.0, "silver": 4000.0},
        per_asset_reports={},
    )
    out_path = save_portfolio_summary(report, tmp_path / report.run_id)
    data = json.loads(out_path.read_text(encoding="utf-8"))
    _assert_provenance(data)
    assert not (out_path.parent / "portfolio_risk.json").exists()
    assert not (out_path.parent / "portfolio_correlation.json").exists()
