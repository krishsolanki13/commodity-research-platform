from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import APIRouter, Query

from api.dependencies import KNOWN_ASSETS
from api.models import (
    AssetDataStatus,
    ConfigResponse,
    DataFlag,
    DataStatusResponse,
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
