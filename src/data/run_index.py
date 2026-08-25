"""SQLite run index for fast GET /api/runs queries.

Replaces synchronous per-file metrics.json reads with a single
SQLite query. Index is updated on every RunManager.save_metrics() call.

Schema mirrors the fields currently returned by GET /api/runs.
Full run artifacts remain in data/runs/{run_id}/ unchanged.

The index file lives at {runs_dir}/index.db so tests that redirect
_runs_dir() get an isolated index instead of the production database.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_RUNS_DIR = Path("data/runs")


def _index_path(runs_dir: Path | None = None) -> Path:
    return (runs_dir if runs_dir is not None else _DEFAULT_RUNS_DIR) / "index.db"


@contextmanager
def _get_connection(runs_dir: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Get a SQLite connection. Always closed on exit (Windows file locks)."""
    path = _index_path(runs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    # WAL for concurrent reads in production; DELETE on Windows so
    # TemporaryDirectory tests can unlink index.db after the request.
    if os.name == "nt":
        conn.execute("PRAGMA journal_mode=DELETE")
    else:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_schema(runs_dir: Path | None = None) -> None:
    """Create index table if it does not exist."""
    with _get_connection(runs_dir) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id          TEXT PRIMARY KEY,
                asset           TEXT,
                strategy        TEXT,
                executed_at     TEXT,
                is_portfolio    INTEGER DEFAULT 0,
                sharpe          REAL,
                total_return    REAL,
                max_drawdown    REAL,
                n_trades        INTEGER,
                win_rate        REAL,
                cagr            REAL,
                from_date       TEXT,
                to_date         TEXT,
                ic              REAL,
                ic_band         TEXT,
                metrics_json    TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_executed_at ON runs(executed_at DESC)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy ON runs(strategy)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_asset ON runs(asset)")
        conn.commit()
    logger.debug("Run index schema ensured at %s", _index_path(runs_dir))


def _scalar(metrics: dict[str, Any]) -> dict[str, Any]:
    raw = metrics.get("scalar_metrics")
    return raw if isinstance(raw, dict) else {}


def _signal(metrics: dict[str, Any]) -> dict[str, Any]:
    raw = metrics.get("signal_metrics")
    return raw if isinstance(raw, dict) else {}


def _trade_stats(metrics: dict[str, Any]) -> dict[str, Any]:
    raw = metrics.get("trade_statistics")
    return raw if isinstance(raw, dict) else {}


def _n_trades(metrics: dict[str, Any]) -> int:
    scalar = _scalar(metrics)
    trades = _trade_stats(metrics)
    raw = scalar.get("n_trades")
    if raw is None:
        raw = trades.get("n_trades", 0)
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def upsert_run(
    run_id: str,
    metrics: dict[str, Any],
    runs_dir: Path | None = None,
) -> None:
    """Insert or update a run in the index.

    Called from RunManager.save_metrics() after writing metrics.json.
    `metrics` may be enriched with params.json fields (asset, strategy,
    executed_at, from_date, to_date) so the list endpoint does not need
    a second disk read.
    """
    ensure_schema(runs_dir)

    scalar = _scalar(metrics)
    signal = _signal(metrics)
    se = metrics.get("signal_evaluation")
    se_dict = se if isinstance(se, dict) else {}

    with _get_connection(runs_dir) as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, asset, strategy, executed_at, is_portfolio,
                sharpe, total_return, max_drawdown, n_trades, win_rate,
                cagr, from_date, to_date, ic, ic_band, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                asset        = excluded.asset,
                strategy     = excluded.strategy,
                executed_at  = excluded.executed_at,
                is_portfolio = excluded.is_portfolio,
                sharpe       = excluded.sharpe,
                total_return = excluded.total_return,
                max_drawdown = excluded.max_drawdown,
                n_trades     = excluded.n_trades,
                win_rate     = excluded.win_rate,
                cagr         = excluded.cagr,
                from_date    = excluded.from_date,
                to_date      = excluded.to_date,
                ic           = excluded.ic,
                ic_band      = excluded.ic_band,
                metrics_json = excluded.metrics_json
            """,
            (
                run_id,
                metrics.get("asset") or _asset_from_run_id(run_id),
                metrics.get("strategy")
                or metrics.get("strategy_name")
                or _strategy_from_run_id(run_id),
                metrics.get("executed_at") or "",
                1 if "portfolio" in run_id else 0,
                scalar.get("sharpe", scalar.get("sharpe_ratio")),
                scalar.get("total_return"),
                scalar.get("max_drawdown"),
                _n_trades(metrics),
                scalar.get("win_rate"),
                scalar.get("cagr"),
                metrics.get("from_date") or metrics.get("data_start") or "",
                metrics.get("to_date") or metrics.get("data_end") or "",
                signal.get("ic", se_dict.get("ic")),
                signal.get("ic_band") or se_dict.get("ic_band"),
                json.dumps(metrics, default=str),
            ),
        )
        conn.commit()
    logger.debug("Run index upserted: %s", run_id)


def query_runs(
    strategy: str | None = None,
    asset: str | None = None,
    limit: int | None = 200,
    offset: int = 0,
    runs_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Query the run index. Returns list of run summary dicts.

    Falls back to empty list if index does not exist (first run).
    Pass limit=None to return all matching rows (needed for correct
    pagination totals on GET /api/runs).
    """
    path = _index_path(runs_dir)
    if not path.exists():
        return []

    ensure_schema(runs_dir)

    conditions: list[str] = []
    params: list[Any] = []

    if strategy:
        conditions.append("strategy = ?")
        params.append(strategy)
    if asset:
        conditions.append("asset = ?")
        params.append(asset)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    limit_sql = ""
    if limit is not None:
        limit_sql = "LIMIT ? OFFSET ?"
        params.extend([limit, offset])

    with _get_connection(runs_dir) as conn:
        rows = conn.execute(
            f"""
            SELECT run_id, asset, strategy, executed_at, is_portfolio,
                   sharpe, total_return, max_drawdown, n_trades, win_rate,
                   cagr, from_date, to_date, ic, ic_band, metrics_json
            FROM runs
            {where}
            ORDER BY executed_at DESC
            {limit_sql}
            """,
            params,
        ).fetchall()

    return [dict(row) for row in rows]


def delete_run(run_id: str, runs_dir: Path | None = None) -> None:
    """Remove a run from the index (e.g. if artifacts are deleted)."""
    if not _index_path(runs_dir).exists():
        return
    with _get_connection(runs_dir) as conn:
        conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        conn.commit()


def backfill_from_disk(runs_dir: Path | None = None) -> int:
    """Backfill the index from existing metrics.json files on disk.

    Called once on startup or manually to populate index from
    existing runs. Idempotent — safe to run multiple times.
    Merges params.json (asset/strategy/dates) with metrics.json.
    Returns number of runs indexed.
    """
    if runs_dir is None:
        runs_dir = _DEFAULT_RUNS_DIR

    ensure_schema(runs_dir)
    count = 0

    for metrics_path in runs_dir.glob("*/metrics.json"):
        run_id = metrics_path.parent.name
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            params_path = metrics_path.parent / "params.json"
            if params_path.exists():
                params = json.loads(params_path.read_text(encoding="utf-8"))
                metrics["asset"] = metrics.get("asset") or params.get("asset")
                metrics["strategy"] = (
                    metrics.get("strategy")
                    or metrics.get("strategy_name")
                    or params.get("strategy_name")
                    or params.get("strategy")
                )
                metrics["executed_at"] = metrics.get("executed_at") or params.get(
                    "executed_at", ""
                )
                metrics["from_date"] = params.get("data_start") or params.get(
                    "from_date", ""
                )
                metrics["to_date"] = params.get("data_end") or params.get("to_date", "")
                if params.get("signal_evaluation") and not metrics.get(
                    "signal_evaluation"
                ):
                    metrics["signal_evaluation"] = params["signal_evaluation"]
            metrics["asset"] = metrics.get("asset") or _asset_from_run_id(run_id)
            metrics["strategy"] = (
                metrics.get("strategy")
                or metrics.get("strategy_name")
                or _strategy_from_run_id(run_id)
            )
            upsert_run(run_id, metrics, runs_dir=runs_dir)
            count += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backfill: skipping %s — %s", run_id, exc)

    logger.info("Run index backfill complete: %d runs indexed", count)
    return count


def _asset_from_run_id(run_id: str) -> str:
    """Extract asset from run_id convention: YYYYMMDD_HHMMSS_strategy_asset."""
    parts = run_id.split("_")
    return parts[-1] if len(parts) >= 4 else ""


def _strategy_from_run_id(run_id: str) -> str:
    """Extract strategy from run_id. Handles multi-word strategy names."""
    parts = run_id.split("_")
    if len(parts) >= 4:
        return "_".join(parts[2:-1])
    return ""
