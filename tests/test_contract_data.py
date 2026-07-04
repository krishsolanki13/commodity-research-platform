"""Tests for Module 8: Contract Data Layer.

Tests ContractMetadata, parse_contract_ticker, FuturesContractSource,
ContractParquetStore, and ContractDataLoader using synthetic data and
tmp_path fixtures. No network calls — all yfinance calls are mocked.

See ADR-001 (contract data strategy) and Architecture Section 8.1
(ticker convention documentation).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.core.config import Config
from src.core.types import ContractMetadata
from src.data.contract_loader import ContractDataLoader
from src.data.contract_store import ContractParquetStore
from src.data.sources.futures_contract import (
    FuturesContractSource,
    parse_contract_ticker,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_contract_ohlcv(n: int = 20, ticker: str = "GCZ24") -> pd.DataFrame:
    """Build a synthetic normalized OHLCV DataFrame for a contract."""
    dates = pd.bdate_range(start="2024-10-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": [1900.0 + i for i in range(n)],
            "high": [1920.0 + i for i in range(n)],
            "low": [1880.0 + i for i in range(n)],
            "close": [1910.0 + i for i in range(n)],
            "volume": [25000.0] * n,
            "open_interest": [float("nan")] * n,
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )


def _make_raw_csv_df(n: int = 20) -> pd.DataFrame:
    """Build a synthetic raw yfinance CSV-format DataFrame."""
    dates = pd.bdate_range(start="2024-10-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "Date": dates.strftime("%Y-%m-%d"),
            "Open": [1900.0 + i for i in range(n)],
            "High": [1920.0 + i for i in range(n)],
            "Low": [1880.0 + i for i in range(n)],
            "Close": [1910.0 + i for i in range(n)],
            "Adj Close": [1910.0 + i for i in range(n)],
            "Volume": [25000] * n,
        }
    )


@pytest.fixture
def tmp_config(tmp_path: Path) -> Config:
    """Config fixture redirecting contract paths to a temporary directory."""
    cfg = Config.load("config/")
    cfg.paths["contracts_raw"] = str(tmp_path / "data" / "raw" / "contracts") + "/"
    cfg.paths["contracts_processed"] = (
        str(tmp_path / "data" / "processed" / "contracts") + "/"
    )
    (tmp_path / "data" / "raw" / "contracts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "processed" / "contracts").mkdir(parents=True, exist_ok=True)
    return cfg


# ---------------------------------------------------------------------------
# ContractMetadata tests
# ---------------------------------------------------------------------------


def test_contract_metadata_month_code_property() -> None:
    """ContractMetadata.month_code returns correct CME month code."""
    meta = ContractMetadata(
        ticker="GCZ24",
        asset="gold",
        contract_root="GC",
        contract_month=12,
        contract_year=2024,
    )
    assert meta.month_code == "Z", f"December should be 'Z', got '{meta.month_code}'"


def test_contract_metadata_str_representation() -> None:
    """ContractMetadata.__str__ returns human-readable string."""
    meta = ContractMetadata(
        ticker="CLF25",
        asset="wti",
        contract_root="CL",
        contract_month=1,
        contract_year=2025,
    )
    s = str(meta)
    assert "CLF25" in s
    assert "wti" in s


def test_contract_metadata_optional_fields_default_to_none() -> None:
    """ContractMetadata optional fields default to None and 0."""
    meta = ContractMetadata(
        ticker="NGH25",
        asset="natural_gas",
        contract_root="NG",
        contract_month=3,
        contract_year=2025,
    )
    assert meta.expiry_date is None
    assert meta.first_notice_date is None
    assert meta.n_bars == 0


# ---------------------------------------------------------------------------
# parse_contract_ticker tests
# ---------------------------------------------------------------------------


def test_parse_contract_ticker_gold_december_2024() -> None:
    """parse_contract_ticker correctly parses GCZ24."""
    meta = parse_contract_ticker("GCZ24", "gold", "GC")
    assert meta.ticker == "GCZ24"
    assert meta.asset == "gold"
    assert meta.contract_root == "GC"
    assert meta.contract_month == 12
    assert meta.contract_year == 2024
    assert meta.month_code == "Z"


def test_parse_contract_ticker_wti_january_2025() -> None:
    """parse_contract_ticker correctly parses CLF25."""
    meta = parse_contract_ticker("CLF25", "wti", "CL")
    assert meta.contract_month == 1
    assert meta.contract_year == 2025
    assert meta.month_code == "F"


def test_parse_contract_ticker_all_month_codes() -> None:
    """All 12 CME month codes parse to correct month integers."""
    expected = {
        "F": 1,
        "G": 2,
        "H": 3,
        "J": 4,
        "K": 5,
        "M": 6,
        "N": 7,
        "Q": 8,
        "U": 9,
        "V": 10,
        "X": 11,
        "Z": 12,
    }
    for code, month in expected.items():
        ticker = f"GC{code}25"
        meta = parse_contract_ticker(ticker, "gold", "GC")
        assert (
            meta.contract_month == month
        ), f"Month code '{code}' should parse to {month}, got {meta.contract_month}"


def test_parse_contract_ticker_invalid_month_code_raises() -> None:
    """parse_contract_ticker raises ValueError for invalid month code."""
    with pytest.raises(ValueError, match="month code"):
        parse_contract_ticker("GCA24", "gold", "GC")


def test_parse_contract_ticker_invalid_year_raises() -> None:
    """parse_contract_ticker raises ValueError for non-numeric year."""
    with pytest.raises(ValueError):
        parse_contract_ticker("GCXXX", "gold", "GC")


# ---------------------------------------------------------------------------
# FuturesContractSource tests
# ---------------------------------------------------------------------------


def test_futures_contract_source_fetch_reads_csv(tmp_config: Config) -> None:
    """FuturesContractSource.fetch() reads an existing CSV file."""
    raw_dir = Path(tmp_config.paths["contracts_raw"]) / "gold"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_df = _make_raw_csv_df(10)
    raw_df.to_csv(raw_dir / "GCZ24.csv", index=False)

    source = FuturesContractSource(tmp_config)
    result = source.fetch("gold", date(2024, 1, 1), date(2025, 1, 1), ticker="GCZ24")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 10
    assert "Close" in result.columns or "close" in result.columns


def test_futures_contract_source_fetch_raises_without_ticker(
    tmp_config: Config,
) -> None:
    """FuturesContractSource.fetch() raises ValueError when ticker is None."""
    source = FuturesContractSource(tmp_config)
    with pytest.raises(ValueError, match="explicit ticker"):
        source.fetch("gold", date(2024, 1, 1), date(2025, 1, 1), ticker=None)


def test_futures_contract_source_fetch_raises_for_missing_file(
    tmp_config: Config,
) -> None:
    """FuturesContractSource.fetch() raises FileNotFoundError for absent CSV."""
    source = FuturesContractSource(tmp_config)
    with pytest.raises(FileNotFoundError, match="acquire_contract_data"):
        source.fetch("gold", date(2024, 1, 1), date(2025, 1, 1), ticker="GCX99")


def test_futures_contract_source_list_available_tickers(
    tmp_config: Config,
) -> None:
    """list_available_tickers returns sorted list of CSV stems."""
    raw_dir = Path(tmp_config.paths["contracts_raw"]) / "gold"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for ticker in ["GCZ24", "GCF25", "GCG25"]:
        (raw_dir / f"{ticker}.csv").write_text("", encoding="utf-8")

    source = FuturesContractSource(tmp_config)
    tickers = source.list_available_tickers("gold")

    assert tickers == ["GCF25", "GCG25", "GCZ24"]


# ---------------------------------------------------------------------------
# ContractParquetStore tests
# ---------------------------------------------------------------------------


def test_contract_parquet_store_write_and_read_roundtrip(
    tmp_config: Config,
) -> None:
    """ContractParquetStore write then read returns identical DataFrame."""
    store = ContractParquetStore(tmp_config)
    df = _make_contract_ohlcv(15, "GCZ24")
    meta = ContractMetadata(
        ticker="GCZ24",
        asset="gold",
        contract_root="GC",
        contract_month=12,
        contract_year=2024,
        n_bars=15,
    )

    store.write(df, "gold", "GCZ24", meta)
    loaded = store.read("gold", "GCZ24")

    assert len(loaded) == len(df)
    # Parquet does not preserve DatetimeIndex frequency metadata — compare values only
    assert list(loaded["close"].values) == list(df["close"].values)


def test_contract_parquet_store_metadata_roundtrip(tmp_config: Config) -> None:
    """ContractParquetStore persists ContractMetadata in sidecar JSON."""
    store = ContractParquetStore(tmp_config)
    df = _make_contract_ohlcv(10, "CLF25")
    meta = ContractMetadata(
        ticker="CLF25",
        asset="wti",
        contract_root="CL",
        contract_month=1,
        contract_year=2025,
        n_bars=10,
    )

    store.write(df, "wti", "CLF25", meta)
    loaded_meta = store.read_metadata("wti", "CLF25")

    assert loaded_meta is not None
    assert loaded_meta.ticker == "CLF25"
    assert loaded_meta.contract_month == 1
    assert loaded_meta.contract_year == 2025
    assert loaded_meta.n_bars == 10


def test_contract_parquet_store_exists(tmp_config: Config) -> None:
    """ContractParquetStore.exists() returns False before write, True after."""
    store = ContractParquetStore(tmp_config)
    assert not store.exists("gold", "GCZ24")

    df = _make_contract_ohlcv(5)
    meta = ContractMetadata(
        ticker="GCZ24",
        asset="gold",
        contract_root="GC",
        contract_month=12,
        contract_year=2024,
    )
    store.write(df, "gold", "GCZ24", meta)
    assert store.exists("gold", "GCZ24")


def test_contract_parquet_store_list_tickers(tmp_config: Config) -> None:
    """ContractParquetStore.list_tickers() returns sorted list of written tickers."""
    store = ContractParquetStore(tmp_config)
    for ticker, month in [("GCF25", 1), ("GCG25", 2), ("GCH25", 3)]:
        df = _make_contract_ohlcv(5, ticker)
        meta = ContractMetadata(
            ticker=ticker,
            asset="gold",
            contract_root="GC",
            contract_month=month,
            contract_year=2025,
        )
        store.write(df, "gold", ticker, meta)

    tickers = store.list_tickers("gold")
    assert tickers == ["GCF25", "GCG25", "GCH25"]


# ---------------------------------------------------------------------------
# ContractDataLoader tests
# ---------------------------------------------------------------------------


def test_contract_data_loader_load_contract_fast_path(
    tmp_config: Config,
) -> None:
    """ContractDataLoader uses fast path when Parquet exists."""
    store = ContractParquetStore(tmp_config)
    df = _make_contract_ohlcv(20, "GCZ24")
    meta = ContractMetadata(
        ticker="GCZ24",
        asset="gold",
        contract_root="GC",
        contract_month=12,
        contract_year=2024,
        n_bars=20,
    )
    store.write(df, "gold", "GCZ24", meta)

    loader = ContractDataLoader(tmp_config)
    result = loader.load_contract("gold", "GCZ24")

    assert len(result) == 20
    assert isinstance(result.index, pd.DatetimeIndex)


def test_contract_data_loader_load_contract_slow_path(
    tmp_config: Config,
) -> None:
    """ContractDataLoader runs full pipeline when Parquet absent."""
    raw_dir = Path(tmp_config.paths["contracts_raw"]) / "gold"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_df = _make_raw_csv_df(15)
    raw_df.to_csv(raw_dir / "GCZ24.csv", index=False)

    loader = ContractDataLoader(tmp_config)
    result = loader.load_contract("gold", "GCZ24")

    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0
    store = ContractParquetStore(tmp_config)
    assert store.exists("gold", "GCZ24")


def test_contract_data_loader_load_curve_returns_sorted_contracts(
    tmp_config: Config,
) -> None:
    """ContractDataLoader.load_curve() returns contracts sorted by delivery date."""
    store = ContractParquetStore(tmp_config)
    for ticker, month in [("GCH25", 3), ("GCF25", 1), ("GCG25", 2)]:
        df = _make_contract_ohlcv(5, ticker)
        meta = ContractMetadata(
            ticker=ticker,
            asset="gold",
            contract_root="GC",
            contract_month=month,
            contract_year=2025,
        )
        store.write(df, "gold", ticker, meta)

    loader = ContractDataLoader(tmp_config)
    curve = loader.load_curve("gold", n_contracts=3, reference_date=date(2025, 1, 1))

    assert len(curve) == 3
    months = [meta.contract_month for meta, _ in curve]
    assert months == sorted(
        months
    ), "Curve must be sorted by delivery date (nearest first)"


def test_contract_data_loader_list_contracts_empty_for_new_asset(
    tmp_config: Config,
) -> None:
    """ContractDataLoader.list_contracts() returns empty list for asset with no data."""
    loader = ContractDataLoader(tmp_config)
    result = loader.list_contracts("copper")
    assert result == []


def test_contract_data_loader_load_curve_raises_when_no_contracts(
    tmp_config: Config,
) -> None:
    """ContractDataLoader.load_curve() raises ValueError when no data exists."""
    loader = ContractDataLoader(tmp_config)
    with pytest.raises(ValueError, match="acquire_contract_data"):
        loader.load_curve("silver", n_contracts=6)
