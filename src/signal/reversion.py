"""Mean-reversion signal generator: RSI Reversion.

Reads from pre-computed RSI column in FeatureFrame.
Build FeatureFrame with FeaturePipeline([RSI(period)]) before calling generate().
See ADR-007.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.research.oscillators import RSI
from src.signal.base import SignalGenerator


class RSIReversionSignal(SignalGenerator):
    """Mean-reversion signal based on RSI deviation from neutral (50).

    RawSignal = -(RSI[t] - 50) / 50.
        - RSI < 50 (oversold tendency) → positive signal (expect price up)
        - RSI > 50 (overbought tendency) → negative signal (expect price down)
        - Values bounded approximately in [-1, +1]

    Requires FeatureFrame column: rsi_{period}
    Build FeatureFrame with FeaturePipeline([RSI(period)]) before calling generate().

    Note: oversold_threshold/overbought_threshold values in strategies.yaml
    (30/70) are PositionSignal-construction concerns, not RawSignal concerns,
    per ADR-007 (RawSignal must remain continuous and unthresholded). They
    are applied downstream by PositionSignalConstructor.build(raw_signal,
    threshold=...), not here. This class intentionally does not accept
    threshold parameters.
    """

    def __init__(self, period: int = 14) -> None:
        """Initialise RSIReversionSignal.

        Args:
            period: RSI period. Default 14 per strategies.yaml.
        """
        self._period = period
        self._rsi_col = RSI(period=period).column_name
        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Return signal identifier: rsi_reversion_{period}."""
        return f"rsi_reversion_{self._period}"

    def generate(self, feature_frame: Any) -> pd.Series:
        """Generate RSI reversion RawSignal from FeatureFrame.

        RawSignal[t] = -(RSI[t] - 50) / 50
        Bounded approximately in [-1, +1].

        Args:
            feature_frame: FeatureFrame instance with RSI column.

        Returns:
            RawSignal pd.Series inversely proportional to RSI.

        Raises:
            KeyError: If RSI column not in feature_frame.data.
        """
        df = feature_frame.data

        if self._rsi_col not in df.columns:
            raise KeyError(
                f"RSIReversionSignal requires column '{self._rsi_col}' in FeatureFrame. "
                f"Build FeatureFrame with FeaturePipeline([RSI({self._period})]) first. "
                f"Available columns: {list(df.columns)}"
            )

        raw_signal = -(df[self._rsi_col] - 50.0) / 50.0
        raw_signal.name = self.name
        return raw_signal
