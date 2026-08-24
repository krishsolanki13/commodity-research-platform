from __future__ import annotations

import concurrent.futures as _cf
import datetime
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from api.exceptions import ApiError
from api.models import (
    DecayEntry,
    ParamSpec,
    RollingICResponse,
    SignalEvaluateRequest,
    SignalEvaluateResponse,
    SignalEvaluationData,
    SignalGenerateRequest,
    SignalGenerateResponse,
    StrategyCatalogResponse,
    StrategyMeta,
    series_to_columnar,
)

router = APIRouter(prefix="/api", tags=["signals"])
logger = logging.getLogger(__name__)


def _evaluate_with_timeout(fn, timeout_seconds: int = 120):
    """Run a sync callable with a hard timeout (evaluate is not async)."""
    with _cf.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout_seconds)
        except _cf.TimeoutError:
            raise TimeoutError(
                f"Signal evaluation timed out after {timeout_seconds}s. "
                "Try a shorter date range (use 1Y–3Y instead of full history)."
            ) from None


def classify_ic_band(
    ic: float | None,
) -> Literal["strong", "weak_positive", "weak_inverse", "inverse_meaningful", "noise"]:
    """ADR-007 five-way IC classification."""
    if ic is None:
        return "noise"
    abs_ic = abs(ic)
    if abs_ic >= 0.05:
        return "strong" if ic > 0 else "inverse_meaningful"
    if abs_ic >= 0.02:
        return "weak_positive" if ic > 0 else "weak_inverse"
    return "noise"


def _load_strategy_catalog() -> list[StrategyMeta]:
    """Build strategy catalog from strategies.yaml defaults."""
    from pathlib import Path  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    p = Path("config/strategies.yaml")
    raw: dict[str, Any] = yaml.safe_load(p.read_text()) if p.exists() else {}

    strategies = [
        StrategyMeta(
            name="ema_crossover",
            display_name="EMA Crossover",
            description=(
                "Long when fast EMA > slow EMA, short when fast EMA < slow EMA. "
                "Classic trend-following signal."
            ),
            params_schema=[
                ParamSpec(
                    name="fast_period",
                    kind="int",
                    default=50,
                    min=2,
                    max=200,
                    description="Fast EMA period",
                    unit="bars",
                ),
                ParamSpec(
                    name="slow_period",
                    kind="int",
                    default=200,
                    min=10,
                    max=500,
                    description="Slow EMA period",
                    unit="bars",
                ),
                ParamSpec(
                    name="signal_threshold",
                    kind="float",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    description="Threshold for position entry",
                ),
            ],
            default_params=raw.get("ema_crossover", {}),
        ),
        StrategyMeta(
            name="momentum",
            display_name="Momentum",
            description=(
                "Long when z-scored momentum is positive, short when negative. "
                "Cross-sectional momentum adapted for single-asset use."
            ),
            params_schema=[
                ParamSpec(
                    name="lookback_period",
                    kind="int",
                    default=20,
                    min=5,
                    max=252,
                    description="Momentum lookback",
                    unit="bars",
                ),
                ParamSpec(
                    name="z_score_window",
                    kind="int",
                    default=63,
                    min=10,
                    max=252,
                    description="Z-score window",
                    unit="bars",
                ),
                ParamSpec(
                    name="signal_threshold",
                    kind="float",
                    default=0.5,
                    min=0.0,
                    max=3.0,
                    description="Z-score threshold",
                ),
            ],
            default_params=raw.get("momentum", {}),
        ),
        StrategyMeta(
            name="rsi_reversion",
            display_name="RSI Reversion",
            description=(
                "Long when RSI is oversold, short when overbought. "
                "Mean-reversion signal using RSI oscillator."
            ),
            params_schema=[
                ParamSpec(
                    name="period",
                    kind="int",
                    default=14,
                    min=2,
                    max=50,
                    description="RSI period",
                    unit="bars",
                ),
                ParamSpec(
                    name="oversold_threshold",
                    kind="float",
                    default=30.0,
                    min=10.0,
                    max=45.0,
                    description="Oversold level",
                ),
                ParamSpec(
                    name="overbought_threshold",
                    kind="float",
                    default=70.0,
                    min=55.0,
                    max=90.0,
                    description="Overbought level",
                ),
            ],
            default_params=raw.get("rsi_reversion", {}),
        ),
        StrategyMeta(
            name="donchian_breakout",
            display_name="Donchian Breakout",
            description=(
                "Long on upward channel breakout, short on downward breakout. "
                "Classic trend-following channel system."
            ),
            params_schema=[
                ParamSpec(
                    name="channel_period",
                    kind="int",
                    default=20,
                    min=5,
                    max=252,
                    description="Channel lookback",
                    unit="bars",
                ),
            ],
            default_params=raw.get("donchian_breakout", {}),
        ),
        StrategyMeta(
            name="carry",
            display_name="Carry",
            description=(
                "Long in backwardation (positive roll yield), short in contango. "
                "Commodity risk premium from the futures curve."
            ),
            params_schema=[
                ParamSpec(
                    name="threshold",
                    kind="float",
                    default=0.0,
                    min=0.0,
                    max=0.5,
                    description="Minimum annualized roll yield magnitude to generate signal",
                ),
                ParamSpec(
                    name="n_contracts",
                    kind="int",
                    default=4,
                    min=2,
                    max=12,
                    description="Number of contracts used in forward curve construction",
                ),
            ],
            default_params=raw.get("carry", {}),
        ),
        StrategyMeta(
            name="wti_brent_spread",
            display_name="WTI-Brent Spread",
            description=(
                "Mean-reversion signal based on the WTI-Brent crude oil spread z-score. "
                "Long WTI when spread is narrow (WTI cheap); short WTI when wide. "
                "Requires asset='wti'. Single-asset approximation of a spread trade."
            ),
            params_schema=[
                ParamSpec(
                    name="lookback",
                    kind="int",
                    default=63,
                    min=20,
                    max=252,
                    description="Rolling window for spread mean and std (trading days)",
                ),
                ParamSpec(
                    name="threshold",
                    kind="float",
                    default=1.0,
                    min=0.5,
                    max=3.0,
                    description="Entry threshold (|z| > threshold to enter position)",
                ),
            ],
            default_params=raw.get("wti_brent_spread", {}),
        ),
        StrategyMeta(
            name="cot_positioning",
            display_name="COT Positioning",
            description=(
                "Contrarian signal from CFTC net speculative positioning. "
                "Percentile rank > 80 → short (overcrowded long). < 20 → long."
            ),
            params_schema=[
                ParamSpec(
                    name="upper_pct",
                    kind="float",
                    default=80.0,
                    min=50.0,
                    max=99.0,
                    description="Percentile rank above which to go short (overcrowded long)",
                ),
                ParamSpec(
                    name="lower_pct",
                    kind="float",
                    default=20.0,
                    min=1.0,
                    max=50.0,
                    description="Percentile rank below which to go long (overcrowded short)",
                ),
            ],
            default_params=raw.get("cot_positioning", {}),
        ),
        StrategyMeta(
            name="eia_inventory",
            display_name="EIA Inventory",
            description=(
                "Fundamental signal from EIA weekly petroleum inventory surprise. "
                "WTI and Brent only. Drawdown (negative surprise) -> long. "
                "Build (positive) -> short. Flat for all non-crude assets."
            ),
            params_schema=[
                ParamSpec(
                    name="threshold",
                    kind="float",
                    default=1.0,
                    min=0.5,
                    max=3.0,
                    description="Z-score threshold for inventory surprise entry",
                ),
            ],
            default_params=raw.get("eia_inventory", {}),
        ),
    ]
    return strategies


STRATEGY_CATALOG = _load_strategy_catalog()
_STRATEGY_MAP: dict[str, StrategyMeta] = {s.name: s for s in STRATEGY_CATALOG}


def _parse_date(s: str | None) -> datetime.date | None:
    if s is None:
        return None
    return datetime.date.fromisoformat(s)


def _build_signal_pipeline(
    strategy: str, params: dict[str, Any], asset: str
) -> tuple[list[Any], Any]:
    """Return (indicators, signal_generator) for a given strategy + params."""
    from src.research.momentum import Momentum  # noqa: PLC0415
    from src.research.moving_averages import EMA  # noqa: PLC0415
    from src.research.oscillators import RSI  # noqa: PLC0415
    from src.signal.breakout import DonchianBreakoutSignal  # noqa: PLC0415
    from src.signal.reversion import RSIReversionSignal  # noqa: PLC0415
    from src.signal.trend import EMACrossoverSignal, MomentumSignal  # noqa: PLC0415

    if strategy == "ema_crossover":
        fast = params.get("fast_period", 50)
        slow = params.get("slow_period", 200)
        return [EMA(period=fast), EMA(period=slow)], EMACrossoverSignal(
            fast_period=fast, slow_period=slow
        )

    if strategy == "momentum":
        lookback = params.get("lookback_period", 20)
        z_window = params.get("z_score_window", 63)
        return [Momentum(lookback=lookback)], MomentumSignal(
            lookback=lookback, z_score_window=z_window
        )

    if strategy == "rsi_reversion":
        period = params.get("period", 14)
        return [RSI(period=period)], RSIReversionSignal(period=period)

    if strategy == "donchian_breakout":
        ch_period = params.get("channel_period", 20)
        return [], DonchianBreakoutSignal(channel_period=ch_period)

    if strategy == "carry":
        from src.core.config import Config  # noqa: PLC0415
        from src.signal.carry import CarrySignal  # noqa: PLC0415

        return [], CarrySignal(
            config=Config.load(),
            threshold=params.get("threshold", 0.0),
            n_contracts=int(params.get("n_contracts", 4)),
        )

    if strategy == "wti_brent_spread":
        from src.core.config import Config  # noqa: PLC0415
        from src.signal.spread import WTIBrentSpreadSignal  # noqa: PLC0415

        if asset != "wti":
            raise ValueError(f"wti_brent_spread requires asset='wti', got '{asset}'")
        return [], WTIBrentSpreadSignal(
            config=Config.load(),
            lookback=int(params.get("lookback", 63)),
            threshold=float(params.get("threshold", 1.0)),
        )

    if strategy == "cot_positioning":
        from src.core.config import Config  # noqa: PLC0415
        from src.signal.cot import COTPositioningSignal  # noqa: PLC0415

        return [], COTPositioningSignal(
            config=Config.load(),
            upper_pct=float(params.get("upper_pct", 80.0)),
            lower_pct=float(params.get("lower_pct", 20.0)),
        )

    if strategy == "eia_inventory":
        from src.core.config import Config  # noqa: PLC0415
        from src.signal.eia import EIAInventorySignal  # noqa: PLC0415

        return [], EIAInventorySignal(
            config=Config.load(),
            threshold=float(params.get("threshold", 1.0)),
        )

    raise ApiError(
        code="UNKNOWN_STRATEGY",
        message=f"Strategy '{strategy}' is not registered.",
        status=400,
    )


def _run_signal_pipeline(
    asset: str,
    strategy: str,
    params: dict[str, Any],
    from_date: str | None,
    to_date: str | None,
):
    """Full pipeline: DataLoader → FeaturePipeline → SignalGenerator."""
    from src.core.config import Config  # noqa: PLC0415
    from src.data.loader import DataLoader  # noqa: PLC0415
    from src.research.feature_frame import FeatureFrame  # noqa: PLC0415
    from src.research.pipeline import FeaturePipeline  # noqa: PLC0415
    from src.signal.position import PositionSignalConstructor  # noqa: PLC0415

    # Scenario A: dates already reach DataLoader. Carry with no range
    # loads full history (~4k bars) and hangs in build_historical_curves.
    if strategy == "carry" and from_date is None:
        to_d = _parse_date(to_date) or datetime.date.today()
        try:
            from_d = datetime.date(to_d.year - 2, to_d.month, to_d.day)
        except ValueError:
            from_d = datetime.date(to_d.year - 2, 2, 28)
        from_date = from_d.isoformat()
        to_date = to_date or to_d.isoformat()
        logger.info(
            "CarrySignal: no date range provided — applying 2-year default "
            "to prevent full-history computation (%s to %s)",
            from_date,
            to_date,
        )

    cfg = Config.load()
    ohlcv = DataLoader(cfg).load(
        asset,
        start=_parse_date(from_date),
        end=_parse_date(to_date),
    )

    indicators, signal_gen = _build_signal_pipeline(strategy, params, asset)

    if indicators:
        feature_frame = FeaturePipeline(indicators).compute(ohlcv, asset=asset)
    else:
        feature_frame = FeatureFrame(ohlcv, feature_specs=[], asset=asset)

    raw_signal = signal_gen.generate(feature_frame)

    threshold = params.get("signal_threshold", 0.0)
    pos_signal = PositionSignalConstructor().build(raw_signal, threshold=threshold)

    return ohlcv, raw_signal, pos_signal


@router.get("/strategies", response_model=StrategyCatalogResponse)
def get_strategies() -> StrategyCatalogResponse:
    """Strategy catalog: names, param schemas, strategies.yaml defaults."""
    return StrategyCatalogResponse(strategies=STRATEGY_CATALOG)


@router.post("/signals/generate", response_model=SignalGenerateResponse)
def generate_signal(request: SignalGenerateRequest) -> SignalGenerateResponse:
    """Generate RawSignal and PositionSignal for an asset + strategy."""
    if request.strategy not in _STRATEGY_MAP:
        raise ApiError(
            code="UNKNOWN_STRATEGY",
            message=f"Strategy '{request.strategy}' is not registered.",
            status=400,
        )

    ohlcv, raw_signal, pos_signal = _run_signal_pipeline(
        request.asset,
        request.strategy,
        request.params,
        request.from_date,
        request.to_date,
    )

    valid = raw_signal.dropna()
    return SignalGenerateResponse(
        asset=request.asset,
        strategy=request.strategy,
        params=request.params,
        bars=len(valid),
        raw_signal=series_to_columnar(valid, col_name="raw"),
        position_signal=series_to_columnar(
            pos_signal.loc[valid.index], col_name="position"
        ),
    )


@router.post("/signals/evaluate", response_model=SignalEvaluateResponse)
def evaluate_signal(request: SignalEvaluateRequest) -> SignalEvaluateResponse:
    """Evaluate signal quality: IC, ICIR, decay. This is the IC Gate data source."""
    if request.strategy not in _STRATEGY_MAP:
        raise ApiError(
            code="UNKNOWN_STRATEGY",
            message=f"Strategy '{request.strategy}' is not registered.",
            status=400,
        )

    from src.signal.evaluation import SignalEvaluator  # noqa: PLC0415

    def _run_eval():
        ohlcv, raw_signal, _ = _run_signal_pipeline(
            request.asset,
            request.strategy,
            request.params,
            request.from_date,
            request.to_date,
        )
        evaluation = SignalEvaluator(asset=request.asset).evaluate(raw_signal, ohlcv)
        return ohlcv, raw_signal, evaluation

    try:
        _ohlcv, raw_signal, evaluation = _evaluate_with_timeout(_run_eval)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=408,
            detail={"code": "EVALUATION_TIMEOUT", "message": str(exc)},
        ) from exc

    decay = [
        DecayEntry(horizon=h, ic=evaluation.ic_decay.get(h))
        for h in sorted(evaluation.ic_decay)
    ]

    eval_data = SignalEvaluationData(
        ic=evaluation.ic,
        icir=evaluation.icir,
        turnover=evaluation.turnover,
        decay=decay,
        evaluation_window=len(raw_signal.dropna()),
        computed_at=datetime.datetime.now(datetime.UTC).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3]
        + "Z",
        ic_band=classify_ic_band(evaluation.ic),
    )

    return SignalEvaluateResponse(
        asset=request.asset,
        strategy=request.strategy,
        params=request.params,
        evaluation=eval_data,
    )


@router.get("/signals/rolling-ic")
async def get_rolling_ic(
    asset: str,
    strategy: str,
    params: str = "{}",
    window: int = Query(default=63, ge=10, le=252),
) -> RollingICResponse:
    """Rolling IC: Pearson(RawSignal, forward_return) over a rolling window.

    Query parameters:
      asset:    Asset identifier (e.g. 'gold')
      strategy: Strategy name (e.g. 'ema_crossover')
      params:   JSON-encoded parameter dict
      window:   Rolling window in bars (default 63, min 10, max 252)

    Returns RollingICResponse with ColumnarSeries (epoch-ms index,
    rolling_ic column). Null for first window-1 bars.
    Invalid params JSON → 422.
    """
    import json as _json  # noqa: PLC0415

    from src.signal.evaluation import SignalEvaluator  # noqa: PLC0415

    try:
        parameters = _json.loads(params)
    except _json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid params JSON: {exc}",
        ) from exc

    try:
        evaluator = SignalEvaluator(asset=asset, ic_rolling_window=window)
        rolling_ic_series = evaluator.compute_rolling_ic(
            strategy_name=strategy,
            parameters=parameters,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Rolling IC computation failed: {exc}",
        ) from exc

    columnar = series_to_columnar(rolling_ic_series, col_name="rolling_ic")

    return RollingICResponse(
        asset=asset,
        strategy_name=strategy,
        parameters=parameters,
        window=window,
        data=columnar,
    )
