from __future__ import annotations

import datetime
import json
import math
import traceback
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks

from api import state
from api.exceptions import ApiError
from api.models import (
    BacktestLaunchRequest,
    SignalEvaluationData,
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


def _api_eval_to_core(
    se: SignalEvaluationData,
    *,
    signal_name: str,
    asset: str,
    evaluation_start: datetime.date,
    evaluation_end: datetime.date,
) -> Any:
    """Convert API SignalEvaluationData → core SignalEvaluation dataclass.

    evaluation_window maps to ic_rolling_window. ic_band and computed_at are
    API-only fields and are not stored on the dataclass (they remain in
    params.json via _persist_signal_evaluation).
    """
    from src.core.types import SignalEvaluation  # noqa: PLC0415

    def _f(v: float | None) -> float:
        return float("nan") if v is None else v

    ic_decay: dict[int, float] = {}
    for e in se.decay:
        if e.ic is None or (isinstance(e.ic, float) and math.isnan(e.ic)):
            continue
        ic_decay[e.horizon] = e.ic

    return SignalEvaluation(
        signal_name=signal_name,
        asset=asset,
        ic=_f(se.ic),
        icir=_f(se.icir),
        ic_decay=ic_decay,
        turnover=_f(se.turnover),
        ic_rolling_window=se.evaluation_window,
        evaluation_start=evaluation_start,
        evaluation_end=evaluation_end,
    )


def _persist_signal_evaluation(
    cfg: Any,
    run_id: str,
    se_data: SignalEvaluationData | None,
) -> None:
    """Write signal_evaluation into params.json after RunManager.save().

    RunManager only serialises BacktestMetadata — signal_evaluation lives on
    BacktestResult and is not written by save(). The API layer patches
    params.json so GET /api/runs/{id} can return the IC Gate payload.
    """
    params_path = Path(cfg.paths["runs"]) / run_id / "params.json"
    params = json.loads(params_path.read_text(encoding="utf-8"))
    params["signal_evaluation"] = se_data.model_dump() if se_data is not None else None
    params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")


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

        # Prefer client-provided IC Gate evaluation. None = IC Gate override
        # (or absent field) — persist null and skip recompute so override is
        # visible on the Signal Quality tab.
        se_data = request.signal_evaluation
        if se_data is not None:
            eval_start = ohlcv.index[0].date()
            eval_end = ohlcv.index[-1].date()
            signal_evaluation = _api_eval_to_core(
                se_data,
                signal_name=signal_gen.name,
                asset=request.asset,
                evaluation_start=eval_start,
                evaluation_end=eval_end,
            )
        else:
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
        _persist_signal_evaluation(cfg, backtest_result.run_id, se_data)

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
