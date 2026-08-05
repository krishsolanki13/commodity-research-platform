"""CFTC COT positioning signal — contrarian commodity sentiment.

Net speculative positioning (non-commercial longs minus shorts) from the
CFTC COT report is a widely-used sentiment indicator. The signal is
contrarian: crowded long positions (high percentile rank) suggest a
reversal downward; crowded short positions suggest a reversal upward.

Signal generation:
  percentile_rank > upper_pct (default 80) → SHORT (overcrowded long)
  percentile_rank < lower_pct (default 20) → LONG (overcrowded short)
  otherwise → FLAT

Data source: CFTC COT Disaggregated Futures report (weekly).
Run scripts/acquire_cot_data.py to refresh data.

COT data is weekly. Signal is forward-filled to daily frequency:
Tuesday COT release applies to all trading days until next Tuesday.

Brent crude has no CFTC COT data (ICE London contract) — returns flat
signal for Brent without raising an exception.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.core.config import Config
    from src.research.feature_frame import FeatureFrame

logger = logging.getLogger(__name__)


class COTPositioningSignal:
    """CFTC COT contrarian positioning signal.

    Generates a long/short/flat signal based on the percentile rank of
    net speculative positioning relative to historical levels.

    The percentile rank is pre-computed by scripts/acquire_cot_data.py
    using a 52-week rolling window.

    Args:
        config: Platform Config (required by SignalGenerator convention).
        upper_pct: Percentile rank above which to go short (default 80).
            Crowd is maximally long → expect reversal downward.
        lower_pct: Percentile rank below which to go long (default 20).
            Crowd is maximally short → expect reversal upward.

    Catalog parameters:
        upper_pct: 80.0
        lower_pct: 20.0
    """

    def __init__(
        self,
        config: Config,
        upper_pct: float = 80.0,
        lower_pct: float = 20.0,
    ) -> None:
        self._config = config
        self._upper_pct = upper_pct
        self._lower_pct = lower_pct

    @property
    def name(self) -> str:
        """Strategy identifier. DEV-EM7-1: @property required."""
        return "cot_positioning"

    def generate(self, feature_frame: FeatureFrame) -> pd.Series:
        """Generate COT positioning signal for the given asset.

        Args:
            feature_frame: FeatureFrame from FeaturePipeline([]).
                Uses feature_frame.asset and feature_frame.data.index.

        Returns:
            pd.Series of {+1.0, 0.0, -1.0} indexed by trading-day DatetimeIndex.
            series.name = self.name (DEV-EM7-2).
            Returns flat zero signal if COT data unavailable for the asset
            (Brent, missing acquisition, or insufficient history).
        """
        from src.data.cot_loader import COTDataLoader  # noqa: PLC0415

        # DEV-EM7-3: feature_frame.asset and feature_frame.data.index
        asset = feature_frame.asset
        dates_index = feature_frame.data.index

        flat = pd.Series(0.0, index=dates_index, name=self.name)

        loader = COTDataLoader()
        cot_df = loader.load(asset)

        if cot_df.empty:
            logger.warning(
                "COTPositioningSignal: no COT data for '%s' — returning flat signal. "
                "Run scripts/acquire_cot_data.py to download.",
                asset,
            )
            return flat

        if "percentile_rank" not in cot_df.columns:
            logger.warning(
                "COTPositioningSignal: 'percentile_rank' column missing "
                "in COT data for '%s' — returning flat signal.",
                asset,
            )
            return flat

        pct_rank = cot_df["percentile_rank"].dropna()

        if len(pct_rank) < 10:
            logger.warning(
                "COTPositioningSignal: insufficient COT data for '%s' "
                "(%d records) — returning flat signal.",
                asset,
                len(pct_rank),
            )
            return flat

        # Generate weekly signal from percentile rank
        weekly_signal = pd.Series(0.0, index=pct_rank.index, name=self.name)
        weekly_signal[pct_rank > self._upper_pct] = -1.0  # overcrowded long → short
        weekly_signal[pct_rank < self._lower_pct] = 1.0  # overcrowded short → long

        # Forward-fill weekly signal to daily trading calendar.
        # Tuesday COT release applies to all trading days until the next Tuesday.
        # DEV-EM7-4 pattern: reindex to union, ffill, reindex to target dates.
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
            "COTPositioningSignal: %s — long=%d, short=%d, flat=%d bars",
            asset,
            n_long,
            n_short,
            n_flat,
        )

        return daily_signal
