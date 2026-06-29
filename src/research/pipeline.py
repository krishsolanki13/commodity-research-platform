"""FeaturePipeline: applies a sequence of Indicators to produce a FeatureFrame.

The primary entry point for Layer 1. Layer 2 (Signal Research) calls
FeaturePipeline.compute() to build feature frames before signal generation.
See ADR-006 for the FeatureFrame and FeaturePipeline design decision.
"""

from __future__ import annotations

import datetime
import logging

import pandas as pd

from src.core.registry import Indicator
from src.core.types import FeatureSpec
from src.research.feature_frame import FeatureFrame


class FeaturePipeline:
    """Applies an ordered list of Indicators to a NormalizedOHLCV DataFrame.

    Produces a FeatureFrame containing the original OHLCV columns plus one
    computed column per Indicator, with a matching FeatureSpec for each.

    Indicators run in the order provided. Each Indicator's output column is
    added to the working DataFrame before the next Indicator runs — allowing
    Indicators that consume other Indicators' outputs to work correctly if
    ordered appropriately.

    The input DataFrame is never mutated. A copy is made at the start of compute().
    """

    def __init__(self, indicators: list[Indicator]) -> None:
        """Initialise FeaturePipeline with an ordered list of Indicators.

        Args:
            indicators: List of Indicator instances to apply in sequence.
        """
        self._indicators = indicators
        self._logger = logging.getLogger(__name__)

    def compute(self, ohlcv: pd.DataFrame, asset: str) -> FeatureFrame:
        """Apply all Indicators to the input OHLCV DataFrame.

        Args:
            ohlcv: NormalizedOHLCV DataFrame from DataLoader.load(). Not mutated.
            asset: Asset identifier written into each FeatureSpec (e.g., "gold").

        Returns:
            FeatureFrame with:
                - data: copy of ohlcv with one column added per Indicator
                - feature_specs: one FeatureSpec per Indicator
                - asset: the asset argument
        """
        result = ohlcv.copy()
        feature_specs: list[FeatureSpec] = []

        for indicator in self._indicators:
            self._logger.debug(
                "FeaturePipeline: computing %s for %s",
                indicator.column_name,
                asset,
            )
            series = indicator.compute(result)
            series.name = indicator.column_name
            result[indicator.column_name] = series

            spec = FeatureSpec(
                indicator_name=type(indicator).__name__.lower(),
                parameters=indicator.parameters,
                column_name=indicator.column_name,
                asset=asset,
                computed_at=datetime.datetime.now(tz=datetime.UTC),
            )
            feature_specs.append(spec)

        return FeatureFrame(data=result, feature_specs=feature_specs, asset=asset)
