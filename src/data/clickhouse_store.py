"""ClickHouseStore: ClickHouse-backed implementation of the DataStore ABC.

Stores and retrieves NormalizedOHLCV continuous series data from a
ClickHouse analytical database. Replaces ParquetStore when
storage.backend = "clickhouse" in config.yaml.

Upper layers (DataLoader, FeaturePipeline, etc.) are unchanged — the
store implementation is injected via DataLoader.__init__() based on config.

Connection: clickhouse-connect HTTP client (port 8123).
Table: ohlcv_continuous (see scripts/setup_clickhouse_schema.py).
Deduplication: ReplacingMergeTree on (asset, date) — idempotent writes.

Phase 3 scope: continuous OHLCV data only. Contract data migration
is a separate concern (pre-M19 housekeeping or future module).

See ADR-004 (Storage Strategy: Parquet + ClickHouse Migration Path).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.config import Config
from src.data.store import DataStore


class ClickHouseStore(DataStore):
    """DataStore implementation backed by a ClickHouse analytical database.

    Lazy-initializes the ClickHouse HTTP client on first access. Subsequent
    reads and writes reuse the same client connection within the session.

    Usage (direct — normally instantiated by DataLoader):
        store = ClickHouseStore(config)
        store.write(df, "gold")
        df = store.read("gold")
        assets = store.list_assets()
        exists = store.exists("gold")
    """

    def __init__(self, config: Config) -> None:
        """Initialise ClickHouseStore.

        Args:
            config: Config instance from Config.load(). Reads:
                config.clickhouse_host, config.clickhouse_port,
                config.clickhouse_database, config.clickhouse_table_ohlcv,
                config.clickhouse_connect_timeout,
                config.clickhouse_send_receive_timeout.
        """
        self._config = config
        self._client: Any | None = None
        self._logger = logging.getLogger(__name__)

    def _get_client(self) -> Any:
        """Lazy-initialize and return the ClickHouse HTTP client.

        Connection is created on first access and reused thereafter.
        Both connect_timeout and send_receive_timeout are wired from config
        so that changes to config.yaml take effect without code changes.
        Raises clickhouse_connect.driver.exceptions.DatabaseError on failure.
        """
        if self._client is None:
            import clickhouse_connect  # noqa: PLC0415

            self._logger.debug(
                "ClickHouseStore: connecting to %s:%d/%s",
                self._config.clickhouse_host,
                self._config.clickhouse_port,
                self._config.clickhouse_database,
            )
            self._client = clickhouse_connect.get_client(
                host=self._config.clickhouse_host,
                port=self._config.clickhouse_port,
                database=self._config.clickhouse_database,
                connect_timeout=self._config.clickhouse_connect_timeout,
                send_receive_timeout=self._config.clickhouse_send_receive_timeout,
            )
        return self._client

    def exists(self, asset: str) -> bool:
        """Return True if any rows exist for this asset in ClickHouse.

        Args:
            asset: Platform asset identifier (e.g. 'gold').

        Returns:
            True if at least one row found, False otherwise.
        """
        client = self._get_client()
        result = client.query(
            f"SELECT count() FROM {self._config.clickhouse_table_ohlcv} "
            "WHERE asset = {asset:String}",
            parameters={"asset": asset},
        )
        count = result.first_row[0]
        self._logger.debug("ClickHouseStore.exists('%s'): %d rows", asset, count)
        return int(count) > 0

    def write(self, df: pd.DataFrame, asset: str) -> Path:
        """Insert or replace OHLCV rows for this asset in ClickHouse.

        Idempotent: ReplacingMergeTree engine deduplicates on (asset, date)
        on the next compaction. Safe to call multiple times with the same data.

        Args:
            df: NormalizedOHLCV DataFrame with UTC DatetimeIndex and columns
                [open, high, low, close, volume, open_interest].
            asset: Platform asset identifier.

        Returns:
            Pseudo-path indicating the write destination. Not a real filesystem
            path — used to satisfy the DataStore ABC return type signature.
            Format: Path(f"clickhouse://{database}/{table}/{asset}")
        """
        client = self._get_client()
        insert_df = self._prepare_for_insert(df, asset)

        client.insert_df(
            self._config.clickhouse_table_ohlcv,
            insert_df,
            column_names=insert_df.columns.tolist(),
        )

        self._logger.info(
            "ClickHouseStore: wrote %d rows for %s to %s.%s",
            len(insert_df),
            asset,
            self._config.clickhouse_database,
            self._config.clickhouse_table_ohlcv,
        )

        return Path(
            f"clickhouse://{self._config.clickhouse_database}"
            f"/{self._config.clickhouse_table_ohlcv}/{asset}"
        )

    def read(self, asset: str) -> pd.DataFrame:
        """Load NormalizedOHLCV data for an asset from ClickHouse.

        Args:
            asset: Platform asset identifier (e.g. 'gold').

        Returns:
            NormalizedOHLCV DataFrame with UTC DatetimeIndex and columns
            [open, high, low, close, volume, open_interest]. Same structure
            as ParquetStore.read() — upper layers cannot tell the difference.

        Raises:
            FileNotFoundError: If no rows exist for this asset.
        """
        if not self.exists(asset):
            raise FileNotFoundError(
                f"ClickHouseStore: no data found for '{asset}' in "
                f"{self._config.clickhouse_database}.{self._config.clickhouse_table_ohlcv}. "
                f"Run: python scripts/migrate_to_clickhouse.py --assets {asset}"
            )

        client = self._get_client()
        result_df = client.query_df(
            f"SELECT date, open, high, low, close, volume, open_interest "
            f"FROM {self._config.clickhouse_table_ohlcv} "
            "WHERE asset = {asset:String} ORDER BY date ASC",
            parameters={"asset": asset},
        )

        # Restore DatetimeIndex with UTC timezone (matching ParquetStore contract)
        result_df.index = pd.DatetimeIndex(pd.to_datetime(result_df["date"]), tz="UTC")
        result_df = result_df.drop(columns=["date"])
        result_df.index.name = None

        # Re-populate attrs (same as DataLoader.load() does after Parquet fast path)
        result_df.attrs["asset"] = asset
        result_df.attrs["source"] = "clickhouse"
        result_df.attrs["continuous"] = True

        self._logger.info("ClickHouseStore: read %d rows for %s", len(result_df), asset)
        return result_df

    def list_assets(self) -> list[str]:
        """Return all asset identifiers that have rows in ClickHouse.

        Returns:
            Sorted list of asset identifier strings.
        """
        client = self._get_client()
        result = client.query(
            f"SELECT DISTINCT asset FROM {self._config.clickhouse_table_ohlcv} "
            "ORDER BY asset ASC"
        )
        return [str(row[0]) for row in result.result_rows]

    def close(self) -> None:
        """Close the ClickHouse client connection. Safe to call multiple times."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
            finally:
                self._client = None

    def _prepare_for_insert(self, df: pd.DataFrame, asset: str) -> pd.DataFrame:
        """Prepare a NormalizedOHLCV DataFrame for ClickHouse insertion.

        Transforms the DataFrame to match the DDL schema column order:
            date (Date), asset (String), open, high, low, close,
            volume, open_interest (Nullable Float64).
        """
        insert_df = df.copy()

        # Strip timezone from DatetimeIndex — ClickHouse Date type is timezone-agnostic
        if hasattr(insert_df.index, "tz") and insert_df.index.tz is not None:
            insert_df.index = insert_df.index.tz_localize(None)
        insert_df.index = pd.DatetimeIndex(insert_df.index).normalize()
        insert_df.index.name = "date"
        insert_df = insert_df.reset_index()

        insert_df["asset"] = asset

        # Ensure open_interest column exists
        if "open_interest" not in insert_df.columns:
            insert_df["open_interest"] = None

        # Match DDL column order exactly
        return insert_df[
            ["date", "asset", "open", "high", "low", "close", "volume", "open_interest"]
        ]
