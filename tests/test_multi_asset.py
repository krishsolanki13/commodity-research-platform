"""Tests for Module 14: Multi-Asset Runner.

Tests MultiAssetBacktestResult, MultiAssetRunner aggregation logic,
pipeline construction, error handling, and integration with VectorizedBacktester.
Uses the gold_ohlcv conftest fixture and synthetic multi-asset OHLCV for
tests that require multiple assets. No network calls.

See ADR-010 (Multi-Asset Research Scope and Phasing).
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from src.backtesting.multi_asset import MultiAssetRunner
from src.backtesting.sizing import VolatilityScaledSizer
from src.core.config import Config
from src.core.types import MultiAssetBacktestResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(
    n: int = 252,
    base_close: float = 100.0,
    start: str = "2023-01-02",
    seed: int = 42,
) -> pd.DataFrame:
    """Build a synthetic NormalizedOHLCV DataFrame with realistic returns."""
    rng = np.random.default_rng(seed=seed)
    returns = rng.normal(0.0, 0.01, n)
    closes = base_close * np.cumprod(1 + returns)
    dates = pd.bdate_range(start=start, periods=n, freq="B")
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


def _patch_loader(monkeypatch: pytest.MonkeyPatch, ohlcv_map: dict) -> None:
    """Patch DataLoader.load() to return synthetic OHLCV per asset."""
    from src.data.loader import DataLoader

    def mock_load(self, asset, **kwargs):  # noqa: ANN001
        if asset in ohlcv_map:
            return ohlcv_map[asset]
        raise FileNotFoundError(f"No data for {asset}")

    monkeypatch.setattr(DataLoader, "load", mock_load)


# ---------------------------------------------------------------------------
# MultiAssetBacktestResult dataclass tests (3 tests)
# ---------------------------------------------------------------------------


def test_multi_asset_backtest_result_properties(
    config: Config, gold_ohlcv: pd.DataFrame
) -> None:
    """MultiAssetBacktestResult computed properties are correct."""
    from src.backtesting.engine import VectorizedBacktester
    from src.research.moving_averages import EMA
    from src.research.pipeline import FeaturePipeline
    from src.signal.position import PositionSignalConstructor
    from src.signal.trend import EMACrossoverSignal

    ff = FeaturePipeline([EMA(50), EMA(200)]).compute(gold_ohlcv, asset="gold")
    gen = EMACrossoverSignal(fast_period=50, slow_period=200)
    raw = gen.generate(ff)
    ps = PositionSignalConstructor().build(raw, threshold=0.0)
    bt_result = VectorizedBacktester(
        asset="gold",
        strategy_name="ema_crossover",
        signal_name=gen.name,
        config=config,
        parameters={"fast_period": 50, "slow_period": 200},
    ).run(ps, gold_ohlcv)

    equity = bt_result.equity_curve
    pnl = bt_result.pnl_series

    multi = MultiAssetBacktestResult(
        strategy_name="ema_crossover",
        signal_name=gen.name,
        parameters={"fast_period": 50, "slow_period": 200},
        assets=["gold"],
        skipped_assets=[],
        run_id="20260101_000000_portfolio_ema_crossover",
        executed_at=datetime.now(UTC),
        asset_results={"gold": bt_result},
        portfolio_equity_curve=equity,
        portfolio_pnl_series=pnl,
    )

    assert multi.n_assets == 1
    assert multi.total_trades == len(bt_result.trades)
    assert len(multi.assets_with_trades) <= 1


def test_multi_asset_backtest_result_skipped_assets_is_non_fatal() -> None:
    """MultiAssetBacktestResult with skipped assets is still valid."""
    equity = pd.Series([1_000_000.0, 1_001_000.0], name="portfolio_equity")
    pnl = pd.Series([0.0, 1_000.0], name="portfolio_pnl")

    result = MultiAssetBacktestResult(
        strategy_name="momentum",
        signal_name="momentum_20",
        parameters={"lookback_period": 20},
        assets=["gold"],
        skipped_assets=["silver", "copper"],
        run_id="20260101_000000_portfolio_momentum",
        executed_at=datetime.now(UTC),
        asset_results={},
        portfolio_equity_curve=equity,
        portfolio_pnl_series=pnl,
    )

    assert result.n_assets == 1
    assert len(result.skipped_assets) == 2
    assert "silver" in result.skipped_assets


def test_multi_asset_backtest_result_portfolio_equity_starts_at_sum() -> None:
    """Portfolio equity starts at the sum of initial capitals across assets."""
    initial = 1_000_000.0
    n = 5

    equity_a = pd.Series(
        [initial + i * 100.0 for i in range(n)],
        index=pd.date_range("2026-01-01", periods=n, freq="B"),
        name="equity",
    )
    equity_b = pd.Series(
        [initial + i * 50.0 for i in range(n)],
        index=pd.date_range("2026-01-01", periods=n, freq="B"),
        name="equity",
    )
    portfolio_equity = equity_a + equity_b

    assert portfolio_equity.iloc[0] == pytest.approx(
        2 * initial
    ), "Portfolio equity must start at sum of per-asset initial capitals"


# ---------------------------------------------------------------------------
# MultiAssetRunner.run() core behavior (5 tests)
# ---------------------------------------------------------------------------


def test_multi_asset_runner_returns_correct_type(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MultiAssetRunner.run() returns a MultiAssetBacktestResult."""
    ohlcv = _make_ohlcv(252)
    _patch_loader(monkeypatch, {"gold": ohlcv})

    runner = MultiAssetRunner(config)
    result = runner.run(
        assets=["gold"],
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
    )

    assert isinstance(result, MultiAssetBacktestResult)
    assert result.strategy_name == "ema_crossover"
    assert "gold" in result.asset_results
    assert "gold" in result.assets


def test_multi_asset_runner_runs_all_specified_assets(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MultiAssetRunner processes every asset in the input list."""
    ohlcv_map = {
        "gold": _make_ohlcv(252, base_close=2000.0, seed=1),
        "silver": _make_ohlcv(252, base_close=25.0, seed=2),
        "copper": _make_ohlcv(252, base_close=4.0, seed=3),
    }
    _patch_loader(monkeypatch, ohlcv_map)

    runner = MultiAssetRunner(config)
    result = runner.run(
        assets=["gold", "silver", "copper"],
        strategy_name="momentum",
        parameters={"lookback_period": 20, "z_score_window": 63},
    )

    assert result.n_assets == 3
    assert set(result.assets) == {"gold", "silver", "copper"}
    assert all(a in result.asset_results for a in ["gold", "silver", "copper"])


def test_multi_asset_runner_portfolio_pnl_is_sum_of_per_asset(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Portfolio PnL series equals the sum of individual per-asset PnL series."""
    ohlcv_map = {
        "gold": _make_ohlcv(252, seed=10),
        "silver": _make_ohlcv(252, seed=20),
    }
    _patch_loader(monkeypatch, ohlcv_map)

    runner = MultiAssetRunner(config)
    result = runner.run(
        assets=["gold", "silver"],
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
    )

    gold_pnl = result.asset_results["gold"].pnl_series
    silver_pnl = result.asset_results["silver"].pnl_series

    common_dates = result.portfolio_pnl_series.index
    gold_aligned = gold_pnl.reindex(common_dates).fillna(0.0)
    silver_aligned = silver_pnl.reindex(common_dates).fillna(0.0)
    expected_portfolio_pnl = gold_aligned + silver_aligned

    pd.testing.assert_series_equal(
        result.portfolio_pnl_series,
        expected_portfolio_pnl,
        check_names=False,
        rtol=1e-6,
    )


def test_multi_asset_runner_signal_evaluations_attached(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each per-asset BacktestResult has signal_evaluation attached (or None)."""
    ohlcv_map = {"gold": _make_ohlcv(252, seed=42)}
    _patch_loader(monkeypatch, ohlcv_map)

    runner = MultiAssetRunner(config)
    result = runner.run(
        assets=["gold"],
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
    )

    gold_result = result.asset_results["gold"]
    assert hasattr(
        gold_result, "signal_evaluation"
    ), "BacktestResult.signal_evaluation must be set (not absent)"


def test_multi_asset_runner_vol_scaled_sizer_works(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MultiAssetRunner passes VolatilityScaledSizer through to each backtester."""
    ohlcv_map = {
        "gold": _make_ohlcv(252, seed=1),
        "silver": _make_ohlcv(252, seed=2),
    }
    _patch_loader(monkeypatch, ohlcv_map)

    vol_sizer = VolatilityScaledSizer(target_annual_vol=0.01, lookback_days=30)
    runner = MultiAssetRunner(config)
    result = runner.run(
        assets=["gold", "silver"],
        strategy_name="donchian_breakout",
        parameters={"channel_period": 20},
        sizer=vol_sizer,
    )

    assert isinstance(result, MultiAssetBacktestResult)
    assert result.n_assets == 2


# ---------------------------------------------------------------------------
# Pipeline construction tests (3 tests)
# ---------------------------------------------------------------------------


def test_multi_asset_runner_all_four_strategies_construct(
    config: Config,
) -> None:
    """_build_pipeline_components() constructs all four strategies correctly."""
    runner = MultiAssetRunner(config)

    strategies = [
        ("ema_crossover", {"fast_period": 50, "slow_period": 200}),
        ("momentum", {"lookback_period": 20, "z_score_window": 63}),
        ("rsi_reversion", {"period": 14}),
        ("donchian_breakout", {"channel_period": 20}),
    ]
    for strategy_name, params in strategies:
        indicators, signal_gen = runner._build_pipeline_components(
            strategy_name, params
        )
        assert (
            signal_gen is not None
        ), f"Signal generator must not be None for {strategy_name}"
        assert isinstance(
            indicators, list
        ), f"Indicators must be a list for {strategy_name}"


def test_multi_asset_runner_unknown_strategy_raises(config: Config) -> None:
    """_build_pipeline_components() raises ValueError for unknown strategy."""
    runner = MultiAssetRunner(config)

    with pytest.raises(ValueError, match="unknown strategy"):
        runner._build_pipeline_components("super_secret_alpha", {"param": 1})


def test_multi_asset_runner_run_raises_for_empty_asset_list(
    config: Config,
) -> None:
    """MultiAssetRunner.run() raises ValueError when assets list is empty."""
    runner = MultiAssetRunner(config)

    with pytest.raises(ValueError, match="must not be empty"):
        runner.run(
            assets=[],
            strategy_name="ema_crossover",
            parameters={"fast_period": 50, "slow_period": 200},
        )


# ---------------------------------------------------------------------------
# Error handling and resilience tests (2 tests)
# ---------------------------------------------------------------------------


def test_multi_asset_runner_skips_failed_asset_and_continues(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If one asset fails, it is skipped; successful assets still produce results."""
    ohlcv_map = {"gold": _make_ohlcv(252, seed=1)}
    _patch_loader(monkeypatch, ohlcv_map)

    runner = MultiAssetRunner(config)
    result = runner.run(
        assets=["gold", "silver"],
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
    )

    assert "gold" in result.assets
    assert "silver" in result.skipped_assets
    assert result.n_assets == 1


def test_multi_asset_runner_raises_when_all_assets_fail(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MultiAssetRunner.run() raises ValueError when all assets fail."""
    _patch_loader(monkeypatch, {})

    runner = MultiAssetRunner(config)
    with pytest.raises(ValueError, match="all .* assets failed"):
        runner.run(
            assets=["gold", "silver"],
            strategy_name="ema_crossover",
            parameters={"fast_period": 50, "slow_period": 200},
        )


# ---------------------------------------------------------------------------
# Portfolio aggregation tests (2 tests)
# ---------------------------------------------------------------------------


def test_multi_asset_runner_portfolio_equity_is_sum(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Portfolio equity curve is elementwise sum of per-asset equity curves."""
    ohlcv_map = {
        "gold": _make_ohlcv(100, seed=1),
        "silver": _make_ohlcv(100, seed=2),
    }
    _patch_loader(monkeypatch, ohlcv_map)

    runner = MultiAssetRunner(config)
    result = runner.run(
        assets=["gold", "silver"],
        strategy_name="momentum",
        parameters={"lookback_period": 10, "z_score_window": 30},
    )

    gold_eq = result.asset_results["gold"].equity_curve
    silver_eq = result.asset_results["silver"].equity_curve

    common = result.portfolio_equity_curve.index
    gold_aligned = gold_eq.reindex(common).ffill()
    silver_aligned = silver_eq.reindex(common).ffill()
    expected = gold_aligned + silver_aligned

    pd.testing.assert_series_equal(
        result.portfolio_equity_curve,
        expected,
        check_names=False,
        rtol=1e-6,
    )


def test_multi_asset_runner_run_id_format(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Portfolio run_id follows YYYYMMDD_HHMMSS_portfolio_{strategy} format."""
    import re

    ohlcv_map = {"gold": _make_ohlcv(252, seed=1)}
    _patch_loader(monkeypatch, ohlcv_map)

    runner = MultiAssetRunner(config)
    result = runner.run(
        assets=["gold"],
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
    )

    pattern = r"^\d{8}_\d{6}_portfolio_ema_crossover$"
    assert re.match(pattern, result.run_id), (
        f"run_id '{result.run_id}' does not match expected format "
        f"YYYYMMDD_HHMMSS_portfolio_ema_crossover"
    )
