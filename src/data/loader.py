"""DataLoader: Layer 0 pipeline orchestration.

The single entry point for all data access in Layer 1 and above.
Orchestrates: LocalCSVSource → OHLCVValidator → OHLCVNormalizer → ParquetStore.
Upper layers call DataLoader.load() and receive a NormalizedOHLCV DataFrame.
They never interact with sources, validators, normalizers, or the store directly.
See Architecture Section 5 (Layer 0 Responsibilities) and ADR-004.
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from src.core.config import Config
from src.data.normalizer import OHLCVNormalizer
from src.data.sources.csv import LocalCSVSource
from src.data.store import DataStore, ParquetStore
from src.data.validator import OHLCVValidator


class DataLoader:
    """Orchestrates the complete Layer 0 data pipeline.

    Pipeline: LocalCSVSource → OHLCVValidator → OHLCVNormalizer → ParquetStore

    Caching behaviour:
        force_reload=False (default): returns Parquet if it exists (fast path)
        force_reload=True:            re-runs full pipeline regardless
        Parquet absent:               runs full pipeline regardless of force_reload

    The pipeline is idempotent: two runs on unchanged raw data produce
    identical Parquet output.

    Date filtering:
        The full date range is always stored in Parquet.
        Date filtering is applied to the returned DataFrame at load time.
        Filtering never modifies what is persisted.
    """

    def __init__(self, config: Config) -> None:
        """Initialise DataLoader with all pipeline components.

        Args:
            config: Config instance from Config.load().
        """
        self._config = config
        self._source = LocalCSVSource(config)
        self._normalizer = OHLCVNormalizer()
        self._logger = logging.getLogger(__name__)
        if config.storage_backend == "clickhouse":
            from src.data.clickhouse_store import ClickHouseStore  # noqa: PLC0415

            self._store: DataStore = ClickHouseStore(config)
            self._logger.info(
                "DataLoader: using ClickHouseStore backend (%s:%d/%s)",
                config.clickhouse_host,
                config.clickhouse_port,
                config.clickhouse_database,
            )
        else:
            self._store = ParquetStore(config)
            self._logger.debug("DataLoader: using ParquetStore backend")

    def load(
        self,
        asset: str,
        start: date | None = None,
        end: date | None = None,
        force_reload: bool = False,
    ) -> pd.DataFrame:
        """Return a NormalizedOHLCV DataFrame for the given asset.

        Fast path: if Parquet exists and force_reload is False, reads from
        Parquet. Slow path: runs the full pipeline and writes Parquet.

        Args:
            asset: Asset identifier (e.g., "gold").
            start: Inclusive start date. Defaults to config.data.default_start_date.
            end: Inclusive end date. Defaults to today.
            force_reload: If True, re-runs pipeline even when Parquet exists.

        Returns:
            NormalizedOHLCV DataFrame filtered to [start, end].
        """
        resolved_start, resolved_end = self._resolve_dates(start, end)

        if not force_reload and self._store.exists(asset):
            self._logger.info("Loading %s from Parquet cache (fast path)", asset)
            df = self._store.read(asset)
        else:
            self._logger.info(
                "Running data pipeline for %s: source → validate → normalise → store",
                asset,
            )
            df = self._run_pipeline(asset, resolved_start, resolved_end)

        # Re-populate consumer-facing attrs after both fast and slow paths.
        # Parquet does not preserve attrs — we reconstruct from known parameters.
        # This matches the attrs set by OHLCVNormalizer.normalize() on the slow path.
        df.attrs["asset"] = asset
        df.attrs["source"] = "parquet"  # always — data canonical form is Parquet
        df.attrs["continuous"] = True  # DataLoader handles continuous series only

        return self._filter_date_range(df, resolved_start, resolved_end)

    def _run_pipeline(
        self,
        asset: str,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """Execute the full ingestion pipeline for the given asset.

        Steps:
            1. Fetch raw data from LocalCSVSource
            2. Validate with OHLCVValidator (raises DataValidationError on failure)
            3. Normalise with OHLCVNormalizer
            4. Write to ParquetStore
            5. Return normalised DataFrame

        Args:
            asset: Asset identifier.
            start: Inclusive start date passed to source.fetch().
            end: Inclusive end date passed to source.fetch().

        Returns:
            NormalizedOHLCV DataFrame.
        """
        # Step 1: Fetch
        raw_df = self._source.fetch(asset, start, end)

        # Step 2: Validate
        validator = OHLCVValidator(asset, strict_ohlc=False)
        validation_result = validator.validate(raw_df)
        if validation_result.warnings:
            self._logger.warning(
                "Validation for %s completed with %d warnings — see logs above",
                asset,
                len(validation_result.warnings),
            )

        # Step 3: Normalise
        normalised_df = self._normalizer.normalize(raw_df, asset, source="local_csv")

        # Step 4: Store
        path = self._store.write(normalised_df, asset)
        self._logger.info("Wrote %d rows for %s to %s", len(normalised_df), asset, path)

        return normalised_df

    def _resolve_dates(
        self,
        start: date | None,
        end: date | None,
    ) -> tuple[date, date]:
        """Resolve optional start/end to concrete dates using config defaults.

        Args:
            start: User-supplied start date, or None.
            end: User-supplied end date, or None.

        Returns:
            Tuple of (resolved_start, resolved_end) as date objects.
        """
        resolved_start = (
            start
            if start is not None
            else date.fromisoformat(self._config.data["default_start_date"])
        )

        default_end = self._config.data.get("default_end_date")
        resolved_end = (
            end
            if end is not None
            else (date.fromisoformat(default_end) if default_end else date.today())
        )

        return resolved_start, resolved_end

    def _filter_date_range(
        self,
        df: pd.DataFrame,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """Filter the DataFrame index to [start, end] inclusive.

        Preserves DataFrame.attrs through the filter operation.

        Args:
            df: NormalizedOHLCV DataFrame with UTC DatetimeIndex.
            start: Inclusive start date.
            end: Inclusive end date.

        Returns:
            Filtered DataFrame with attrs preserved.
        """
        mask = (df.index.date >= start) & (df.index.date <= end)
        filtered = df.loc[mask].copy()
        # Explicitly carry attrs through copy (copy() does not always preserve them)
        filtered.attrs = df.attrs.copy()
        if len(filtered) > 0:
            filtered.attrs["data_start"] = filtered.index.min().date()
            filtered.attrs["data_end"] = filtered.index.max().date()
        return filtered
