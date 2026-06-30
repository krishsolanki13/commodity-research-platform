"""Tests for signal generators and PositionSignalConstructor.

Verifies signal generation logic, look-ahead bias absence, position
signal discretization, and all four Phase 1 signal implementations.
See ADR-002 (timing convention) and ADR-007 (signal research design).
"""

from __future__ import annotations

import pandas as pd

from src.research.moving_averages import EMA
from src.research.pipeline import FeaturePipeline
from src.signal.position import PositionSignalConstructor
from src.signal.trend import EMACrossoverSignal

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
