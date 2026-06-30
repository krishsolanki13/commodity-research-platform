"""Tests for signal generators and PositionSignalConstructor.

Verifies signal generation logic, look-ahead bias absence, position
signal discretization, and all four Phase 1 signal implementations.
See ADR-002 (timing convention) and ADR-007 (signal research design).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.research.momentum import Momentum
from src.research.moving_averages import EMA
from src.research.oscillators import RSI
from src.research.pipeline import FeaturePipeline
from src.signal.breakout import DonchianBreakoutSignal
from src.signal.position import PositionSignalConstructor
from src.signal.reversion import RSIReversionSignal
from src.signal.trend import EMACrossoverSignal, MomentumSignal

# ---------------------------------------------------------------------------
# EMA Crossover signal tests
# ---------------------------------------------------------------------------


def test_ema_crossover_positive_when_fast_above_slow(gold_ohlcv: pd.DataFrame) -> None:
    """EMACrossoverSignal: raw signal is positive where fast EMA > slow EMA."""
    pipeline = FeaturePipeline([EMA(10), EMA(50)])
    ff = pipeline.compute(gold_ohlcv, asset="gold")
    signal_gen = EMACrossoverSignal(fast_period=10, slow_period=50)
    raw = signal_gen.generate(ff)

    fast = ff.data["ema_10"]
    slow = ff.data["ema_50"]
    both_valid = fast.notna() & slow.notna() & raw.notna()

    positive_where_fast_above = raw[both_valid & (fast > slow)]
    assert (
        positive_where_fast_above > 0
    ).all(), "Raw signal must be positive wherever fast EMA > slow EMA"


def test_ema_crossover_negative_when_fast_below_slow(gold_ohlcv: pd.DataFrame) -> None:
    """EMACrossoverSignal: raw signal is negative where fast EMA < slow EMA."""
    pipeline = FeaturePipeline([EMA(10), EMA(50)])
    ff = pipeline.compute(gold_ohlcv, asset="gold")
    signal_gen = EMACrossoverSignal(fast_period=10, slow_period=50)
    raw = signal_gen.generate(ff)

    fast = ff.data["ema_10"]
    slow = ff.data["ema_50"]
    both_valid = fast.notna() & slow.notna() & raw.notna()

    negative_where_fast_below = raw[both_valid & (fast < slow)]
    assert (
        negative_where_fast_below < 0
    ).all(), "Raw signal must be negative wherever fast EMA < slow EMA"


def test_no_look_ahead_bias_ema_crossover(gold_ohlcv: pd.DataFrame) -> None:
    """Signal at bar t is unchanged when future bars are removed (ADR-002)."""
    pipeline = FeaturePipeline([EMA(10), EMA(50)])
    signal_gen = EMACrossoverSignal(fast_period=10, slow_period=50)

    # Full series signal
    ff_full = pipeline.compute(gold_ohlcv, asset="gold")
    raw_full = signal_gen.generate(ff_full)

    # Truncated to first 100 bars
    ohlcv_trunc = gold_ohlcv.iloc[:100].copy()
    ff_trunc = pipeline.compute(ohlcv_trunc, asset="gold")
    raw_trunc = signal_gen.generate(ff_trunc)

    # Signal at bar 90 must be identical in both series
    test_bar = 90
    assert abs(raw_full.iloc[test_bar] - raw_trunc.iloc[test_bar]) < 1e-10, (
        f"Signal at bar {test_bar} changed when future rows removed — look-ahead bias detected. "
        f"Full: {raw_full.iloc[test_bar]:.10f}, Truncated: {raw_trunc.iloc[test_bar]:.10f}"
    )


def test_position_signal_values_restricted(gold_ohlcv: pd.DataFrame) -> None:
    """PositionSignalConstructor output contains only values from {-1, 0, +1}."""
    pipeline = FeaturePipeline([EMA(10), EMA(50)])
    ff = pipeline.compute(gold_ohlcv, asset="gold")
    signal_gen = EMACrossoverSignal(fast_period=10, slow_period=50)
    raw = signal_gen.generate(ff)

    constructor = PositionSignalConstructor()
    position = constructor.build(raw, threshold=0.0)

    actual_values = set(position.dropna().unique())
    valid_values = {-1, 0, 1}
    assert actual_values.issubset(
        valid_values
    ), f"PositionSignal contains invalid values: {actual_values - valid_values}"
    assert (
        position.dtype == "int8"
    ), f"PositionSignal dtype must be int8, got {position.dtype}"


# ---------------------------------------------------------------------------
# PositionSignalConstructor threshold test
# ---------------------------------------------------------------------------


def test_position_signal_threshold_flat_zone(gold_ohlcv: pd.DataFrame) -> None:
    """Threshold creates a flat zone: |raw| < threshold → 0 (flat)."""
    raw = pd.Series(
        [0.05, -0.05, 0.50, -0.50, 0.00],
        index=gold_ohlcv.index[:5],
        name="test_threshold",
    )
    constructor = PositionSignalConstructor()
    position = constructor.build(raw, threshold=0.1)

    assert position.iloc[0] == 0, "0.05 < threshold 0.10 → flat"
    assert position.iloc[1] == 0, "-0.05 within threshold 0.10 → flat"
    assert position.iloc[2] == 1, "0.50 > threshold 0.10 → long"
    assert position.iloc[3] == -1, "-0.50 < -threshold -0.10 → short"
    assert position.iloc[4] == 0, "0.00 within threshold → flat"


# ---------------------------------------------------------------------------
# MomentumSignal test
# ---------------------------------------------------------------------------


def test_momentum_signal_produces_valid_output(gold_ohlcv: pd.DataFrame) -> None:
    """MomentumSignal generates a non-empty Series with correct name and index."""
    pipeline = FeaturePipeline([Momentum(lookback=20)])
    ff = pipeline.compute(gold_ohlcv, asset="gold")

    signal_gen = MomentumSignal(lookback=20, z_score_window=0)
    raw = signal_gen.generate(ff)

    assert isinstance(raw, pd.Series), f"Expected pd.Series, got {type(raw)}"
    assert (
        len(raw.dropna()) > 0
    ), "MomentumSignal must produce at least some non-NaN values"
    assert raw.name == "momentum_20", f"Expected name 'momentum_20', got '{raw.name}'"
    assert raw.index.equals(
        gold_ohlcv.index
    ), "Signal index must match FeatureFrame index"


# ---------------------------------------------------------------------------
# RSIReversionSignal test
# ---------------------------------------------------------------------------


def test_rsi_reversion_inversely_correlated_with_rsi(gold_ohlcv: pd.DataFrame) -> None:
    """RSIReversionSignal is strongly negatively correlated with RSI (mean-reversion)."""
    pipeline = FeaturePipeline([RSI(period=14)])
    ff = pipeline.compute(gold_ohlcv, asset="gold")

    signal_gen = RSIReversionSignal(period=14)
    raw = signal_gen.generate(ff)

    rsi_values = ff.data["rsi_14"]
    valid = rsi_values.notna() & raw.notna()

    correlation = float(rsi_values[valid].corr(raw[valid]))
    assert correlation < -0.9, (
        f"RSI reversion signal should be strongly negatively correlated with RSI "
        f"(mean-reversion logic). Got correlation: {correlation:.4f}"
    )


# ---------------------------------------------------------------------------
# DonchianBreakoutSignal test
# ---------------------------------------------------------------------------


def test_donchian_breakout_produces_finite_values(gold_ohlcv: pd.DataFrame) -> None:
    """DonchianBreakoutSignal produces finite non-NaN values on 252-bar fixture."""
    pipeline = FeaturePipeline([])
    ff = pipeline.compute(gold_ohlcv, asset="gold")

    signal_gen = DonchianBreakoutSignal(channel_period=20)
    raw = signal_gen.generate(ff)

    valid = raw.dropna()
    assert len(valid) > 0, "DonchianBreakoutSignal must produce some non-NaN values"
    assert np.isfinite(valid.values).all(), "All Donchian signal values must be finite"
    assert (
        raw.name == "donchian_breakout_20"
    ), f"Expected name 'donchian_breakout_20', got '{raw.name}'"
