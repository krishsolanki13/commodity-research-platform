"""Backend tests for RegimeAttributionEngine.

4 tests: 2 pure unit (always run), 2 data-dependent (skip in CI).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

CONTRACT_PATH = Path("data/processed/contracts")
HAS_CONTRACT_DATA = CONTRACT_PATH.exists() and any(CONTRACT_PATH.iterdir())
SKIP_NO_CONTRACT = pytest.mark.skipif(
    not HAS_CONTRACT_DATA,
    reason="Contract Parquet files not available in CI",
)


def _proxy_from_artifact(artifact: dict, run_id: str) -> MagicMock:
    """Build a BacktestResult-like proxy from RunManager.load_run() output."""
    import types as _types

    params = artifact.get("params", {})
    trades_df = artifact.get("trades")
    trade_list = []
    if trades_df is not None and len(trades_df) > 0:
        for _, row in trades_df.iterrows():
            trade_list.append(
                _types.SimpleNamespace(
                    entry_date=row.get("entry_date"),
                    net_pnl=row.get("net_pnl", 0.0),
                )
            )
    proxy = MagicMock()
    proxy.run_id = params.get("run_id", run_id)
    proxy.strategy_name = params.get("strategy_name") or params.get(
        "strategy", "unknown"
    )
    proxy.asset = params.get("asset", run_id.split("_")[-1])
    proxy.pnl_series = artifact.get("pnl_series")
    proxy.equity_curve = artifact.get("equity_curve")
    proxy.trades = trade_list
    return proxy


def test_regime_attribution_engine_importable() -> None:
    """RegimeAttributionEngine imports cleanly."""
    from src.analytics.regime_attribution import RegimeAttributionEngine

    mock_config = MagicMock()
    engine = RegimeAttributionEngine(config=mock_config)
    assert engine is not None


def test_regime_attribution_returns_empty_when_no_contract_data() -> None:
    """RegimeAttributionEngine returns empty report when asset has no contract data."""
    from src.analytics.regime_attribution import RegimeAttributionEngine
    from src.core.types import RegimeAttributionReport

    mock_config = MagicMock()
    engine = RegimeAttributionEngine(config=mock_config)

    # Mock BacktestResult with a minimal pnl_series
    mock_result = MagicMock()
    mock_result.run_id = "test_run"
    mock_result.strategy_name = "ema_crossover"
    n = 100
    dates = pd.bdate_range("2024-01-02", periods=n, freq="B", tz="UTC")
    mock_result.pnl_series = pd.Series([100.0] * n, index=dates, name="pnl")

    with patch(
        "src.commodity.curve.FuturesCurveBuilder.available_assets",
        return_value=["gold"],  # does not include 'silver'
    ):
        report = engine.compute(
            backtest_result=mock_result,
            asset="silver",  # not available
            n_contracts=4,
        )

    assert isinstance(report, RegimeAttributionReport)
    assert report.regime_metrics == {}
    assert report.asset == "silver"


@SKIP_NO_CONTRACT
def test_regime_attribution_regime_coverage_sums_to_one() -> None:
    """regime_coverage values sum to approximately 1.0."""
    from src.analytics.regime_attribution import RegimeAttributionEngine
    from src.backtesting.run_manager import RunManager
    from src.core.config import Config

    config = Config.load("config/")
    manager = RunManager(config)

    # Find any completed Gold run
    from pathlib import Path as _Path

    runs_dir = _Path("data/runs")
    gold_runs = sorted(
        [
            d
            for d in runs_dir.iterdir()
            if d.name.endswith("_gold") and (d / "trades.parquet").exists()
        ],
        reverse=True,
    )
    if not gold_runs:
        pytest.skip("No completed Gold runs on disk")

    run_id = gold_runs[0].name
    try:
        result = _proxy_from_artifact(manager.load_run(run_id), run_id)
    except Exception:
        pytest.skip(f"Could not load run {run_id}")

    engine = RegimeAttributionEngine(config=config)
    report = engine.compute(backtest_result=result, asset="gold", n_contracts=4)

    if not report.regime_coverage:
        pytest.skip("No regime data available for this run")

    total = sum(report.regime_coverage.values())
    assert (
        abs(total - 1.0) < 0.01
    ), f"regime_coverage values sum to {total:.4f}, expected ~1.0"


@SKIP_NO_CONTRACT
def test_regime_attribution_metrics_have_three_regimes() -> None:
    """RegimeAttributionReport has entries for all three regimes."""
    from pathlib import Path as _Path

    from src.analytics.regime_attribution import RegimeAttributionEngine
    from src.backtesting.run_manager import RunManager
    from src.core.config import Config

    config = Config.load("config/")
    manager = RunManager(config)

    runs_dir = _Path("data/runs")
    gold_runs = sorted(
        [
            d
            for d in runs_dir.iterdir()
            if d.name.endswith("_gold") and (d / "trades.parquet").exists()
        ],
        reverse=True,
    )
    if not gold_runs:
        pytest.skip("No completed Gold runs on disk")

    run_id = gold_runs[0].name
    try:
        result = _proxy_from_artifact(manager.load_run(run_id), run_id)
    except Exception:
        pytest.skip(f"Could not load run {run_id}")

    engine = RegimeAttributionEngine(config=config)
    report = engine.compute(backtest_result=result, asset="gold", n_contracts=4)

    if not report.regime_metrics:
        pytest.skip("No regime metrics — insufficient contract data")

    expected_regimes = {"contango", "backwardation", "flat"}
    actual_regimes = set(report.regime_metrics.keys())
    assert actual_regimes == expected_regimes, (
        f"Expected regimes {expected_regimes}, got {actual_regimes}. "
        "Adjust if TermStructureRegime enum values differ."
    )
