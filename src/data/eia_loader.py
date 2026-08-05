"""EIA petroleum inventory data loader.

Loads weekly EIA petroleum storage data for WTI and Brent crude.
Computes inventory surprise = actual_change - 5-year seasonal average change.

Data source: EIA API v2 (https://api.eia.gov/v2/)
Storage: data/processed/eia/{asset}.parquet

EIA data is only meaningful for WTI and Brent crude oil.
EIAInventorySignal returns flat zero for all other assets.

Known limitation: WCSSTUS1 (Cushing crude stocks) is used as a Brent
proxy. Cushing is the WTI delivery point; it is not a direct measure
of North Sea/Brent supply. This is documented as an approximation.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_EIA_DIR = Path("data/processed/eia")

# EIA series IDs per platform asset
EIA_SERIES_MAP: dict[str, str] = {
    "wti": "WCRSTUS1",  # US crude oil stocks (weekly, thousand barrels)
    "brent": "WCSSTUS1",  # Cushing crude stocks as Brent proxy (known limitation)
}

# Public constant — used by signal generator and API router.
# Derived from EIA_SERIES_MAP so there is a single source of truth.
EIA_SUPPORTED_ASSETS: frozenset[str] = frozenset(EIA_SERIES_MAP.keys())


class EIADataLoader:
    """Loads EIA petroleum inventory data from processed Parquet files.

    Usage:
        loader = EIADataLoader()
        df = loader.load("wti")
    """

    def load(self, asset: str) -> pd.DataFrame:
        """Load EIA data for an asset from the processed Parquet.

        Args:
            asset: Platform asset identifier. Only 'wti' and 'brent' have data.

        Returns:
            DataFrame with DatetimeIndex (UTC, weekly) and columns:
              inventory, inventory_change, surprise, surprise_zscore
            Empty DataFrame if no EIA data for the asset.
        """
        parquet_path = _EIA_DIR / f"{asset}.parquet"
        if not parquet_path.exists():
            if asset in EIA_SERIES_MAP:
                logger.warning(
                    "EIADataLoader: no EIA data for '%s'. "
                    "Run scripts/acquire_eia_data.py to download.",
                    asset,
                )
            return pd.DataFrame()

        df = pd.read_parquet(parquet_path)
        logger.info("EIADataLoader: loaded %d EIA records for '%s'", len(df), asset)
        return df

    def available_assets(self) -> list[str]:
        """Return list of assets with EIA Parquet files on disk."""
        if not _EIA_DIR.exists():
            return []
        return [f.stem for f in _EIA_DIR.glob("*.parquet")]
