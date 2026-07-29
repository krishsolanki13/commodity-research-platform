"""Tests for VolatilityScaledSizer correctness — EM2 engine fixes.

Tests cover:
  - TD-C: point-in-time vol uses only past data (no look-ahead)
  - TD-B: position size scales with MTM equity (not static initial capital)
  - Backward compatibility: FixedNotionalSizer unaffected
  - Golden-master: existing FixedNotional EMA test unchanged

See Architecture Known Limitations #6 (TD-B) and #7 (TD-C).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.backtesting.sizing import FixedNotionalSizer, VolatilityScaledSizer

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """Synthetic OHLCV with controlled returns for vol testing."""
    rng = np.random.default_rng(seed=seed)
    dates = pd.bdate_range("2020-01-02", periods=n, freq="B")
    returns = rng.normal(0, 0.01, n)  # 1% daily vol → ~16%/yr
    closes = 100.0 * np.cumprod(1 + returns)
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


def _make_two_regime_ohlcv(n_calm: int = 100, n_volatile: int = 100) -> pd.DataFrame:
    """OHLCV with two distinct volatility regimes for regime-sensitivity testing."""
    rng = np.random.default_rng(seed=99)
    dates = pd.bdate_range("2020-01-02", periods=n_calm + n_volatile, freq="B")
    calm_returns = rng.normal(0, 0.005, n_calm)
    volatile_returns = rng.normal(0, 0.02, n_volatile)
    all_returns = np.concatenate([calm_returns, volatile_returns])
    closes = 100.0 * np.cumprod(1 + all_returns)
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes * 1.001,
            "low": closes * 0.999,
            "close": closes,
            "volume": [25000.0] * (n_calm + n_volatile),
            "open_interest": [float("nan")] * (n_calm + n_volatile),
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )


# ── TD-C Tests: Point-in-time volatility ─────────────────────────────────────


def test_vol_sizer_configure_stores_series_not_scalar() -> None:
    """After configure(), VolatilityScaledSizer has a vol Series, not only a scalar.

    TD-C fix: rolling vol Series must be stored after configure().
    """
    sizer = VolatilityScaledSizer(target_annual_vol=0.15, lookback_days=63)
    ohlcv = _make_ohlcv(n=300)
    sizer.configure(ohlcv)

    assert hasattr(sizer, "_vol_series"), (
        "TD-C fix: VolatilityScaledSizer must store _vol_series after configure(). "
        "Previously only stored _realized_vol (scalar look-ahead estimate)."
    )
    assert isinstance(
        sizer._vol_series, pd.Series
    ), "_vol_series must be a pd.Series indexed by bar date"
    assert len(sizer._vol_series) == len(
        ohlcv
    ), "_vol_series must have same length as input OHLCV"


def test_vol_sizer_early_bars_use_only_past_data() -> None:
    """Vol estimate at bar 50 must NOT use data from bars 51+.

    This is the core TD-C look-ahead test. We compute vol at bar 50 using
    the full dataset, then compare it to vol computed using only bars 0-50.
    They should be equal (or at worst equal within floating-point tolerance).
    If the sizer used look-ahead (full-sample vol), the values would differ
    significantly on a dataset where bars 51+ have different volatility.
    """
    sizer = VolatilityScaledSizer(target_annual_vol=0.15, lookback_days=30)
    ohlcv_two_regime = _make_two_regime_ohlcv(n_calm=50, n_volatile=50)
    sizer.configure(ohlcv_two_regime)

    boundary_date = ohlcv_two_regime.index[49]
    vol_at_boundary = float(sizer._vol_series.loc[boundary_date])

    ohlcv_past_only = ohlcv_two_regime.iloc[:50]
    sizer_past = VolatilityScaledSizer(target_annual_vol=0.15, lookback_days=30)
    sizer_past.configure(ohlcv_past_only)
    vol_past_only = float(sizer_past._vol_series.iloc[-1])

    assert abs(vol_at_boundary - vol_past_only) < 1e-6, (
        f"TD-C: vol at bar 49 using full dataset ({vol_at_boundary:.6f}) "
        f"differs from vol using only past data ({vol_past_only:.6f}). "
        "Look-ahead bias detected — sizer is using future bars in vol estimate."
    )


def test_vol_sizer_position_smaller_in_high_vol_regime() -> None:
    """Positions must be smaller in the high-vol regime than in the calm regime.

    TD-C confirms the vol scaling is dynamic: a strategy targeting 15%/yr vol
    must hold smaller positions when realized vol is high.
    """
    sizer = VolatilityScaledSizer(target_annual_vol=0.15, lookback_days=30)
    ohlcv = _make_two_regime_ohlcv(n_calm=100, n_volatile=100)
    sizer.configure(ohlcv)

    equity = 1_000_000.0

    calm_date = ohlcv.index[80]
    volatile_date = ohlcv.index[180]

    # Determine how to get size at a specific date
    # Pattern A: compute_size accepts bar_date
    if "bar_date" in __import__("inspect").signature(sizer.compute_size).parameters:
        size_calm = abs(sizer.compute_size(1.0, "gold", equity, bar_date=calm_date))
        size_volatile = abs(
            sizer.compute_size(1.0, "gold", equity, bar_date=volatile_date)
        )
    # Pattern B: check vol series directly
    else:
        vol_calm = float(sizer._vol_series.loc[calm_date])
        vol_volatile = float(sizer._vol_series.loc[volatile_date])
        target_dv = equity * 0.15 / math.sqrt(252)
        size_calm = target_dv / vol_calm if vol_calm > 0 else 0
        size_volatile = target_dv / vol_volatile if vol_volatile > 0 else 0

    assert size_calm > size_volatile, (
        f"TD-C: position in calm regime ({size_calm:.0f}) must be LARGER than "
        f"in volatile regime ({size_volatile:.0f}). "
        "Vol-scaled sizing must shrink positions when volatility is high."
    )


# ── TD-B Tests: Rolling equity ────────────────────────────────────────────────


def test_vol_sizer_smaller_position_in_drawdown() -> None:
    """Position size must be smaller when equity is below initial capital.

    TD-B fix: the engine must pass rolling MTM equity, not static initial capital.
    This test verifies that compute_size() correctly scales with equity.
    """
    sizer = VolatilityScaledSizer(target_annual_vol=0.15, lookback_days=63)
    ohlcv = _make_ohlcv(n=300)
    sizer.configure(ohlcv)

    initial_equity = 1_000_000.0
    drawdown_equity = 700_000.0  # 30% drawdown

    size_full = abs(sizer.compute_size(1.0, "gold", initial_equity))
    size_drawdown = abs(sizer.compute_size(1.0, "gold", drawdown_equity))

    assert size_drawdown < size_full, (
        f"TD-B: position in drawdown ({size_drawdown:.0f}) must be SMALLER than "
        f"at full equity ({size_full:.0f}). "
        "Vol-scaled sizing must reduce positions when account is in drawdown."
    )

    expected_ratio = drawdown_equity / initial_equity
    actual_ratio = size_drawdown / size_full
    assert abs(actual_ratio - expected_ratio) < 0.01, (
        f"TD-B: size ratio ({actual_ratio:.4f}) should be approximately equal to "
        f"equity ratio ({expected_ratio:.4f}). Deviation: {abs(actual_ratio - expected_ratio):.4f}"
    )


# ── Backward compatibility ────────────────────────────────────────────────────


def test_fixed_notional_sizer_unaffected_by_em2() -> None:
    """FixedNotionalSizer behavior is identical before and after EM2 fixes.

    EM2 only modifies VolatilityScaledSizer. FixedNotionalSizer must produce
    the same notional_usd * signal for any equity level.
    """
    sizer = FixedNotionalSizer(notional_usd=100_000.0)
    ohlcv = _make_ohlcv(n=300)
    sizer.configure(ohlcv)

    assert sizer.compute_size(1.0, "gold", 1_000_000.0) == pytest.approx(100_000.0)
    assert sizer.compute_size(1.0, "gold", 700_000.0) == pytest.approx(100_000.0)
    assert sizer.compute_size(-1.0, "gold", 1_500_000.0) == pytest.approx(-100_000.0)
    assert sizer.compute_size(0.0, "gold", 1_000_000.0) == pytest.approx(0.0)
