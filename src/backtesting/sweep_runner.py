"""Parameter sweep infrastructure for systematic strategy research.

SweepRunner executes a strategy across a grid of parameter combinations
and returns a SweepResult containing per-combination performance metrics.
Every run in the sweep is saved to disk and tagged in MLflow, so that:
  1. Runs appear in the Run Explorer alongside standalone backtests.
  2. MLflow trial counts (used in DSR computation) correctly reflect
     the full number of parameter configurations evaluated.

Parameter grid expansion uses itertools.product — all combinations of
the provided value lists are evaluated in order.

Example:
    runner = SweepRunner(config)
    result = runner.run_sweep(
        asset='gold',
        strategy_name='ema_crossover',
        param_grid={'fast_period': [10, 20, 50], 'slow_period': [100, 200]},
        sweep_id='20260722_120000_sweep_ema_crossover_gold',
    )
    # result.n_combinations == 6
    # result.runs has 6 SweepRunSummary entries
"""

from __future__ import annotations

import datetime
import itertools
import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.core.config import Config
    from src.core.types import SweepResult, SweepRunSummary

logger = logging.getLogger(__name__)


class SweepRunner:
    """Executes a parameter sweep over a strategy/asset combination.

    Each parameter combination runs a full vectorized backtest.
    Results are saved to disk via RunManager and tagged in MLflow.
    Failed combinations are recorded with status='failed' and do not
    interrupt the remaining sweep.

    Args:
        config: Platform Config for loading data and constructing sizers.
    """

    def __init__(self, config: Config) -> None:
        self._config = config

    def run_sweep(
        self,
        asset: str,
        strategy_name: str,
        param_grid: dict[str, list],
        sweep_id: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> SweepResult:
        """Execute the full parameter sweep and return a SweepResult.

        Args:
            asset: Asset identifier (e.g. 'gold').
            strategy_name: Strategy name (e.g. 'ema_crossover').
            param_grid: Dict mapping parameter names to lists of values.
                E.g. {'fast_period': [10, 20, 50], 'slow_period': [100, 200]}
            sweep_id: Unique sweep identifier (assigned by the API layer).
                Format: YYYYMMDD_HHMMSS_sweep_{strategy}_{asset}.
            progress_callback: Optional callback invoked after each combination
                with the cumulative count of runs whose status is 'complete'.

        Returns:
            SweepResult with one SweepRunSummary per parameter combination.
        """
        from src.core.provenance import capture  # noqa: PLC0415
        from src.core.types import SweepResult  # noqa: PLC0415
        from src.data.loader import DataLoader  # noqa: PLC0415

        combinations = list(self._generate_combinations(param_grid))
        n = len(combinations)
        logger.info(
            "SweepRunner: %s/%s — %d combinations, sweep_id=%s",
            asset,
            strategy_name,
            n,
            sweep_id,
        )

        # Load OHLCV once — reused for all combinations
        ohlcv = DataLoader(self._config).load(asset)

        runs: list[SweepRunSummary] = []
        for i, params in enumerate(combinations):
            logger.info("SweepRunner: combination %d/%d — params=%s", i + 1, n, params)
            summary = self._run_single(
                asset=asset,
                strategy_name=strategy_name,
                parameters=params,
                sweep_id=sweep_id,
                combination_idx=i,
                ohlcv=ohlcv,
            )
            runs.append(summary)
            if progress_callback is not None:
                n_complete_so_far = sum(1 for r in runs if r.status == "complete")
                try:
                    progress_callback(n_complete_so_far)
                except Exception as cb_exc:  # noqa: BLE001
                    logger.debug("Progress callback failed (non-fatal): %s", cb_exc)

        n_complete = sum(1 for r in runs if r.status == "complete")
        n_failed = n - n_complete

        logger.info(
            "SweepRunner: sweep_id=%s complete — %d/%d succeeded",
            sweep_id,
            n_complete,
            n,
        )

        _prov = capture()
        return SweepResult(
            sweep_id=sweep_id,
            asset=asset,
            strategy_name=strategy_name,
            param_grid=param_grid,
            n_combinations=n,
            n_complete=n_complete,
            n_failed=n_failed,
            computation_date=datetime.date.today(),
            runs=runs,
            git_sha=_prov["git_sha"],
            dirty_flag=_prov["dirty_flag"],
            package_versions=_prov["package_versions"],
        )

    def _run_single(
        self,
        asset: str,
        strategy_name: str,
        parameters: dict,
        sweep_id: str,
        combination_idx: int,
        ohlcv: pd.DataFrame,
    ) -> SweepRunSummary:
        """Run one parameter combination and return its summary.

        Saves run artifacts to disk and logs to MLflow with sweep_id tag.
        Returns a SweepRunSummary with status='failed' on any error —
        does not propagate exceptions.
        """
        from src.backtesting.engine import VectorizedBacktester  # noqa: PLC0415
        from src.backtesting.pipeline_builder import (
            build_pipeline_components,  # noqa: PLC0415
        )
        from src.backtesting.run_manager import RunManager  # noqa: PLC0415
        from src.core.types import SweepRunSummary  # noqa: PLC0415
        from src.performance.report import PerformanceEngine  # noqa: PLC0415
        from src.research.pipeline import FeaturePipeline  # noqa: PLC0415
        from src.signal.position import PositionSignalConstructor  # noqa: PLC0415

        # Fallback run_id — used in the except block where result was never
        # constructed. Success path uses result.run_id.
        now = datetime.datetime.now(datetime.UTC)
        run_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{strategy_name}_{asset}"

        try:
            # DEV-EM5-1: build_pipeline_components returns 2-tuple
            indicators, signal_gen = build_pipeline_components(
                strategy_name=strategy_name,
                parameters=parameters,
                config=self._config,
            )
            feature_pipeline = FeaturePipeline(indicators)
            feature_frame = feature_pipeline.compute(ohlcv, asset=asset)
            raw_signal = signal_gen.generate(feature_frame)

            position_signal = PositionSignalConstructor().build(
                raw_signal, threshold=0.0
            )

            backtester = VectorizedBacktester(
                asset=asset,
                strategy_name=strategy_name,
                signal_name=getattr(signal_gen, "name", strategy_name),
                config=self._config,
                parameters=parameters,
            )
            result = backtester.run(position_signal, ohlcv)

            # DEV-EM5-2: PerformanceEngine at src.performance.report
            perf_engine = PerformanceEngine()
            perf_report = perf_engine.compute(result)
            metrics = perf_report.scalar_metrics or {}

            sharpe = float(metrics.get("sharpe", float("nan")))
            total_return = float(metrics.get("total_return", float("nan")))
            max_drawdown = float(metrics.get("max_drawdown", float("nan")))
            n_trades = len(result.trades) if hasattr(result, "trades") else 0

            # Save artifacts (non-fatal)
            try:
                manager = RunManager(self._config)
                manager.save(result)
                manager.save_metrics(result.run_id, perf_report)
                self._tag_mlflow_run(result.run_id, sweep_id, asset)
            except Exception as save_exc:  # noqa: BLE001
                logger.warning(
                    "SweepRunner: save failed for run %s: %s",
                    result.run_id,
                    save_exc,
                )

            return SweepRunSummary(
                sweep_id=sweep_id,
                run_id=result.run_id,
                parameters=parameters,
                sharpe=sharpe,
                total_return=total_return,
                max_drawdown=max_drawdown,
                n_trades=n_trades,
                status="complete",
                error=None,
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SweepRunner: combination %d failed — params=%s: %s",
                combination_idx,
                parameters,
                exc,
            )
            return SweepRunSummary(
                sweep_id=sweep_id,
                run_id=run_id,
                parameters=parameters,
                sharpe=float("nan"),
                total_return=float("nan"),
                max_drawdown=float("nan"),
                n_trades=0,
                status="failed",
                error=str(exc)[:500],
            )

    def _tag_mlflow_run(self, run_id: str, sweep_id: str, asset: str) -> None:
        """Tag a completed MLflow run with its parent sweep_id.

        Uses the same experiment naming convention as get_trial_count()
        in src/validation/mlflow_client.py (BUG-EM5-A fix):
          experiment_name = f"{config.mlflow_experiment_prefix}_{asset}"

        Non-fatal on any failure — sweep result is unaffected.
        """
        try:
            import mlflow  # noqa: PLC0415

            # Experiment name per ADR-006 / BUG-EM5-A fix
            try:
                experiment_prefix = getattr(
                    self._config,
                    "mlflow_experiment_prefix",
                    "commodity_research",
                )
            except Exception:  # noqa: BLE001
                experiment_prefix = "commodity_research"

            experiment_name = f"{experiment_prefix}_{asset}"
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                logger.debug(
                    "MLflow: experiment '%s' not found — sweep tag skipped",
                    experiment_name,
                )
                return

            # Search within the specific experiment (not experiment_ids=[])
            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                filter_string=f"tags.mlflow.runName = '{run_id}'",
                max_results=1,
                output_format="list",
            )
            if runs:
                client = mlflow.tracking.MlflowClient()
                client.set_tag(runs[0].info.run_id, "sweep_id", sweep_id)
                logger.debug(
                    "MLflow: tagged run '%s' with sweep_id='%s'",
                    run_id,
                    sweep_id,
                )
            else:
                logger.debug(
                    "MLflow: run '%s' not found in experiment '%s' — tag skipped",
                    run_id,
                    experiment_name,
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("MLflow sweep tagging failed (non-fatal): %s", exc)

    @staticmethod
    def _generate_combinations(
        param_grid: dict[str, list],
    ) -> list[dict]:
        """Expand a parameter grid to all combinations using itertools.product.

        Args:
            param_grid: {'fast_period': [10, 20], 'slow_period': [100, 200]}

        Returns:
            List of dicts: [{'fast_period': 10, 'slow_period': 100}, ...]
            Ordered as itertools.product orders them (last key varies fastest).
        """
        if not param_grid:
            return [{}]
        keys = list(param_grid.keys())
        value_lists = [param_grid[k] for k in keys]
        return [
            dict(zip(keys, combo, strict=True))
            for combo in itertools.product(*value_lists)
        ]
