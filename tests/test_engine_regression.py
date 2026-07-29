"""Engine golden-master regression tests.

Creates a fixture on first run; guards against silent regressions on subsequent runs.
Any change to VectorizedBacktester, FeaturePipeline, SignalGenerator, or CostModel
that silently changes trade outputs will fail these tests.

These tests are the safety net for EM2 (engine correctness fixes):
  - Run EM1 first → fixture created with current (pre-fix) values
  - Run EM2 (TD-B + TD-C fixes) → fixture intentionally changes
  - Update fixture after EM2 is verified → re-locked for future safety

Fixture file: tests/fixtures/engine_golden_master.json
To recreate: delete the fixture file and run pytest — it will be recreated.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

FIXTURE_PATH = Path("tests/fixtures/engine_golden_master.json")
FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)

ASSET = "gold"
STRATEGY = "ema_crossover"
PARAMETERS = {"fast_period": 50, "slow_period": 200}


@pytest.fixture(scope="module")
def golden_result():
    """Run the canonical EMA 50/200 on Gold and return the BacktestResult."""
    from pathlib import Path  # noqa: PLC0415

    data_path = Path("data/processed/continuous/gold.parquet")
    if not data_path.exists():
        pytest.skip(
            f"Gold Parquet not available at {data_path}. "
            "Golden-master tests require local data files — skipped in CI."
        )

    from src.backtesting.engine import VectorizedBacktester
    from src.backtesting.pipeline_builder import build_pipeline_components
    from src.core.config import Config
    from src.data.loader import DataLoader
    from src.research.pipeline import FeaturePipeline
    from src.signal.position import PositionSignalConstructor

    config = Config.load("config/")
    ohlcv = DataLoader(config).load(ASSET)

    indicators, signal_generator = build_pipeline_components(
        strategy_name=STRATEGY,
        parameters=PARAMETERS,
        config=config,
    )

    feature_frame = FeaturePipeline(indicators).compute(ohlcv, asset=ASSET)
    raw_signal = signal_generator.generate(feature_frame)
    position_signal = PositionSignalConstructor().build(raw_signal, threshold=0.0)

    backtester = VectorizedBacktester(
        asset=ASSET,
        strategy_name=STRATEGY,
        signal_name=signal_generator.name,
        config=config,
        parameters=PARAMETERS,
    )
    return backtester.run(position_signal, ohlcv)


def _equity_checksum(result) -> str:
    """SHA256 of the rounded equity curve (2dp) for exact comparison."""
    rounded = [round(v, 2) for v in result.equity_curve.values.tolist()]
    return hashlib.sha256(json.dumps(rounded).encode()).hexdigest()[:16]


def test_golden_master_fixture_created_or_matches(golden_result) -> None:
    """On first run: create fixture. On subsequent runs: assert exact match.

    Fixture captures: trade count, final equity, first 5 trade net_pnls,
    equity curve checksum. Any silent engine regression changes at least one.
    """
    result = golden_result
    trades = result.trades if hasattr(result, "trades") else []

    actual = {
        "n_trades": len(trades),
        "final_equity": round(float(result.equity_curve.iloc[-1]), 2),
        "first_5_trade_pnls": [round(float(t.net_pnl), 4) for t in trades[:5]]
        if trades
        else [],
        "equity_checksum": _equity_checksum(result),
        "asset": ASSET,
        "strategy": STRATEGY,
        "parameters": PARAMETERS,
    }

    if not FIXTURE_PATH.exists():
        FIXTURE_PATH.write_text(json.dumps(actual, indent=2), encoding="utf-8")
        pytest.skip(
            f"Golden-master fixture created at {FIXTURE_PATH}. "
            "Run pytest again to activate the regression guard."
        )

    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert actual["n_trades"] == expected["n_trades"], (
        f"Trade count changed: {expected['n_trades']} → {actual['n_trades']}. "
        "If this is an intentional engine fix, delete the fixture file and re-run."
    )
    assert (
        actual["final_equity"] == expected["final_equity"]
    ), f"Final equity changed: {expected['final_equity']} → {actual['final_equity']}"
    assert actual["equity_checksum"] == expected["equity_checksum"], (
        "Equity curve checksum changed. "
        "Engine output has changed — intended or regression? "
        "Delete fixture and re-run if intentional."
    )


def test_golden_master_first_5_trades_stable(golden_result) -> None:
    """First 5 trade PnLs must match the fixture exactly (4dp tolerance)."""
    if not FIXTURE_PATH.exists():
        pytest.skip(
            "Fixture not yet created — run test_golden_master_fixture_created_or_matches first."
        )

    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    trades = golden_result.trades if hasattr(golden_result, "trades") else []
    actual_pnls = [round(float(t.net_pnl), 4) for t in trades[:5]]

    assert actual_pnls == expected["first_5_trade_pnls"], (
        f"First 5 trade PnLs changed:\n"
        f"  expected: {expected['first_5_trade_pnls']}\n"
        f"  actual:   {actual_pnls}"
    )
