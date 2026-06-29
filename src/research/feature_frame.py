"""FeatureFrame: typed wrapper for OHLCV DataFrames with computed indicator columns.

Defined here per ADR-006. Upper layers import FeatureFrame from this module directly.
Do NOT import FeatureFrame into src/core/types.py — circular import exists because
this module imports FeatureSpec from types.py.
"""

from __future__ import annotations

import pandas as pd

from src.core.types import FeatureSpec


class FeatureFrame:
    """Typed wrapper for a DataFrame containing OHLCV and indicator columns.

    Produced by FeaturePipeline.compute(). Consumed by SignalGenerator.generate().

    Properties:
        data:          The underlying DataFrame (OHLCV + indicator columns).
        feature_specs: List of FeatureSpec, one per computed indicator column.
        asset:         Asset identifier string.

    Per ADR-006: FeatureFrame uses composition (wraps a DataFrame) not inheritance.
    Do not subclass pd.DataFrame.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        feature_specs: list[FeatureSpec],
        asset: str,
    ) -> None:
        """Initialise FeatureFrame.

        Args:
            data: DataFrame with OHLCV columns plus computed indicator columns.
            feature_specs: One FeatureSpec per computed indicator column.
            asset: Asset identifier (e.g., "gold").
        """
        self._data = data
        self._feature_specs = feature_specs
        self._asset = asset

    @property
    def data(self) -> pd.DataFrame:
        """Return the underlying DataFrame with OHLCV and indicator columns."""
        return self._data

    @property
    def feature_specs(self) -> list[FeatureSpec]:
        """Return FeatureSpec list for all computed indicator columns."""
        return self._feature_specs

    @property
    def asset(self) -> str:
        """Return the asset identifier."""
        return self._asset
