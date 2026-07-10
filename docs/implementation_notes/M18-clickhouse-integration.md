---
# M18 Implementation Notes - ClickHouse Integration

**Date:** 2026-07-10
**Branch:** module/M18-clickhouse-integration
**Tests:** 264 passing (248 baseline + 16 new)
**Tag:** M18-complete (after merge)

## Files Created
- docker-compose.yml - Local ClickHouse 24.3-alpine service and named volume
- docker/clickhouse/config.xml - Server config overlay (mounted read-only)
- scripts/setup_clickhouse_schema.py - Database bootstrap and ohlcv_continuous DDL
- scripts/migrate_to_clickhouse.py - Parquet to ClickHouse migration CLI
- scripts/m18_gate.py - Parquet vs ClickHouse end-to-end equivalence gate
- src/data/clickhouse_store.py - ClickHouseStore (DataStore ABC)
- tests/test_clickhouse_store.py - 16 tests (config, store, loader backend, migration helpers)
- docs/clickhouse/SETUP.md - Operator runbook
- docs/implementation_notes/M18-clickhouse-integration.md

## Files Modified
- config/config.yaml - storage.backend and storage.clickhouse section
- pyproject.toml - clickhouse-connect dependency
- src/core/config.py - storage_backend and ClickHouse connection properties (incl. send_receive_timeout)
- src/data/loader.py - ClickHouseStore vs ParquetStore selection in __init__

## Design Decisions
- Parquet remains default backend; ClickHouse is opt-in via config.yaml (ADR-004 migration path).
- ClickHouseStore implements the existing DataStore ABC so DataLoader, features, and research layers are unchanged.
- clickhouse-connect over HTTP (port 8123); lazy client initialization with connect and send/receive timeouts from config.
- ohlcv_continuous uses ReplacingMergeTree ordered by (asset, date) for idempotent inserts and re-migration.
- open_interest stored as Nullable(Float64) to match Yahoo-sourced NormalizedOHLCV (no OI field).
- Phase 3 scope: continuous OHLCV only; contract-level Parquet is out of scope for M18.
- setup_clickhouse_schema.py bootstraps CREATE DATABASE IF NOT EXISTS before DDL (ClickHouse 24.3 requirement).
- write() returns a pseudo-path (clickhouse://...) to satisfy the DataStore ABC without implying a filesystem location.

## End-to-End Gate Output
```
ClickHouse version: 24.3.18.7

Migration verification:
  brent           4118 rows  2010-01-04 to 2026-07-02
  copper          4149 rows  2010-01-04 to 2026-07-02
  gold            4148 rows  2010-01-04 to 2026-07-02
  natural_gas     4150 rows  2010-01-04 to 2026-07-02
  silver          4148 rows  2010-01-04 to 2026-07-02
  wti             4149 rows  2010-01-04 to 2026-07-02

Parquet vs ClickHouse equivalence:
  gold            4148 rows  MATCH
  silver          4148 rows  MATCH
  copper          4149 rows  MATCH
  wti             4149 rows  MATCH
  brent           4118 rows  MATCH
  natural_gas     4150 rows  MATCH

Backend (Parquet):    ParquetStore
Backend (ClickHouse): ClickHouseStore

Module 18 end-to-end gate: PASSED
```

Total migrated rows: 24,862 (6 assets). OHLCV columns compared with pandas.testing.assert_series_equal rtol=1e-6.

## Technical Debt
None.

## Deviations from Transfer Package
1. Test count is 16 new tests, not 15 — added test_clickhouse_store_close_is_idempotent for client lifecycle.
2. Explicit CREATE DATABASE IF NOT EXISTS in setup_clickhouse_schema.py (CLICKHOUSE_DB env unreliable on 24.3).
3. Logger initialized before backend switch branch in DataLoader.__init__ so ClickHouse path can log at INFO.
4. DataStore type annotation on self._store in DataLoader for mypy (ClickHouseStore | ParquetStore via ABC).
5. send_receive_timeout exposed as Config property and wired to clickhouse-connect (Tech Lead ruling).
6. Windows UTF-8: migration summary checkmarks require PYTHONIOENCODING=utf-8 (documented in SETUP.md).

## Open Questions
None.
---
