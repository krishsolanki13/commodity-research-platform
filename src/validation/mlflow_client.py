"""MLflow utilities for the validation module.

Reads trial counts from MLflow experiments to support the
Deflated Sharpe Ratio's multiple-testing correction.

FIX (Issue 1): Experiments are named {mlflow_experiment_prefix}_{asset}
(e.g., 'commodity_research_gold'), not '{strategy}_{asset}'. The prefix
is read from config. Runs within the experiment are filtered by strategy
name, which appears in the run_name (= run_id = YYYYMMDD_HHMMSS_{strategy}_{asset}).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_trial_count(asset: str, strategy_name: str) -> int:
    """Return the number of runs logged to the MLflow experiment for
    this asset/strategy combination.

    MLflow experiments are named {mlflow_experiment_prefix}_{asset}
    (e.g., 'commodity_research_gold'). Within that experiment, runs are
    filtered by strategy_name, which appears in the run_name field
    (format: YYYYMMDD_HHMMSS_{strategy}_{asset}).

    This is the n_trials input to the Deflated Sharpe Ratio. It counts
    all parameter configurations evaluated for this (asset, strategy) pair.

    Falls back to 1 if MLflow is unavailable or returns 0 matching runs.
    n_trials = 1 means no multiple-testing correction is applied (DSR = PSR),
    which is the correct behaviour when only one trial has been run.

    Args:
        asset: Asset identifier (e.g. 'gold').
        strategy_name: Strategy name (e.g. 'ema_crossover').

    Returns:
        Number of strategy runs in the MLflow experiment. Minimum 1.
    """
    try:
        import mlflow  # noqa: PLC0415

        # Resolve experiment prefix from config; fall back to documented default
        try:
            from src.core.config import Config  # noqa: PLC0415

            config = Config.load("config/")
            experiment_prefix = config.mlflow_experiment_prefix
        except Exception:  # noqa: BLE001
            experiment_prefix = "commodity_research"  # matches config.yaml default

        # Correct naming convention: {prefix}_{asset}, e.g. 'commodity_research_gold'
        experiment_name = f"{experiment_prefix}_{asset}"
        experiment = mlflow.get_experiment_by_name(experiment_name)

        if experiment is None:
            logger.info(
                "MLflow experiment '%s' not found — using n_trials=1",
                experiment_name,
            )
            return 1

        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            output_format="list",
        )
        if not runs:
            return 1

        # Filter to this strategy via run_name.
        # run_name = run_id = YYYYMMDD_HHMMSS_{strategy}_{asset} (set in RunManager M12).
        # mlflow.entities.Run.info.run_name holds this value in MLflow 3.x.
        strategy_runs = [
            r for r in runs if strategy_name in (getattr(r.info, "run_name", "") or "")
        ]
        count = max(1, len(strategy_runs))
        logger.info(
            "MLflow: experiment '%s' has %d total runs, %d for strategy '%s' "
            "— using n_trials=%d",
            experiment_name,
            len(runs),
            strategy_name,
            count,
        )
        return count

    except Exception as exc:  # noqa: BLE001
        logger.warning("MLflow trial count unavailable (%s) — using n_trials=1", exc)
        return 1
