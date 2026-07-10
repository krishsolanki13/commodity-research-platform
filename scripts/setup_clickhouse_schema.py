"""ClickHouse schema setup for the Commodity Systematic Research Platform.

Creates all required tables. Idempotent — safe to run multiple times.
Must be run before migrate_to_clickhouse.py.

Requires:
    - Docker ClickHouse container running (docker compose up -d)
    - clickhouse-connect installed in .venv

Usage (from project root with .venv active):
    python scripts/setup_clickhouse_schema.py
    python scripts/setup_clickhouse_schema.py --drop-existing  # DROP + recreate (destructive)
    python scripts/setup_clickhouse_schema.py --host localhost --port 8123

Table design notes:
    ohlcv_continuous:
        Engine: ReplacingMergeTree — deduplicates rows with same (asset, date) on
            compaction. Idempotent inserts are safe — re-migration never creates
            duplicates after FINAL or OPTIMIZE TABLE.
        Primary key: (asset, date) — supports per-asset range scans and
            full-table scans efficiently.
        open_interest: Nullable(Float64) — Yahoo Finance does not provide OI;
            this column is NaN for all current assets.

See ADR-004 (Storage Strategy: Parquet + ClickHouse Migration Path).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# DDL for all platform tables
SCHEMA_DDL: dict[str, str] = {
    "ohlcv_continuous": """
        CREATE TABLE IF NOT EXISTS ohlcv_continuous (
            date             Date,
            asset            LowCardinality(String),
            open             Float64,
            high             Float64,
            low              Float64,
            close            Float64,
            volume           Float64,
            open_interest    Nullable(Float64)
        ) ENGINE = ReplacingMergeTree()
        ORDER BY (asset, date)
        SETTINGS index_granularity = 8192
        COMMENT 'Continuous futures OHLCV series — one row per asset per trading day.'
    """,
}

DROP_DDL: dict[str, str] = {
    table: f"DROP TABLE IF EXISTS {table}" for table in SCHEMA_DDL
}


def setup_schema(
    host: str = "localhost",
    port: int = 8123,
    database: str = "commodity_research",
    drop_existing: bool = False,
) -> None:
    """Create (or recreate) the ClickHouse schema.

    Args:
        host: ClickHouse server hostname.
        port: ClickHouse HTTP interface port.
        database: Target database name.
        drop_existing: If True, DROP all tables before creating.
            Destructive — all data will be lost.
    """
    try:
        import clickhouse_connect
    except ImportError:
        logger.error(
            "clickhouse-connect not installed. Run: .venv\\Scripts\\pip install clickhouse-connect"
        )
        sys.exit(1)

    logger.info("Connecting to ClickHouse at %s:%d (database=%s)", host, port, database)

    try:
        # Connect without database first to ensure it exists.
        # CLICKHOUSE_DB env var does not reliably auto-create the database
        # in ClickHouse 24.3 — create it explicitly before connecting to it.
        bootstrap_client = clickhouse_connect.get_client(
            host=host,
            port=port,
            connect_timeout=10,
        )
        bootstrap_client.command(f"CREATE DATABASE IF NOT EXISTS {database}")
        bootstrap_client.close()
        logger.info("Database ready: %s", database)

        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            database=database,
            connect_timeout=10,
        )
    except Exception as exc:
        logger.error(
            "Cannot connect to ClickHouse: %s\n"
            "Ensure the container is running: docker compose up -d",
            exc,
        )
        sys.exit(1)

    version = client.query("SELECT version()").first_row[0]
    logger.info("Connected — ClickHouse %s", version)

    if drop_existing:
        logger.warning(
            "--drop-existing specified: dropping all tables (DATA WILL BE LOST)"
        )
        for table, ddl in DROP_DDL.items():
            client.command(ddl)
            logger.info("Dropped table: %s", table)

    for table, ddl in SCHEMA_DDL.items():
        client.command(ddl)
        # Verify by checking row count
        count = client.query(f"SELECT count() FROM {table}").first_row[0]
        logger.info("Table ready: %s (%d existing rows)", table, count)

    client.close()
    logger.info("Schema setup complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up ClickHouse schema.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--database", default="commodity_research")
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="DROP all tables before creating. DESTRUCTIVE — all data lost.",
    )
    args = parser.parse_args()

    setup_schema(
        host=args.host,
        port=args.port,
        database=args.database,
        drop_existing=args.drop_existing,
    )
