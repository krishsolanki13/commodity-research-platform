"""Backend tests for SweepRunner.

5 tests: 3 pure unit (always run), 2 data-dependent (skip in CI).
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKIP_NO_DATA = pytest.mark.skipif(
    not Path("data/processed/continuous/gold.parquet").exists(),
    reason="Gold Parquet not available in CI",
)


def test_generate_combinations_empty_grid() -> None:
    """Empty param_grid produces one combination: an empty dict."""
    from src.backtesting.sweep_runner import SweepRunner

    result = SweepRunner._generate_combinations({})
    assert result == [{}]


def test_generate_combinations_single_param() -> None:
    """Single-param grid produces one combination per value."""
    from src.backtesting.sweep_runner import SweepRunner

    result = SweepRunner._generate_combinations({"fast_period": [10, 20, 50]})
    assert len(result) == 3
    assert result[0] == {"fast_period": 10}
    assert result[2] == {"fast_period": 50}


def test_generate_combinations_two_params() -> None:
    """Two-param grid produces Cartesian product combinations."""
    from src.backtesting.sweep_runner import SweepRunner

    result = SweepRunner._generate_combinations(
        {
            "fast_period": [10, 20],
            "slow_period": [100, 200],
        }
    )
    assert len(result) == 4
    assert {"fast_period": 10, "slow_period": 100} in result
    assert {"fast_period": 10, "slow_period": 200} in result
    assert {"fast_period": 20, "slow_period": 100} in result
    assert {"fast_period": 20, "slow_period": 200} in result


def test_progress_callback_receives_cumulative_n_complete() -> None:
    """progress_callback is invoked after each combination with n_complete."""
    from unittest.mock import MagicMock, patch

    import pandas as pd

    from src.backtesting.sweep_runner import SweepRunner
    from src.core.types import SweepRunSummary

    seen: list[int] = []

    dummy = SweepRunSummary(
        sweep_id="s",
        run_id="r",
        parameters={},
        status="complete",
    )
    runner = SweepRunner(MagicMock())
    with (
        patch("src.data.loader.DataLoader") as loader_cls,
        patch.object(runner, "_run_single", return_value=dummy),
    ):
        loader_cls.return_value.load.return_value = pd.DataFrame()
        result = runner.run_sweep(
            asset="gold",
            strategy_name="ema_crossover",
            param_grid={"fast_period": [10, 20], "slow_period": [100]},
            sweep_id="test_progress",
            progress_callback=seen.append,
        )

    assert result.n_combinations == 2
    assert seen == [1, 2]


@SKIP_NO_DATA
def test_sweep_runner_produces_correct_n_combinations() -> None:
    """SweepRunner.run_sweep() produces exactly n_combinations results."""
    from src.backtesting.sweep_runner import SweepRunner
    from src.core.config import Config

    config = Config.load("config/")
    runner = SweepRunner(config)

    result = runner.run_sweep(
        asset="gold",
        strategy_name="ema_crossover",
        param_grid={"fast_period": [10, 50], "slow_period": [100, 200]},
        sweep_id="test_sweep_001",
    )

    assert result.n_combinations == 4
    assert len(result.runs) == 4
    assert result.asset == "gold"
    assert result.strategy_name == "ema_crossover"
    assert result.n_complete + result.n_failed == 4


@SKIP_NO_DATA
def test_sweep_runner_results_contain_valid_metrics() -> None:
    """Completed sweep runs have non-NaN sharpe and valid status."""
    from src.backtesting.sweep_runner import SweepRunner
    from src.core.config import Config

    config = Config.load("config/")
    runner = SweepRunner(config)

    result = runner.run_sweep(
        asset="gold",
        strategy_name="ema_crossover",
        param_grid={"fast_period": [20, 50], "slow_period": [100]},
        sweep_id="test_sweep_002",
    )

    complete_runs = [r for r in result.runs if r.status == "complete"]
    assert len(complete_runs) >= 1, "At least one run should complete"

    for run in complete_runs:
        assert run.status == "complete"
        assert run.error is None
        assert isinstance(run.parameters, dict)
        assert "fast_period" in run.parameters
        assert "slow_period" in run.parameters
        assert isinstance(run.sharpe, float)
