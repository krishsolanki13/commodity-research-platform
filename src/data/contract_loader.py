"""ContractDataLoader: Layer 0 contract-level pipeline orchestration.

Parallel to DataLoader (continuous series) but operates on individual
futures delivery contracts. The two loaders coexist and do not interact.

Pipeline: FuturesContractSource -> OHLCVValidator(strict_ohlc=False)
          -> OHLCVNormalizer -> ContractParquetStore

Primary entry points:
    load_contract(asset, ticker)         -> NormalizedOHLCV for one contract
    load_curve(asset, n_contracts)       -> list of (metadata, DataFrame) pairs
    list_contracts(asset)                -> list of ContractMetadata

See ADR-001 (contract vs. continuous strategy).
See Architecture Section 8.1 (ticker convention).
See Architecture Section 9.2 (directory layout).
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from src.core.config import Config
from src.core.types import ContractMetadata
from src.data.contract_store import ContractParquetStore
from src.data.normalizer import OHLCVNormalizer
from src.data.sources.futures_contract import (
    FuturesContractSource,
    parse_contract_ticker,
)
from src.data.validator import OHLCVValidator


class ContractDataLoader:
    """Orchestrates the contract-level data pipeline.

    Caching behaviour:
        force_reload=False (default): returns Parquet if it exists (fast path)
        force_reload=True:            re-runs full pipeline from CSV
        Parquet absent:               runs full pipeline regardless of force_reload

    Each call to load_contract() or load_curve() triggers the fast path
    (Parquet exists) or slow path (CSV -> validate -> normalize -> Parquet)
    transparently.
    """

    def __init__(self, config: Config) -> None:
        """Initialise ContractDataLoader with all pipeline components.

        Args:
            config: Config instance from Config.load().
        """
        self._config = config
        self._source = FuturesContractSource(config)
        self._normalizer = OHLCVNormalizer()
        self._store = ContractParquetStore(config)
        self._logger = logging.getLogger(__name__)

    def load_contract(
        self,
        asset: str,
        ticker: str,
        force_reload: bool = False,
    ) -> pd.DataFrame:
        """Return a NormalizedOHLCV DataFrame for a single futures contract.

        Fast path: if Parquet exists and force_reload is False, reads Parquet.
        Slow path: runs full pipeline (CSV -> validate -> normalize -> Parquet).

        Args:
            asset: Platform asset identifier (e.g. 'gold').
            ticker: Contract ticker (e.g. 'GCZ24').
            force_reload: If True, re-runs pipeline even when Parquet exists.

        Returns:
            NormalizedOHLCV DataFrame with UTC DatetimeIndex, columns:
            [open, high, low, close, volume, open_interest].

        Raises:
            FileNotFoundError: If no CSV exists for this ticker.
                Run scripts/acquire_contract_data.py first.
        """
        if not force_reload and self._store.exists(asset, ticker):
            self._logger.info(
                "ContractDataLoader: fast path — %s/%s from Parquet", asset, ticker
            )
            return self._store.read(asset, ticker)

        self._logger.info(
            "ContractDataLoader: slow path — %s/%s: CSV -> validate -> normalize -> Parquet",
            asset,
            ticker,
        )
        return self._run_pipeline(asset, ticker)

    def load_curve(
        self,
        asset: str,
        n_contracts: int = 6,
        force_reload: bool = False,
        reference_date: date | None = None,
    ) -> list[tuple[ContractMetadata, pd.DataFrame]]:
        """Load the forward curve for an asset as a list of contracts.

        The forward curve is the sequence of consecutive delivery months
        starting from the nearest available contract on or after reference_date.
        Used by Module 9 (FuturesCurveLayer) to construct the term structure.

        Args:
            asset: Platform asset identifier (e.g. 'gold').
            n_contracts: Number of curve points (contracts) to return. Default 6.
                A value of 6 gives approximately 6 months of forward curve.
            force_reload: If True, re-runs pipeline for each contract.
            reference_date: Anchor date for nearest contract. Defaults to today.

        Returns:
            List of (ContractMetadata, NormalizedOHLCV) pairs, sorted by
            delivery date (nearest first). Length may be less than n_contracts
            if fewer contracts are available.

        Raises:
            ValueError: If no contracts are available for this asset.
        """
        if reference_date is None:
            reference_date = date.today()

        all_meta = self.list_contracts(asset)
        if not all_meta:
            raise ValueError(
                f"No contracts available for '{asset}'. "
                f"Run: python scripts/acquire_contract_data.py --assets {asset}"
            )

        # Filter to contracts whose delivery month is on or after reference_date
        future_meta = [
            m
            for m in all_meta
            if date(m.contract_year, m.contract_month, 1)
            >= reference_date.replace(day=1)
        ]
        selected = future_meta[:n_contracts]

        if not selected:
            self._logger.warning(
                "ContractDataLoader: no future contracts found for %s after %s. "
                "Using most recent %d available contracts.",
                asset,
                reference_date,
                n_contracts,
            )
            selected = all_meta[-n_contracts:]

        curve: list[tuple[ContractMetadata, pd.DataFrame]] = []
        for meta in selected:
            try:
                df = self.load_contract(asset, meta.ticker, force_reload=force_reload)
                curve.append((meta, df))
            except FileNotFoundError:
                self._logger.warning(
                    "ContractDataLoader: %s/%s has metadata but no CSV — skipping",
                    asset,
                    meta.ticker,
                )

        self._logger.info(
            "ContractDataLoader: loaded curve for %s — %d contracts (requested %d)",
            asset,
            len(curve),
            n_contracts,
        )
        return curve

    def list_contracts(self, asset: str) -> list[ContractMetadata]:
        """Return ContractMetadata for all available contracts for this asset.

        Returns contracts for which a Parquet file exists (processed) OR
        a CSV file exists (raw, not yet processed). Sorted by delivery date.

        Args:
            asset: Platform asset identifier.

        Returns:
            List of ContractMetadata sorted by (contract_year, contract_month).
        """
        # From Parquet store (already processed)
        stored_meta = self._store.list_metadata(asset)
        stored_tickers = {m.ticker for m in stored_meta}

        # From source (raw CSVs not yet processed)
        raw_tickers = set(self._source.list_available_tickers(asset))
        unprocessed = raw_tickers - stored_tickers

        contract_root = self._config.assets[asset].get("contract_root", "")
        unprocessed_meta: list[ContractMetadata] = []
        for ticker in unprocessed:
            try:
                meta = parse_contract_ticker(ticker, asset, contract_root)
                unprocessed_meta.append(meta)
            except ValueError:
                self._logger.debug("Skipping unparseable ticker: %s", ticker)

        all_meta = stored_meta + unprocessed_meta
        return sorted(all_meta, key=lambda m: (m.contract_year, m.contract_month))

    def _run_pipeline(self, asset: str, ticker: str) -> pd.DataFrame:
        """Execute the full ingestion pipeline for one contract.

        Steps:
            1. Fetch raw CSV via FuturesContractSource
            2. Validate with OHLCVValidator(strict_ohlc=False)
            3. Normalize with OHLCVNormalizer
            4. Build ContractMetadata
            5. Write to ContractParquetStore
            6. Return normalized DataFrame
        """
        # Step 1: Fetch raw CSV
        raw_df = self._source.fetch(
            asset,
            start=date(2000, 1, 1),
            end=date.today(),
            ticker=ticker,
        )

        # Step 2: Validate (lenient for Yahoo Finance data per ADR-001)
        validator = OHLCVValidator(asset, strict_ohlc=False)
        validation_result = validator.validate(raw_df)
        if validation_result.warnings:
            self._logger.debug(
                "ContractDataLoader: %s/%s validation — %d warnings",
                asset,
                ticker,
                len(validation_result.warnings),
            )

        # Step 3: Normalize
        normalised_df = self._normalizer.normalize(
            raw_df, asset, source=f"contract/{ticker}"
        )

        # Step 4: Build metadata
        contract_root = self._config.assets[asset].get("contract_root", "")
        try:
            meta = parse_contract_ticker(ticker, asset, contract_root)
            meta.n_bars = len(normalised_df)
        except ValueError:
            meta = ContractMetadata(
                ticker=ticker,
                asset=asset,
                contract_root=contract_root,
                contract_month=0,
                contract_year=0,
                n_bars=len(normalised_df),
            )

        # Step 5: Store
        self._store.write(normalised_df, asset, ticker, meta)

        return normalised_df
