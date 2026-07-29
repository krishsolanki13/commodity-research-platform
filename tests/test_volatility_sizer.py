"""Tests for Module 11: Volatility Scaled Sizer.

Tests VolatilityScaledSizer, the PositionSizer.configure() protocol, and
VectorizedBacktester integration with the new sizer.

See ADR-005 (position sizing strategy) and Architecture Section 12
(PositionSizer interface).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.backtesting.engine import VectorizedBacktester
from src.backtesting.sizing import FixedNotionalSizer, VolatilityScaledSizer
from src.core.config import Config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv_with_vol(
    n: int, daily_vol: float, base_close: float = 100.0
) -> pd.DataFrame:
    """Build a synthetic OHLCV DataFrame with specified daily return volatility."""
    rng = np.random.default_rng(seed=42)
    returns = rng.normal(loc=0.0, scale=daily_vol, size=n)
    closes = base_close * np.cumprod(1 + returns)
    dates = pd.bdate_range(start="2023-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": closes * 0.999,
            "high": closes * 1.001,
            "low": closes * 0.999,
            "close": closes,
            "volume": [25000.0] * n,
            "open_interest": [float("nan")] * n,
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )


def _make_position_signal(n: int, ohlcv: pd.DataFrame) -> pd.Series:
    """Build a simple all-long position signal for backtester integration tests."""
    return pd.Series([0] + [1] * (n - 1), index=ohlcv.index, dtype="int8")


# ---------------------------------------------------------------------------
# PositionSizer ABC configure() protocol (2 tests)
# ---------------------------------------------------------------------------


def test_position_sizer_configure_default_noop() -> None:
    """PositionSizer.configure() default implementation is a no-op.

    FixedNotionalSizer inherits the no-op — calling configure() must not
    raise and must not change sizer behavior.
    """
    sizer = FixedNotionalSizer(notional_usd=100_000.0)
    ohlcv = _make_ohlcv_with_vol(30, daily_vol=0.01)

    sizer.configure(ohlcv)

    result = sizer.compute_size(1.0, "gold", 1_000_000.0)
    assert result == pytest.approx(100_000.0)


def test_fixed_notional_sizer_still_works_with_configure_protocol() -> None:
    """FixedNotionalSizer works correctly through the configure protocol."""
    sizer = FixedNotionalSizer(notional_usd=50_000.0)
    ohlcv = _make_ohlcv_with_vol(100, daily_vol=0.02)
    sizer.configure(ohlcv)

    assert sizer.compute_size(1.0, "gold", 1_000_000.0) == pytest.approx(50_000.0)
    assert sizer.compute_size(-1.0, "gold", 1_000_000.0) == pytest.approx(-50_000.0)


# ---------------------------------------------------------------------------
# VolatilityScaledSizer initialization and properties (2 tests)
# ---------------------------------------------------------------------------


def test_volatility_scaled_sizer_default_parameters() -> None:
    """VolatilityScaledSizer default parameters match documented values."""
    sizer = VolatilityScaledSizer()

    assert sizer.target_annual_vol == pytest.approx(0.01)
    assert sizer.lookback_days == 63
    assert not sizer.is_configured
    assert math.isnan(sizer.realized_vol)


def test_volatility_scaled_sizer_configure_populates_realized_vol() -> None:
    """configure() populates realized_vol from OHLCV data."""
    sizer = VolatilityScaledSizer(lookback_days=20)
    ohlcv = _make_ohlcv_with_vol(n=30, daily_vol=0.01)

    sizer.configure(ohlcv)

    assert sizer.is_configured
    assert not math.isnan(sizer.realized_vol)
    assert sizer.realized_vol > 0.0
    assert sizer.realized_vol <= 0.50


# ---------------------------------------------------------------------------
# compute_realized_vol() correctness (3 tests)
# ---------------------------------------------------------------------------


def test_compute_realized_vol_annualizes_correctly() -> None:
    """compute_realized_vol produces annualized vol from daily returns."""
    target_daily_vol = 0.01
    sizer = VolatilityScaledSizer(lookback_days=60, vol_cap=1.0)
    ohlcv = _make_ohlcv_with_vol(n=100, daily_vol=target_daily_vol)

    vol = sizer.compute_realized_vol(ohlcv)

    expected_annual = target_daily_vol * math.sqrt(252)
    assert vol == pytest.approx(expected_annual, rel=0.30)


def test_compute_realized_vol_caps_at_vol_cap() -> None:
    """compute_realized_vol caps the result at vol_cap."""
    sizer = VolatilityScaledSizer(lookback_days=20, vol_cap=0.50)
    high_vol_ohlcv = _make_ohlcv_with_vol(n=50, daily_vol=0.05)

    vol = sizer.compute_realized_vol(high_vol_ohlcv)

    assert vol == pytest.approx(0.50)


def test_compute_realized_vol_nan_for_insufficient_data() -> None:
    """compute_realized_vol returns NaN when fewer than lookback_days bars."""
    sizer = VolatilityScaledSizer(lookback_days=63)
    short_ohlcv = _make_ohlcv_with_vol(n=30, daily_vol=0.01)

    vol = sizer.compute_realized_vol(short_ohlcv)

    assert math.isnan(vol)


# ---------------------------------------------------------------------------
# size() correctness (4 tests)
# ---------------------------------------------------------------------------


def test_size_zero_before_configure_called() -> None:
    """size() returns 0.0 if configure() has not been called."""
    sizer = VolatilityScaledSizer()

    result = sizer.size(signal=1.0, current_equity=1_000_000.0)
    assert result == pytest.approx(0.0)


def test_size_zero_for_flat_signal() -> None:
    """size() returns 0.0 for flat (zero) signal regardless of configuration."""
    sizer = VolatilityScaledSizer(lookback_days=20)
    ohlcv = _make_ohlcv_with_vol(n=50, daily_vol=0.01)
    sizer.configure(ohlcv)

    result = sizer.size(signal=0.0, current_equity=1_000_000.0)
    assert result == pytest.approx(0.0)


def test_size_scales_inversely_with_volatility() -> None:
    """Higher volatility produces smaller position size for same target vol."""
    sizer = VolatilityScaledSizer(lookback_days=30, vol_cap=1.0, target_annual_vol=0.01)
    equity = 1_000_000.0

    low_vol_ohlcv = _make_ohlcv_with_vol(n=60, daily_vol=0.005)
    sizer.configure(low_vol_ohlcv)
    size_low_vol = sizer.size(signal=1.0, current_equity=equity)

    high_vol_ohlcv = _make_ohlcv_with_vol(n=60, daily_vol=0.02)
    sizer.configure(high_vol_ohlcv)
    size_high_vol = sizer.size(signal=1.0, current_equity=equity)

    assert size_low_vol > size_high_vol


def test_size_respects_max_notional() -> None:
    """size() does not exceed max_notional even with very low realized vol."""
    max_cap = 200_000.0
    sizer = VolatilityScaledSizer(
        lookback_days=20, target_annual_vol=0.01, max_notional=max_cap, vol_cap=1.0
    )
    tiny_vol_ohlcv = _make_ohlcv_with_vol(n=40, daily_vol=0.0001)
    sizer.configure(tiny_vol_ohlcv)

    result = sizer.size(signal=1.0, current_equity=10_000_000.0)

    assert result <= max_cap


# ---------------------------------------------------------------------------
# VectorizedBacktester integration (4 tests)
# ---------------------------------------------------------------------------


class _ConfiguredTracker(VolatilityScaledSizer):
    """Subclass that tracks whether configure() was called before compute_size()."""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.configure_calls: int = 0
        self.compute_size_calls: int = 0

    def configure(self, ohlcv: pd.DataFrame) -> None:
        self.configure_calls += 1
        super().configure(ohlcv)

    def compute_size(
        self,
        signal: float,
        asset: str,
        equity: float,
        bar_date: object = None,
    ) -> float:
        self.compute_size_calls += 1
        return super().compute_size(signal, asset, equity, bar_date=bar_date)


def test_backtester_calls_configure_before_simulation(
    config: Config, gold_ohlcv: pd.DataFrame
) -> None:
    """VectorizedBacktester.run() calls sizer.configure() before compute_size()."""
    tracker = _ConfiguredTracker(target_annual_vol=0.01, lookback_days=30)
    ps = _make_position_signal(len(gold_ohlcv), gold_ohlcv)

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test",
        signal_name="test",
        config=config,
        sizer=tracker,
    )
    backtester.run(ps, gold_ohlcv)

    assert tracker.configure_calls == 1
    assert tracker.compute_size_calls > 0
    assert tracker.configure_calls <= tracker.compute_size_calls


def test_backtester_with_vol_sizer_produces_valid_result(
    config: Config, gold_ohlcv: pd.DataFrame
) -> None:
    """VectorizedBacktester.run() with VolatilityScaledSizer returns valid BacktestResult."""
    from src.core.types import BacktestResult

    sizer = VolatilityScaledSizer(target_annual_vol=0.01, lookback_days=30)
    ps = _make_position_signal(len(gold_ohlcv), gold_ohlcv)

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="vol_scaled",
        signal_name="test",
        config=config,
        sizer=sizer,
    )
    result = backtester.run(ps, gold_ohlcv)

    assert isinstance(result, BacktestResult)
    assert len(result.equity_curve) == len(gold_ohlcv)
    assert result.equity_curve.notna().all()
    assert (result.equity_curve > 0).all()


def test_backtester_vol_sizer_positions_differ_from_fixed_notional(
    config: Config, gold_ohlcv: pd.DataFrame
) -> None:
    """VolatilityScaledSizer produces different position sizes than FixedNotionalSizer."""
    ps = _make_position_signal(len(gold_ohlcv), gold_ohlcv)

    backtester_fixed = VectorizedBacktester(
        asset="gold",
        strategy_name="fixed",
        signal_name="test",
        config=config,
        sizer=FixedNotionalSizer(notional_usd=100_000.0),
    )
    result_fixed = backtester_fixed.run(ps, gold_ohlcv)

    backtester_vol = VectorizedBacktester(
        asset="gold",
        strategy_name="vol_scaled",
        signal_name="test",
        config=config,
        sizer=VolatilityScaledSizer(target_annual_vol=0.01, lookback_days=30),
    )
    result_vol = backtester_vol.run(ps, gold_ohlcv)

    assert len(result_fixed.positions) == len(result_vol.positions)
    positions_differ = not (result_fixed.positions == result_vol.positions).all()
    assert positions_differ


def test_backtester_sizer_none_uses_default_fixed_notional(
    config: Config, gold_ohlcv: pd.DataFrame
) -> None:
    """VectorizedBacktester with sizer=None uses FixedNotionalSizer (backward compatibility)."""
    from src.core.types import BacktestResult

    ps = _make_position_signal(len(gold_ohlcv), gold_ohlcv)

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="default",
        signal_name="test",
        config=config,
    )
    result = backtester.run(ps, gold_ohlcv)

    assert isinstance(result, BacktestResult)
    assert isinstance(backtester._sizer, FixedNotionalSizer)


# ---------------------------------------------------------------------------
# Economic property test
# ---------------------------------------------------------------------------


def test_higher_vol_asset_gets_smaller_position_than_lower_vol() -> None:
    """Verifies the core economic property: higher vol asset → smaller position."""
    equity = 1_000_000.0
    target_vol = 0.01

    gold_sizer = VolatilityScaledSizer(
        target_annual_vol=target_vol, lookback_days=30, vol_cap=1.0
    )
    gold_ohlcv = _make_ohlcv_with_vol(n=50, daily_vol=0.01)
    gold_sizer.configure(gold_ohlcv)
    gold_position = gold_sizer.size(1.0, equity)

    ng_sizer = VolatilityScaledSizer(
        target_annual_vol=target_vol, lookback_days=30, vol_cap=1.0
    )
    ng_ohlcv = _make_ohlcv_with_vol(n=50, daily_vol=0.04)
    ng_sizer.configure(ng_ohlcv)
    ng_position = ng_sizer.size(1.0, equity)

    assert gold_position > ng_position

    gold_vol_contribution = gold_sizer.realized_vol * gold_position / equity
    ng_vol_contribution = ng_sizer.realized_vol * ng_position / equity
    assert gold_vol_contribution == pytest.approx(ng_vol_contribution, rel=0.05)
