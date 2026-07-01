"""Tests for PerformanceEngine, scalar metrics, rolling metrics, and save_metrics.

Increment 2: Tests 1-15 — core metrics and PerformanceEngine.
Increment 3: Tests 16-20 — save_metrics, rolling warmup, compare_runs.
See Architecture Section 7 (PerformanceReport) and Implementation Roadmap Module 6.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.backtesting.engine import VectorizedBacktester
from src.core.config import Config
from src.core.types import (
    BacktestMetadata,
    BacktestResult,
    PerformanceReport,
    SignalEvaluation,
    TradeRecord,
)
from src.performance.metrics import compute_daily_returns, compute_scalar_metrics
from src.performance.report import PerformanceEngine
from src.performance.rolling import compute_rolling_metrics

# ---------------------------------------------------------------------------
# Shared helpers and fixtures
# ---------------------------------------------------------------------------


def _make_simple_result(
    equity_values: list[float],
    pnl_values: list[float],
    trades: list[TradeRecord] | None = None,
    initial_capital: float = 1_000_000.0,
) -> BacktestResult:
    """Build a minimal BacktestResult from raw values for unit testing metrics.

    equity_values[0] must equal initial_capital (BacktestResult contract).
    pnl_values[0] must be 0.0 (bar 0 is always flat per ADR-002).
    Does not use VectorizedBacktester — suitable for pure metric unit tests.
    """
    n = len(equity_values)
    dates = pd.bdate_range(start="2023-01-02", periods=n, freq="B")
    index = pd.DatetimeIndex(dates, tz="UTC")

    equity_curve = pd.Series(equity_values, index=index, name="equity", dtype="float64")
    pnl_series = pd.Series(pnl_values, index=index, name="pnl", dtype="float64")
    positions = pd.Series([0.0] * n, index=index, name="position", dtype="float64")

    metadata = BacktestMetadata(
        run_id="test_run",
        asset="gold",
        strategy_name="test",
        signal_name="test",
        parameters={},
        data_source="synthetic",
        data_start=index[0].date(),
        data_end=index[-1].date(),
        initial_capital_usd=initial_capital,
        cost_model_params={},
        sizing_model_params={},
        executed_at=datetime(2024, 1, 1, tzinfo=UTC),
        git_commit_hash="test",
    )

    return BacktestResult(
        run_id="test_run",
        asset="gold",
        trades=trades or [],
        equity_curve=equity_curve,
        positions=positions,
        pnl_series=pnl_series,
        metadata=metadata,
    )


def _make_trade(
    direction: int = 1,
    entry_price: float = 100.0,
    exit_price: float = 110.0,
    size_notional: float = 100_000.0,
    commission: float = 0.0,
) -> TradeRecord:
    """Build a TradeRecord with correct gross/net PnL for the given prices."""
    gross_pnl = direction * (exit_price - entry_price) * size_notional / entry_price
    net_pnl = gross_pnl - commission
    return TradeRecord(
        run_id="test_run",
        asset="gold",
        direction=direction,
        entry_date=date(2023, 1, 2),
        exit_date=date(2023, 1, 20),
        entry_price=entry_price,
        exit_price=exit_price,
        size_notional=size_notional,
        size_contracts=size_notional / (entry_price * 100.0),
        gross_pnl=gross_pnl,
        transaction_cost=commission,
        net_pnl=net_pnl,
        duration_bars=18,
        return_pct=net_pnl / size_notional,
        force_closed=False,
    )


def _make_signal_evaluation() -> SignalEvaluation:
    """Build a minimal SignalEvaluation for signal_metrics tests."""
    return SignalEvaluation(
        signal_name="ema_crossover_50_200",
        asset="gold",
        ic=0.045,
        icir=0.62,
        ic_decay={1: 0.045, 2: 0.038, 5: 0.021, 10: 0.012, 20: 0.005},
        turnover=0.10,
        ic_rolling_window=63,
        evaluation_start=date(2023, 1, 2),
        evaluation_end=date(2023, 12, 29),
    )


def _make_ohlcv_for_backtest(closes: list[float]) -> pd.DataFrame:
    """Build a minimal NormalizedOHLCV DataFrame for VectorizedBacktester tests."""
    n = len(closes)
    dates = pd.bdate_range(start="2023-01-02", periods=n, freq="B")
    opens = [closes[0]] + closes[:-1]
    df = pd.DataFrame(
        {
            "open": opens,
            "high": [c * 1.001 for c in closes],
            "low": [c * 0.999 for c in closes],
            "close": closes,
            "volume": [25000.0] * n,
            "open_interest": [float("nan")] * n,
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )
    df.attrs["source"] = "synthetic"
    df.attrs["continuous"] = True
    return df


@pytest.fixture
def tmp_config(tmp_path: Path) -> Config:
    """Config fixture redirecting paths.runs to a temporary directory."""
    cfg = Config.load("config/")
    cfg.paths["runs"] = str(tmp_path / "data" / "runs") + "/"
    (tmp_path / "data" / "runs").mkdir(parents=True, exist_ok=True)
    return cfg


# ---------------------------------------------------------------------------
# Increment 2 — Tests 1-15: Core metrics and PerformanceEngine
# ---------------------------------------------------------------------------


def test_daily_returns_first_bar_is_zero() -> None:
    """daily_return[0] is always 0.0 regardless of pnl (bar 0 is always flat)."""
    initial = 1_000_000.0
    equity_values = [initial, initial + 1000.0, initial + 2000.0]
    pnl_values = [0.0, 1000.0, 1000.0]

    result = _make_simple_result(equity_values, pnl_values, initial_capital=initial)
    daily_ret = compute_daily_returns(result.pnl_series, result.equity_curve)

    assert daily_ret.iloc[0] == pytest.approx(
        0.0
    ), "Bar 0 must always be 0.0 — pnl[0] is always 0 per ADR-002"


def test_daily_returns_formula_uses_prior_equity() -> None:
    """daily_return[t] = pnl[t] / equity[t-1], not pnl[t] / initial_capital."""
    initial = 1_000_000.0
    # equity[1] = 1_001_000, equity[2] = 1_003_000
    # daily_return[1] = 1000 / 1_000_000 = 0.001
    # daily_return[2] = 2000 / 1_001_000 ≈ 0.001998 (not 2000 / 1_000_000 = 0.002)
    equity_values = [initial, initial + 1_000.0, initial + 3_000.0]
    pnl_values = [0.0, 1_000.0, 2_000.0]

    result = _make_simple_result(equity_values, pnl_values, initial_capital=initial)
    daily_ret = compute_daily_returns(result.pnl_series, result.equity_curve)

    assert daily_ret.iloc[1] == pytest.approx(1_000.0 / initial, rel=1e-6)
    assert daily_ret.iloc[2] == pytest.approx(2_000.0 / (initial + 1_000.0), rel=1e-6)
    assert daily_ret.iloc[2] != pytest.approx(
        2_000.0 / initial, rel=1e-4
    ), "Must use equity[t-1], not initial_capital, as denominator"


def test_sharpe_zero_variance_returns_zero() -> None:
    """Sharpe is 0.0 when all daily returns are identical (zero variance)."""
    initial = 1_000_000.0
    n = 50
    pnl = [0.0] * n
    equity = [initial] * n

    result = _make_simple_result(equity, pnl, initial_capital=initial)
    scalar = compute_scalar_metrics(result)

    assert scalar["sharpe"] == pytest.approx(
        0.0
    ), "Sharpe must be 0.0 when daily return variance is zero"


def test_sharpe_positive_for_positive_mean_return() -> None:
    """Sharpe is positive when mean daily return is positive and variance is nonzero."""
    initial = 1_000_000.0
    n = 100
    # Alternating +200, +100 → mean = 150 > 0, variance > 0
    pnl = [200.0 if i % 2 == 0 else 100.0 for i in range(n)]
    equity = [initial + sum(pnl[: i + 1]) for i in range(n)]

    result = _make_simple_result(equity, pnl, initial_capital=initial)
    scalar = compute_scalar_metrics(result)

    assert scalar["sharpe"] > 0.0, "Sharpe must be positive for positive mean return"


def test_sharpe_manual_calculation() -> None:
    """Sharpe matches manual formula: mean(daily_return)/std(daily_return)*sqrt(252)."""
    initial = 1_000_000.0
    n = 30
    pnl = [1_000.0 if i % 2 == 0 else -500.0 for i in range(n)]
    equity = [initial + sum(pnl[: i + 1]) for i in range(n)]

    # Compute expected Sharpe manually
    daily_returns_manual = [0.0]  # bar 0 = 0
    for i in range(1, n):
        daily_returns_manual.append(pnl[i] / equity[i - 1])
    dr = pd.Series(daily_returns_manual)
    expected_sharpe = float(dr.mean() / dr.std() * math.sqrt(252))

    result = _make_simple_result(equity, pnl, initial_capital=initial)
    scalar = compute_scalar_metrics(result)

    assert scalar["sharpe"] == pytest.approx(expected_sharpe, rel=1e-4)


def test_max_drawdown_monotonic_equity_is_zero() -> None:
    """Max drawdown of a monotonically non-decreasing equity curve is 0.0."""
    initial = 1_000_000.0
    n = 30
    equity = [initial + 1_000.0 * i for i in range(n)]
    pnl = [0.0] + [1_000.0] * (n - 1)

    result = _make_simple_result(equity, pnl, initial_capital=initial)
    scalar = compute_scalar_metrics(result)

    assert scalar["max_drawdown"] == pytest.approx(
        0.0
    ), "Max drawdown must be 0.0 for monotonically non-decreasing equity"


def test_max_drawdown_known_series() -> None:
    """Max drawdown computed correctly for a known equity series with a specific dip."""
    initial = 1_000_000.0
    # equity peaks at 1_150_000 then drops to 1_050_000
    # max_drawdown = (1_050_000 - 1_150_000) / 1_150_000 = -100_000 / 1_150_000
    equity_values = [
        1_000_000.0,
        1_050_000.0,
        1_100_000.0,
        1_150_000.0,
        1_080_000.0,
        1_050_000.0,
        1_120_000.0,
    ]
    pnl_values = [0.0, 50_000.0, 50_000.0, 50_000.0, -70_000.0, -30_000.0, 70_000.0]

    result = _make_simple_result(equity_values, pnl_values, initial_capital=initial)
    scalar = compute_scalar_metrics(result)

    expected_max_dd = (1_050_000.0 - 1_150_000.0) / 1_150_000.0
    assert scalar["max_drawdown"] == pytest.approx(expected_max_dd, rel=1e-6)
    assert (
        scalar["max_drawdown"] < 0.0
    ), "Max drawdown must be negative for a dipping equity"


def test_calmar_equals_cagr_over_abs_max_drawdown() -> None:
    """Calmar = CAGR / |max_drawdown| — formula verified on known scenario."""
    initial = 1_000_000.0
    n = 252
    # Rising equity with a mid-series dip to test non-zero drawdown
    equity_values = [initial * (1.0 + 0.001 * i) for i in range(n)]
    # Insert a 3% dip at bar 100
    for i in range(100, 115):
        equity_values[i] = equity_values[i] * 0.97
    pnl_values = [0.0] + [equity_values[i] - equity_values[i - 1] for i in range(1, n)]

    result = _make_simple_result(equity_values, pnl_values, initial_capital=initial)
    scalar = compute_scalar_metrics(result)

    # Verify the formula holds — use computed cagr and max_drawdown
    if abs(scalar["max_drawdown"]) > 1e-10:
        expected_calmar = scalar["cagr"] / abs(scalar["max_drawdown"])
        assert scalar["calmar"] == pytest.approx(expected_calmar, rel=1e-4)
    else:
        assert scalar["calmar"] == pytest.approx(0.0)


def test_win_rate_fifty_fifty() -> None:
    """Win rate is 0.5 when exactly half of trades are winning."""
    winning = [_make_trade(exit_price=110.0) for _ in range(10)]
    losing = [_make_trade(exit_price=90.0) for _ in range(10)]
    trades = winning + losing

    initial = 1_000_000.0
    result = _make_simple_result(
        [initial] * 10, [0.0] * 10, trades=trades, initial_capital=initial
    )
    scalar = compute_scalar_metrics(result)

    assert scalar["win_rate"] == pytest.approx(0.5)


def test_win_rate_zero_when_no_trades() -> None:
    """Win rate is 0.0 when there are no trades (all-flat PositionSignal)."""
    initial = 1_000_000.0
    result = _make_simple_result(
        [initial] * 20, [0.0] * 20, trades=[], initial_capital=initial
    )
    scalar = compute_scalar_metrics(result)

    assert scalar["win_rate"] == pytest.approx(0.0)
    assert scalar["profit_factor"] == pytest.approx(0.0)
    assert scalar["avg_trade_duration_bars"] == pytest.approx(0.0)


def test_profit_factor_correct() -> None:
    """Profit factor = sum(winning net_pnl) / abs(sum(losing net_pnl)).

    2 winning trades (+10000 each) vs 1 losing trade (-10000):
    profit_factor = 20000 / 10000 = 2.0.
    """
    # direction=1, entry=100, exit=110, size=100000:
    # gross_pnl = 1*(110-100)*100000/100 = 10000
    winning = [_make_trade(exit_price=110.0) for _ in range(2)]
    losing = [_make_trade(exit_price=90.0) for _ in range(1)]
    trades = winning + losing

    initial = 1_000_000.0
    result = _make_simple_result(
        [initial] * 10, [0.0] * 10, trades=trades, initial_capital=initial
    )
    scalar = compute_scalar_metrics(result)

    assert scalar["profit_factor"] == pytest.approx(2.0, rel=1e-4)


def test_all_scalar_metrics_finite(config: Config) -> None:
    """All scalar metrics are finite (no NaN, no inf) for a valid BacktestResult."""
    # Price rises for 30 bars then falls — creates both winning and losing trades
    closes = [100.0 + i for i in range(30)] + [130.0 - i for i in range(30)]
    ohlcv = _make_ohlcv_for_backtest(closes)
    # Long first half, short second half
    ps = pd.Series([0] + [1] * 29 + [-1] * 30, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold", strategy_name="test", signal_name="test", config=config
    )
    result = backtester.run(ps, ohlcv)
    engine = PerformanceEngine()
    report = engine.compute(result)

    for key, value in report.scalar_metrics.items():
        assert np.isfinite(value), f"Metric '{key}' is not finite: {value}"


def test_sortino_zero_when_no_negative_returns() -> None:
    """Sortino is 0.0 when there are no negative daily returns."""
    initial = 1_000_000.0
    n = 30
    # All returns are non-negative
    pnl = [100.0] * n
    equity = [initial + 100.0 * i for i in range(n)]

    result = _make_simple_result(equity, pnl, initial_capital=initial)
    scalar = compute_scalar_metrics(result)

    assert scalar["sortino"] == pytest.approx(
        0.0
    ), "Sortino must be 0.0 when no negative daily returns exist"


def test_performance_engine_returns_performance_report(config: Config) -> None:
    """PerformanceEngine.compute() returns a PerformanceReport with all four dict fields."""
    n = 30
    closes = [100.0 + i for i in range(n)]
    ohlcv = _make_ohlcv_for_backtest(closes)
    ps = pd.Series([0] + [1] * (n - 1), index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold", strategy_name="test", signal_name="test", config=config
    )
    result = backtester.run(ps, ohlcv)

    engine = PerformanceEngine()
    report = engine.compute(result)

    assert isinstance(report, PerformanceReport)
    assert report.run_id == result.run_id
    assert isinstance(report.scalar_metrics, dict)
    assert isinstance(report.rolling_metrics, dict)
    assert isinstance(report.trade_statistics, dict)
    assert isinstance(report.signal_metrics, dict)
    # Verify core scalar_metrics keys are present
    for key in ("sharpe", "max_drawdown", "win_rate", "total_return", "cagr"):
        assert key in report.scalar_metrics, f"Missing scalar metric: {key}"
    # Verify rolling_metrics keys are present
    for key in ("rolling_sharpe_63", "rolling_vol_63", "rolling_drawdown"):
        assert key in report.rolling_metrics, f"Missing rolling metric: {key}"


def test_signal_metrics_empty_when_evaluation_none(config: Config) -> None:
    """signal_metrics is an empty dict when BacktestResult.signal_evaluation is None."""
    n = 20
    closes = [100.0 + i for i in range(n)]
    ohlcv = _make_ohlcv_for_backtest(closes)
    ps = pd.Series([0] + [1] * (n - 1), index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold", strategy_name="test", signal_name="test", config=config
    )
    result = backtester.run(ps, ohlcv)
    assert (
        result.signal_evaluation is None
    ), "Module 5 always sets signal_evaluation=None"

    engine = PerformanceEngine()
    report = engine.compute(result)

    assert (
        report.signal_metrics == {}
    ), "signal_metrics must be empty dict when signal_evaluation is None"


def test_signal_metrics_populated_when_evaluation_present(config: Config) -> None:
    """signal_metrics contains ic, icir, and decay keys when evaluation is attached."""
    n = 20
    closes = [100.0 + i for i in range(n)]
    ohlcv = _make_ohlcv_for_backtest(closes)
    ps = pd.Series([0] + [1] * (n - 1), index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold", strategy_name="test", signal_name="test", config=config
    )
    result = backtester.run(ps, ohlcv)

    # Attach signal evaluation (simulating orchestration layer)
    result.signal_evaluation = _make_signal_evaluation()

    engine = PerformanceEngine()
    report = engine.compute(result)

    assert "ic" in report.signal_metrics
    assert "icir" in report.signal_metrics
    for horizon in (1, 2, 5, 10, 20):
        assert (
            f"signal_decay_{horizon}" in report.signal_metrics
        ), f"Missing signal_decay_{horizon} in signal_metrics"
    assert report.signal_metrics["ic"] == pytest.approx(0.045)
    assert report.signal_metrics["icir"] == pytest.approx(0.62)


# ---------------------------------------------------------------------------
# Increment 3 — Tests 16-20: save_metrics, rolling, compare_runs
# ---------------------------------------------------------------------------


def test_save_metrics_writes_metrics_json(tmp_config: Config) -> None:
    """RunManager.save_metrics() writes metrics.json to the run directory."""
    from src.backtesting.run_manager import RunManager

    n = 20
    closes = [100.0 + i for i in range(n)]
    ohlcv = _make_ohlcv_for_backtest(closes)
    ps = pd.Series([0] + [1] * (n - 1), index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold", strategy_name="test", signal_name="test", config=tmp_config
    )
    result = backtester.run(ps, ohlcv)

    manager = RunManager(tmp_config)
    run_dir = manager.save(result)
    assert not (
        run_dir / "metrics.json"
    ).exists(), (
        "metrics.json must NOT exist after save() — only save_metrics() writes it"
    )

    engine = PerformanceEngine()
    report = engine.compute(result)
    manager.save_metrics(result.run_id, report)

    assert (
        run_dir / "metrics.json"
    ).exists(), "metrics.json must exist after save_metrics()"


def test_metrics_json_contains_expected_keys(tmp_config: Config) -> None:
    """metrics.json contains run_id, scalar_metrics, and signal_metrics keys."""
    import json

    from src.backtesting.run_manager import RunManager

    n = 25
    closes = [100.0 + i for i in range(n)]
    ohlcv = _make_ohlcv_for_backtest(closes)
    ps = pd.Series([0] + [1] * (n - 1), index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold", strategy_name="test", signal_name="test", config=tmp_config
    )
    result = backtester.run(ps, ohlcv)

    manager = RunManager(tmp_config)
    run_dir = manager.save(result)

    engine = PerformanceEngine()
    report = engine.compute(result)
    manager.save_metrics(result.run_id, report)

    with open(run_dir / "metrics.json") as f:
        loaded = json.load(f)

    assert loaded["run_id"] == result.run_id
    assert "scalar_metrics" in loaded
    assert "signal_metrics" in loaded
    assert "trade_statistics" in loaded
    assert "sharpe" in loaded["scalar_metrics"]
    assert "max_drawdown" in loaded["scalar_metrics"]


def test_save_metrics_raises_when_run_not_found(tmp_config: Config) -> None:
    """save_metrics raises FileNotFoundError when run directory does not exist."""
    from src.backtesting.run_manager import RunManager

    manager = RunManager(tmp_config)

    # Create a minimal PerformanceReport with empty dicts
    report = PerformanceReport(
        run_id="nonexistent_run",
        initial_capital_usd=1_000_000.0,
        scalar_metrics={},
        rolling_metrics={},
        trade_statistics={},
        signal_metrics={},
    )

    with pytest.raises(FileNotFoundError):
        manager.save_metrics("nonexistent_run_id", report)


def test_rolling_sharpe_has_correct_nan_warmup() -> None:
    """Rolling Sharpe(63) produces NaN for first 62 bars, valid from bar 62."""
    initial = 1_000_000.0
    n = 100
    # Alternating pnl for non-zero variance
    pnl = [200.0 if i % 2 == 0 else -100.0 for i in range(n)]
    equity = [initial + sum(pnl[: i + 1]) for i in range(n)]

    result = _make_simple_result(equity, pnl, initial_capital=initial)
    rolling = compute_rolling_metrics(result)

    rs63 = rolling["rolling_sharpe_63"]

    assert (
        rs63.iloc[:62].isna().all()
    ), "Rolling Sharpe(63) must be NaN for the first 62 bars (warmup period)"
    assert not pd.isna(
        rs63.iloc[62]
    ), "Rolling Sharpe(63) bar 62 must be the first valid value (63-bar window)"


def test_compare_runs_returns_dataframe(tmp_config: Config) -> None:
    """RunManager.compare_runs() returns a DataFrame with one row per run_id.

    Closes Module 5 Open Question 2: compare_runs() is now tested.
    """
    from src.backtesting.run_manager import RunManager

    n = 20
    closes = [100.0 + i for i in range(n)]
    ohlcv = _make_ohlcv_for_backtest(closes)
    ps = pd.Series([0] + [1] * (n - 1), index=ohlcv.index, dtype="int8")

    backtester_a = VectorizedBacktester(
        asset="gold",
        strategy_name="strategy_a",
        signal_name="test",
        config=tmp_config,
    )
    backtester_b = VectorizedBacktester(
        asset="gold",
        strategy_name="strategy_b",
        signal_name="test",
        config=tmp_config,
    )

    result_a = backtester_a.run(ps, ohlcv)
    result_b = backtester_b.run(ps, ohlcv)

    manager = RunManager(tmp_config)
    manager.save(result_a)
    manager.save(result_b)

    comparison = manager.compare_runs([result_a.run_id, result_b.run_id])

    assert isinstance(
        comparison, pd.DataFrame
    ), "compare_runs() must return a pd.DataFrame"
    assert len(comparison) == 2, f"Expected 2 rows (one per run), got {len(comparison)}"
    assert "run_id" in comparison.columns
