"""RSI and RVGI oscillator indicator implementations.

RSI: Relative Strength Index using Wilder's exponential smoothing (com = period - 1).
RVGI: Relative Vigor Index using symmetrically weighted 4-bar moving average.
Column naming: rsi_{period}, rvgi_{period}. See ADR-006.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.research.base import Indicator


class RSI(Indicator):
    """Relative Strength Index using Wilder's exponential smoothing.

    Uses ewm(com=period-1, ...) which sets alpha=1/period — Wilder's definition.
    Note: com=period-1 is NOT the same as span=period (span gives alpha=2/(period+1)).
    RSI values are bounded in [0, 100].
    column_name: rsi_{period}
    """

    def __init__(self, period: int = 14) -> None:
        """Initialise RSI.

        Args:
            period: Smoothing period. Default 14 per Wilder's specification.
        """
        self._period = period

    @property
    def column_name(self) -> str:
        """Return RSI column name: rsi_{period}."""
        return f"rsi_{self._period}"

    @property
    def parameters(self) -> dict[str, Any]:
        """Return RSI parameters."""
        return {"period": self._period}

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute RSI using Wilder's smoothing.

        Algorithm:
            1. delta = close.diff()
            2. gain = delta.clip(lower=0)
            3. loss = (-delta).clip(lower=0)
            4. avg_gain = gain.ewm(com=period-1, min_periods=period, adjust=False).mean()
            5. avg_loss = loss.ewm(com=period-1, min_periods=period, adjust=False).mean()
            6. RS = avg_gain / avg_loss
            7. RSI = 100 - (100 / (1 + RS))

        Args:
            df: DataFrame with a "close" column.

        Returns:
            pd.Series bounded in [0, 100]. NaN in warmup period.
        """
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.ewm(
            com=self._period - 1,
            min_periods=self._period,
            adjust=False,
        ).mean()
        avg_loss = loss.ewm(
            com=self._period - 1,
            min_periods=self._period,
            adjust=False,
        ).mean()

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi.name = self.column_name
        return rsi


class RVGI(Indicator):
    """Relative Vigor Index.

    RVGI = rolling_sum(swma(close - open)) / rolling_sum(swma(high - low))

    swma applies a 4-bar symmetrically weighted average with weights [1, 2, 2, 1] / 6.
    The rolling_sum uses window=period.
    column_name: rvgi_{period}
    """

    def __init__(self, period: int = 10) -> None:
        """Initialise RVGI.

        Args:
            period: Rolling window size for summing SWMA values.
        """
        self._period = period

    @property
    def column_name(self) -> str:
        """Return RVGI column name: rvgi_{period}."""
        return f"rvgi_{self._period}"

    @property
    def parameters(self) -> dict[str, Any]:
        """Return RVGI parameters."""
        return {"period": self._period}

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute RVGI from OHLC data.

        Requires open, high, low, close columns.

        Args:
            df: DataFrame with open, high, low, close columns.

        Returns:
            pd.Series. NaN in warmup period (first period + 3 bars).
        """
        co = df["close"] - df["open"]
        hl = df["high"] - df["low"]

        num_swma = self._swma(co)
        den_swma = self._swma(hl)

        rvgi_num = num_swma.rolling(window=self._period).sum()
        rvgi_den = den_swma.rolling(window=self._period).sum()

        result = rvgi_num / rvgi_den
        result.name = self.column_name
        return result

    @staticmethod
    def _swma(series: pd.Series) -> pd.Series:
        """Apply symmetrically weighted 4-bar moving average.

        Weights: [1, 2, 2, 1] / 6 applied to [t, t-1, t-2, t-3].
        """
        return (
            series + 2.0 * series.shift(1) + 2.0 * series.shift(2) + series.shift(3)
        ) / 6.0
