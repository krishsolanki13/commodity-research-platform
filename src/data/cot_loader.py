"""CFTC COT (Commitments of Traders) data loader.

Downloads, parses, and stores weekly CFTC COT disaggregated futures data.
Net speculative position = non-commercial longs - non-commercial shorts.

Data source: https://www.cftc.gov (public, free, no API key)
Storage: data/processed/cot/{asset}.parquet

COT data is weekly (Tuesday release). Forward-fill to daily when used
in signal generation. The net speculative position is the primary
sentiment indicator for commodity mean-reversion signals.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# CFTC market names per platform asset identifier.
# Confirmed from actual COT data — update if column values differ after Task 0a.
COT_MARKET_MAP: dict[str, str] = {
    "gold": "GOLD - COMMODITY EXCHANGE INC.",
    "silver": "SILVER - COMMODITY EXCHANGE INC.",
    "copper": "COPPER- #1 - COMMODITY EXCHANGE INC.",
    "wti": "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
    "natural_gas": "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE",
}

_COT_DIR = Path("data/processed/cot")


class COTDataLoader:
    """Loads and provides access to CFTC COT data for platform assets.

    Usage:
        loader = COTDataLoader()
        df = loader.load("gold")  # returns weekly COT DataFrame
    """

    def load(self, asset: str) -> pd.DataFrame:
        """Load COT data for an asset from the processed Parquet.

        Args:
            asset: Platform asset identifier (e.g. 'gold').

        Returns:
            DataFrame with DatetimeIndex (UTC, weekly) and columns:
              net_speculative, long_specs, short_specs, percentile_rank
            Empty DataFrame if no COT data for the asset.
        """
        parquet_path = _COT_DIR / f"{asset}.parquet"
        if not parquet_path.exists():
            logger.warning(
                "COTDataLoader: no COT data for '%s' at %s. "
                "Run scripts/acquire_cot_data.py to download.",
                asset,
                parquet_path,
            )
            return pd.DataFrame()

        df = pd.read_parquet(parquet_path)
        logger.info("COTDataLoader: loaded %d COT records for '%s'", len(df), asset)
        return df

    def available_assets(self) -> list[str]:
        """Return list of assets that have COT Parquet files on disk."""
        if not _COT_DIR.exists():
            return []
        return [f.stem for f in _COT_DIR.glob("*.parquet")]
