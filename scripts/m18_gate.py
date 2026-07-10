"""Module 18 end-to-end gate — Parquet vs ClickHouse equivalence check."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import clickhouse_connect  # noqa: E402
import pandas as pd  # noqa: E402

from src.core.config import Config  # noqa: E402
from src.data.clickhouse_store import ClickHouseStore  # noqa: E402
from src.data.loader import DataLoader  # noqa: E402
from src.data.store import ParquetStore  # noqa: E402

# Step 1: Verify ClickHouse connection
client = clickhouse_connect.get_client(
    host="localhost", port=8123, database="commodity_research"
)
version = client.query("SELECT version()").first_row[0]
print(f"ClickHouse version: {version}")

# Step 2: Check migration row counts
result = client.query(
    "SELECT asset, count() as rows, min(date) as start, max(date) as end "
    "FROM ohlcv_continuous GROUP BY asset ORDER BY asset"
)
print()
print("Migration verification:")
for row in result.result_rows:
    print(f"  {row[0]:<14}  {row[1]:>5} rows  {row[2]} to {row[3]}")
client.close()

# Step 3: Parquet vs ClickHouse numerical equivalence
config_parquet = Config.load("config/")
assert config_parquet.storage_backend == "parquet"
loader_parquet = DataLoader(config_parquet)
assert isinstance(loader_parquet._store, ParquetStore)

config_ch = Config.load("config/")
config_ch._config.setdefault("storage", {})["backend"] = "clickhouse"
assert config_ch.storage_backend == "clickhouse"
loader_ch = DataLoader(config_ch)
assert isinstance(loader_ch._store, ClickHouseStore)

assets = ["gold", "silver", "copper", "wti", "brent", "natural_gas"]
print()
print("Parquet vs ClickHouse equivalence:")
for asset in assets:
    df_parquet = loader_parquet.load(asset)
    df_ch = loader_ch.load(asset)
    assert len(df_parquet) == len(
        df_ch
    ), f"{asset}: row count mismatch Parquet={len(df_parquet)} CH={len(df_ch)}"
    for col in ["open", "high", "low", "close", "volume"]:
        pd.testing.assert_series_equal(
            df_parquet[col].reset_index(drop=True),
            df_ch[col].reset_index(drop=True),
            check_names=False,
            rtol=1e-6,
        )
    print(f"  {asset:<14}  {len(df_parquet)} rows  MATCH")

print()
print(f"Backend (Parquet):    {type(loader_parquet._store).__name__}")
print(f"Backend (ClickHouse): {type(loader_ch._store).__name__}")
print()
print("Module 18 end-to-end gate: PASSED")
