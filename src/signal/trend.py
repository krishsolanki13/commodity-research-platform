"""Trend-following signal generators: EMA Crossover and Momentum.

Both generators read from pre-computed indicator columns in the FeatureFrame.
The FeaturePipeline must be run with the appropriate indicators before
calling generate(). See ADR-007 and Architecture Section 10.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.research.momentum import Momentum
from src.research.moving_averages import EMA
from src.signal.base import SignalGenerator


class EMACrossoverSignal(SignalGenerator):
    """Trend-following signal based on EMA fast/slow crossover.

    RawSignal = EMA(fast) - EMA(slow). Positive when trend is up.
    PositionSignal: +1 when fast > slow, -1 when fast < slow.

    Requires FeatureFrame to contain columns:
        ema_{fast_period}  (e.g., "ema_50")
        ema_{slow_period}  (e.g., "ema_200")

    Build FeatureFrame with FeaturePipeline([EMA(fast), EMA(slow)]) first.
    See ADR-007.
    """

    def __init__(self, fast_period: int = 50, slow_period: int = 200) -> None:
        """Initialise EMACrossoverSignal.

        Args:
            fast_period: Fast EMA period. Default 50 per strategies.yaml.
            slow_period: Slow EMA period. Default 200 per strategies.yaml.
        """
        if fast_period >= slow_period:
            raise ValueError(
                f"fast_period ({fast_period}) must be less than slow_period ({slow_period})"
            )
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._fast_col = EMA(period=fast_period).column_name
        self._slow_col = EMA(period=slow_period).column_name
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Return signal identifier: ema_crossover_{fast}_{slow}."""
        return f"ema_crossover_{self._fast_period}_{self._slow_period}"

    def generate(self, feature_frame: Any) -> pd.Series:
        """Generate EMA crossover RawSignal from FeatureFrame.

        RawSignal[t] = EMA(fast)[t] - EMA(slow)[t]

        No look-ahead bias: both EMAs at t use only close prices up to t.

        Args:
            feature_frame: FeatureFrame instance with ema_fast and ema_slow columns.

        Returns:
            RawSignal pd.Series (unbounded float). Positive = bullish, negative = bearish.

        Raises:
            KeyError: If required EMA columns are not in feature_frame.data.
        """
        df = feature_frame.data

        for col in (self._fast_col, self._slow_col):
            if col not in df.columns:
                raise KeyError(
                    f"EMACrossoverSignal requires column '{col}' in FeatureFrame. "
                    f"Build FeatureFrame with FeaturePipeline([EMA({self._fast_period}), "
                    f"EMA({self._slow_period})]) before calling generate(). "
                    f"Available columns: {list(df.columns)}"
                )

        raw_signal = df[self._fast_col] - df[self._slow_col]
        raw_signal.name = self.name

        self._logger.debug(
            "EMACrossoverSignal: generated signal '%s' — %d valid bars",
            self.name,
            raw_signal.notna().sum(),
        )
        return raw_signal


class MomentumSignal(SignalGenerator):
    """Trend-following signal based on rate-of-change momentum.

    RawSignal = z-scored Momentum(lookback). Positive when momentum is strong.
    Optional z-scoring normalizes the signal across time.

    Requires FeatureFrame to contain column: momentum_{lookback}
    Build FeatureFrame with FeaturePipeline([Momentum(lookback)]) first.
    See ADR-007.
    """

    def __init__(self, lookback: int = 20, z_score_window: int = 63) -> None:
        """Initialise MomentumSignal.

        Args:
            lookback: Momentum lookback period. Default 20 per strategies.yaml.
            z_score_window: Rolling window for z-score normalization.
                Set to 0 to disable z-scoring. Default 63 per strategies.yaml.
        """
        self._lookback = lookback
        self._z_score_window = z_score_window
        self._mom_col = Momentum(lookback=lookback).column_name
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Return signal identifier: momentum_{lookback}."""
        return f"momentum_{self._lookback}"

    def generate(self, feature_frame: Any) -> pd.Series:
        """Generate momentum RawSignal from FeatureFrame.

        If z_score_window > 0, applies rolling z-score normalization.

        Args:
            feature_frame: FeatureFrame instance with momentum column.

        Returns:
            RawSignal pd.Series. Z-scored if z_score_window > 0.

        Raises:
            KeyError: If momentum column not in feature_frame.data.
        """
        df = feature_frame.data

        if self._mom_col not in df.columns:
            raise KeyError(
                f"MomentumSignal requires column '{self._mom_col}' in FeatureFrame. "
                f"Build FeatureFrame with FeaturePipeline([Momentum({self._lookback})]) first. "
                f"Available columns: {list(df.columns)}"
            )

        raw = df[self._mom_col].copy()

        if self._z_score_window > 0:
            rolling_mean = raw.rolling(
                window=self._z_score_window, min_periods=self._z_score_window
            ).mean()
            rolling_std = raw.rolling(
                window=self._z_score_window, min_periods=self._z_score_window
            ).std()
            raw = (raw - rolling_mean) / (rolling_std + 1e-10)

        raw.name = self.name
        return raw
