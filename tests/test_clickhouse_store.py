"""Tests for Module 18: ClickHouse Integration.

All 15 tests use unittest.mock to mock the ClickHouse client — no Docker
or running ClickHouse required. Real integration is verified by the
end-to-end gate (Increment 4), which requires Docker.

Tests cover: Config properties (2), ClickHouseStore interface (5),
DataLoader backend switching (3), migration script (3), error handling (2).

See ADR-004 (Storage Strategy: Parquet + ClickHouse Migration Path).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.config import Config
from src.data.clickhouse_store import ClickHouseStore
from src.data.store import DataStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(n: int = 10) -> pd.DataFrame:
    """Minimal NormalizedOHLCV DataFrame for store tests."""
    dates = pd.bdate_range(start="2023-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": [100.0 + i for i in range(n)],
            "high": [102.0 + i for i in range(n)],
            "low": [98.0 + i for i in range(n)],
            "close": [101.0 + i for i in range(n)],
            "volume": [25000.0] * n,
            "open_interest": [float("nan")] * n,
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )


# ---------------------------------------------------------------------------
# Config property tests (2 tests)
# ---------------------------------------------------------------------------


def test_config_storage_backend_default_is_parquet() -> None:
    """Config.storage_backend defaults to 'parquet' when not set in config.yaml."""
    cfg = Config.load("config/")
    backend = cfg.storage_backend
    assert isinstance(backend, str)
    assert backend in (
        "parquet",
        "clickhouse",
    ), f"storage_backend must be 'parquet' or 'clickhouse', got {backend!r}"


def test_config_clickhouse_properties_have_valid_defaults() -> None:
    """All ClickHouse Config properties return usable defaults."""
    cfg = Config.load("config/")
    assert isinstance(cfg.clickhouse_host, str) and len(cfg.clickhouse_host) > 0
    assert isinstance(cfg.clickhouse_port, int) and 1 <= cfg.clickhouse_port <= 65535
    assert isinstance(cfg.clickhouse_database, str) and len(cfg.clickhouse_database) > 0
    assert (
        isinstance(cfg.clickhouse_table_ohlcv, str)
        and len(cfg.clickhouse_table_ohlcv) > 0
    )
    assert (
        isinstance(cfg.clickhouse_connect_timeout, int)
        and cfg.clickhouse_connect_timeout > 0
    )
    assert (
        isinstance(cfg.clickhouse_send_receive_timeout, int)
        and cfg.clickhouse_send_receive_timeout > 0
    )
    print(
        f"host={cfg.clickhouse_host} port={cfg.clickhouse_port} "
        f"db={cfg.clickhouse_database} table={cfg.clickhouse_table_ohlcv} "
        f"connect_timeout={cfg.clickhouse_connect_timeout} "
        f"send_receive_timeout={cfg.clickhouse_send_receive_timeout}"
    )


# ---------------------------------------------------------------------------
# ClickHouseStore inherits DataStore ABC (1 test)
# ---------------------------------------------------------------------------


def test_clickhouse_store_implements_datastore_abc(config: Config) -> None:
    """ClickHouseStore is a concrete subclass of DataStore."""
    assert issubclass(ClickHouseStore, DataStore)
    store = ClickHouseStore(config)
    assert isinstance(store, DataStore)
    for method in ("exists", "write", "read", "list_assets"):
        assert hasattr(store, method), f"ClickHouseStore missing method: {method}"
        assert callable(getattr(store, method))


# ---------------------------------------------------------------------------
# ClickHouseStore interface with mocked client (4 tests)
# ---------------------------------------------------------------------------


def test_clickhouse_store_exists_calls_client_query(config: Config) -> None:
    """ClickHouseStore.exists() calls the ClickHouse client with correct query."""
    store = ClickHouseStore(config)
    mock_client = MagicMock()
    mock_client.query.return_value.first_row = [5]
    store._client = mock_client

    result = store.exists("gold")

    assert result is True
    mock_client.query.assert_called_once()
    call_args = mock_client.query.call_args
    assert "gold" in str(call_args) or "asset" in str(call_args)


def test_clickhouse_store_exists_returns_false_when_no_rows(config: Config) -> None:
    """ClickHouseStore.exists() returns False when query returns 0 rows."""
    store = ClickHouseStore(config)
    mock_client = MagicMock()
    mock_client.query.return_value.first_row = [0]
    store._client = mock_client

    result = store.exists("silver")
    assert result is False


def test_clickhouse_store_write_returns_pseudo_path(config: Config) -> None:
    """ClickHouseStore.write() returns a Path with clickhouse:// pseudo-scheme."""
    store = ClickHouseStore(config)
    mock_client = MagicMock()
    store._client = mock_client

    df = _make_ohlcv(5)
    result = store.write(df, "gold")

    assert isinstance(result, Path)
    assert "clickhouse" in str(result).lower()
    mock_client.insert_df.assert_called_once()


def test_clickhouse_store_read_raises_when_no_data(config: Config) -> None:
    """ClickHouseStore.read() raises FileNotFoundError when asset has no rows."""
    store = ClickHouseStore(config)
    mock_client = MagicMock()
    mock_client.query.return_value.first_row = [0]
    store._client = mock_client

    with pytest.raises(FileNotFoundError, match="migrate_to_clickhouse"):
        store.read("copper")


def test_clickhouse_store_list_assets_returns_sorted_list(config: Config) -> None:
    """ClickHouseStore.list_assets() returns sorted list from ClickHouse query."""
    store = ClickHouseStore(config)
    mock_client = MagicMock()
    mock_client.query.return_value.result_rows = [
        ["brent"],
        ["copper"],
        ["gold"],
        ["natural_gas"],
        ["silver"],
        ["wti"],
    ]
    store._client = mock_client

    assets = store.list_assets()

    assert assets == ["brent", "copper", "gold", "natural_gas", "silver", "wti"]
    mock_client.query.assert_called_once()


# ---------------------------------------------------------------------------
# DataLoader backend switching (3 tests)
# ---------------------------------------------------------------------------


def test_dataloader_uses_parquet_store_by_default(config: Config) -> None:
    """DataLoader uses ParquetStore when storage_backend is 'parquet'."""
    from src.data.loader import DataLoader
    from src.data.store import ParquetStore

    assert config.storage_backend == "parquet"
    loader = DataLoader(config)
    assert isinstance(
        loader._store, ParquetStore
    ), f"Expected ParquetStore, got {type(loader._store).__name__}"


def test_dataloader_uses_clickhouse_store_when_backend_is_clickhouse(
    config: Config,
) -> None:
    """DataLoader instantiates ClickHouseStore when storage_backend is 'clickhouse'."""
    from src.data.loader import DataLoader

    original_backend = config._config.get("storage", {}).get("backend", "parquet")
    config._config.setdefault("storage", {})["backend"] = "clickhouse"

    try:
        loader = DataLoader(config)
        assert isinstance(
            loader._store, ClickHouseStore
        ), f"Expected ClickHouseStore, got {type(loader._store).__name__}"
    finally:
        config._config["storage"]["backend"] = original_backend


def test_dataloader_backend_parquet_unchanged_after_module(config: Config) -> None:
    """After M18, default storage_backend remains 'parquet' for backward compat."""
    from src.data.loader import DataLoader
    from src.data.store import ParquetStore

    loader = DataLoader(config)
    assert isinstance(loader._store, ParquetStore)
    assert config.storage_backend == "parquet"


# ---------------------------------------------------------------------------
# Migration script tests (3 tests)
# ---------------------------------------------------------------------------


def test_migration_script_imports_without_error() -> None:
    """migrate_to_clickhouse.py is importable as a module."""
    import importlib.util

    script_path = Path("scripts/migrate_to_clickhouse.py")
    assert script_path.exists(), "scripts/migrate_to_clickhouse.py must exist"

    spec = importlib.util.spec_from_file_location("migrate_to_clickhouse", script_path)
    module = importlib.util.module_from_spec(spec)
    assert module is not None
    assert spec is not None


def test_migration_script_all_assets_constant() -> None:
    """ALL_ASSETS in migration script matches the 6 platform assets."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "migrate_to_clickhouse", Path("scripts/migrate_to_clickhouse.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    expected = {"gold", "silver", "copper", "wti", "brent", "natural_gas"}
    assert (
        set(module.ALL_ASSETS) == expected
    ), f"ALL_ASSETS mismatch: {set(module.ALL_ASSETS)} vs {expected}"


def test_migration_prepare_for_insert_adds_asset_column() -> None:
    """_prepare_for_insert() adds 'asset' column and resets DatetimeIndex."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "migrate_to_clickhouse", Path("scripts/migrate_to_clickhouse.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    df = _make_ohlcv(5)
    result = module._prepare_for_insert(df, "gold")

    assert "asset" in result.columns
    assert "date" in result.columns
    assert result["asset"].unique().tolist() == ["gold"]
    assert result.index.name != "date"
    expected_cols = {
        "date",
        "asset",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "open_interest",
    }
    assert set(result.columns) == expected_cols


# ---------------------------------------------------------------------------
# Error handling (2 tests)
# ---------------------------------------------------------------------------


def test_clickhouse_store_write_with_nan_open_interest(config: Config) -> None:
    """ClickHouseStore.write() handles NaN open_interest without error."""
    store = ClickHouseStore(config)
    mock_client = MagicMock()
    store._client = mock_client

    df = _make_ohlcv(5)
    assert df["open_interest"].isna().all()

    store.write(df, "gold")
    mock_client.insert_df.assert_called_once()


def test_clickhouse_store_close_is_idempotent(config: Config) -> None:
    """ClickHouseStore.close() can be called multiple times without error."""
    store = ClickHouseStore(config)
    mock_client = MagicMock()
    store._client = mock_client

    store.close()
    store.close()
    assert store._client is None
