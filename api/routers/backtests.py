from __future__ import annotations

import datetime
import traceback
from typing import Any

from fastapi import APIRouter, BackgroundTasks

from api import state
from api.exceptions import ApiError
from api.models import (
    BacktestLaunchRequest,
    TaskLaunchResponse,
    TaskStatusResponse,
)

router = APIRouter(prefix="/api", tags=["backtests"])


def _build_full_pipeline(
    strategy: str, params: dict[str, Any], asset: str
) -> tuple[list[Any], Any]:
    """Return (indicators, signal_generator) for strategy + params.

    Mirrors _build_signal_pipeline() in signals.py — kept local to avoid
    cross-router imports. TD-M14-A equivalent: extract to pipeline_builder.py
    in a future housekeeping pass.
    """
    from src.research.momentum import Momentum  # noqa: PLC0415
    from src.research.moving_averages import EMA  # noqa: PLC0415
    from src.research.oscillators import RSI  # noqa: PLC0415
    from src.signal.breakout import DonchianBreakoutSignal  # noqa: PLC0415
    from src.signal.reversion import RSIReversionSignal  # noqa: PLC0415
    from src.signal.trend import EMACrossoverSignal, MomentumSignal  # noqa: PLC0415

    indicators: list[Any]
    gen: Any

    if strategy == "ema_crossover":
        fast = params.get("fast_period", 50)
        slow = params.get("slow_period", 200)
        indicators = [EMA(period=fast), EMA(period=slow)]
        gen = EMACrossoverSignal(fast_period=fast, slow_period=slow)

    elif strategy == "momentum":
        lookback = params.get("lookback_period", 20)
        z_window = params.get("z_score_window", 63)
        indicators = [Momentum(lookback=lookback)]
        gen = MomentumSignal(lookback=lookback, z_score_window=z_window)

    elif strategy == "rsi_reversion":
        period = params.get("period", 14)
        indicators = [RSI(period=period)]
        gen = RSIReversionSignal(period=period)

    elif strategy == "donchian_breakout":
        ch_period = params.get("channel_period", 20)
        indicators = []
        gen = DonchianBreakoutSignal(channel_period=ch_period)

    else:
        raise ApiError(
            code="UNKNOWN_STRATEGY",
            message=f"Strategy '{strategy}' is not registered.",
            status=400,
        )

    return indicators, gen


def _run_backtest_task(polling_run_id: str, request: BacktestLaunchRequest) -> None:
    """Background task: full research pipeline for one asset."""
    try:
        state.update(polling_run_id, "running")

        from src.backtesting.engine import VectorizedBacktester  # noqa: PLC0415
        from src.backtesting.run_manager import RunManager  # noqa: PLC0415
        from src.backtesting.sizing import (  # noqa: PLC0415
            FixedNotionalSizer,
            VolatilityScaledSizer,
        )
        from src.core.config import Config  # noqa: PLC0415
        from src.data.loader import DataLoader  # noqa: PLC0415
        from src.performance.report import PerformanceEngine  # noqa: PLC0415
        from src.research.feature_frame import FeatureFrame  # noqa: PLC0415
        from src.research.pipeline import FeaturePipeline  # noqa: PLC0415
        from src.signal.evaluation import SignalEvaluator  # noqa: PLC0415
        from src.signal.position import PositionSignalConstructor  # noqa: PLC0415

        cfg = Config.load()
        cfg.costs = {
            **cfg.costs,
            "default_commission_usd": request.commission_per_trade,
            "default_slippage_ticks": request.slippage_ticks,
        }

        start = (
            datetime.date.fromisoformat(request.from_date)
            if request.from_date
            else None
        )
        end = datetime.date.fromisoformat(request.to_date) if request.to_date else None
        ohlcv = DataLoader(cfg).load(request.asset, start=start, end=end)

        indicators, signal_gen = _build_full_pipeline(
            request.strategy, request.params, request.asset
        )
        if indicators:
            feature_frame = FeaturePipeline(indicators).compute(
                ohlcv, asset=request.asset
            )
        else:
            feature_frame = FeatureFrame(ohlcv, feature_specs=[], asset=request.asset)

        raw_signal = signal_gen.generate(feature_frame)

        try:
            signal_evaluation = SignalEvaluator(asset=request.asset).evaluate(
                raw_signal, ohlcv
            )
        except ValueError:
            signal_evaluation = None

        threshold = request.params.get("signal_threshold", request.signal_threshold)
        pos_signal = PositionSignalConstructor().build(raw_signal, threshold=threshold)

        sizer: VolatilityScaledSizer | FixedNotionalSizer
        if (
            request.sizing_method == "volatility_scaled"
            and request.target_annual_vol is not None
        ):
            sizer = VolatilityScaledSizer(target_annual_vol=request.target_annual_vol)
        else:
            sizer = FixedNotionalSizer(notional_usd=request.notional_usd)

        backtester = VectorizedBacktester(
            asset=request.asset,
            strategy_name=request.strategy,
            signal_name=signal_gen.name,
            config=cfg,
            parameters=request.params,
            initial_capital_usd=request.initial_capital,
            sizer=sizer,
        )
        backtest_result = backtester.run(pos_signal, ohlcv)
        backtest_result.signal_evaluation = signal_evaluation

        perf_report = PerformanceEngine().compute(backtest_result)

        run_manager = RunManager(cfg)
        run_manager.save(backtest_result)
        run_manager.save_metrics(backtest_result.run_id, perf_report)

        state.set_artifact_id(polling_run_id, backtest_result.run_id)

        executed_at = (
            datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")
        )
        state.update(polling_run_id, "complete", executed_at=executed_at)

    except Exception as e:
        state.update(
            polling_run_id,
            "failed",
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()[:800]}",
        )


@router.post("/backtests", response_model=TaskLaunchResponse, status_code=202)
def launch_backtest(
    request: BacktestLaunchRequest,
    background_tasks: BackgroundTasks,
) -> TaskLaunchResponse:
    """Launch a backtest asynchronously. Returns polling run_id immediately.

    signal_evaluation: null is accepted without error — gate
    enforcement is client-side doctrine only (ADR-007).
    """
    ts = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    polling_run_id = f"poll_{ts}_{request.strategy}_{request.asset}"
    state.register(polling_run_id)
    background_tasks.add_task(_run_backtest_task, polling_run_id, request)
    return TaskLaunchResponse(run_id=polling_run_id, status="queued")


@router.get("/backtests/{run_id}/status", response_model=TaskStatusResponse)
def get_backtest_status(run_id: str) -> TaskStatusResponse:
    """Poll task status. Returns queued|running|complete|failed."""
    task = state.get(run_id)
    if task is None:
        raise ApiError(
            code="RUN_NOT_FOUND",
            message=f"Run '{run_id}' not found.",
            status=404,
        )
    return TaskStatusResponse(
        run_id=run_id,
        status=task["status"],
        error=task.get("error"),
        executed_at=task.get("executed_at"),
    )
