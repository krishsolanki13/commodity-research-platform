"""Simple Moving Average and Exponential Moving Average implementations.

Column naming: sma_{period}, ema_{period}. See ADR-006.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.research.base import Indicator


class SMA(Indicator):
    """Simple Moving Average of the close price.

    Uses rolling(window=period, min_periods=period).mean().
    Warmup: first (period - 1) values are NaN.
    column_name: sma_{period}
    """

    def __init__(self, period: int) -> None:
        """Initialise SMA with rolling window size.

        Args:
            period: Rolling window size in bars.
        """
        self._period = period

    @property
    def column_name(self) -> str:
        """Return column name: sma_{period}."""
        return f"sma_{self._period}"

    @property
    def parameters(self) -> dict[str, Any]:
        """Return SMA parameters for FeatureSpec serialization."""
        return {"period": self._period}

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute SMA over df["close"].

        Args:
            df: DataFrame with a "close" column.

        Returns:
            pd.Series. NaN for first (period - 1) bars, then rolling mean.
        """
        result = (
            df["close"].rolling(window=self._period, min_periods=self._period).mean()
        )
        result.name = self.column_name
        return result


class EMA(Indicator):
    """Exponential Moving Average of the close price.

    Uses ewm(span=period, min_periods=period, adjust=False).mean().
    min_periods enforces NaN in the warmup period matching SMA behaviour.
    Warmup: first (period - 1) values are NaN. First valid at bar {period}.
    column_name: ema_{period}
    """

    def __init__(self, period: int) -> None:
        """Initialise EMA with span.

        Args:
            period: EMA span. alpha = 2 / (period + 1).
        """
        self._period = period

    @property
    def column_name(self) -> str:
        """Return column name: ema_{period}."""
        return f"ema_{self._period}"

    @property
    def parameters(self) -> dict[str, Any]:
        """Return EMA parameters for FeatureSpec serialization."""
        return {"period": self._period}

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute EMA over df["close"].

        CRITICAL: Uses min_periods=period to produce NaN in warmup period.
        Without min_periods, ewm produces values from bar 1 (no NaN warmup).

        Args:
            df: DataFrame with a "close" column.

        Returns:
            pd.Series. NaN for first (period - 1) bars. First valid at bar period.
        """
        result = (
            df["close"]
            .ewm(
                span=self._period,
                min_periods=self._period,
                adjust=False,
            )
            .mean()
        )
        result.name = self.column_name
        return result
