"""LocalCSVSource: reads continuous futures data from local CSV files.

Phase 1 data source implementation. Reads OHLCV CSVs from data/raw/continuous/.
Raw files are never modified. See ADR-001.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from src.core.config import Config
from src.data.sources.base import ContinuousDataSource


class LocalCSVSource(ContinuousDataSource):
    """Reads continuous futures data from local CSV files.

    File discovery order:
        1. {raw_data_dir}/continuous/{asset}.csv        (exact match)
        2. {raw_data_dir}/continuous/{asset}_*.csv      (glob, most recently modified)

    Raw files are read-only. This class never writes to data/raw/.
    """

    def __init__(self, config: Config) -> None:
        """Initialise with the loaded Config.

        Args:
            config: Config instance from Config.load(). Used to resolve
                the raw data directory path via config.paths["raw_data"].
        """
        self._config = config
        self._logger = logging.getLogger(__name__)

    def fetch(self, asset: str, start: date, end: date) -> pd.DataFrame:
        """Read raw OHLCV data for the given asset from data/raw/continuous/.

        Does NOT normalise column names, dtypes, or index. Raw reading only.
        Date filtering is best-effort: if a date column can be identified,
        rows outside [start, end] are dropped. If not found, the full
        DataFrame is returned and the normalizer handles it downstream.

        Args:
            asset: Asset identifier (e.g., "gold").
            start: Inclusive start date for filtering.
            end: Inclusive end date for filtering.

        Returns:
            Raw pandas DataFrame with original column names and dtypes.

        Raises:
            FileNotFoundError: If no CSV file is found for the asset.
        """
        raw_dir = Path(self._config.paths["raw_data"]) / "continuous"
        csv_path = self._discover_file(raw_dir, asset)

        self._logger.debug("LocalCSVSource: discovered file %s", csv_path)
        df = pd.read_csv(csv_path)
        df = self._filter_by_date(df, asset, start, end)
        return df

    def available_assets(self) -> list[str]:
        """Return asset names derived from CSV filenames in data/raw/continuous/.

        Returns:
            List of asset name strings (Path.stem of each .csv file).
            Returns empty list if the directory does not exist.
        """
        raw_dir = Path(self._config.paths["raw_data"]) / "continuous"
        if not raw_dir.exists():
            return []
        return [p.stem for p in sorted(raw_dir.glob("*.csv"))]

    def _discover_file(self, raw_dir: Path, asset: str) -> Path:
        """Locate the CSV file for the given asset.

        Args:
            raw_dir: Directory to search.
            asset: Asset identifier.

        Returns:
            Path to the discovered CSV file.

        Raises:
            FileNotFoundError: If no matching file exists.
        """
        exact = raw_dir / f"{asset}.csv"
        if exact.exists():
            return exact

        matches = sorted(
            raw_dir.glob(f"{asset}_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if matches:
            return matches[0]

        raise FileNotFoundError(
            f"No CSV file found for asset '{asset}' in {raw_dir}. "
            f"Expected '{asset}.csv' or '{asset}_*.csv'."
        )

    def _filter_by_date(
        self,
        df: pd.DataFrame,
        asset: str,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """Apply best-effort date range filtering.

        Identifies a date column by case-insensitive name match. If found,
        converts to datetime and filters rows to [start, end] inclusive.
        If not found, returns the full DataFrame unchanged.

        Args:
            df: Raw DataFrame from pd.read_csv.
            asset: Asset name (for logging context only).
            start: Inclusive start date.
            end: Inclusive end date.

        Returns:
            Filtered or unfiltered DataFrame.
        """
        date_col: str | None = None
        for col in df.columns:
            if col.lower() in ("date", "datetime", "timestamp"):
                date_col = col
                break

        if date_col is None:
            self._logger.debug(
                "LocalCSVSource: no date column identified for %s — "
                "returning full DataFrame without date filtering",
                asset,
            )
            return df

        try:
            parsed = pd.to_datetime(df[date_col])
            mask = (parsed.dt.date >= start) & (parsed.dt.date <= end)
            filtered = df[mask].copy()
            self._logger.debug(
                "LocalCSVSource: filtered %s to [%s, %s] — %d rows",
                asset,
                start,
                end,
                len(filtered),
            )
            return filtered
        except Exception:  # noqa: BLE001
            self._logger.debug(
                "LocalCSVSource: date filtering failed for %s — "
                "returning full DataFrame",
                asset,
            )
            return df
