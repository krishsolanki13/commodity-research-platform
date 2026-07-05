"""OHLCV normalizer for Layer 0 data infrastructure.

Transforms structurally valid raw DataFrames into NormalizedOHLCV-compliant
DataFrames. Assumes input has passed OHLCVValidator.validate() first.
See Architecture Section 7 (NormalizedOHLCV layer contract).
"""

from __future__ import annotations

import logging
from typing import ClassVar

import pandas as pd


class OHLCVNormalizer:
    """Normalises raw OHLCV DataFrames to the NormalizedOHLCV contract.

    Processing steps (always in this order):
        1. Lowercase and strip all column names
        2. Drop Adj Close variants (raw close used per ADR-001)
        3. Map columns to standard names and drop unknowns
        4. Set UTC DatetimeIndex from the date column
        5. Sort index ascending
        6. Add open_interest column (float64 NaN) if not present
        7. Enforce float64 dtype on all OHLCV columns
        8. Enforce column order: open, high, low, close, volume, open_interest
        9. Populate DataFrame.attrs with five required keys

    Stateless: no instance state is mutated between calls.
    Does not re-validate: assumes valid input.
    """

    # Maps lowercase source column names to standard names.
    # Applied after lowercasing all column names.
    COLUMN_MAP: ClassVar[dict[str, str]] = {
        "date": "date",
        "datetime": "date",
        "timestamp": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "open interest": "open_interest",
        "open_interest": "open_interest",
    }

    # Columns to drop if present (Adj Close explicitly excluded per ADR-001).
    DROP_COLUMNS: ClassVar[list[str]] = [
        "adj close",
        "adj_close",
        "adjusted_close",
        "adjclose",
    ]

    # Required output column order per NormalizedOHLCV contract.
    OHLCV_COLUMNS: ClassVar[list[str]] = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "open_interest",
    ]

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def normalize(
        self,
        df: pd.DataFrame,
        asset: str,
        source: str,
    ) -> pd.DataFrame:
        """Normalise a raw OHLCV DataFrame to the NormalizedOHLCV contract.

        Args:
            df: Raw DataFrame from LocalCSVSource.fetch(). Must have passed
                OHLCVValidator.validate() before calling this method.
            asset: Asset identifier (e.g., "gold"). Written to attrs.
            source: Data source identifier (e.g., "local_csv"). Written to attrs.

        Returns:
            NormalizedOHLCV-compliant pd.DataFrame with:
                - UTC DatetimeIndex named "date"
                - Columns: open, high, low, close, volume, open_interest
                - All columns as float64
                - attrs: asset, source, continuous=True, data_start, data_end
        """
        result = df.copy()

        # Step 1: lowercase and strip all column names
        result.columns = [c.lower().strip() for c in result.columns]

        # Step 2: drop Adj Close variants
        to_drop = [c for c in result.columns if c in self.DROP_COLUMNS]
        if to_drop:
            result = result.drop(columns=to_drop)
            for col in to_drop:
                self._logger.debug(
                    "OHLCVNormalizer: dropped column '%s' for %s", col, asset
                )

        # Step 3: keep only columns in COLUMN_MAP and rename them
        columns_to_keep = [c for c in result.columns if c in self.COLUMN_MAP]
        result = result[columns_to_keep].rename(columns=self.COLUMN_MAP)

        # Handle unlikely case of duplicate target names after rename
        result = result.loc[:, ~result.columns.duplicated(keep="first")]

        # Step 4: set UTC DatetimeIndex from date column
        if "date" in result.columns:
            result["date"] = pd.to_datetime(result["date"], utc=True)
            result = result.set_index("date")
        elif isinstance(result.index, pd.DatetimeIndex):
            if result.index.tzinfo is None:
                result.index = result.index.tz_localize("UTC")
            else:
                result.index = result.index.tz_convert("UTC")
        else:
            result.index = pd.to_datetime(result.index, utc=True)

        result.index.name = "date"

        # Step 5: sort ascending
        result = result.sort_index()

        # Step 6: add open_interest as float64 NaN if not present
        if "open_interest" not in result.columns:
            result["open_interest"] = float("nan")

        # Step 7: enforce float64 dtype on all OHLCV columns
        for col in self.OHLCV_COLUMNS:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors="coerce").astype(
                    "float64"
                )

        # Step 8: enforce column order (all six columns, in order)
        result = result[self.OHLCV_COLUMNS]

        # Step 9: populate attrs (not preserved through Parquet — re-populated on read)
        result.attrs["asset"] = asset
        result.attrs["source"] = source
        result.attrs["continuous"] = True
        result.attrs["data_start"] = result.index.min().date()
        result.attrs["data_end"] = result.index.max().date()

        result.attrs = {}
        return result
