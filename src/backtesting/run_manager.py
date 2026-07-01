"""RunManager: run ID assignment and BacktestResult persistence.

Consolidates ADR-009's RunManager (assign/save) and RunRegistry
(list/load/compare/delete) responsibilities into one class. See Module 5
Transfer Package Section 8 for the resolved-ambiguity rationale.

NOTE: This file currently contains only generate_run_id(). The full
RunManager class is added in Increment 4.
"""

from __future__ import annotations

import datetime
import json
import logging
import shutil
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.config import Config
from src.core.types import BacktestResult, PerformanceReport, TradeRecord


def generate_run_id(strategy_name: str, asset: str) -> str:
    """Generate a run_id in the format YYYYMMDD_HHMMSS_{strategy}_{asset}.

    Args:
        strategy_name: Strategy identifier (e.g., "ema_crossover").
        asset: Asset identifier (e.g., "gold").

    Returns:
        run_id string. See ADR-009.
    """
    timestamp = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{strategy_name}_{asset}"


class RunManager:
    """Persists and retrieves BacktestResult artifacts. See ADR-009.

    Run artifacts are immutable once written. Reruns create new run IDs
    via generate_run_id() — RunManager never overwrites an existing
    run directory.
    """

    def __init__(self, config: Config) -> None:
        """Initialise RunManager.

        Args:
            config: Config instance from Config.load().
        """
        self._config = config
        self._logger = logging.getLogger(__name__)

    def save(self, backtest_result: BacktestResult) -> Path:
        """Persist a BacktestResult to data/runs/{run_id}/.

        Writes: params.json, trades.parquet, equity_curve.parquet,
        pnl_series.parquet, positions.parquet. Does NOT write
        metrics.json — that is Module 6's responsibility.
        """
        run_dir = Path(self._config.paths["runs"]) / backtest_result.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        params = asdict(backtest_result.metadata)
        params["data_start"] = backtest_result.metadata.data_start.isoformat()
        params["data_end"] = backtest_result.metadata.data_end.isoformat()
        params["executed_at"] = backtest_result.metadata.executed_at.isoformat()
        with open(run_dir / "params.json", "w") as f:
            json.dump(params, f, indent=2)

        if backtest_result.trades:
            trades_df = pd.DataFrame([asdict(t) for t in backtest_result.trades])
            trades_df["entry_date"] = trades_df["entry_date"].astype(str)
            trades_df["exit_date"] = trades_df["exit_date"].astype(str)
        else:
            trade_columns = [f.name for f in fields(TradeRecord)]
            trades_df = pd.DataFrame(columns=trade_columns)
        trades_df.to_parquet(run_dir / "trades.parquet", engine="pyarrow", index=False)

        backtest_result.equity_curve.to_frame(name="equity").to_parquet(
            run_dir / "equity_curve.parquet", engine="pyarrow"
        )
        backtest_result.pnl_series.to_frame(name="pnl").to_parquet(
            run_dir / "pnl_series.parquet", engine="pyarrow"
        )
        backtest_result.positions.to_frame(name="position").to_parquet(
            run_dir / "positions.parquet", engine="pyarrow"
        )

        self._logger.info(
            "RunManager: saved run %s to %s (%d trades)",
            backtest_result.run_id,
            run_dir,
            len(backtest_result.trades),
        )
        return run_dir

    def load_run(self, run_id: str) -> dict[str, Any]:
        """Load all persisted artifacts for a run.

        Raises:
            FileNotFoundError: If the run directory does not exist.
        """
        run_dir = Path(self._config.paths["runs"]) / run_id
        if not run_dir.exists():
            raise FileNotFoundError(f"No run found at {run_dir}")

        with open(run_dir / "params.json") as f:
            params = json.load(f)

        trades_df = pd.read_parquet(run_dir / "trades.parquet", engine="pyarrow")
        equity_curve = pd.read_parquet(
            run_dir / "equity_curve.parquet", engine="pyarrow"
        )["equity"]
        pnl_series = pd.read_parquet(run_dir / "pnl_series.parquet", engine="pyarrow")[
            "pnl"
        ]
        positions = pd.read_parquet(run_dir / "positions.parquet", engine="pyarrow")[
            "position"
        ]

        return {
            "params": params,
            "trades": trades_df,
            "equity_curve": equity_curve,
            "pnl_series": pnl_series,
            "positions": positions,
        }

    def list_runs(self) -> list[str]:
        """Return all saved run_ids sorted ascending. Empty list if none exist."""
        runs_dir = Path(self._config.paths["runs"])
        if not runs_dir.exists():
            return []
        return sorted(p.name for p in runs_dir.iterdir() if p.is_dir())

    def compare_runs(self, run_ids: list[str]) -> pd.DataFrame:
        """Build a comparison DataFrame of parameter snapshots across runs."""
        rows = []
        for rid in run_ids:
            data = self.load_run(rid)
            rows.append({"run_id": rid, **data["params"]})
        return pd.DataFrame(rows)

    def delete_run(self, run_id: str) -> None:
        """Delete a run directory and all its artifacts."""
        run_dir = Path(self._config.paths["runs"]) / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
            self._logger.info("RunManager: deleted run %s", run_id)

    def save_metrics(self, run_id: str, report: PerformanceReport) -> None:
        """Write metrics.json to an existing run directory.

        Called after PerformanceEngine.compute(). RunManager.save() does
        not write metrics.json — that separation is intentional per
        Architecture Section 9.1 and ADR-009.

        metrics.json contains scalar_metrics, signal_metrics, and
        trade_statistics. rolling_metrics (pd.Series) are not serialized
        to JSON — they are recomputable from persisted Parquet files.

        Args:
            run_id: Existing run identifier. Run directory must exist.
            report: PerformanceReport from PerformanceEngine.compute().

        Raises:
            FileNotFoundError: If the run directory does not exist.
                Call RunManager.save(backtest_result) before save_metrics().
        """
        run_dir = Path(self._config.paths["runs"]) / run_id
        if not run_dir.exists():
            raise FileNotFoundError(
                f"No run directory found at {run_dir}. "
                f"Call RunManager.save(backtest_result) before save_metrics()."
            )

        metrics_dict = {
            "run_id": report.run_id,
            "initial_capital_usd": report.initial_capital_usd,
            "scalar_metrics": report.scalar_metrics,
            "signal_metrics": report.signal_metrics,
            "trade_statistics": report.trade_statistics,
        }

        with open(run_dir / "metrics.json", "w") as f:
            json.dump(metrics_dict, f, indent=2, default=str)

        self._logger.info(
            "RunManager: saved metrics.json for run %s (Sharpe=%.4f)",
            run_id,
            report.scalar_metrics.get("sharpe", float("nan")),
        )
