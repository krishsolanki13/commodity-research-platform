"""Momentum indicator: close[t] / close[t - lookback] - 1.

Column naming: momentum_{lookback}. See ADR-006.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.research.base import Indicator


class Momentum(Indicator):
    """Rate-of-change momentum indicator.

    Formula: close[t] / close[t - lookback] - 1
    Returns fractional returns (not percentage).
    Warmup: first lookback bars are NaN.
    column_name: momentum_{lookback}
    """

    def __init__(self, lookback: int) -> None:
        """Initialise Momentum.

        Args:
            lookback: Number of bars to look back for the base price.
        """
        self._lookback = lookback

    @property
    def column_name(self) -> str:
        """Return Momentum column name: momentum_{lookback}."""
        return f"momentum_{self._lookback}"

    @property
    def parameters(self) -> dict[str, Any]:
        """Return Momentum parameters."""
        return {"lookback": self._lookback}

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute momentum as close[t] / close[t - lookback] - 1.

        Args:
            df: DataFrame with a "close" column.

        Returns:
            pd.Series of fractional returns. NaN for first lookback bars.
        """
        result = df["close"] / df["close"].shift(self._lookback) - 1.0
        result.name = self.column_name
        return result
