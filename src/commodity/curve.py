"""FuturesCurveBuilder: constructs term structure snapshots from contract data.

Takes contract OHLCV DataFrames from ContractDataLoader and assembles FuturesCurve
objects representing the forward price structure at a given observation date.

This module produces the curve — a price snapshot. Analytics (contango,
backwardation, roll yield, basis, regime detection) belong in Module 10
(TermStructureAnalytics, src/commodity/term_structure.py).

Architecture: Layer 5 — Commodity Intelligence.
See ADR-001 for the contract vs. continuous data strategy.
See Architecture Section 5 (Layer 5 Responsibilities).
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from src.core.config import Config
from src.core.types import ContractMetadata, CurvePoint, FuturesCurve
from src.data.contract_loader import ContractDataLoader


class FuturesCurveBuilder:
    """Constructs FuturesCurve snapshots from contract OHLCV data.

    Each call to build() is stateless and independent — no curve state is
    retained between calls. The builder holds a ContractDataLoader for
    data access only.

    Layer 5 analytical separation: this class constructs curves (price facts).
    It does not compute analytics. Contango detection, roll yield, and basis
    are Module 10 responsibilities.

    Usage:
        builder = FuturesCurveBuilder(config)
        curve = builder.build("gold", observation_date=date(2026, 7, 1))
        print(f"Gold forward curve: {curve.n_points} contracts")
        print(f"Front price: {curve.front_price:.2f}")
        print(f"Structure: {'contango' if curve.is_contango else 'backwardation'}")
    """

    def __init__(self, config: Config) -> None:
        """Initialise FuturesCurveBuilder.

        Args:
            config: Config instance from Config.load().
                Reads contracts_raw and contracts_processed paths.
        """
        self._config = config
        self._loader = ContractDataLoader(config)
        self._logger = logging.getLogger(__name__)

    def build(
        self,
        asset: str,
        observation_date: date | None = None,
        n_contracts: int = 6,
        force_reload: bool = False,
    ) -> FuturesCurve:
        """Build a futures term structure snapshot.

        For each contract in the forward curve on or after the observation_date,
        finds the last available closing price on or before the observation_date.
        Contracts with no data on or before the observation_date are excluded.

        Args:
            asset: Platform asset identifier (e.g. 'gold').
            observation_date: Anchor date for the curve snapshot. Defaults to today.
                Pass a historical date to reconstruct the past term structure.
            n_contracts: Number of curve points to include. Actual points may
                be fewer if yfinance coverage is thin.
            force_reload: If True, re-runs the contract pipeline even when
                Parquet files exist.

        Returns:
            FuturesCurve with points sorted by delivery date (nearest first).
            May have fewer than n_contracts points if coverage is thin.

        Raises:
            ValueError: If no contracts are available for this asset.
                Run scripts/acquire_contract_data.py first.
        """
        if observation_date is None:
            observation_date = date.today()

        try:
            contract_list = self._loader.load_curve(
                asset=asset,
                n_contracts=n_contracts,
                force_reload=force_reload,
                reference_date=observation_date,
            )
        except ValueError:
            raise ValueError(
                f"No contract data available for '{asset}'. "
                f"Run: python scripts/acquire_contract_data.py --assets {asset}"
            ) from None

        points: list[CurvePoint] = []
        for meta, df in contract_list:
            point = self._build_curve_point(meta, df, observation_date)
            if point is not None:
                points.append(point)

        # Ensure sorted by delivery date (nearest first)
        points.sort(key=lambda p: (p.metadata.contract_year, p.metadata.contract_month))

        self._logger.info(
            "FuturesCurveBuilder: %s curve at %s — %d/%d points",
            asset,
            observation_date,
            len(points),
            n_contracts,
        )

        return FuturesCurve(
            asset=asset,
            observation_date=observation_date,
            points=points,
        )

    def build_historical_curves(
        self,
        asset: str,
        dates: list[date],
        n_contracts: int = 6,
    ) -> list[FuturesCurve]:
        """Build term structure snapshots for a list of observation dates.

        Used for historical contango/backwardation analysis. Each date
        produces an independent FuturesCurve snapshot.

        Args:
            asset: Platform asset identifier.
            dates: List of observation dates. May be historical.
                Dates are processed in chronological order.
            n_contracts: Number of curve points per snapshot.

        Returns:
            List of FuturesCurve objects, one per date, sorted by
            observation_date ascending. Dates with no contract data
            produce FuturesCurve with empty points list (not omitted).
        """
        curves: list[FuturesCurve] = []
        for obs_date in sorted(dates):
            try:
                curve = self.build(
                    asset, observation_date=obs_date, n_contracts=n_contracts
                )
                curves.append(curve)
            except ValueError:
                curves.append(
                    FuturesCurve(
                        asset=asset,
                        observation_date=obs_date,
                        points=[],
                    )
                )
                self._logger.debug(
                    "FuturesCurveBuilder: no contracts for %s at %s — empty curve",
                    asset,
                    obs_date,
                )
        return curves

    def available_assets(self) -> list[str]:
        """Return assets that have at least one contract Parquet file.

        Uses the contracts_processed directory to determine which assets
        have been fully ingested (not just acquired).

        Returns:
            Sorted list of asset identifiers with processed contract data.
            Empty list if no contract data has been processed.
        """
        processed_dir = Path(self._config.paths["contracts_processed"])
        if not processed_dir.exists():
            return []
        return sorted(
            d.name
            for d in processed_dir.iterdir()
            if d.is_dir() and any(d.glob("*.parquet"))
        )

    def list_contracts(self, asset: str) -> list[ContractMetadata]:
        """Return ContractMetadata for all available contracts for this asset.

        Public delegation to ContractDataLoader.list_contracts(), provided to
        avoid external callers accessing the private _loader attribute.

        Pre-M14 housekeeping: replaces builder._loader.list_contracts(asset)
        in dashboard/pages/6_futures_curve.py.

        Args:
            asset: Platform asset identifier (e.g. 'gold').

        Returns:
            List of ContractMetadata sorted by (contract_year, contract_month).
            Empty list if no contracts are available for this asset.
        """
        return self._loader.list_contracts(asset)

    def _build_curve_point(
        self,
        meta: ContractMetadata,
        df: pd.DataFrame,
        observation_date: date,
    ) -> CurvePoint | None:
        """Build a single CurvePoint from contract OHLCV data.

        Finds the last available closing price on or before observation_date.
        Returns None if no data exists at or before observation_date.

        Args:
            meta: ContractMetadata for this delivery contract.
            df: NormalizedOHLCV DataFrame for this contract (UTC DatetimeIndex).
            observation_date: Anchor date for price lookup.

        Returns:
            CurvePoint at the observation_date, or None if no data available.
        """
        # Filter to rows on or before observation_date
        available = df[df.index.date <= observation_date]

        if available.empty:
            self._logger.debug(
                "FuturesCurveBuilder: no data for %s on or before %s — excluded",
                meta.ticker,
                observation_date,
            )
            return None

        last_row = available.iloc[-1]
        data_date = available.index[-1].date()
        close_val = float(last_row["close"])
        volume_val = (
            float(last_row["volume"])
            if "volume" in last_row.index and pd.notna(last_row["volume"])
            else float("nan")
        )

        # days_to_delivery: approximate using delivery month start date
        # Module 10 may refine using a roll calendar if expiry_date is populated
        delivery_start = date(meta.contract_year, meta.contract_month, 1)
        days_to_delivery = (delivery_start - observation_date).days

        return CurvePoint(
            metadata=meta,
            close=close_val,
            volume=volume_val,
            observation_date=observation_date,
            data_date=data_date,
            days_to_delivery=days_to_delivery,
        )
