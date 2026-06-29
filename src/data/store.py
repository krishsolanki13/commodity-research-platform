"""DataStore ABC and ParquetStore for Layer 0 data infrastructure.

Defines the storage abstraction that decouples Parquet I/O from upper layers.
Phase 3 introduces ClickHouseStore implementing the same DataStore interface.
Upper layers access data through DataLoader, not DataStore directly.
See ADR-004 for the storage strategy.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from src.core.config import Config


class DataStore(ABC):
    """Abstract storage interface for processed OHLCV data.

    Layer 0 internal abstraction. Upper layers use DataLoader, not DataStore.

    Phase 1/2 implementation: ParquetStore
    Phase 3 implementation: ClickHouseStore (same interface, different backend)

    See ADR-004. The interface is designed so that ClickHouseStore can
    substitute ParquetStore without modifying DataLoader or any upper layer.
    """

    @abstractmethod
    def write(self, df: pd.DataFrame, asset: str) -> Path:
        """Persist normalised DataFrame for the given asset.

        Args:
            df: NormalizedOHLCV DataFrame from OHLCVNormalizer.normalize().
            asset: Asset identifier (e.g., "gold").

        Returns:
            Path where data was written.
        """

    @abstractmethod
    def read(self, asset: str) -> pd.DataFrame:
        """Retrieve normalised DataFrame for the given asset.

        IMPORTANT: Must re-populate DataFrame.attrs after reading.
        pandas does not preserve attrs through Parquet round-trips.

        Args:
            asset: Asset identifier (e.g., "gold").

        Returns:
            NormalizedOHLCV DataFrame with attrs populated.

        Raises:
            FileNotFoundError: If no processed data exists for the asset.
        """

    @abstractmethod
    def exists(self, asset: str) -> bool:
        """Return True if processed data exists for the given asset."""


class ParquetStore(DataStore):
    """Stores and retrieves normalised OHLCV data as Parquet files.

    Write path: {config.paths['processed_data']}continuous/{asset}.parquet
    Read path:  same as write path

    Uses pyarrow engine. Overwrites existing files (idempotent per ADR-004).
    Re-populates DataFrame.attrs after reading because Parquet does not
    preserve them through the write/read cycle.
    """

    def __init__(self, config: Config) -> None:
        """Initialise with the loaded Config.

        Args:
            config: Config instance. Used to resolve processed_data path.
        """
        self._config = config
        self._logger = logging.getLogger(__name__)

    def write(self, df: pd.DataFrame, asset: str) -> Path:
        """Write DataFrame to data/processed/continuous/{asset}.parquet.

        Creates the parent directory if it does not exist.
        Overwrites any existing file (idempotent regeneration per ADR-004).

        Args:
            df: NormalizedOHLCV DataFrame.
            asset: Asset identifier.

        Returns:
            Path where the Parquet file was written.
        """
        path = self._get_path(asset)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Temporarily convert date attrs to ISO strings for JSON serialization
        # datetime.date is not JSON-serializable; Parquet metadata requires JSON.
        # attrs are re-populated from data on read, so this only affects the write path.
        df_to_write = df.copy()
        if "data_start" in df_to_write.attrs:
            df_to_write.attrs["data_start"] = df_to_write.attrs[
                "data_start"
            ].isoformat()
        if "data_end" in df_to_write.attrs:
            df_to_write.attrs["data_end"] = df_to_write.attrs["data_end"].isoformat()
        df_to_write.to_parquet(path, engine="pyarrow", index=True)
        self._logger.debug(
            "ParquetStore: wrote %d rows for %s to %s", len(df), asset, path
        )
        return path

    def read(self, asset: str) -> pd.DataFrame:
        """Read from data/processed/continuous/{asset}.parquet.

        Re-populates five DataFrame.attrs fields after reading because
        Parquet does not preserve them through the round-trip.

        Args:
            asset: Asset identifier.

        Returns:
            NormalizedOHLCV DataFrame with attrs populated.

        Raises:
            FileNotFoundError: If the Parquet file does not exist.
        """
        path = self._get_path(asset)
        if not path.exists():
            raise FileNotFoundError(
                f"No processed Parquet file for asset '{asset}' at {path}. "
                f"Run DataLoader(config).load('{asset}', force_reload=True) "
                f"to generate it."
            )

        df = pd.read_parquet(path, engine="pyarrow")

        # Ensure UTC timezone (Parquet may drop or alter timezone information)
        if df.index.tzinfo is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")

        # Re-populate attrs — not preserved through Parquet round-trip
        df.attrs["asset"] = asset
        df.attrs["source"] = "parquet_cache"
        df.attrs["continuous"] = True
        df.attrs["data_start"] = df.index.min().date()
        df.attrs["data_end"] = df.index.max().date()

        return df

    def exists(self, asset: str) -> bool:
        """Return True if the Parquet file exists for the given asset."""
        return self._get_path(asset).exists()

    def _get_path(self, asset: str) -> Path:
        """Return the full filesystem Path for the asset's Parquet file."""
        return (
            Path(self._config.paths["processed_data"])
            / "continuous"
            / f"{asset}.parquet"
        )
