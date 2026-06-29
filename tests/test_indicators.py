"""Tests for Phase 1 technical indicator implementations.

This file grows across Increments 2 and 3.
Increment 2: SMA and EMA tests (7 tests).
Increment 3: RSI, RVGI, and Momentum tests appended (8 more tests).
See ADR-006 for column naming convention.
"""

from __future__ import annotations

import pandas as pd

from src.research.moving_averages import EMA, SMA

# ---------------------------------------------------------------------------
# SMA tests
# ---------------------------------------------------------------------------


def test_sma_correct_values() -> None:
    """SMA(3) of [1, 2, 3, 4, 5] produces [NaN, NaN, 2.0, 3.0, 4.0]."""
    df = pd.DataFrame({"close": [1.0, 2.0, 3.0, 4.0, 5.0]})
    result = SMA(period=3).compute(df)

    assert (
        result.isna().sum() == 2
    ), f"SMA(3) must have 2 NaN values, got {result.isna().sum()}"
    expected = pd.Series([2.0, 3.0, 4.0])
    pd.testing.assert_series_equal(
        result.dropna().reset_index(drop=True),
        expected,
        check_names=False,
    )


def test_sma_column_name() -> None:
    """SMA column name follows sma_{period} convention."""
    assert SMA(period=20).column_name == "sma_20"
    assert SMA(period=50).column_name == "sma_50"


def test_sma_warmup_boundary(gold_ohlcv: pd.DataFrame) -> None:
    """SMA(5): first 4 bars NaN, bar 4 (index 4) is first valid value."""
    result = SMA(period=5).compute(gold_ohlcv)
    assert result.iloc[:4].isna().all(), "SMA(5) bars 0-3 must be NaN"
    assert not pd.isna(result.iloc[4]), "SMA(5) bar 4 must be the first valid value"


# ---------------------------------------------------------------------------
# EMA tests
# ---------------------------------------------------------------------------


def test_ema_column_name() -> None:
    """EMA column name follows ema_{period} convention."""
    assert EMA(period=50).column_name == "ema_50"
    assert EMA(period=200).column_name == "ema_200"


def test_ema_warmup_boundary(gold_ohlcv: pd.DataFrame) -> None:
    """EMA(50): bars 0-48 are NaN, bar 49 is the first valid value."""
    result = EMA(period=50).compute(gold_ohlcv)
    assert result.iloc[:49].isna().all(), (
        f"EMA(50) bars 0-48 must all be NaN. "
        f"First non-NaN at index: {result.first_valid_index()}"
    )
    assert not pd.isna(
        result.iloc[49]
    ), "EMA(50) bar 49 (50th bar) must be the first valid value"


def test_ema_200_valid_count(gold_ohlcv: pd.DataFrame) -> None:
    """EMA(200) on 252-bar fixture produces exactly 52 non-NaN values."""
    result = EMA(period=200).compute(gold_ohlcv)
    valid_count = result.notna().sum()
    assert (
        valid_count == 53
    ), f"EMA(200) on 252 bars must have 53 valid values (252 - 199), got {valid_count}"


def test_ema_values_are_positive(gold_ohlcv: pd.DataFrame) -> None:
    """EMA(50) non-NaN values are strictly positive (prices are positive)."""
    result = EMA(period=50).compute(gold_ohlcv)
    valid = result.dropna()
    assert (valid > 0).all(), "EMA values must be positive for positive price series"
