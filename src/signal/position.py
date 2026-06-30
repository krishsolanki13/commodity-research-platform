"""PositionSignalConstructor: discretizes RawSignal into {+1, 0, -1}.

Sits between Layer 2 (Signal Research) and Layer 3 (Backtesting Engine).
The VectorizedBacktester in Module 5 consumes PositionSignal.
See ADR-007.
"""

from __future__ import annotations

import logging

import pandas as pd


class PositionSignalConstructor:
    """Converts a continuous RawSignal into a discrete PositionSignal.

    Thresholding rules:
        raw_signal[t] > threshold   → +1 (long)
        raw_signal[t] < -threshold  → -1 (short)
        otherwise                   → 0  (flat)

    With threshold=0.0, any positive raw signal → long, any negative → short.
    No flat zone exists with threshold=0.0.
    With threshold > 0.0, a flat zone exists around zero.

    Output dtype is int8 for memory efficiency.
    See ADR-007.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def build(
        self,
        raw_signal: pd.Series,
        threshold: float = 0.0,
    ) -> pd.Series:
        """Discretize RawSignal into {+1, 0, -1} PositionSignal.

        Args:
            raw_signal: RawSignal pd.Series from a SignalGenerator.
            threshold: Flat zone boundary. Values within [-threshold, +threshold]
                produce 0 (flat). Default 0.0 (no flat zone).

        Returns:
            PositionSignal pd.Series with int8 dtype, values in {-1, 0, +1}.
            Preserves the RawSignal's name.
        """
        position = pd.Series(
            0,
            index=raw_signal.index,
            dtype="int8",
            name=raw_signal.name,
        )
        position[raw_signal > threshold] = 1
        position[raw_signal < -threshold] = -1

        long_count = int((position == 1).sum())
        short_count = int((position == -1).sum())
        flat_count = int((position == 0).sum())
        self._logger.debug(
            "PositionSignalConstructor: long=%d, short=%d, flat=%d",
            long_count,
            short_count,
            flat_count,
        )
        return position
