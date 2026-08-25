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
import math
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
        try:
            from src.data.run_index import (
                delete_run as delete_index_run,  # noqa: PLC0415
            )

            delete_index_run(run_id, runs_dir=Path(self._config.paths["runs"]))
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("Run index delete failed for %s: %s", run_id, exc)

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

        try:
            from src.data.run_index import upsert_run  # noqa: PLC0415

            index_payload = dict(metrics_dict)
            params_path = run_dir / "params.json"
            if params_path.exists():
                params = json.loads(params_path.read_text(encoding="utf-8"))
                index_payload["asset"] = params.get("asset", "")
                index_payload["strategy"] = params.get("strategy_name") or params.get(
                    "strategy", ""
                )
                index_payload["executed_at"] = params.get("executed_at", "")
                index_payload["from_date"] = params.get("data_start") or params.get(
                    "from_date", ""
                )
                index_payload["to_date"] = params.get("data_end") or params.get(
                    "to_date", ""
                )
                if params.get("signal_evaluation"):
                    index_payload["signal_evaluation"] = params["signal_evaluation"]
            upsert_run(
                run_id,
                index_payload,
                runs_dir=Path(self._config.paths["runs"]),
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "Run index upsert failed for %s — index will be rebuilt "
                "on next startup. Error: %s",
                run_id,
                exc,
            )

        self._logger.info(
            "RunManager: saved metrics.json for run %s (Sharpe=%.4f)",
            run_id,
            report.scalar_metrics.get("sharpe", float("nan")),
        )

        # Log to MLflow alongside file-based artifacts (best-effort, ADR-009 Phase 2)
        self._try_log_to_mlflow(run_id, report)

    def _try_log_to_mlflow(
        self,
        run_id: str,
        report: PerformanceReport,
    ) -> None:
        """Attempt to log run parameters and metrics to MLflow.

        Non-fatal — any exception caught and logged as WARNING.
        File-based artifacts are never affected by MLflow failures.
        Reads parameters from params.json (already written by save()).
        """
        try:
            import os

            import mlflow  # noqa: PLC0415

            # MLflow 3.x places the filesystem tracking backend in maintenance mode.
            # setdefault respects an explicitly-set value while ensuring the default works.
            os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
        except ImportError:
            self._logger.debug(
                "RunManager: mlflow not installed — skipping MLflow logging for run %s",
                run_id,
            )
            return

        try:
            run_dir = Path(self._config.paths["runs"]) / run_id
            params_path = run_dir / "params.json"

            if not params_path.exists():
                self._logger.warning(
                    "RunManager: params.json not found for run %s — cannot log to MLflow",
                    run_id,
                )
                return

            with open(params_path, encoding="utf-8") as f:
                stored_params = json.load(f)

            asset = stored_params.get("asset", "unknown")
            experiment_name = f"{self._config.mlflow_experiment_prefix}_{asset}"

            mlflow.set_tracking_uri(self._config.mlflow_tracking_uri)
            mlflow.set_experiment(experiment_name)

            with mlflow.start_run(run_name=run_id):
                mlflow_params: dict[str, str] = {
                    "asset": str(stored_params.get("asset", "")),
                    "strategy_name": str(stored_params.get("strategy_name", "")),
                    "signal_name": str(stored_params.get("signal_name", "")),
                    "initial_capital": str(
                        stored_params.get("initial_capital_usd", "")
                    ),
                    "data_source": str(stored_params.get("data_source", "")),
                    "data_start": str(stored_params.get("data_start", "")),
                    "data_end": str(stored_params.get("data_end", "")),
                }
                for k, v in stored_params.get("parameters", {}).items():
                    safe_key = _sanitize_mlflow_key(f"param_{k}")
                    mlflow_params[safe_key] = str(v)[:500]

                mlflow.log_params(mlflow_params)

                mlflow_metrics: dict[str, float] = {
                    k: float(v)
                    for k, v in report.scalar_metrics.items()
                    if isinstance(v, int | float) and not math.isnan(float(v))
                }
                if report.signal_metrics:
                    mlflow_metrics.update(
                        {
                            k: float(v)
                            for k, v in report.signal_metrics.items()
                            if isinstance(v, int | float) and not math.isnan(float(v))
                        }
                    )
                if mlflow_metrics:
                    mlflow.log_metrics(mlflow_metrics)

                mlflow.set_tag("file_run_id", run_id)
                mlflow.set_tag("artifacts_path", str(run_dir))

            self._logger.info(
                "RunManager: MLflow logged run %s to experiment '%s'",
                run_id,
                experiment_name,
            )

        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "RunManager: MLflow logging failed for run %s — %s: %s. "
                "File-based artifacts are unaffected.",
                run_id,
                type(exc).__name__,
                exc,
            )


def _sanitize_mlflow_key(key: str) -> str:
    """Sanitize a string for use as an MLflow parameter key.

    MLflow keys cannot contain spaces or most special characters.
    Replaces non-alphanumeric characters (except _.-/) with underscores.
    Truncates to 250 characters (MLflow key limit).
    """
    import re

    sanitized = re.sub(r"[^a-zA-Z0-9_.\-/]", "_", key)
    return sanitized[:250]
