# ClickHouse Operator Runbook

Operator guide for the local ClickHouse instance used by the Commodity Systematic Research Platform (Phase 3 storage backend). For architectural context see ADR-004 (Parquet + ClickHouse migration path).

---

## Infrastructure overview

| Item | Value |
|------|-------|
| Docker service | `clickhouse` (Compose) |
| Container name | `commodity_research_clickhouse` |
| Image | `clickhouse/clickhouse-server:24.3-alpine` |
| Named volume | `commodity_research_clickhouse_data` (Compose key: `clickhouse_data`) |
| HTTP interface | `http://localhost:8123` (used by `clickhouse-connect`) |
| Native TCP | `localhost:9000` (used by `clickhouse-client`) |
| Database | `commodity_research` |
| Primary table | `ohlcv_continuous` |
| Config mount | `./docker/clickhouse/config.xml` → `/etc/clickhouse-server/config.d/custom.xml` |

**Table `ohlcv_continuous`**

- Engine: `ReplacingMergeTree()` — rows with the same `(asset, date)` are deduplicated on merge/compaction; re-inserts are safe (idempotent migration and writes).
- `ORDER BY (asset, date)` — efficient per-asset range scans.
- Columns: `date`, `asset` (`LowCardinality(String)`), OHLCV floats, `open_interest` as `Nullable(Float64)` (Yahoo Finance does not supply OI; values are null/NaN for current assets).

**Health check:** `curl http://localhost:8123/ping` should return `Ok.`

---

## First-time setup

Run from the repository root with Docker Desktop running and the project `.venv` activated.

### 1. Start ClickHouse

```powershell
docker compose up -d
docker compose ps
docker compose logs -f clickhouse
```

Wait until the health check passes (or `ping` returns `Ok.`).

### 2. Install Python dependency (if not already in `.venv`)

```powershell
.venv\Scripts\pip install clickhouse-connect
```

(`clickhouse-connect` is also declared in `pyproject.toml`.)

### 3. Create database and schema

```powershell
python scripts/setup_clickhouse_schema.py
```

Optional flags: `--host`, `--port`, `--database`, `--drop-existing` (destructive — drops tables before recreate).

The script connects without a database first, runs `CREATE DATABASE IF NOT EXISTS commodity_research`, then creates `ohlcv_continuous`. This is required on ClickHouse 24.3 (see notes below).

### 4. Migrate Parquet → ClickHouse

Ensure processed continuous Parquet files exist under `data/processed/continuous/` (run `python scripts/acquire_data.py` if needed).

```powershell
python scripts/migrate_to_clickhouse.py
```

Options: `--assets gold silver ...`, `--dry-run`, `--host`, `--port`, `--database`, `--table`.

On Windows, if the migration summary prints garbled checkmarks, set UTF-8 for stdout first:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python scripts/migrate_to_clickhouse.py
```

### 5. Module 18 gate (Parquet vs ClickHouse equivalence)

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts/m18_gate.py
```

Expect version `24.3.x`, per-asset row counts, and `MATCH` for all six assets on OHLCV columns with `rtol=1e-6`.

---

## Daily usage

### Container lifecycle

```powershell
docker compose up -d          # start
docker compose stop           # stop (data kept in volume)
docker compose down           # remove container, keep volume
docker compose down -v        # DESTRUCTIVE: delete volume and all CH data
docker compose logs -f clickhouse
```

### Client access

HTTP ping:

```powershell
curl http://localhost:8123/ping
```

Via Docker (native client):

```powershell
docker exec -it commodity_research_clickhouse clickhouse-client --database commodity_research
```

### Useful SQL

Row counts by asset:

```sql
SELECT asset, count() AS rows, min(date) AS start, max(date) AS end
FROM ohlcv_continuous
GROUP BY asset
ORDER BY asset;
```

Total rows:

```sql
SELECT count() FROM ohlcv_continuous;
```

Latest dates:

```sql
SELECT asset, max(date) AS last_date
FROM ohlcv_continuous
GROUP BY asset
ORDER BY asset;
```

Force deduplication after repeated inserts (ReplacingMergeTree):

```sql
OPTIMIZE TABLE ohlcv_continuous FINAL;
```

For reads that must see deduplicated rows immediately, query with `FINAL` (heavier than normal reads):

```sql
SELECT * FROM ohlcv_continuous FINAL WHERE asset = 'gold' ORDER BY date LIMIT 10;
```

### Application backend switch

Default backend is Parquet. To use ClickHouse for `DataLoader` reads/writes, edit `config/config.yaml`:

```yaml
storage:
  backend: "clickhouse"   # or "parquet"
  clickhouse:
    host: "localhost"
    port: 8123
    database: "commodity_research"
    table_ohlcv: "ohlcv_continuous"
    connect_timeout: 10
    send_receive_timeout: 30
```

Restart any long-running processes after changing config. `DataLoader` selects `ClickHouseStore` vs `ParquetStore` based on `storage.backend` only; feature pipelines and research code stay unchanged.

### Re-migration / refresh

Safe to re-run `migrate_to_clickhouse.py` — ReplacingMergeTree handles duplicate `(asset, date)` keys. Run `OPTIMIZE TABLE ohlcv_continuous FINAL` if you need immediate deduplication for ad-hoc SQL.

---

## Data recovery

| Scenario | Action |
|----------|--------|
| ClickHouse empty but Parquet intact | `docker compose up -d` → `setup_clickhouse_schema.py` → `migrate_to_clickhouse.py` |
| Corrupt or wrong CH data | `setup_clickhouse_schema.py --drop-existing` then migrate again from Parquet |
| Lost Docker volume | Recreate container (`docker compose up -d`), schema + migrate from Parquet |
| Parquet is source of truth | Platform always retains Parquet under `data/processed/continuous/`; ClickHouse is an analytical copy |

Parquet files are the canonical offline store until production cutover; do not delete them when experimenting with ClickHouse.

---

## Windows-specific notes

1. **UTF-8 / migration summary icons** — PowerShell’s default code page may mangle Unicode checkmarks in `migrate_to_clickhouse.py` output. Use `$env:PYTHONIOENCODING = "utf-8"` (or `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`) before running migration or gate scripts.

2. **PowerShell command chaining** — Use `;` to separate commands on one line, not `&&` (unless PowerShell 7+). Example: `$env:PYTHONPATH = (Get-Location).Path; python scripts/m18_gate.py`

3. **PYTHONPATH** — From repo root: `$env:PYTHONPATH = (Get-Location).Path` so `import src...` works when invoking scripts directly.

4. **Paths** — Prefer forward slashes in YAML; Docker Compose bind-mounts use `./docker/clickhouse/config.xml` relative to the repo root.

5. **Line endings** — Keep shell scripts and Compose files LF if CI/Linux teammates consume the same repo.

---

## ClickHouse 24.3 notes

- **Version:** Local image tag `24.3-alpine`; gate and setup log `SELECT version()` (e.g. `24.3.18.7`).
- **`CREATE DATABASE IF NOT EXISTS`:** Required in `setup_clickhouse_schema.py`. The `CLICKHOUSE_DB: commodity_research` environment variable in `docker-compose.yml` does **not** reliably auto-create the database on 24.3 — always bootstrap explicitly before connecting with `database=commodity_research`.
- **`ReplacingMergeTree`:** Inserts are append-only; duplicates collapse on background merge or after `OPTIMIZE ... FINAL`. Application code treats writes as idempotent.
- **`Nullable(open_interest)`:** Matches Parquet/NormalizedOHLCV where OI is missing; inserts map NaN to null.
- **`clickhouse-connect`:** Uses HTTP port 8123; `send_receive_timeout` is configurable via `config.yaml` (see `Config.clickhouse_send_receive_timeout`).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| `Cannot connect to ClickHouse` | Container down or port blocked | `docker compose up -d`; check `8123` not in use |
| `ping` fails | Health check still starting | Wait 30s; `docker compose logs clickhouse` |
| `Database commodity_research doesn't exist` | Skipped schema setup | Run `python scripts/setup_clickhouse_schema.py` |
| `Table ohlcv_continuous doesn't exist` | Schema not applied | Run setup script (not migrate alone) |
| Migration `FileNotFoundError` for Parquet | Missing processed data | Run data acquisition / pipeline to populate `data/processed/continuous/` |
| Row count lower than Parquet | Partial migrate | Re-run migrate without `--assets` filter or add missing assets |
| Duplicate-looking rows in SQL | ReplacingMergeTree not merged | `OPTIMIZE TABLE ohlcv_continuous FINAL` or use `FINAL` in query |
| `DataLoader` still uses Parquet | Config unchanged | Set `storage.backend: clickhouse` in `config/config.yaml` |
| Gate `row count mismatch` | Stale CH data | Re-migrate; verify six assets |
| Gate float mismatch | Precision / partial load | Re-migrate asset; check `rtol=1e-6` columns only (OHLCV) |
| Garbled ✓/✗ in migration summary | Windows console encoding | `$env:PYTHONIOENCODING = "utf-8"` |
| `clickhouse-connect not installed` | Missing package | `.venv\Scripts\pip install clickhouse-connect` |
| Slow large scans | Default timeout | Increase `storage.clickhouse.send_receive_timeout` in config |

---

## Related scripts and docs

- `scripts/setup_clickhouse_schema.py` — DDL and database bootstrap
- `scripts/migrate_to_clickhouse.py` — Parquet → ClickHouse load
- `scripts/m18_gate.py` — Parquet vs ClickHouse numerical equivalence
- `src/data/clickhouse_store.py` — `DataStore` implementation
- `docs/implementation_notes/M18-clickhouse-integration.md` — module implementation record
