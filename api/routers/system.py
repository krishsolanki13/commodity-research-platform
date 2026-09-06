from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import APIRouter, HTTPException, Query

from api.dependencies import KNOWN_ASSETS
from api.models import (
    AssetDataStatus,
    ConfigResponse,
    COTDataResponse,
    COTRecordResponse,
    DataFlag,
    DataStatusResponse,
    EIADataResponse,
    EIARecordResponse,
    IngestRequest,
    IngestResponse,
    QCReportResponse,
)

router = APIRouter(prefix="/api/system", tags=["system"])


def _sanitize(obj: Any) -> Any:
    """Recursively remove keys containing sensitive terms."""
    sensitive = {"password", "api_key", "secret", "token"}
    if isinstance(obj, dict):
        return {
            k: _sanitize(v)
            for k, v in obj.items()
            if not any(s in k.lower() for s in sensitive)
        }
    if isinstance(obj, list):
        return [_sanitize(i) for i in obj]
    return obj


@router.get("/data-status", response_model=DataStatusResponse)
def get_data_status(asset: str | None = Query(None)) -> DataStatusResponse:
    """Per-asset ingestion status: bar count, date range, health."""
    from src.core.config import Config
    from src.data.loader import DataLoader

    cfg = Config.load()
    loader = DataLoader(cfg)

    assets_to_check = [asset] if asset else sorted(KNOWN_ASSETS)
    statuses: list[AssetDataStatus] = []

    for name in assets_to_check:
        try:
            ohlcv = loader.load(name)
            bar_count = len(ohlcv)
            from_date = ohlcv.index[0].date().isoformat() if bar_count else None
            to_date = ohlcv.index[-1].date().isoformat() if bar_count else None
            health: Literal["ok", "warn", "crit", "missing"] = (
                "ok" if bar_count > 0 else "missing"
            )
            statuses.append(
                AssetDataStatus(
                    name=name,
                    bar_count=bar_count,
                    from_date=from_date,
                    to_date=to_date,
                    last_ingested=None,
                    flagged_anomalies=0,
                    data_health=health,
                    flags=[],
                )
            )
        except Exception as e:
            statuses.append(
                AssetDataStatus(
                    name=name,
                    bar_count=0,
                    from_date=None,
                    to_date=None,
                    last_ingested=None,
                    flagged_anomalies=0,
                    data_health="missing",
                    flags=[
                        DataFlag(
                            date="",
                            violation_type="load_error",
                            detail=str(e)[:200],
                        )
                    ],
                )
            )

    total_flags = sum(s.flagged_anomalies for s in statuses)
    return DataStatusResponse(assets=statuses, total_flags=total_flags)


@router.get("/curve-coverage/{asset}")
def get_curve_coverage(
    asset: str,
    n_contracts: int = Query(default=4, ge=2, le=12),
) -> dict:
    """Earliest date this asset's futures curve has genuine 2-point coverage.

    Used by Research Workbench and Strategy Builder date pickers to disable
    windows that predate usable contract data for Carry.
    Cached in-process; recomputed after contract-data acquisition (cache
    invalidation) or process restart.
    """
    from api.curve_coverage import get_curve_coverage_start  # noqa: PLC0415

    if asset not in KNOWN_ASSETS:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ASSET_NOT_FOUND",
                "message": f"Asset '{asset}' is not in the universe.",
            },
        )

    coverage_start = get_curve_coverage_start(asset, n_contracts)
    return {
        "asset": asset,
        "curve_coverage_start": str(coverage_start) if coverage_start else None,
        "n_contracts": n_contracts,
        "message": (
            f"Curve-dependent signals (Carry) are only evaluable from "
            f"{coverage_start} onward for {asset} — earlier dates lack "
            f"sufficient contract data to construct a term structure."
            if coverage_start
            else f"No usable curve data found for {asset} at any date."
        ),
    }


@router.get("/data/qc", response_model=QCReportResponse)
def get_data_qc(asset: str = Query(...)) -> QCReportResponse:
    """On-demand data quality assessment for one asset's OHLCV history.

    Loads the processed Parquet for the asset, runs QC checks, and
    returns a QCReport. Computation is fast (< 100ms for 4,150 bars).
    """
    import datetime as _dt  # noqa: PLC0415

    from src.core.config import Config  # noqa: PLC0415
    from src.data.acquisition_qc import compute_qc  # noqa: PLC0415
    from src.data.loader import DataLoader  # noqa: PLC0415

    def _crit_response(reason: str) -> QCReportResponse:
        return QCReportResponse(
            asset=asset,
            generated_at=_dt.datetime.now(_dt.UTC).isoformat(),
            bar_count=0,
            from_date="",
            to_date="",
            zero_volume_days=0,
            ohlc_violations=0,
            large_gap_flags=0,
            data_health="crit",
            anomalies=[reason],
        )

    if asset not in KNOWN_ASSETS:
        # Match existing file's unknown-asset pattern (no HTTPException).
        return _crit_response(
            f"Unknown asset '{asset}'. Known assets: {sorted(KNOWN_ASSETS)}"
        )

    try:
        config = Config.load()
        ohlcv = DataLoader(config).load(asset)
    except Exception as exc:  # noqa: BLE001
        return _crit_response(f"Failed to load data: {exc}")

    report = compute_qc(ohlcv, asset)
    return QCReportResponse(
        asset=report.asset,
        generated_at=report.generated_at,
        bar_count=report.bar_count,
        from_date=report.from_date,
        to_date=report.to_date,
        zero_volume_days=report.zero_volume_days,
        ohlc_violations=report.ohlc_violations,
        large_gap_flags=report.large_gap_flags,
        data_health=report.data_health,
        anomalies=report.anomalies,
    )


@router.get("/data/cot", response_model=COTDataResponse)
def get_cot_data(asset: str = Query(...)) -> COTDataResponse:
    """Return weekly COT positioning history for an asset."""
    import math as _math  # noqa: PLC0415

    from src.data.cot_loader import COTDataLoader  # noqa: PLC0415

    loader = COTDataLoader()
    df = loader.load(asset)

    if df.empty:
        return COTDataResponse(
            asset=asset,
            available=False,
            records=[],
            message=f"No COT data for '{asset}'. Run scripts/acquire_cot_data.py.",
        )

    records = []
    for dt, row in df.iterrows():
        net_spec = row.get("net_speculative", float("nan"))
        pct_rank = row.get("percentile_rank", float("nan"))
        records.append(
            COTRecordResponse(
                date=str(dt.date()),
                net_speculative=None
                if _math.isnan(float(net_spec))
                else float(net_spec),
                percentile_rank=None
                if _math.isnan(float(pct_rank))
                else float(pct_rank),
            )
        )

    return COTDataResponse(
        asset=asset,
        available=True,
        records=records,
        message=f"{len(records)} weekly COT records",
    )


@router.get("/data/eia", response_model=EIADataResponse)
def get_eia_data(asset: str = Query(...)) -> EIADataResponse:
    """Return weekly EIA inventory history for an asset (WTI and Brent only)."""
    import math as _math  # noqa: PLC0415

    from src.data.eia_loader import EIA_SUPPORTED_ASSETS, EIADataLoader  # noqa: PLC0415

    if asset not in EIA_SUPPORTED_ASSETS:
        return EIADataResponse(
            asset=asset,
            available=False,
            records=[],
            message=(
                f"EIA data only available for crude oil assets: "
                f"{sorted(EIA_SUPPORTED_ASSETS)}"
            ),
        )

    loader = EIADataLoader()
    df = loader.load(asset)

    if df.empty:
        return EIADataResponse(
            asset=asset,
            available=False,
            records=[],
            message=f"No EIA data for '{asset}'. Run scripts/acquire_eia_data.py.",
        )

    records = []
    for dt, row in df.iterrows():
        inv = row.get("inventory", float("nan"))
        surp = row.get("surprise", float("nan"))
        zsc = row.get("surprise_zscore", float("nan"))
        records.append(
            EIARecordResponse(
                date=str(dt.date()),
                inventory=None if _math.isnan(float(inv)) else float(inv),
                surprise=None if _math.isnan(float(surp)) else float(surp),
                surprise_zscore=None if _math.isnan(float(zsc)) else float(zsc),
            )
        )

    return EIADataResponse(
        asset=asset,
        available=True,
        records=records,
        message=f"{len(records)} weekly EIA records",
    )


@router.post("/ingest", response_model=IngestResponse, status_code=202)
def trigger_ingest(request: IngestRequest) -> IngestResponse:
    """Trigger DataLoader.load() to refresh processed Parquet from raw CSV."""
    from src.core.config import Config
    from src.data.loader import DataLoader

    cfg = Config.load()
    loader = DataLoader(cfg)

    targets = [request.asset] if request.asset else sorted(KNOWN_ASSETS)
    ingested: list[str] = []
    failed: list[str] = []

    for name in targets:
        try:
            loader.load(name)
            ingested.append(name)
        except Exception:
            failed.append(name)

    status: Literal["ok", "partial", "failed"]
    if not failed:
        status = "ok"
    elif not ingested:
        status = "failed"
    else:
        status = "partial"

    return IngestResponse(
        status=status,
        assets_ingested=ingested,
        assets_failed=failed,
    )


@router.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    """Sanitized read-only view of config.yaml, assets.yaml, strategies.yaml."""
    config_dir = Path("config")

    def _load(filename: str) -> dict:
        p = config_dir / filename
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
        return {}

    return ConfigResponse(
        config=_sanitize(_load("config.yaml")),
        assets=_sanitize(_load("assets.yaml")),
        strategies=_sanitize(_load("strategies.yaml")),
    )
