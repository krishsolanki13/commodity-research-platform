"""FuturesContractSource: individual futures contract data access.

Implements the DataSource ABC for contract-level OHLCV data.
Reads from data/raw/contracts/{asset}/{ticker}.csv files produced
by scripts/acquire_contract_data.py.

Contract tickers follow CME naming convention: {root}{month_code}{2-digit-year}
e.g. GCZ24 (Gold December 2024), CLM25 (WTI May 2025).

See ADR-001 for the contract vs. continuous data strategy.
See Architecture Section 8.1 for ticker convention documentation.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from src.core.config import Config
from src.core.registry import DataSource
from src.core.types import ContractMetadata

# CME month codes — matches Architecture Section 8.1
_MONTH_CODES: dict[int, str] = {
    1: "F",
    2: "G",
    3: "H",
    4: "J",
    5: "K",
    6: "M",
    7: "N",
    8: "Q",
    9: "U",
    10: "V",
    11: "X",
    12: "Z",
}

_MONTH_FROM_CODE: dict[str, int] = {v: k for k, v in _MONTH_CODES.items()}


def parse_contract_ticker(
    ticker: str, asset: str, contract_root: str
) -> ContractMetadata:
    """Parse a CME-format ticker string into a ContractMetadata.

    Args:
        ticker: e.g. 'GCZ24'
        asset: Platform asset identifier (e.g. 'gold')
        contract_root: CME root symbol (e.g. 'GC')

    Returns:
        ContractMetadata with month and year populated.

    Raises:
        ValueError: If ticker does not match expected format.
    """
    suffix = ticker[len(contract_root) :]
    if len(suffix) < 3:
        raise ValueError(
            f"Cannot parse ticker '{ticker}': expected '{contract_root}' + month_code + YY, "
            f"got suffix '{suffix}'"
        )
    month_code = suffix[0]
    year_str = suffix[1:]
    if month_code not in _MONTH_FROM_CODE:
        raise ValueError(
            f"Unknown month code '{month_code}' in ticker '{ticker}'. "
            f"Valid codes: {list(_MONTH_FROM_CODE.keys())}"
        )
    try:
        year_2digit = int(year_str)
    except ValueError:
        raise ValueError(
            f"Cannot parse year from ticker '{ticker}': '{year_str}'"
        ) from None

    # Interpret 2-digit year: 00–49 → 2000–2049, 50–99 → 1950–1999
    year_4digit = 2000 + year_2digit if year_2digit < 50 else 1900 + year_2digit

    return ContractMetadata(
        ticker=ticker,
        asset=asset,
        contract_root=contract_root,
        contract_month=_MONTH_FROM_CODE[month_code],
        contract_year=year_4digit,
    )


class FuturesContractSource(DataSource):
    """Reads individual futures contract CSVs from data/raw/contracts/{asset}/.

    Implements DataSource ABC. Each CSV is produced by acquire_contract_data.py
    and contains Yahoo Finance OHLCV data for a single delivery contract.

    CSV column format matches yfinance output:
        Date, Open, High, Low, Close, Volume

    OHLCVValidator is applied downstream with strict_ohlc=False per ADR-001.
    See Architecture Section 8.1 for the ticker naming convention.
    """

    def __init__(self, config: Config) -> None:
        """Initialise FuturesContractSource.

        Args:
            config: Config instance from Config.load().
                Reads config.paths["contracts_raw"] for the root directory.
        """
        self._config = config
        self._raw_dir = Path(config.paths["contracts_raw"])
        self._logger = logging.getLogger(__name__)

    def fetch(
        self,
        asset: str,
        start: date,
        end: date,
        ticker: str | None = None,
    ) -> pd.DataFrame:
        """Fetch raw OHLCV data for a specific contract.

        When ticker is provided, returns data for that single contract.
        When ticker is None, raises ValueError (contract tickers must be explicit).

        Args:
            asset: Platform asset identifier (e.g. 'gold').
            start: Inclusive start date filter.
            end: Inclusive end date filter.
            ticker: Contract ticker (e.g. 'GCZ24'). Required.

        Returns:
            Raw OHLCV DataFrame from the CSV file with Date, Open, High, Low,
            Close, Volume columns. Not yet normalized.

        Raises:
            ValueError: If ticker is None.
            FileNotFoundError: If the CSV file for this ticker does not exist.
        """
        if ticker is None:
            raise ValueError(
                "FuturesContractSource.fetch() requires an explicit ticker argument. "
                "Use ContractDataLoader.load_contract(asset, ticker) for single contracts, "
                "or ContractDataLoader.load_curve(asset) for forward curve loading."
            )

        csv_path = self._raw_dir / asset / f"{ticker}.csv"

        if not csv_path.exists():
            raise FileNotFoundError(
                f"No CSV found for {ticker} ({asset}) at {csv_path}. "
                f"Run: python scripts/acquire_contract_data.py --assets {asset}"
            )

        self._logger.debug(
            "FuturesContractSource: reading %s (%s) from %s",
            ticker,
            asset,
            csv_path,
        )

        df = pd.read_csv(csv_path, encoding="utf-8")
        return df

    def list_available_tickers(self, asset: str) -> list[str]:
        """Return all ticker names for which a CSV file exists for this asset.

        Args:
            asset: Platform asset identifier.

        Returns:
            Sorted list of ticker strings (e.g. ['GCF25', 'GCG25', 'GCH25']).
            Empty list if no contracts have been downloaded for this asset.
        """
        asset_dir = self._raw_dir / asset
        if not asset_dir.exists():
            return []
        return sorted(p.stem for p in asset_dir.glob("*.csv"))

    def available_assets(self) -> list[str]:
        """Return asset identifiers for which contract CSV directories exist.

        Returns:
            Sorted list of asset names (e.g. ['gold', 'wti']).
            Empty list if no contract data has been downloaded.
        """
        if not self._raw_dir.exists():
            return []
        return sorted(d.name for d in self._raw_dir.iterdir() if d.is_dir())
