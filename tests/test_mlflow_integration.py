"""Tests for Module 12: MLflow Integration.

Tests Config MLflow properties, RunManager._try_log_to_mlflow(),
and graceful degradation when MLflow raises or is unavailable.

All tests route MLflow through tmp_config — the tracking URI is overridden
in cfg._config so _try_log_to_mlflow() reads the temp URI via
self._config.mlflow_tracking_uri. No parallel tmp_mlruns variable needed.

MLflow 3.x requires MLFLOW_ALLOW_FILE_STORE=true for filesystem backend.
The autouse fixture sets this for every test in this module.

See ADR-009 (run tracking strategy — Phase 2 MLflow integration).
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from unittest.mock import patch

import mlflow
import pandas as pd
import pytest

from src.backtesting.engine import VectorizedBacktester
from src.backtesting.run_manager import RunManager
from src.core.config import Config
from src.core.types import PerformanceReport
from src.performance.report import PerformanceEngine

# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def allow_mlflow_file_store():
    """MLflow 3.x blocks the filesystem tracking backend by default.

    MLFLOW_ALLOW_FILE_STORE=true re-enables it. Set for every test in
    this module via autouse=True.
    """
    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
    yield
    os.environ.pop("MLFLOW_ALLOW_FILE_STORE", None)


@pytest.fixture
def tmp_config(tmp_path: Path) -> Config:
    """Config fixture with all paths redirected to tmp_path.

    Overrides the MLflow tracking URI directly in cfg._config so that
    _try_log_to_mlflow() reads the temp URI from self._config.mlflow_tracking_uri
    rather than the real data/mlruns/. This is the correct isolation pattern:
    all MLflow URI routing goes through tmp_config, not a parallel variable.
    """
    cfg = Config.load("config/")
    cfg.paths["runs"] = str(tmp_path / "data" / "runs") + "/"
    (tmp_path / "data" / "runs").mkdir(parents=True, exist_ok=True)
    cfg._config.setdefault("mlflow", {})["tracking_uri"] = f"file:{tmp_path / 'mlruns'}"
    return cfg


def _make_ohlcv(n: int = 60) -> pd.DataFrame:
    """Build a minimal NormalizedOHLCV for backtester tests."""
    closes = [100.0 + i * 0.5 for i in range(n)]
    dates = pd.bdate_range(start="2023-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": [c - 1.0 for c in closes],
            "high": [c + 2.0 for c in closes],
            "low": [c - 2.0 for c in closes],
            "close": closes,
            "volume": [25000.0] * n,
            "open_interest": [float("nan")] * n,
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )


def _run_full_pipeline(
    tmp_config: Config,
) -> tuple[RunManager, str, PerformanceReport]:
    """Run the full pipeline and return (manager, run_id, report).

    MLflow URI is read from tmp_config.mlflow_tracking_uri — no separate
    mlflow.set_tracking_uri() call needed. _try_log_to_mlflow() reads
    self._config.mlflow_tracking_uri which already points to tmp_path.
    """
    ohlcv = _make_ohlcv(60)
    ps = pd.Series([0] + [1] * 59, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="ema_crossover",
        signal_name="ema_crossover_50_200",
        config=tmp_config,
        parameters={"fast_period": 50, "slow_period": 200},
    )
    result = backtester.run(ps, ohlcv)
    report = PerformanceEngine().compute(result)

    manager = RunManager(tmp_config)
    manager.save(result)
    manager.save_metrics(result.run_id, report)

    return manager, result.run_id, report


def _get_mlflow_client(cfg: Config) -> mlflow.tracking.MlflowClient:
    """Return an MlflowClient pointed at the same URI as _try_log_to_mlflow().

    Uses cfg.mlflow_tracking_uri — always consistent with what the method logged to.
    """
    return mlflow.tracking.MlflowClient(tracking_uri=cfg.mlflow_tracking_uri)


# ---------------------------------------------------------------------------
# Config MLflow property tests (2 tests)
# ---------------------------------------------------------------------------


def test_config_mlflow_tracking_uri_default() -> None:
    """Config.mlflow_tracking_uri returns the default when not overridden."""
    cfg = Config.load("config/")
    uri = cfg.mlflow_tracking_uri
    assert isinstance(uri, str)
    assert "mlruns" in uri or uri.startswith("file:") or uri.startswith("http")
    print(f"mlflow_tracking_uri: {uri}")


def test_config_mlflow_experiment_prefix_default() -> None:
    """Config.mlflow_experiment_prefix returns a non-empty string."""
    cfg = Config.load("config/")
    prefix = cfg.mlflow_experiment_prefix
    assert isinstance(prefix, str)
    assert len(prefix) > 0
    assert " " not in prefix, "Experiment prefix must not contain spaces"
    print(f"mlflow_experiment_prefix: {prefix}")


# ---------------------------------------------------------------------------
# MLflow logging correctness tests (4 tests)
# ---------------------------------------------------------------------------


def test_save_metrics_creates_mlflow_run(tmp_config: Config) -> None:
    """save_metrics() creates an MLflow run in the configured experiment."""
    manager, run_id, report = _run_full_pipeline(tmp_config)

    client = _get_mlflow_client(tmp_config)
    experiment = client.get_experiment_by_name(
        f"{tmp_config.mlflow_experiment_prefix}_gold"
    )
    assert experiment is not None, (
        f"Experiment '{tmp_config.mlflow_experiment_prefix}_gold' "
        "must exist after save_metrics()"
    )
    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    assert len(runs) >= 1, "At least one MLflow run must exist after save_metrics()"


def test_mlflow_run_parameters_match_backtest_metadata(
    tmp_config: Config,
) -> None:
    """MLflow run parameters match the BacktestResult metadata stored in params.json."""
    manager, run_id, report = _run_full_pipeline(tmp_config)

    client = _get_mlflow_client(tmp_config)
    experiment = client.get_experiment_by_name(
        f"{tmp_config.mlflow_experiment_prefix}_gold"
    )
    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    assert len(runs) >= 1
    run = runs[0]

    logged_params = run.data.params
    assert logged_params.get("asset") == "gold"
    assert logged_params.get("strategy_name") == "ema_crossover"
    assert logged_params.get("signal_name") == "ema_crossover_50_200"


def test_mlflow_run_metrics_match_performance_report(
    tmp_config: Config,
) -> None:
    """MLflow run metrics match PerformanceReport.scalar_metrics."""
    manager, run_id, report = _run_full_pipeline(tmp_config)

    client = _get_mlflow_client(tmp_config)
    experiment = client.get_experiment_by_name(
        f"{tmp_config.mlflow_experiment_prefix}_gold"
    )
    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    run = runs[0]

    logged_metrics = run.data.metrics
    assert "sharpe" in logged_metrics, "sharpe metric must be logged to MLflow"
    assert not math.isnan(logged_metrics["sharpe"])
    assert "max_drawdown" in logged_metrics, "max_drawdown must be logged to MLflow"


def test_mlflow_run_tagged_with_file_run_id(
    tmp_config: Config,
) -> None:
    """MLflow run is tagged with file_run_id for cross-reference to file artifacts."""
    manager, run_id, report = _run_full_pipeline(tmp_config)

    client = _get_mlflow_client(tmp_config)
    experiment = client.get_experiment_by_name(
        f"{tmp_config.mlflow_experiment_prefix}_gold"
    )
    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    run = runs[0]

    logged_tags = run.data.tags
    assert (
        "file_run_id" in logged_tags
    ), "MLflow run must be tagged with file_run_id for cross-reference"
    assert (
        logged_tags["file_run_id"] == run_id
    ), "file_run_id tag must match the BacktestResult.run_id"


# ---------------------------------------------------------------------------
# Graceful degradation tests (2 tests)
# ---------------------------------------------------------------------------


def test_file_artifacts_written_even_when_mlflow_raises(
    tmp_config: Config,
) -> None:
    """File-based artifacts are written successfully even when MLflow raises.

    ADR-009: MLflow failure must never be a run failure.
    """
    ohlcv = _make_ohlcv(60)
    ps = pd.Series([0] + [1] * 59, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test",
        signal_name="test",
        config=tmp_config,
    )
    result = backtester.run(ps, ohlcv)
    report = PerformanceEngine().compute(result)

    manager = RunManager(tmp_config)
    run_dir = manager.save(result)

    with patch(
        "mlflow.start_run", side_effect=RuntimeError("tracking server unavailable")
    ):
        manager.save_metrics(result.run_id, report)

    assert (
        run_dir / "metrics.json"
    ).exists(), "metrics.json must be written even when MLflow logging fails"
    assert (run_dir / "params.json").exists()
    assert (run_dir / "trades.parquet").exists()


def test_mlflow_logging_skipped_gracefully_when_mlflow_unavailable(
    tmp_config: Config,
) -> None:
    """save_metrics() succeeds when mlflow import is unavailable.

    Tests the ImportError branch of _try_log_to_mlflow().
    """
    ohlcv = _make_ohlcv(60)
    ps = pd.Series([0] + [1] * 59, index=ohlcv.index, dtype="int8")

    backtester = VectorizedBacktester(
        asset="gold",
        strategy_name="test",
        signal_name="test",
        config=tmp_config,
    )
    result = backtester.run(ps, ohlcv)
    report = PerformanceEngine().compute(result)

    manager = RunManager(tmp_config)
    run_dir = manager.save(result)

    original_mlflow = sys.modules.get("mlflow")
    sys.modules["mlflow"] = None  # type: ignore[assignment]
    try:
        manager.save_metrics(result.run_id, report)
    finally:
        if original_mlflow is not None:
            sys.modules["mlflow"] = original_mlflow
        elif "mlflow" in sys.modules:
            del sys.modules["mlflow"]

    assert (
        run_dir / "metrics.json"
    ).exists(), "metrics.json must be written even when mlflow is not importable"


# ---------------------------------------------------------------------------
# Integration tests (2 tests)
# ---------------------------------------------------------------------------


def test_full_pipeline_creates_mlflow_experiment_and_run(
    tmp_config: Config,
) -> None:
    """Full pipeline (save + save_metrics) creates an MLflow experiment and run."""
    manager, run_id, report = _run_full_pipeline(tmp_config)

    client = _get_mlflow_client(tmp_config)
    experiment_name = f"{tmp_config.mlflow_experiment_prefix}_gold"
    experiment = client.get_experiment_by_name(experiment_name)

    assert experiment is not None
    assert experiment.name == experiment_name

    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    assert len(runs) == 1
    assert runs[0].info.run_name == run_id


def test_compare_runs_unaffected_by_mlflow_integration(
    tmp_config: Config,
) -> None:
    """RunManager.compare_runs() still works correctly after MLflow integration."""
    ohlcv = _make_ohlcv(60)
    manager = RunManager(tmp_config)

    run_ids = []
    for strategy_name in ["strategy_a", "strategy_b"]:
        ps = pd.Series([0] + [1] * 59, index=ohlcv.index, dtype="int8")
        backtester = VectorizedBacktester(
            asset="gold",
            strategy_name=strategy_name,
            signal_name="test",
            config=tmp_config,
        )
        result = backtester.run(ps, ohlcv)
        report = PerformanceEngine().compute(result)
        manager.save(result)
        manager.save_metrics(result.run_id, report)
        run_ids.append(result.run_id)

    comparison = manager.compare_runs(run_ids)

    assert isinstance(comparison, pd.DataFrame)
    assert len(comparison) == 2, f"Expected 2 rows, got {len(comparison)}"
    assert "run_id" in comparison.columns
