"""ContractStore and ContractParquetStore: Parquet storage for contract-level data.

Contract Parquet files are stored at:
    data/processed/contracts/{asset}/{ticker}.parquet

This store is parallel to ParquetStore (continuous series) but operates
on the contracts/ subdirectory tree. The two stores never share paths.

See Architecture Section 9.2 for the directory layout specification.
See ADR-004 for the Phase 2 Parquet strategy.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.config import Config
from src.core.types import ContractMetadata


class ContractStore(ABC):
    """Abstract base for contract-level Parquet storage.

    Parallel to DataStore (continuous series). Separates the storage
    interface from the implementation so Phase 3 can substitute
    a ClickHouse store without changing ContractDataLoader.
    """

    @abstractmethod
    def exists(self, asset: str, ticker: str) -> bool:
        """Return True if a Parquet file exists for this contract."""

    @abstractmethod
    def write(
        self,
        df: pd.DataFrame,
        asset: str,
        ticker: str,
        metadata: ContractMetadata,
    ) -> Path:
        """Persist normalized contract DataFrame to Parquet."""

    @abstractmethod
    def read(self, asset: str, ticker: str) -> pd.DataFrame:
        """Load a normalized contract DataFrame from Parquet."""

    @abstractmethod
    def list_tickers(self, asset: str) -> list[str]:
        """Return all tickers that have been persisted for this asset."""


class ContractParquetStore(ContractStore):
    """Parquet-backed contract store.

    Writes to: data/processed/contracts/{asset}/{ticker}.parquet
    Metadata (ContractMetadata fields) is stored alongside the Parquet
    as a sidecar JSON file: {ticker}.meta.json

    Uses pyarrow engine consistently with Phase 1 ParquetStore.
    write() merges with any existing Parquet for the same ticker:
    new rows union in, overlapping dates keep the incoming value.
    """

    def __init__(self, config: Config) -> None:
        """Initialise ContractParquetStore.

        Args:
            config: Config instance. Reads config.paths["contracts_processed"].
        """
        self._processed_dir = Path(config.paths["contracts_processed"])
        self._logger = logging.getLogger(__name__)

    def exists(self, asset: str, ticker: str) -> bool:
        """Return True if a Parquet file exists for this contract."""
        return self._parquet_path(asset, ticker).exists()

    def write(
        self,
        df: pd.DataFrame,
        asset: str,
        ticker: str,
        metadata: ContractMetadata,
    ) -> Path:
        """Persist normalized contract DataFrame and metadata to disk.

        Merge-on-write: if a Parquet file already exists for this ticker,
        concatenate it with ``df``, drop duplicate index entries keeping the
        new value, then sort. First write of a ticker is a plain create.

        Sidecar n_bars / earliest_bar / latest_bar reflect the accumulated
        range, not only the latest download.

        Args:
            df: NormalizedOHLCV DataFrame for this contract.
            asset: Platform asset identifier.
            ticker: Contract ticker string.
            metadata: ContractMetadata instance for this contract.

        Returns:
            Path to the written Parquet file.
        """
        parquet_path = self._parquet_path(asset, ticker)
        parquet_path.parent.mkdir(parents=True, exist_ok=True)

        combined = df
        merged = False
        if parquet_path.exists():
            existing = pd.read_parquet(parquet_path, engine="pyarrow")
            incoming = df.copy()
            if isinstance(existing.index, pd.DatetimeIndex) and isinstance(
                incoming.index, pd.DatetimeIndex
            ):
                existing, incoming = self._align_index_tz(existing, incoming)
            combined = pd.concat([existing, incoming])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined = combined.sort_index()
            merged = True

        combined.attrs = {}
        combined.to_parquet(parquet_path, engine="pyarrow")

        earliest = combined.index.min()
        latest = combined.index.max()
        meta_dict: dict[str, Any] = {
            "ticker": metadata.ticker,
            "asset": metadata.asset,
            "contract_root": metadata.contract_root,
            "contract_month": metadata.contract_month,
            "contract_year": metadata.contract_year,
            "expiry_date": metadata.expiry_date.isoformat()
            if metadata.expiry_date
            else None,
            "first_notice_date": (
                metadata.first_notice_date.isoformat()
                if metadata.first_notice_date
                else None
            ),
            "n_bars": len(combined),
            "earliest_bar": self._index_date_str(earliest),
            "latest_bar": self._index_date_str(latest),
            "accumulated": merged,
        }
        meta_path = parquet_path.with_suffix(".meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_dict, f, indent=2)

        self._logger.info(
            "ContractParquetStore: wrote %d bars for %s/%s to %s%s",
            len(combined),
            asset,
            ticker,
            parquet_path,
            " (merged)" if merged else "",
        )
        return parquet_path

    def read(self, asset: str, ticker: str) -> pd.DataFrame:
        """Load normalized contract DataFrame from Parquet.

        Args:
            asset: Platform asset identifier.
            ticker: Contract ticker string.

        Returns:
            NormalizedOHLCV DataFrame with UTC DatetimeIndex.

        Raises:
            FileNotFoundError: If the Parquet file does not exist.
        """
        parquet_path = self._parquet_path(asset, ticker)
        if not parquet_path.exists():
            raise FileNotFoundError(
                f"No Parquet found for {ticker} ({asset}) at {parquet_path}. "
                f"Run ContractDataLoader.load_contract('{asset}', '{ticker}') first."
            )
        return pd.read_parquet(parquet_path, engine="pyarrow")

    def read_metadata(self, asset: str, ticker: str) -> ContractMetadata | None:
        """Load ContractMetadata from the sidecar JSON file.

        Args:
            asset: Platform asset identifier.
            ticker: Contract ticker string.

        Returns:
            ContractMetadata, or None if no sidecar file exists.
        """
        meta_path = self._parquet_path(asset, ticker).with_suffix(".meta.json")
        if not meta_path.exists():
            return None
        with open(meta_path, encoding="utf-8") as f:
            d = json.load(f)
        return ContractMetadata(
            ticker=d["ticker"],
            asset=d["asset"],
            contract_root=d["contract_root"],
            contract_month=d["contract_month"],
            contract_year=d["contract_year"],
            expiry_date=date.fromisoformat(d["expiry_date"])
            if d["expiry_date"]
            else None,
            first_notice_date=(
                date.fromisoformat(d["first_notice_date"])
                if d["first_notice_date"]
                else None
            ),
            n_bars=d.get("n_bars", 0),
        )

    def list_tickers(self, asset: str) -> list[str]:
        """Return tickers for all Parquet files under this asset's directory.

        Returns:
            Sorted list of ticker strings. Empty if no contracts processed.
        """
        asset_dir = self._processed_dir / asset
        if not asset_dir.exists():
            return []
        return sorted(p.stem for p in asset_dir.glob("*.parquet"))

    def list_metadata(self, asset: str) -> list[ContractMetadata]:
        """Return ContractMetadata for all available contracts for this asset.

        Reads sidecar JSON files. Skips tickers with no sidecar.
        Returns contracts sorted by (contract_year, contract_month).
        """
        tickers = self.list_tickers(asset)
        results: list[ContractMetadata] = []
        for ticker in tickers:
            meta = self.read_metadata(asset, ticker)
            if meta is not None:
                results.append(meta)
        return sorted(results, key=lambda m: (m.contract_year, m.contract_month))

    def _parquet_path(self, asset: str, ticker: str) -> Path:
        """Return the Parquet file path for this contract."""
        return self._processed_dir / asset / f"{ticker}.parquet"

    @staticmethod
    def _align_index_tz(
        existing: pd.DataFrame, incoming: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Make DatetimeIndexes timezone-compatible before concat."""
        existing_tz = existing.index.tz
        incoming_tz = incoming.index.tz
        if existing_tz is not None and incoming_tz is None:
            incoming.index = incoming.index.tz_localize(existing_tz)
        elif existing_tz is None and incoming_tz is not None:
            existing = existing.copy()
            existing.index = existing.index.tz_localize(incoming_tz)
        elif (
            existing_tz is not None
            and incoming_tz is not None
            and existing_tz != incoming_tz
        ):
            incoming.index = incoming.index.tz_convert(existing_tz)
        return existing, incoming

    @staticmethod
    def _index_date_str(value: object) -> str:
        """ISO date string from a DatetimeIndex label."""
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value)[:10]
