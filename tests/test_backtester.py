"""Tests for the backtesting engine: CostModel, FixedNotionalSizer,
TradeLog, VectorizedBacktester, and RunManager.

This file grows across Increments 2-5:
  Increment 2: CostModel, FixedNotionalSizer, TradeLog tests (8 tests)
  Increment 3: VectorizedBacktester PnL/equity tests (5 tests)
  Increment 4: RunManager persistence tests (4 tests)
  Increment 5: Edge case tests (3 tests)
See ADR-002, ADR-003, ADR-005, ADR-009.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.backtesting.costs import CostModel
from src.backtesting.sizing import FixedNotionalSizer
from src.backtesting.trade_log import TradeLog
from src.core.config import Config

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_ohlcv(closes: list[float], opens: list[float] | None = None) -> pd.DataFrame:
    """Helper: build a minimal NormalizedOHLCV DataFrame from a close price list.

    If opens is not provided, opens[t] = closes[t-1] for t>0, opens[0] = closes[0].
    high/low are set to a small band around open/close to keep OHLC valid.
    """
    n = len(closes)
    if opens is None:
        opens = [closes[0]] + closes[:-1]
    dates = pd.bdate_range(start="2023-01-02", periods=n, freq="B")
    highs = [max(o, c) * 1.001 for o, c in zip(opens, closes, strict=True)]
    lows = [min(o, c) * 0.999 for o, c in zip(opens, closes, strict=True)]
    df = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [25000.0] * n,
            "open_interest": [float("nan")] * n,
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )
    df.attrs["asset"] = "gold"
    df.attrs["source"] = "synthetic"
    df.attrs["continuous"] = True
    return df


@pytest.fixture
def tmp_config(tmp_path: Path, config: Config) -> Config:
    """Config fixture redirecting paths.runs to a temporary directory."""
    cfg = Config.load("config/")
    cfg.paths["runs"] = str(tmp_path / "data" / "runs") + "/"
    (tmp_path / "data" / "runs").mkdir(parents=True, exist_ok=True)
    return cfg


# ---------------------------------------------------------------------------
# Increment 2 — CostModel, FixedNotionalSizer, TradeLog tests
# ---------------------------------------------------------------------------


def test_cost_model_computes_commission_plus_slippage() -> None:
    """CostModel.compute() returns commission + slippage_ticks * tick_value."""
    model = CostModel(commission_per_trade=5.0, slippage_ticks=1)
    cost = model.compute(tick_value=10.0)
    assert cost == pytest.approx(15.0), f"Expected 5.0+1*10.0=15.0, got {cost}"


def test_fixed_notional_sizer_returns_constant() -> None:
    """FixedNotionalSizer.compute_size() returns the constructor value regardless of args."""
    sizer = FixedNotionalSizer(notional_usd=100_000.0)
    assert sizer.compute_size(signal=1.0, asset="gold", equity=1_000_000.0) == 100_000.0
    assert sizer.compute_size(signal=-1.0, asset="wti", equity=500_000.0) == -100_000.0


def test_trade_log_entry_price_is_open_t_plus_1() -> None:
    """Trade opens at Open[t+1] where t is the bar position_signal first becomes nonzero.

    ADR-002 invariant: executed_position = position_signal.shift(1, fill_value=0).
    ps goes nonzero at index 2 (decided at Close[2]).
    executed_position goes nonzero at index 3 (one bar later).
    Entry price = open[3], entry date = index[3].
    """
    closes = [100.0] * 10
    ohlcv = _make_ohlcv(closes)
    # Signal: flat idx 0-1, long idx 2-8, flat idx 9
    ps = pd.Series([0, 0, 1, 1, 1, 1, 1, 1, 1, 0], index=ohlcv.index, dtype="int8")

    cost_model = CostModel(commission_per_trade=0.0, slippage_ticks=0)
    sizer = FixedNotionalSizer(notional_usd=100_000.0)
    log = TradeLog(
        run_id="test",
        asset="gold",
        cost_model=cost_model,
        position_sizer=sizer,
        contract_multiplier=100.0,
        tick_value=10.0,
        initial_capital_usd=1_000_000.0,
    )
    trades = log.build(ps, ohlcv)

    assert len(trades) == 1
    assert trades[0].entry_price == pytest.approx(ohlcv["open"].iloc[3])
    assert trades[0].entry_date == ohlcv.index[3].date()


def test_trade_log_exit_price_is_open_t_plus_1() -> None:
    """Trade closes at Open[t+1] where t is the bar position_signal returns to 0.

    ADR-002 invariant: executed_position = position_signal.shift(1, fill_value=0).
    ps goes flat at index 5 (ps[5]=0, decided at Close[5]).
    executed_position goes flat at index 6 (one bar later, per shift(1)).
    Last held bar = index 5. Normal close fires at open[6], exit date = index[6].

    Trace:
      ps               = [0, 1, 1, 1, 1, 0, 0, 0, 0, 0]
      executed_position = [0, 0, 1, 1, 1, 1, 0, 0, 0, 0]  (shift(1))
      nonzero run: indices 2-5, end_pos=5
      normal close: open[end_pos + 1] = open[6]
    """
    closes = [100.0] * 10
    ohlcv = _make_ohlcv(closes)
    # Signal: flat idx 0, long idx 1-4, flat idx 5-9
    ps = pd.Series([0, 1, 1, 1, 1, 0, 0, 0, 0, 0], index=ohlcv.index, dtype="int8")

    cost_model = CostModel(commission_per_trade=0.0, slippage_ticks=0)
    sizer = FixedNotionalSizer(notional_usd=100_000.0)
    log = TradeLog(
        run_id="test",
        asset="gold",
        cost_model=cost_model,
        position_sizer=sizer,
        contract_multiplier=100.0,
        tick_value=10.0,
        initial_capital_usd=1_000_000.0,
    )
    trades = log.build(ps, ohlcv)

    assert len(trades) == 1
    assert trades[0].exit_price == pytest.approx(ohlcv["open"].iloc[6])
    assert trades[0].exit_date == ohlcv.index[6].date()
    assert trades[0].force_closed is False


def test_trade_log_force_closes_open_position_at_end() -> None:
    """A position still open at the final bar is force-closed at that bar's close."""
    closes = [100.0] * 10
    ohlcv = _make_ohlcv(closes)
    # Long from idx 1 through the very last bar (idx 9), never exits.
    ps = pd.Series([0, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=ohlcv.index, dtype="int8")

    cost_model = CostModel(commission_per_trade=0.0, slippage_ticks=0)
    sizer = FixedNotionalSizer(notional_usd=100_000.0)
    log = TradeLog(
        run_id="test",
        asset="gold",
        cost_model=cost_model,
        position_sizer=sizer,
        contract_multiplier=100.0,
        tick_value=10.0,
        initial_capital_usd=1_000_000.0,
    )
    trades = log.build(ps, ohlcv)

    assert len(trades) == 1
    assert trades[0].force_closed is True
    assert trades[0].exit_date == ohlcv.index[9].date()
    assert trades[0].exit_price == pytest.approx(ohlcv["close"].iloc[9])


def test_trade_log_direction_reversal_produces_two_trades() -> None:
    """A +1 to -1 flip with no flat bar produces two TradeRecords.

    The long leg's exit and the short leg's entry coincide at the same
    bar and price. Each trade incurs its own transaction cost.
    One trailing flat bar is added so the short closes normally (not force-closed),
    keeping this test focused on reversal mechanics only.

    Architecture Section 11: direction reversal is treated as two trades;
    two transaction costs are applied.
    """
    closes = [100.0] * 12
    ohlcv = _make_ohlcv(closes)
    # Long idx 1-3, directly to short idx 4-9, flat idx 10-11 (normal close)
    ps = pd.Series(
        [0, 1, 1, 1, -1, -1, -1, -1, -1, -1, 0, 0], index=ohlcv.index, dtype="int8"
    )

    cost_model = CostModel(commission_per_trade=5.0, slippage_ticks=1)
    sizer = FixedNotionalSizer(notional_usd=100_000.0)
    log = TradeLog(
        run_id="test",
        asset="gold",
        cost_model=cost_model,
        position_sizer=sizer,
        contract_multiplier=100.0,
        tick_value=10.0,
        initial_capital_usd=1_000_000.0,
    )
    trades = log.build(ps, ohlcv)

    assert len(trades) == 2, f"Expected 2 trades (long + short), got {len(trades)}"
    long_trade = trades[0]
    short_trade = trades[1]
    assert long_trade.direction == 1
    assert short_trade.direction == -1
    # Long trade's exit must equal short trade's entry — same execution event
    assert long_trade.exit_date == short_trade.entry_date
    assert long_trade.exit_price == pytest.approx(short_trade.entry_price)
    # Neither trade is force-closed
    assert long_trade.force_closed is False
    assert short_trade.force_closed is False
    # Both trades incur their own transaction cost
    assert long_trade.transaction_cost == pytest.approx(15.0)
    assert short_trade.transaction_cost == pytest.approx(15.0)


def test_trade_log_no_lookahead_entry_price() -> None:
    """Entry price uses Open[t+1], never Close[t] or Open[t] — verified by inspection.

    ps = [0, 1, 1, 1, 0]. shift(1) → executed_position = [0, 0, 1, 1, 1].
    Nonzero run: indices 2-4. Last bar (idx 4) is the final bar → force-closed.
    Entry = open[2] = 101.5. Not close[1]=101.0. Not open[1]=100.5.
    """
    closes = [100.0, 101.0, 102.0, 103.0, 104.0]
    opens = [100.0, 100.5, 101.5, 102.5, 103.5]
    ohlcv = _make_ohlcv(closes, opens=opens)
    ps = pd.Series([0, 1, 1, 1, 0], index=ohlcv.index, dtype="int8")

    cost_model = CostModel(commission_per_trade=0.0, slippage_ticks=0)
    sizer = FixedNotionalSizer(notional_usd=100_000.0)
    log = TradeLog(
        run_id="test",
        asset="gold",
        cost_model=cost_model,
        position_sizer=sizer,
        contract_multiplier=100.0,
        tick_value=10.0,
        initial_capital_usd=1_000_000.0,
    )
    trades = log.build(ps, ohlcv)

    assert len(trades) == 1
    # ps nonzero at idx 1 -> executed_position nonzero at idx 2 -> entry = open[2] = 101.5
    assert trades[0].entry_price == pytest.approx(101.5)
    assert trades[0].entry_price != pytest.approx(closes[1])  # not Close[t]
    assert trades[0].entry_price != pytest.approx(opens[1])  # not Open[t]


def test_trade_log_all_flat_produces_no_trades() -> None:
    """An all-zero PositionSignal produces an empty trade list."""
    closes = [100.0] * 10
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] * 10, index=ohlcv.index, dtype="int8")

    cost_model = CostModel(commission_per_trade=5.0, slippage_ticks=1)
    sizer = FixedNotionalSizer(notional_usd=100_000.0)
    log = TradeLog(
        run_id="test",
        asset="gold",
        cost_model=cost_model,
        position_sizer=sizer,
        contract_multiplier=100.0,
        tick_value=10.0,
        initial_capital_usd=1_000_000.0,
    )
    trades = log.build(ps, ohlcv)
    assert trades == []


# ---------------------------------------------------------------------------
# Increment 3 — VectorizedBacktester PnL / equity curve tests
# ---------------------------------------------------------------------------


def test_always_long_rising_price_produces_positive_net_pnl(config: Config) -> None:
    """A signal that is always long on a monotonically rising price series has positive net PnL."""
    from src.backtesting.engine import VectorizedBacktester
    from src.core.types import BacktestResult

    closes = [100.0 + i for i in range(20)]
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] + [1] * 19, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=config,
    )
    result = backtester.run(ps, ohlcv)

    assert isinstance(result, BacktestResult)
    total_net_pnl = sum(t.net_pnl for t in result.trades)
    assert (
        total_net_pnl > 0
    ), f"Expected positive net PnL on rising prices, got {total_net_pnl}"


def test_always_flat_produces_zero_pnl(config: Config) -> None:
    """An all-flat PositionSignal produces zero PnL across the entire series."""
    from src.backtesting.engine import VectorizedBacktester

    closes = [100.0 + i for i in range(20)]
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] * 20, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=config,
    )
    result = backtester.run(ps, ohlcv)

    assert result.trades == []
    assert (result.pnl_series == 0.0).all()
    assert (result.equity_curve == result.metadata.initial_capital_usd).all()


def test_transaction_costs_reduce_pnl_by_expected_amount(config: Config) -> None:
    """net_pnl = gross_pnl - transaction_cost exactly, for every trade."""
    from src.backtesting.engine import VectorizedBacktester

    closes = [100.0 + i for i in range(20)]
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] + [1] * 19, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=config,
    )
    result = backtester.run(ps, ohlcv)

    for trade in result.trades:
        expected_net = trade.gross_pnl - trade.transaction_cost
        assert trade.net_pnl == pytest.approx(expected_net)


def test_equity_curve_monotonically_increasing_for_perfect_signal(
    config: Config,
) -> None:
    """Equity curve is monotonically non-decreasing for a perfect always-correct-direction signal."""
    from src.backtesting.engine import VectorizedBacktester

    closes = [100.0 + i for i in range(30)]  # strictly rising
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] + [1] * 29, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=config,
    )
    result = backtester.run(ps, ohlcv)

    diffs = result.equity_curve.diff().dropna()
    assert (diffs >= 0).all(), (
        f"Equity curve must be monotonically non-decreasing for a perfect long "
        f"signal on rising prices. Found {len(diffs[diffs < 0])} decreasing bars."
    )


def test_equity_curve_starts_at_initial_capital(config: Config) -> None:
    """equity_curve[0] == initial_capital_usd exactly, per the BacktestResult contract."""
    from src.backtesting.engine import VectorizedBacktester

    closes = [100.0 + i for i in range(10)]
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([1] * 10, index=ohlcv.index, dtype="int8")  # long from bar 0

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=config,
        initial_capital_usd=1_000_000.0,
    )
    result = backtester.run(ps, ohlcv)

    assert result.equity_curve.iloc[0] == pytest.approx(1_000_000.0), (
        "Bar 0 must always be flat (no prior signal to execute), so "
        "equity_curve[0] must equal initial_capital_usd exactly, even when "
        "position_signal[0] is nonzero."
    )


# ---------------------------------------------------------------------------
# Increment 4 — RunManager persistence tests
# ---------------------------------------------------------------------------


def test_run_manager_save_writes_all_five_files(tmp_config: Config) -> None:
    """RunManager.save() writes params.json and four Parquet files."""
    from src.backtesting.engine import VectorizedBacktester
    from src.backtesting.run_manager import RunManager

    closes = [100.0 + i for i in range(15)]
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] + [1] * 14, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=tmp_config,
    )
    result = backtester.run(ps, ohlcv)

    manager = RunManager(tmp_config)
    run_dir = manager.save(result)

    assert (run_dir / "params.json").exists()
    assert (run_dir / "trades.parquet").exists()
    assert (run_dir / "equity_curve.parquet").exists()
    assert (run_dir / "pnl_series.parquet").exists()
    assert (run_dir / "positions.parquet").exists()
    assert not (
        run_dir / "metrics.json"
    ).exists(), "metrics.json must NOT be written by Module 5 — that is Module 6's job"


def test_run_manager_load_run_round_trips(tmp_config: Config) -> None:
    """RunManager.load_run() returns data consistent with what was saved."""
    from src.backtesting.engine import VectorizedBacktester
    from src.backtesting.run_manager import RunManager

    closes = [100.0 + i for i in range(15)]
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] + [1] * 14, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=tmp_config,
    )
    result = backtester.run(ps, ohlcv)

    manager = RunManager(tmp_config)
    manager.save(result)
    loaded = manager.load_run(result.run_id)

    assert loaded["params"]["run_id"] == result.run_id
    assert len(loaded["trades"]) == len(result.trades)
    assert len(loaded["equity_curve"]) == len(result.equity_curve)
    assert loaded["equity_curve"].iloc[0] == pytest.approx(result.equity_curve.iloc[0])


def test_run_manager_list_runs_returns_saved_run(tmp_config: Config) -> None:
    """RunManager.list_runs() includes a run after it has been saved."""
    from src.backtesting.engine import VectorizedBacktester
    from src.backtesting.run_manager import RunManager

    closes = [100.0] * 10
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] * 10, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=tmp_config,
    )
    result = backtester.run(ps, ohlcv)

    manager = RunManager(tmp_config)
    manager.save(result)

    assert result.run_id in manager.list_runs()


def test_run_manager_delete_run_removes_directory(tmp_config: Config) -> None:
    """RunManager.delete_run() removes the run directory from disk."""
    from src.backtesting.engine import VectorizedBacktester
    from src.backtesting.run_manager import RunManager

    closes = [100.0] * 10
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] * 10, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=tmp_config,
    )
    result = backtester.run(ps, ohlcv)

    manager = RunManager(tmp_config)
    run_dir = manager.save(result)
    assert run_dir.exists()

    manager.delete_run(result.run_id)
    assert not run_dir.exists()
    assert result.run_id not in manager.list_runs()


# ---------------------------------------------------------------------------
# Increment 5 — Edge case tests
# ---------------------------------------------------------------------------


def test_signal_changes_every_bar_maximum_turnover(config: Config) -> None:
    """A PositionSignal that flips every bar runs without error and produces many trades."""
    from src.backtesting.engine import VectorizedBacktester

    n = 20
    closes = [100.0 + (i % 2) for i in range(n)]
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series(
        [1 if i % 2 == 0 else -1 for i in range(n)], index=ohlcv.index, dtype="int8"
    )

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=config,
    )
    result = backtester.run(ps, ohlcv)

    assert len(result.trades) > 1
    assert np.isfinite(result.equity_curve.values).all()
    assert np.isfinite(result.pnl_series.values).all()


def test_known_price_gap_does_not_crash(config: Config) -> None:
    """A large overnight price gap (simulating a roll date) does not crash the engine
    or produce non-finite PnL values. See ADR-001: roll handling is not modeled."""
    from src.backtesting.engine import VectorizedBacktester

    closes = [100.0] * 10 + [150.0] * 10  # 50% overnight gap mid-series
    ohlcv = _make_ohlcv(closes)
    ps = pd.Series([0] + [1] * 19, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test_strategy",
        signal_name="test_signal",
        config=config,
    )
    result = backtester.run(ps, ohlcv)

    assert np.isfinite(result.equity_curve.values).all()
    assert np.isfinite(result.pnl_series.values).all()
    assert len(result.trades) >= 1


def test_run_id_format_matches_spec() -> None:
    """generate_run_id() produces YYYYMMDD_HHMMSS_{strategy}_{asset} format."""
    from src.backtesting.run_manager import generate_run_id

    run_id = generate_run_id("ema_crossover", "gold")
    parts = run_id.split("_")
    assert len(parts) >= 4
    assert len(parts[0]) == 8  # YYYYMMDD
    assert len(parts[1]) == 6  # HHMMSS
    assert "ema" in run_id
    assert "gold" in run_id
