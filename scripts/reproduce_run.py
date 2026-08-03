#!/usr/bin/env python
"""Verify reproducibility of a completed backtest run.

Reads params.json for the specified run, re-runs the exact pipeline
with the same parameters, hashes the equity curve, and compares
against the stored hash from the original run.

Usage:
    python scripts/reproduce_run.py --run-id 20260722_120000_ema_crossover_gold

Exit codes:
    0 — Reproduced: equity curve hash matches
    1 — Mismatch: equity curve hash differs
    2 — Error: could not load run or re-run pipeline

Reproducibility is a core architectural guarantee of the platform.
This script provides an executable proof for any completed run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _hash_equity_curve(equity_values: list[float]) -> str:
    """SHA256 of rounded equity curve values (2dp). Matches golden-master pattern."""
    rounded = [round(v, 2) for v in equity_values]
    return hashlib.sha256(json.dumps(rounded).encode()).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify reproducibility of a completed backtest run."
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run ID to reproduce (e.g. 20260722_120000_ema_crossover_gold)",
    )
    parser.add_argument(
        "--runs-dir",
        default="data/runs",
        help="Directory containing run artifacts (default: data/runs)",
    )
    args = parser.parse_args()

    run_id = args.run_id
    runs_dir = Path(args.runs_dir)
    run_dir = runs_dir / run_id

    print(f"Reproducing run: {run_id}")

    # ── Step 1: Load params.json ──────────────────────────────────────────
    params_path = run_dir / "params.json"
    if not params_path.exists():
        print(f"ERROR: params.json not found at {params_path}", file=sys.stderr)
        return 2

    params = json.loads(params_path.read_text(encoding="utf-8"))
    # strategy_name key with fallback to 'strategy'
    strategy_name = params.get("strategy_name", params.get("strategy", ""))
    asset = params.get("asset", "")
    parameters = params.get("parameters", {})

    if not strategy_name or not asset:
        print(
            f"ERROR: could not extract strategy_name/asset from params.json. "
            f"Keys found: {list(params.keys())}",
            file=sys.stderr,
        )
        return 2

    print(f"  asset:    {asset}")
    print(f"  strategy: {strategy_name}")
    print(f"  params:   {parameters}")

    # ── Step 2: Load original equity curve ───────────────────────────────
    # DEV-EM8-1: load_run returns dict with equity_curve key
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.backtesting.run_manager import RunManager
        from src.core.config import Config

        config = Config.load()
        manager = RunManager(config)
        run_data = manager.load_run(run_id)
        original_equity = run_data.get("equity_curve")

        if original_equity is None or len(original_equity) == 0:
            print("ERROR: no equity_curve in run artifacts", file=sys.stderr)
            return 2

        original_hash = _hash_equity_curve(original_equity.values.tolist())
        print(f"  original equity curve hash: {original_hash}")
        print(f"  bars in original: {len(original_equity)}")

    except Exception as exc:
        print(f"ERROR loading original run: {exc}", file=sys.stderr)
        return 2

    # ── Step 3: Re-run pipeline ───────────────────────────────────────────
    print("  re-running pipeline...")
    try:
        from src.backtesting.engine import VectorizedBacktester
        from src.backtesting.pipeline_builder import build_pipeline_components
        from src.data.loader import DataLoader
        from src.research.pipeline import FeaturePipeline
        from src.signal.position import PositionSignalConstructor

        ohlcv = DataLoader(config).load(asset)

        # DEV-EM5-1: build_pipeline_components returns (indicators, signal_gen) 2-tuple
        indicators, signal_gen = build_pipeline_components(
            strategy_name=strategy_name,
            parameters=parameters,
            config=config,
        )
        feature_pipeline = FeaturePipeline(indicators)
        feature_frame = feature_pipeline.compute(ohlcv, asset=asset)
        raw_signal = signal_gen.generate(feature_frame)
        position_signal = PositionSignalConstructor().build(raw_signal, threshold=0.0)

        backtester = VectorizedBacktester(
            asset=asset,
            strategy_name=strategy_name,
            signal_name=getattr(signal_gen, "name", strategy_name),
            config=config,
            parameters=parameters,
        )
        result = backtester.run(position_signal, ohlcv)

    except Exception as exc:
        print(f"ERROR re-running pipeline: {exc}", file=sys.stderr)
        return 2

    # ── Step 4: Compare hashes ────────────────────────────────────────────
    reproduced_hash = _hash_equity_curve(result.equity_curve.values.tolist())
    print(f"  reproduced equity curve hash: {reproduced_hash}")
    print(f"  bars in reproduced: {len(result.equity_curve)}")

    if reproduced_hash == original_hash:
        print()
        print(f"REPRODUCED: equity curve hash matches ({reproduced_hash})")
        return 0
    else:
        print()
        print("MISMATCH: equity curve hash differs")
        print(f"  original:   {original_hash}")
        print(f"  reproduced: {reproduced_hash}")
        print(
            "The run could not be reproduced. Possible causes: "
            "data was re-ingested with different date range, "
            "code was changed after the run, or non-deterministic component."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
