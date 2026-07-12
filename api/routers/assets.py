from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, Query

from api.dependencies import KNOWN_ASSETS, get_asset_or_404
from api.downsample import lttb_ohlcv
from api.models import (
    AssetMetadata,
    AssetSummaryResponse,
    OhlcvResponse,
    UniverseResponse,
    df_to_columnar,
)

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _display_name(asset_key: str) -> str:
    if asset_key == "wti":
        return "WTI"
    return asset_key.replace("_", " ").title()


def _safe_float(v) -> float | None:
    import math

    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _load_asset_metadata(cfg) -> list[AssetMetadata]:
    """Build AssetMetadata list from assets.yaml via Config."""
    result: list[AssetMetadata] = []
    for name, meta in cfg.assets.items():
        result.append(
            AssetMetadata(
                name=name,
                display_name=_display_name(name),
                ticker_continuous=meta["ticker_continuous"],
                contract_root=meta["contract_root"],
                exchange_suffix=meta["exchange_suffix"],
                exchange=meta["exchange"],
                currency=meta["currency"],
                unit=meta["unit"],
                contract_multiplier=meta["contract_multiplier"],
                tick_size=meta["tick_size"],
                tick_value=meta["tick_value"],
            )
        )
    return sorted(result, key=lambda a: a.name)


def _load_ohlcv(asset: str) -> pd.DataFrame:
    """Load processed Parquet for an asset. Returns NormalizedOHLCV DataFrame."""
    from src.core.config import Config
    from src.data.loader import DataLoader

    cfg = Config.load()
    loader = DataLoader(cfg)
    return loader.load(asset)


def _compute_summary(asset: str, ohlcv: pd.DataFrame) -> AssetSummaryResponse:
    """Compute headline metrics from OHLCV DataFrame."""
    if len(ohlcv) == 0:
        return AssetSummaryResponse(
            name=asset,
            last_price=None,
            last_date=None,
            return_1d=None,
            return_1w=None,
            return_1m=None,
            realized_vol_63d=None,
            avg_volume_20d=None,
            bar_count=0,
            data_health="missing",
            flagged_anomalies=0,
        )

    close = ohlcv["close"]
    flagged_anomalies = 0
    data_health: str = "ok" if flagged_anomalies == 0 else "warn"

    vol_slice = close.pct_change().iloc[-63:]
    realized_vol = (
        float(vol_slice.std() * (252**0.5)) if len(vol_slice.dropna()) > 1 else None
    )

    return AssetSummaryResponse(
        name=asset,
        last_price=float(close.iloc[-1]),
        last_date=ohlcv.index[-1].date().isoformat(),
        return_1d=_safe_float(close.pct_change().iloc[-1]),
        return_1w=_safe_float(close.pct_change(5).iloc[-1]),
        return_1m=_safe_float(close.pct_change(21).iloc[-1]),
        realized_vol_63d=_safe_float(realized_vol),
        avg_volume_20d=_safe_float(ohlcv["volume"].iloc[-20:].mean()),
        bar_count=len(ohlcv),
        data_health=data_health,
        flagged_anomalies=flagged_anomalies,
    )


@router.get("", response_model=UniverseResponse)
def get_assets() -> UniverseResponse:
    """Universe summary: all 6 assets with metadata and headline stats."""
    from src.core.config import Config

    cfg = Config.load()

    asset_meta = _load_asset_metadata(cfg)

    summaries: dict[str, AssetSummaryResponse] = {}
    for name in KNOWN_ASSETS:
        try:
            ohlcv = _load_ohlcv(name)
            summaries[name] = _compute_summary(name, ohlcv)
        except Exception:
            summaries[name] = AssetSummaryResponse(
                name=name,
                last_price=None,
                last_date=None,
                return_1d=None,
                return_1w=None,
                return_1m=None,
                realized_vol_63d=None,
                avg_volume_20d=None,
                bar_count=0,
                data_health="missing",
                flagged_anomalies=0,
            )

    runs_dir = Path(cfg.paths["runs"])
    total_runs = len(list(runs_dir.glob("*/params.json"))) if runs_dir.exists() else 0

    return UniverseResponse(
        assets=asset_meta,
        summaries=summaries,
        total_runs=total_runs,
        last_ingestion=None,
    )


@router.get("/{asset}/ohlcv", response_model=OhlcvResponse)
def get_ohlcv(
    asset: str = Depends(get_asset_or_404),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    downsample: str | None = Query(None),
) -> OhlcvResponse:
    """OHLCV data in columnar format. ?downsample=view applies LTTB to ≤3,000 bars."""
    ohlcv = _load_ohlcv(asset)

    if from_date:
        ohlcv = ohlcv[ohlcv.index >= pd.Timestamp(from_date, tz="UTC")]
    if to_date:
        ohlcv = ohlcv[ohlcv.index <= pd.Timestamp(to_date, tz="UTC")]

    bars_original = len(ohlcv)
    did_downsample = False

    if downsample == "view" and bars_original > 3_000:
        ohlcv = lttb_ohlcv(ohlcv, threshold=3_000)
        did_downsample = True

    cols = [c for c in ["open", "high", "low", "close", "volume"] if c in ohlcv.columns]
    data = df_to_columnar(ohlcv[cols])

    from_str = ohlcv.index[0].date().isoformat() if len(ohlcv) else ""
    to_str = ohlcv.index[-1].date().isoformat() if len(ohlcv) else ""

    return OhlcvResponse(
        asset=asset,
        from_date=from_str,
        to_date=to_str,
        bars=len(ohlcv),
        bars_original=bars_original,
        downsampled=did_downsample,
        data=data,
    )


@router.get("/{asset}/summary", response_model=AssetSummaryResponse)
def get_asset_summary(
    asset: str = Depends(get_asset_or_404),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
) -> AssetSummaryResponse:
    """Headline metrics for one asset: last price, returns, vol, bar count."""
    ohlcv = _load_ohlcv(asset)

    if from_date:
        ohlcv = ohlcv[ohlcv.index >= pd.Timestamp(from_date, tz="UTC")]
    if to_date:
        ohlcv = ohlcv[ohlcv.index <= pd.Timestamp(to_date, tz="UTC")]

    return _compute_summary(asset, ohlcv)
