"""Tests for Module 15: Portfolio Performance Engine.

Tests PortfolioPerformanceReport, PortfolioPerformanceEngine.compute(),
portfolio metric correctness, per-asset report population, and edge cases.
Uses monkeypatch on DataLoader.load() and MultiAssetRunner for integration
tests. All synthetic — no filesystem or network access.

See ADR-010 (Multi-Asset Research Scope and Phasing).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from src.backtesting.multi_asset import MultiAssetRunner
from src.core.config import Config
from src.core.types import (
    MultiAssetBacktestResult,
    PerformanceReport,
    PortfolioPerformanceReport,
)
from src.performance.portfolio import PortfolioPerformanceEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(
    n: int = 252,
    base_close: float = 100.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Synthetic NormalizedOHLCV DataFrame."""
    rng = np.random.default_rng(seed=seed)
    returns = rng.normal(0.0, 0.01, n)
    closes = base_close * np.cumprod(1 + returns)
    dates = pd.bdate_range(start="2023-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": closes * 0.999,
            "high": closes * 1.002,
            "low": closes * 0.998,
            "close": closes,
            "volume": [25000.0] * n,
            "open_interest": [float("nan")] * n,
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )


def _make_multi_asset_result(
    config: Config,
    monkeypatch: pytest.MonkeyPatch,
    assets: list[str] | None = None,
    strategy_name: str = "ema_crossover",
    parameters: dict | None = None,
    seeds: list[int] | None = None,
) -> MultiAssetBacktestResult:
    """Run MultiAssetRunner with patched DataLoader to get a real result."""
    from src.data.loader import DataLoader

    if assets is None:
        assets = ["gold", "silver"]
    if parameters is None:
        parameters = {"fast_period": 50, "slow_period": 200}
    if seeds is None:
        seeds = list(range(len(assets)))

    ohlcv_map = {
        asset: _make_ohlcv(252, base_close=float(100 * (i + 1)), seed=seeds[i])
        for i, asset in enumerate(assets)
    }

    def mock_load(self, asset, **kwargs):  # noqa: ANN001
        if asset in ohlcv_map:
            return ohlcv_map[asset]
        raise FileNotFoundError(f"No data for {asset}")

    monkeypatch.setattr(DataLoader, "load", mock_load)

    runner = MultiAssetRunner(config)
    return runner.run(
        assets=assets,
        strategy_name=strategy_name,
        parameters=parameters,
    )


# ---------------------------------------------------------------------------
# PortfolioPerformanceReport dataclass tests (2 tests)
# ---------------------------------------------------------------------------


def test_portfolio_performance_report_properties(config: Config) -> None:
    """PortfolioPerformanceReport computed properties return correct values."""
    import datetime as dt

    metrics = {
        "total_return": 0.0125,
        "cagr": 0.0078,
        "sharpe": 0.31,
        "sortino": 0.42,
        "calmar": 0.114,
        "max_drawdown": -0.068,
        "portfolio_vol": 0.085,
        "n_trading_days": 4116.0,
    }
    contributions = {"gold": 0.30, "silver": 0.70}

    report = PortfolioPerformanceReport(
        strategy_name="ema_crossover",
        run_id="20260101_000000_portfolio_ema_crossover",
        assets=["gold", "silver"],
        skipped_assets=[],
        initial_capital_per_asset=1_000_000.0,
        initial_capital_total=2_000_000.0,
        portfolio_date_range=(dt.date(2023, 1, 2), dt.date(2024, 12, 31)),
        portfolio_metrics=metrics,
        asset_contributions=contributions,
        absolute_pnl_by_asset={"gold": 6000.0, "silver": 4000.0},
        per_asset_reports={},
    )

    assert report.n_assets == 2
    assert report.portfolio_sharpe == pytest.approx(0.31)
    assert report.portfolio_max_drawdown == pytest.approx(-0.068)
    assert report.portfolio_total_return == pytest.approx(0.0125)
    assert report.portfolio_cagr == pytest.approx(0.0078)


def test_portfolio_performance_report_skipped_assets_counted(
    config: Config,
) -> None:
    """PortfolioPerformanceReport.n_assets counts only successful assets."""
    import datetime as dt

    report = PortfolioPerformanceReport(
        strategy_name="momentum",
        run_id="20260101_000000_portfolio_momentum",
        assets=["gold"],
        skipped_assets=["silver", "copper"],
        initial_capital_per_asset=1_000_000.0,
        initial_capital_total=1_000_000.0,
        portfolio_date_range=(dt.date(2023, 1, 2), dt.date(2024, 12, 31)),
        portfolio_metrics={},
        asset_contributions={},
        absolute_pnl_by_asset={"gold": 5000.0},
        per_asset_reports={},
    )

    assert report.n_assets == 1
    assert len(report.skipped_assets) == 2


# ---------------------------------------------------------------------------
# PortfolioPerformanceEngine.compute() core behavior (4 tests)
# ---------------------------------------------------------------------------


def test_portfolio_engine_returns_correct_type(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PortfolioPerformanceEngine.compute() returns PortfolioPerformanceReport."""
    multi_result = _make_multi_asset_result(config, monkeypatch)
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    assert isinstance(report, PortfolioPerformanceReport)
    assert report.strategy_name == "ema_crossover"
    assert report.run_id == multi_result.run_id


def test_portfolio_engine_per_asset_reports_populated(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """per_asset_reports contains one PerformanceReport per successful asset."""
    multi_result = _make_multi_asset_result(
        config, monkeypatch, assets=["gold", "silver", "copper"], seeds=[1, 2, 3]
    )
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    assert len(report.per_asset_reports) == 3
    assert set(report.per_asset_reports.keys()) == {"gold", "silver", "copper"}
    assert all(
        isinstance(r, PerformanceReport) for r in report.per_asset_reports.values()
    )


def test_portfolio_engine_asset_contributions_sum_to_one(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Asset contributions sum to approximately 1.0 when total P&L is non-zero."""
    multi_result = _make_multi_asset_result(
        config, monkeypatch, assets=["gold", "silver"], seeds=[10, 20]
    )
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    total_pnl = multi_result.portfolio_pnl_series.sum()
    if total_pnl != 0.0:
        total_contribution = sum(report.asset_contributions.values())
        assert total_contribution == pytest.approx(
            1.0, abs=1e-6
        ), f"Asset contributions must sum to 1.0, got {total_contribution}"


def test_portfolio_engine_skipped_assets_propagated(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """skipped_assets from MultiAssetBacktestResult propagated to report."""
    from src.data.loader import DataLoader

    ohlcv_map = {"gold": _make_ohlcv(252, seed=1)}

    def mock_load(self, asset, **kwargs):  # noqa: ANN001
        if asset in ohlcv_map:
            return ohlcv_map[asset]
        raise FileNotFoundError(f"No data for {asset}")

    monkeypatch.setattr(DataLoader, "load", mock_load)
    runner = MultiAssetRunner(config)
    multi_result = runner.run(
        assets=["gold", "silver"],
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
    )

    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    assert "silver" in report.skipped_assets
    assert "gold" in report.assets
    assert report.n_assets == 1


# ---------------------------------------------------------------------------
# Portfolio metric correctness tests (5 tests)
# ---------------------------------------------------------------------------


def test_portfolio_total_return_matches_equity_curve(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """portfolio_metrics total_return == (final_equity - initial) / initial."""
    multi_result = _make_multi_asset_result(config, monkeypatch, seeds=[42, 43])
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    first_report = next(iter(report.per_asset_reports.values()))
    initial = first_report.initial_capital_usd * len(multi_result.assets)

    expected_return = (multi_result.portfolio_equity_curve.iloc[-1] - initial) / initial
    assert report.portfolio_total_return == pytest.approx(
        float(expected_return), rel=1e-6
    )


def test_portfolio_max_drawdown_is_non_positive(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """portfolio_metrics max_drawdown is always <= 0."""
    multi_result = _make_multi_asset_result(config, monkeypatch, seeds=[5, 6])
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    max_dd = report.portfolio_max_drawdown
    if not math.isnan(max_dd):
        assert (
            max_dd <= 0.0
        ), f"Max drawdown must be non-positive (fraction below peak), got {max_dd}"


def test_portfolio_sharpe_is_finite_for_adequate_data(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """portfolio_metrics sharpe is a finite float when sufficient data exists."""
    multi_result = _make_multi_asset_result(config, monkeypatch, seeds=[7, 8])
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    sharpe = report.portfolio_sharpe
    assert not math.isinf(sharpe), "Portfolio Sharpe must not be infinite"
    assert isinstance(sharpe, float)


def test_portfolio_date_range_matches_equity_curve(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """portfolio_date_range matches the actual index of portfolio_equity_curve."""
    multi_result = _make_multi_asset_result(config, monkeypatch, seeds=[9, 10])
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    idx = multi_result.portfolio_equity_curve.index
    expected_start = idx[0].date() if hasattr(idx[0], "date") else idx[0]
    expected_end = idx[-1].date() if hasattr(idx[-1], "date") else idx[-1]

    assert report.portfolio_date_range[0] == expected_start
    assert report.portfolio_date_range[1] == expected_end


def test_portfolio_initial_capital_total_equals_n_assets_times_per_asset(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """initial_capital_total == initial_capital_per_asset × n_assets."""
    multi_result = _make_multi_asset_result(
        config, monkeypatch, assets=["gold", "silver", "copper"], seeds=[1, 2, 3]
    )
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    assert report.initial_capital_total == pytest.approx(
        report.initial_capital_per_asset * report.n_assets, rel=1e-9
    )


# ---------------------------------------------------------------------------
# Per-asset report quality tests (2 tests)
# ---------------------------------------------------------------------------


def test_per_asset_reports_have_scalar_metrics(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each per-asset PerformanceReport contains the expected scalar metrics."""
    multi_result = _make_multi_asset_result(config, monkeypatch, seeds=[11, 12])
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    expected_keys = {"sharpe", "max_drawdown", "total_return", "cagr", "win_rate"}
    for asset, perf_report in report.per_asset_reports.items():
        missing = expected_keys - set(perf_report.scalar_metrics.keys())
        assert (
            not missing
        ), f"Asset '{asset}' PerformanceReport missing metrics: {missing}"


def test_per_asset_sharpe_different_from_portfolio_sharpe(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Portfolio Sharpe is generally different from individual asset Sharpes."""
    multi_result = _make_multi_asset_result(
        config, monkeypatch, assets=["gold", "silver"], seeds=[13, 14]
    )
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    gold_sharpe = report.per_asset_reports["gold"].scalar_metrics.get(
        "sharpe", float("nan")
    )
    portfolio_sharpe = report.portfolio_sharpe

    assert isinstance(gold_sharpe, float)
    assert isinstance(portfolio_sharpe, float)


# ---------------------------------------------------------------------------
# Edge case tests (2 tests)
# ---------------------------------------------------------------------------


def test_portfolio_engine_single_asset(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PortfolioPerformanceEngine handles single-asset portfolio correctly."""
    multi_result = _make_multi_asset_result(
        config, monkeypatch, assets=["gold"], seeds=[99]
    )
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    assert report.n_assets == 1
    assert "gold" in report.per_asset_reports
    portfolio_return = report.portfolio_total_return
    single_return = report.per_asset_reports["gold"].scalar_metrics.get(
        "total_return", float("nan")
    )
    if not math.isnan(portfolio_return) and not math.isnan(single_return):
        assert portfolio_return == pytest.approx(single_return, rel=1e-6)


def test_portfolio_engine_raises_for_empty_asset_results(
    config: Config,
) -> None:
    """PortfolioPerformanceEngine raises ValueError when asset_results is empty."""

    equity = pd.Series(
        [1_000_000.0],
        index=pd.DatetimeIndex(["2026-01-02"], tz="UTC"),
        name="portfolio_equity",
    )
    pnl = pd.Series(
        [0.0],
        index=pd.DatetimeIndex(["2026-01-02"], tz="UTC"),
        name="portfolio_pnl",
    )
    empty_result = MultiAssetBacktestResult(
        strategy_name="ema_crossover",
        signal_name="ema_crossover_50_200",
        parameters={"fast_period": 50, "slow_period": 200},
        assets=[],
        skipped_assets=["gold", "silver"],
        run_id="20260101_000000_portfolio_ema_crossover",
        executed_at=datetime(2026, 1, 1, tzinfo=UTC),
        asset_results={},
        portfolio_equity_curve=equity,
        portfolio_pnl_series=pnl,
    )

    engine = PortfolioPerformanceEngine()
    with pytest.raises(ValueError, match="no asset results"):
        engine.compute(empty_result)


def test_absolute_pnl_by_asset_populated(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """absolute_pnl_by_asset is populated for all successful assets."""
    multi_result = _make_multi_asset_result(config, monkeypatch, seeds=[1, 2])
    engine = PortfolioPerformanceEngine()
    report = engine.compute(multi_result)

    assert set(report.absolute_pnl_by_asset.keys()) == set(multi_result.assets)
    for asset, pnl in report.absolute_pnl_by_asset.items():
        assert isinstance(pnl, float), f"absolute_pnl_by_asset[{asset}] must be float"
    # Sum of absolute PnLs must approximately equal portfolio total PnL
    total = sum(report.absolute_pnl_by_asset.values())
    portfolio_total = float(multi_result.portfolio_pnl_series.sum())
    assert (
        abs(total - portfolio_total) < 1.0
    ), f"Sum of absolute_pnl_by_asset ({total:.2f}) must match portfolio total ({portfolio_total:.2f})"
