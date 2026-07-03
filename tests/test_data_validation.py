"""Tests for OHLCVValidator and DataValidationError.

Verifies structural OHLC validation, gap detection, and anomaly flagging.
All tests construct DataFrames directly without reading any CSV file.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.validator import DataValidationError, OHLCVValidator, ValidationResult


def _make_valid_ohlcv(n_rows: int = 5) -> pd.DataFrame:
    """Helper: create a minimal valid OHLCV DataFrame with n_rows rows.

    All rows satisfy OHLC invariants:
        open=1900, high=1920, low=1880, close=1910, volume=25000
    """
    dates = pd.bdate_range(start="2023-01-02", periods=n_rows, freq="B")
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "open": [1900.0] * n_rows,
            "high": [1920.0] * n_rows,
            "low": [1880.0] * n_rows,
            "close": [1910.0] * n_rows,
            "volume": [25000] * n_rows,
        }
    )


def test_ohlc_high_below_low_raises_data_validation_error() -> None:
    """DataValidationError raised (not ValueError) when high < low."""
    df = _make_valid_ohlcv(3)
    df.loc[1, "high"] = 1860.0  # high (1860) < low (1880)

    with pytest.raises(DataValidationError) as exc_info:
        OHLCVValidator("gold", strict_ohlc=True).validate(df)

    # Error message must mention the violation
    assert "high" in str(exc_info.value).lower() or "low" in str(exc_info.value).lower()


def test_ohlc_close_above_high_raises_data_validation_error() -> None:
    """DataValidationError raised when close > high."""
    df = _make_valid_ohlcv(3)
    df.loc[0, "close"] = 1950.0  # close (1950) > high (1920)

    with pytest.raises(DataValidationError):
        OHLCVValidator("gold", strict_ohlc=True).validate(df)


def test_ohlc_close_below_low_raises_data_validation_error() -> None:
    """DataValidationError raised when close < low."""
    df = _make_valid_ohlcv(3)
    df.loc[2, "close"] = 1800.0  # close (1800) < low (1880)

    with pytest.raises(DataValidationError):
        OHLCVValidator("gold", strict_ohlc=True).validate(df)


def test_ohlc_zero_or_negative_close_raises_data_validation_error() -> None:
    """DataValidationError raised when close is zero or negative."""
    # Case 1: close = 0
    df_zero = _make_valid_ohlcv(3)
    df_zero.loc[0, "close"] = 0.0
    df_zero.loc[0, "low"] = 0.0
    df_zero.loc[0, "high"] = 0.01
    df_zero.loc[0, "open"] = 0.005

    with pytest.raises(DataValidationError):
        OHLCVValidator("gold", strict_ohlc=True).validate(df_zero)

    # Case 2: close < 0
    df_neg = _make_valid_ohlcv(3)
    df_neg.loc[1, "close"] = -1.0
    df_neg.loc[1, "low"] = -2.0
    df_neg.loc[1, "high"] = 0.5
    df_neg.loc[1, "open"] = -0.5

    with pytest.raises(DataValidationError):
        OHLCVValidator("gold", strict_ohlc=True).validate(df_neg)


def test_valid_data_passes_validation(gold_ohlcv: pd.DataFrame) -> None:
    """Valid OHLCV data from the test fixture passes validation without raising."""
    # gold_ohlcv has a DatetimeIndex — reset it to expose the date as a column
    df = gold_ohlcv.reset_index()

    result = OHLCVValidator("gold", strict_ohlc=True).validate(df)

    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert result.errors == []
    assert result.asset == "gold"
    assert result.row_count == 252


def test_gap_detection_returns_warnings_not_error() -> None:
    """Gap detection produces warnings but does not raise DataValidationError."""
    # 2023-01-04 is a business day — intentionally absent
    dates = ["2023-01-02", "2023-01-03", "2023-01-05"]
    df = pd.DataFrame(
        {
            "date": dates,
            "open": [1900.0, 1902.0, 1898.0],
            "high": [1920.0, 1922.0, 1918.0],
            "low": [1880.0, 1882.0, 1878.0],
            "close": [1910.0, 1912.0, 1908.0],
            "volume": [25000, 26000, 24000],
        }
    )

    # Must NOT raise
    result = OHLCVValidator("gold", strict_ohlc=True).validate(df)

    assert result.is_valid is True
    assert len(result.warnings) >= 1
    assert any("2023-01-04" in w for w in result.warnings)


def test_zero_volume_returns_warning_not_error() -> None:
    """Zero volume produces a logged warning but does not raise DataValidationError."""
    df = _make_valid_ohlcv(5)
    df.loc[2, "volume"] = 0  # zero volume on one row

    # Must NOT raise
    result = OHLCVValidator("gold", strict_ohlc=True).validate(df)

    assert result.is_valid is True
    assert any("volume" in w.lower() for w in result.warnings)
