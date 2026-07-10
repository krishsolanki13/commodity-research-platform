"""Migrate processed Parquet data to ClickHouse.

Reads all continuous OHLCV Parquet files from data/processed/continuous/
and inserts rows into the ClickHouse ohlcv_continuous table.

Idempotent: ReplacingMergeTree deduplicates on (asset, date). Re-running
is safe — existing rows will be replaced on the next ClickHouse compaction.
To force immediate deduplication: OPTIMIZE TABLE ohlcv_continuous FINAL

Requires:
    - ClickHouse container running (docker compose up -d)
    - Schema created (python scripts/setup_clickhouse_schema.py)
    - Parquet files present in data/processed/continuous/
    - clickhouse-connect installed in .venv

Usage (from project root with .venv active):
    python scripts/migrate_to_clickhouse.py
    python scripts/migrate_to_clickhouse.py --assets gold silver
    python scripts/migrate_to_clickhouse.py --dry-run    (show what would be migrated)

See ADR-004 (Storage Strategy: Parquet + ClickHouse Migration Path).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

CONTINUOUS_PARQUET_DIR = project_root / "data" / "processed" / "continuous"
ALL_ASSETS = ["gold", "silver", "copper", "wti", "brent", "natural_gas"]


def _load_parquet(asset: str) -> pd.DataFrame:
    """Read the processed Parquet file for an asset."""
    path = CONTINUOUS_PARQUET_DIR / f"{asset}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"No Parquet file found for {asset} at {path}. "
            "Run: python scripts/acquire_data.py"
        )
    df = pd.read_parquet(path, engine="pyarrow")
    return df


def _prepare_for_insert(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """Prepare a NormalizedOHLCV DataFrame for ClickHouse insertion.

    Steps:
        1. Add 'asset' column
        2. Convert UTC DatetimeIndex to Date column (ClickHouse Date type)
        3. Convert open_interest NaN to None (ClickHouse Nullable)
        4. Reorder columns to match DDL schema
    """
    insert_df = df.copy()

    # Normalize index: strip timezone, convert to date
    if hasattr(insert_df.index, "tz") and insert_df.index.tz is not None:
        insert_df.index = insert_df.index.tz_localize(None)
    insert_df.index = pd.DatetimeIndex(insert_df.index).normalize()
    insert_df.index.name = "date"
    insert_df = insert_df.reset_index()

    insert_df["asset"] = asset

    # Ensure open_interest column exists (may be missing in some Parquet files)
    if "open_interest" not in insert_df.columns:
        insert_df["open_interest"] = None

    # Column order must match DDL: date, asset, open, high, low, close, volume, open_interest
    return insert_df[
        ["date", "asset", "open", "high", "low", "close", "volume", "open_interest"]
    ]


def migrate_asset(
    asset: str,
    client: object,
    table: str = "ohlcv_continuous",
    dry_run: bool = False,
) -> dict[str, object]:
    """Migrate one asset from Parquet to ClickHouse.

    Returns a status dict with keys: asset, rows, status, error.
    """
    try:
        df = _load_parquet(asset)
        insert_df = _prepare_for_insert(df, asset)

        if dry_run:
            logger.info(
                "DRY RUN: would insert %d rows for %s",
                len(insert_df),
                asset,
            )
            return {
                "asset": asset,
                "rows": len(insert_df),
                "status": "dry_run",
                "error": None,
            }

        client.insert_df(table, insert_df)  # type: ignore[attr-defined]

        # Verify row count
        count_result = client.query(  # type: ignore[attr-defined]
            f"SELECT count() FROM {table} WHERE asset = {{asset:String}}",
            parameters={"asset": asset},
        )
        row_count = count_result.first_row[0]

        logger.info(
            "Migrated %s: %d rows inserted, %d rows in ClickHouse",
            asset,
            len(insert_df),
            row_count,
        )
        return {"asset": asset, "rows": len(insert_df), "status": "OK", "error": None}

    except Exception as exc:  # noqa: BLE001
        logger.error("Migration failed for %s: %s", asset, exc)
        return {"asset": asset, "rows": 0, "status": "FAILED", "error": str(exc)}


def migrate_all(
    assets: list[str] | None = None,
    host: str = "localhost",
    port: int = 8123,
    database: str = "commodity_research",
    table: str = "ohlcv_continuous",
    dry_run: bool = False,
) -> None:
    """Migrate all specified assets from Parquet to ClickHouse."""
    if assets is None:
        assets = ALL_ASSETS

    try:
        import clickhouse_connect
    except ImportError:
        logger.error(
            "clickhouse-connect not installed. Run: .venv\\Scripts\\pip install clickhouse-connect"
        )
        sys.exit(1)

    if not dry_run:
        try:
            client = clickhouse_connect.get_client(
                host=host, port=port, database=database, connect_timeout=10
            )
        except Exception as exc:
            logger.error(
                "Cannot connect to ClickHouse: %s\n"
                "Start container: docker compose up -d",
                exc,
            )
            sys.exit(1)
    else:
        client = None

    results = []
    for asset in assets:
        results.append(migrate_asset(asset, client, table=table, dry_run=dry_run))

    if client is not None:
        client.close()

    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    for r in results:
        status_icon = "✓" if r["status"] in ("OK", "dry_run") else "✗"
        print(
            f"  {status_icon}  {r['asset']:<14}  {r['rows']:>5} rows  [{r['status']}]"
        )
        if r["error"]:
            print(f"       Error: {r['error']}")
    print("=" * 60)
    print(f"\nTarget: {host}:{port}/{database}.{table}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Parquet data to ClickHouse.")
    parser.add_argument("--assets", nargs="+", choices=ALL_ASSETS, default=None)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--database", default="commodity_research")
    parser.add_argument("--table", default="ohlcv_continuous")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be migrated"
    )
    args = parser.parse_args()

    migrate_all(
        assets=args.assets,
        host=args.host,
        port=args.port,
        database=args.database,
        table=args.table,
        dry_run=args.dry_run,
    )
