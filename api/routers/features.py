from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter

from api.exceptions import ApiError
from api.models import (
    FeatureComputeRequest,
    FeatureComputeResponse,
    FeatureSpecResponse,
    IndicatorCatalogResponse,
    IndicatorMeta,
    ParamSpec,
    df_to_columnar,
)

router = APIRouter(prefix="/api", tags=["features"])

# ── Static indicator catalog ───────────────────────────────────────────────────
# Populated from Indicator __init__ signatures in src/research/*.py.

INDICATOR_CATALOG: list[IndicatorMeta] = [
    IndicatorMeta(
        name="sma",
        display_name="Simple Moving Average",
        category="trend",
        params_schema=[
            ParamSpec(
                name="period",
                kind="int",
                default=20,
                min=2,
                max=500,
                description="Lookback period",
                unit="bars",
            ),
        ],
        column_name_template="sma_{period}",
    ),
    IndicatorMeta(
        name="ema",
        display_name="Exponential Moving Average",
        category="trend",
        params_schema=[
            ParamSpec(
                name="period",
                kind="int",
                default=20,
                min=2,
                max=500,
                description="Lookback period",
                unit="bars",
            ),
        ],
        column_name_template="ema_{period}",
    ),
    IndicatorMeta(
        name="rsi",
        display_name="Relative Strength Index",
        category="oscillator",
        params_schema=[
            ParamSpec(
                name="period",
                kind="int",
                default=14,
                min=2,
                max=100,
                description="RSI period",
                unit="bars",
            ),
        ],
        column_name_template="rsi_{period}",
    ),
    IndicatorMeta(
        name="rvgi",
        display_name="Relative Vigor Index",
        category="momentum",
        params_schema=[
            ParamSpec(
                name="period",
                kind="int",
                default=10,
                min=2,
                max=100,
                description="RVGI period",
                unit="bars",
            ),
        ],
        column_name_template="rvgi_{period}",
    ),
    IndicatorMeta(
        name="momentum",
        display_name="Momentum",
        category="momentum",
        params_schema=[
            ParamSpec(
                name="lookback",
                kind="int",
                default=20,
                min=1,
                max=252,
                description="Lookback period",
                unit="bars",
            ),
        ],
        column_name_template="momentum_{lookback}",
    ),
]

_CATALOG_MAP: dict[str, IndicatorMeta] = {m.name: m for m in INDICATOR_CATALOG}


def _build_indicator(name: str, params: dict[str, Any]):
    """Instantiate a src/ Indicator from a name + params dict."""
    from src.research.momentum import Momentum  # noqa: PLC0415
    from src.research.moving_averages import EMA, SMA  # noqa: PLC0415
    from src.research.oscillators import RSI, RVGI  # noqa: PLC0415

    registry = {
        "sma": lambda p: SMA(period=p.get("period", 20)),
        "ema": lambda p: EMA(period=p.get("period", 20)),
        "rsi": lambda p: RSI(period=p.get("period", 14)),
        "rvgi": lambda p: RVGI(period=p.get("period", 10)),
        "momentum": lambda p: Momentum(lookback=p.get("lookback", 20)),
    }
    if name not in registry:
        raise ApiError(
            code="UNKNOWN_INDICATOR",
            message=f"Indicator '{name}' is not registered.",
            status=400,
        )
    return registry[name](params)


def _parse_date(s: str | None) -> datetime.date | None:
    """Parse ISO date string to datetime.date, or return None."""
    if s is None:
        return None
    return datetime.date.fromisoformat(s)


def _format_utc(dt: datetime.datetime) -> str:
    return dt.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@router.get("/indicators", response_model=IndicatorCatalogResponse)
def get_indicators() -> IndicatorCatalogResponse:
    """Indicator catalog: drives the IndicatorPicker in the frontend."""
    return IndicatorCatalogResponse(indicators=INDICATOR_CATALOG)


@router.post("/features/compute", response_model=FeatureComputeResponse)
def compute_features(request: FeatureComputeRequest) -> FeatureComputeResponse:
    """Compute indicator columns for an asset. Returns columnar FeatureFrame."""
    from src.core.config import Config  # noqa: PLC0415
    from src.data.loader import DataLoader  # noqa: PLC0415
    from src.research.pipeline import FeaturePipeline  # noqa: PLC0415

    cfg = Config.load()
    loader = DataLoader(cfg)
    ohlcv = loader.load(
        request.asset,
        start=_parse_date(request.from_date),
        end=_parse_date(request.to_date),
    )

    indicators = [_build_indicator(spec.name, spec.params) for spec in request.specs]

    if not indicators:
        raise ApiError(
            code="NO_INDICATORS",
            message="At least one indicator spec is required.",
            status=400,
        )

    feature_frame = FeaturePipeline(indicators).compute(ohlcv, asset=request.asset)

    ohlcv_cols = {"open", "high", "low", "close", "volume", "open_interest"}
    feature_cols = [c for c in feature_frame.data.columns if c not in ohlcv_cols]

    spec_responses = [
        FeatureSpecResponse(
            indicator_name=fs.indicator_name,
            params=fs.parameters,
            column_name=fs.column_name,
            asset=fs.asset,
            computed_at=_format_utc(fs.computed_at),
        )
        for fs in feature_frame.feature_specs
    ]

    feature_df = feature_frame.data[feature_cols]
    from_str = ohlcv.index[0].date().isoformat() if len(ohlcv) else ""
    to_str = ohlcv.index[-1].date().isoformat() if len(ohlcv) else ""

    return FeatureComputeResponse(
        asset=request.asset,
        from_date=from_str,
        to_date=to_str,
        bars=len(ohlcv),
        specs=spec_responses,
        columns=df_to_columnar(feature_df),
    )
