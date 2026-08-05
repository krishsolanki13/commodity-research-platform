"""EIA petroleum inventory signal — fundamental supply/demand indicator.

Weekly EIA petroleum storage reports provide the primary fundamental
data for crude oil markets. The inventory surprise (actual change vs
5-year seasonal average) indicates whether supply is tighter or looser
than expected.

Signal generation:
  surprise_zscore < -threshold → LONG (inventory drawdown = bullish)
  surprise_zscore > +threshold → SHORT (inventory build = bearish)
  otherwise → FLAT

Only valid for WTI and Brent crude oil. Returns flat zero signal for
all other assets (gold, silver, copper, natural_gas) with a log message.
No exception is raised for unsupported assets — graceful degradation.

Data source: EIA API v2 (weekly).
Run scripts/acquire_eia_data.py with EIA_API_KEY set to refresh data.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.core.config import Config
    from src.research.feature_frame import FeatureFrame

logger = logging.getLogger(__name__)

# Module-private constant — assets with EIA inventory data.
# Mirrors EIA_SERIES_MAP keys in eia_loader.py. Kept local to avoid
# circular imports and to make this module independently testable.
_EIA_SUPPORTED_ASSETS = frozenset({"wti", "brent"})


class EIAInventorySignal:
    """EIA petroleum inventory surprise signal.

    Long when inventory draws more than expected (bullish crude).
    Short when inventory builds more than expected (bearish crude).
    Flat for all non-crude assets — no exception raised.

    Args:
        config: Platform Config.
        threshold: Z-score threshold for signal entry (default 1.0).
            Entry when |surprise_zscore| > threshold.

    Catalog parameters:
        threshold: 1.0
    """

    def __init__(
        self,
        config: Config,
        threshold: float = 1.0,
    ) -> None:
        self._config = config
        self._threshold = threshold

    @property
    def name(self) -> str:
        """Strategy identifier. DEV-EM7-1: @property required."""
        return "eia_inventory"

    def generate(self, feature_frame: FeatureFrame) -> pd.Series:
        """Generate EIA inventory signal for the given asset.

        Args:
            feature_frame: FeatureFrame from FeaturePipeline([]).
                Uses feature_frame.asset and feature_frame.data.index.

        Returns:
            pd.Series of {+1.0, 0.0, -1.0} indexed by trading-day DatetimeIndex.
            series.name = self.name (DEV-EM7-2).
            Returns flat zero signal if:
              - Asset is not WTI or Brent (immediately, with log info)
              - EIA data unavailable (with log warning)
              - Insufficient history (< 10 records)
        """
        from src.data.eia_loader import EIADataLoader  # noqa: PLC0415

        # DEV-EM7-3: feature_frame.asset and feature_frame.data.index
        asset = feature_frame.asset
        dates_index = feature_frame.data.index

        flat = pd.Series(0.0, index=dates_index, name=self.name)

        if asset not in _EIA_SUPPORTED_ASSETS:
            logger.info(
                "EIAInventorySignal: '%s' is not a crude oil asset — "
                "returning flat signal. Supported: %s",
                asset,
                sorted(_EIA_SUPPORTED_ASSETS),
            )
            return flat

        loader = EIADataLoader()
        eia_df = loader.load(asset)

        if eia_df.empty:
            logger.warning(
                "EIAInventorySignal: no EIA data for '%s' — returning flat signal. "
                "Run scripts/acquire_eia_data.py to download.",
                asset,
            )
            return flat

        if "surprise_zscore" not in eia_df.columns:
            logger.warning(
                "EIAInventorySignal: 'surprise_zscore' column missing "
                "for '%s' — returning flat signal.",
                asset,
            )
            return flat

        zscore = eia_df["surprise_zscore"].dropna()

        if len(zscore) < 10:
            logger.warning(
                "EIAInventorySignal: insufficient EIA data for '%s' "
                "(%d records) — returning flat signal.",
                asset,
                len(zscore),
            )
            return flat

        # Generate weekly signal from z-score
        weekly_signal = pd.Series(0.0, index=zscore.index, name=self.name)
        # Negative surprise = drawdown = less supply than expected = bullish = LONG
        weekly_signal[zscore < -self._threshold] = 1.0
        # Positive surprise = build = more supply than expected = bearish = SHORT
        weekly_signal[zscore > self._threshold] = -1.0

        # Forward-fill weekly to daily trading calendar.
        # Wednesday EIA release applies to all days until next Wednesday.
        daily_signal = (
            weekly_signal.reindex(dates_index.union(weekly_signal.index))
            .ffill()
            .reindex(dates_index)
            .fillna(0.0)
        )
        daily_signal.name = self.name  # DEV-EM7-2

        n_long = int((daily_signal > 0).sum())
        n_short = int((daily_signal < 0).sum())
        n_flat = int((daily_signal == 0).sum())
        logger.info(
            "EIAInventorySignal: %s — long=%d, short=%d, flat=%d bars",
            asset,
            n_long,
            n_short,
            n_flat,
        )

        return daily_signal
