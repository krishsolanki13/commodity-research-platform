"""Breakout signal generator: Donchian Channel Breakout.

Reads OHLCV columns directly from FeatureFrame.data.
No pre-computed indicator columns required — uses raw high/low/close.
See ADR-007.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.signal.base import SignalGenerator


class DonchianBreakoutSignal(SignalGenerator):
    """Trend-following breakout signal based on Donchian channel position.

    Channel is computed from the previous period's high/low to avoid look-ahead:
        upper[t] = max(high[t-period : t-1])   (shift(1) applied)
        lower[t] = min(low[t-period : t-1])    (shift(1) applied)

    RawSignal[t] = (close[t] - midpoint[t]) / channel_width[t]
        - Values near +0.5: close near upper band (bullish)
        - Values near -0.5: close near lower band (bearish)
        - Bounded approximately in [-0.5, +0.5]

    Requires FeatureFrame.data to contain: open, high, low, close columns.
    These are always present in FeatureFrame.data (inherited from NormalizedOHLCV).
    No pre-computed indicator columns required.
    See ADR-007.
    """

    def __init__(self, channel_period: int = 20) -> None:
        """Initialise DonchianBreakoutSignal.

        Args:
            channel_period: Lookback period for channel computation.
                Default 20 per strategies.yaml.
        """
        self._channel_period = channel_period
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Return signal identifier: donchian_breakout_{period}."""
        return f"donchian_breakout_{self._channel_period}"

    def generate(self, feature_frame: Any) -> pd.Series:
        """Generate Donchian channel position RawSignal from FeatureFrame.

        Uses shift(1) on channel computation to ensure signal[t] uses only
        data from bars [t-period, t-1], satisfying the no-look-ahead constraint
        per ADR-002.

        Args:
            feature_frame: FeatureFrame instance. Must have high, low, close columns.

        Returns:
            RawSignal pd.Series approximately bounded in [-0.5, +0.5].

        Raises:
            KeyError: If high, low, or close columns absent from feature_frame.data.
        """
        df = feature_frame.data

        for col in ("high", "low", "close"):
            if col not in df.columns:
                raise KeyError(
                    f"DonchianBreakoutSignal requires '{col}' in FeatureFrame.data. "
                    f"Available columns: {list(df.columns)}"
                )

        # Use previous period's channel (shift(1)) to avoid look-ahead per ADR-002
        upper = df["high"].rolling(window=self._channel_period).max().shift(1)
        lower = df["low"].rolling(window=self._channel_period).min().shift(1)
        midpoint = (upper + lower) / 2.0
        channel_width = upper - lower

        raw_signal = (df["close"] - midpoint) / (channel_width + 1e-10)
        raw_signal.name = self.name

        self._logger.debug(
            "DonchianBreakoutSignal: generated signal '%s' — %d valid bars",
            self.name,
            raw_signal.notna().sum(),
        )
        return raw_signal
