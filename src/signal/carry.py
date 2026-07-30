"""Commodity carry signal based on futures curve roll yield.

The carry signal is the canonical commodity risk premium: long assets in
backwardation (positive roll yield), short assets in contango (negative
roll yield). This implements the time-series carry strategy:

  signal[t] = +1  if roll_yield[t] > threshold   (backwardation)
  signal[t] = -1  if roll_yield[t] < -threshold  (contango)
  signal[t] =  0  if |roll_yield[t]| <= threshold or NaN

Roll yield is computed from individual contract data via FuturesCurveBuilder
and TermStructureAnalyzer — the same infrastructure used by the commodity
intelligence layer (Phase 2, M08-M13).

The carry signal uses no OHLCV-derived indicators. FeaturePipeline([]) is
passed in pipeline_builder.py (empty indicators list), and generate() uses
only feature_frame.data.index for dates and feature_frame.asset for the asset.

References:
    Koijen, R., Moskowitz, T., Pedersen, L. & Vrugt, E. (2018).
    Carry. Journal of Financial Economics, 127(2), 197-225.

    Erb, C. & Harvey, C. (2006). The strategic and tactical value of
    commodity futures. Financial Analysts Journal, 62(2), 69-97.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from src.signal.base import SignalGenerator

if TYPE_CHECKING:
    from src.core.config import Config
    from src.research.feature_frame import FeatureFrame

logger = logging.getLogger(__name__)


class CarrySignal(SignalGenerator):
    """Commodity carry signal from futures curve roll yield.

    Long in backwardation (positive roll yield), short in contango
    (negative roll yield). Roll yield is annualized and computed from
    the slope of the forward curve between the front and second contract.

    Parameters:
        config: Platform Config object for loading contract data.
        threshold: Minimum |roll yield| to generate a signal.
            Default 0.0 = any positive/negative roll yield generates.
            Example: 0.02 = only signal when |roll yield| > 2%/yr.
        n_contracts: Number of contracts to include in the forward curve.
            Default 4. Affects slope and roll yield calculation.
    """

    def __init__(
        self,
        config: Config,
        threshold: float = 0.0,
        n_contracts: int = 4,
    ) -> None:
        self._config = config
        self._threshold = threshold
        self._n_contracts = n_contracts

    @property
    def name(self) -> str:
        """Strategy identifier used in run_id and MLflow logging."""
        return "carry"

    def generate(self, feature_frame: FeatureFrame) -> pd.Series:
        """Generate carry signal from roll yield time series.

        Loads individual contract data for the asset, builds forward curves
        for each trading day in feature_frame.data.index, computes roll yield
        via TermStructureAnalyzer, and returns a signed signal series.

        Args:
            feature_frame: FeatureFrame produced by FeaturePipeline([]).
                Used only for .asset (str) and .data.index (DatetimeIndex).
                No indicator columns are read from feature_frame.

        Returns:
            pd.Series (RawSignal) with values in {+1.0, 0.0, -1.0}, indexed
            by feature_frame.data.index. series.name == "carry".
            0.0 for bars with unavailable contract data or roll yield within
            threshold.
        """
        from src.commodity.curve import FuturesCurveBuilder  # noqa: PLC0415
        from src.commodity.term_structure import TermStructureAnalyzer  # noqa: PLC0415

        asset = feature_frame.asset
        dates_index = feature_frame.data.index
        dates = [d.date() for d in dates_index]

        logger.info(
            "CarrySignal: computing roll yield for %s over %d bars "
            "(n_contracts=%d, threshold=%.4f)",
            asset,
            len(dates),
            self._n_contracts,
            self._threshold,
        )

        builder = FuturesCurveBuilder(self._config)

        available = builder.available_assets()
        if asset not in available:
            logger.warning(
                "CarrySignal: no contract data for '%s' — returning flat signal. "
                "Available assets with contract data: %s",
                asset,
                available,
            )
            flat = pd.Series(0.0, index=dates_index)
            flat.name = self.name
            return flat

        try:
            curves = builder.build_historical_curves(
                asset=asset,
                dates=dates,
                n_contracts=self._n_contracts,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "CarrySignal: curve build failed for '%s' (%s) — flat signal.",
                asset,
                exc,
            )
            flat = pd.Series(0.0, index=dates_index)
            flat.name = self.name
            return flat

        # continuous_close=None: carry signal does not need basis (ADR-001)
        analyzer = TermStructureAnalyzer()
        snapshots = analyzer.analyze_series(
            curves=curves,
            continuous_closes=None,
        )

        # Map observation_date → roll_yield_annualized
        roll_yield_map: dict = {
            snap.observation_date: snap.roll_yield_annualized for snap in snapshots
        }

        # Build roll yield series aligned to trading days
        roll_yield_values = [roll_yield_map.get(d, float("nan")) for d in dates]
        roll_yield = pd.Series(roll_yield_values, index=dates_index)

        n_nan = roll_yield.isna().sum()
        if n_nan > 0:
            logger.info(
                "CarrySignal: %d / %d bars have no roll yield "
                "(insufficient contract data — mapped to 0).",
                n_nan,
                len(dates),
            )

        # Generate signal: +1 (backwardation), -1 (contango), 0 (threshold/NaN)
        signal = pd.Series(0.0, index=dates_index)
        signal[roll_yield > self._threshold] = 1.0
        signal[roll_yield < -self._threshold] = -1.0
        signal.name = self.name

        n_long = int((signal > 0).sum())
        n_short = int((signal < 0).sum())
        n_flat = int((signal == 0).sum())
        logger.info(
            "CarrySignal: %s — long=%d bars, short=%d bars, flat=%d bars",
            asset,
            n_long,
            n_short,
            n_flat,
        )

        return signal
