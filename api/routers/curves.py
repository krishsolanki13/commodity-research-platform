"""
Commodity intelligence routes — Phase 2 backend (M08-M13).

Exposes FuturesCurveBuilder and TermStructureAnalyzer via HTTP.
These backend modules are complete and tested (186 backend tests).
This file wires them into the FastAPI shell for the first time.

Endpoints:
  GET /api/curves/available              → assets with contract Parquet data
  GET /api/curves/{asset}/snapshot       → latest forward curve + analytics
  GET /api/curves/{asset}/history        → monthly term-structure history

NaN fields: TermStructureSnapshot floats are math.nan when < 2 contracts
available. @field_serializer on Pydantic models converts to JSON null.

ADR-001: basis uses continuous close as pseudo-spot proxy. DataLoader
provides continuous close; it never enters the TermStructureAnalyzer
alongside contract data. Dashboard is the only orchestration point.

Note: FuturesCurveBuilder takes config: Config (creates ContractDataLoader
internally). It does not accept contract_loader= — that keyword was incorrect
relative to the Phase 2 API and is intentionally not used here.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_data_loader
from api.models import (
    CurveAvailableResponse,
    CurveHistoryResponse,
    CurvePointResponse,
    FuturesCurveResponse,
    TermStructureSnapshotSummary,
)

if TYPE_CHECKING:
    from src.data.loader import DataLoader

router = APIRouter(prefix="/api/curves", tags=["commodity-intelligence"])


@router.get("/available", response_model=CurveAvailableResponse)
async def get_available_assets() -> CurveAvailableResponse:
    """Return list of assets with processed Parquet contract data.

    Calls FuturesCurveBuilder.available_assets() which checks
    data/processed/contracts/{asset}/ for Parquet files.
    """
    from src.commodity.curve import FuturesCurveBuilder  # noqa: PLC0415
    from src.core.config import Config  # noqa: PLC0415

    builder = FuturesCurveBuilder(Config.load())
    try:
        assets = builder.available_assets()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list available assets: {exc}",
        ) from exc
    return CurveAvailableResponse(assets=assets)


@router.get("/{asset}/snapshot", response_model=FuturesCurveResponse)
async def get_curve_snapshot(
    asset: str,
    n_contracts: int = Query(default=6, ge=1, le=12),
    data_loader: DataLoader = Depends(get_data_loader),  # noqa: B008
) -> FuturesCurveResponse:
    """Construct the forward curve for {asset} as of the latest available date.

    observation_date: date.today(); builder finds nearest available data.
    continuous_close: from DataLoader for basis (ADR-001 pseudo-basis).
    If continuous data is unavailable, basis fields are NaN → null.
    """
    from src.commodity.curve import FuturesCurveBuilder  # noqa: PLC0415
    from src.commodity.term_structure import TermStructureAnalyzer  # noqa: PLC0415
    from src.core.config import Config  # noqa: PLC0415

    builder = FuturesCurveBuilder(Config.load())
    analyzer = TermStructureAnalyzer()

    available = builder.available_assets()
    if asset not in available:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Asset '{asset}' has no processed contract data. "
                f"Available: {available}"
            ),
        )

    try:
        curve = builder.build(
            asset=asset,
            observation_date=date.today(),
            n_contracts=n_contracts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Curve build failed: {exc}"
        ) from exc

    # Continuous close for basis — ADR-001 pseudo-basis
    continuous_close: float = float("nan")
    try:
        ohlcv = data_loader.load(asset)
        continuous_close = float(ohlcv["close"].dropna().iloc[-1])
    except Exception:
        pass  # basis fields will be NaN → serialized as null

    try:
        snapshot = analyzer.analyze(
            curve=curve,
            continuous_close=continuous_close,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    points = [
        CurvePointResponse(
            ticker=cp.metadata.ticker,
            close=cp.close,
            days_to_delivery=cp.days_to_delivery,
            data_date=str(cp.data_date),
        )
        for cp in curve.points
    ]

    return FuturesCurveResponse(
        asset=asset,
        observation_date=str(snapshot.observation_date),
        regime=str(snapshot.regime),  # TermStructureRegime is str,Enum
        front_price=snapshot.front_price,
        back_price=snapshot.back_price,
        n_contracts=snapshot.n_contracts,
        annualized_slope_pct=snapshot.annualized_slope_pct,
        roll_yield_annualized=snapshot.roll_yield_annualized,
        basis=snapshot.basis,
        basis_pct=snapshot.basis_pct,
        points=points,
    )


@router.get("/{asset}/history", response_model=CurveHistoryResponse)
async def get_curve_history(
    asset: str,
    from_date: str = Query(..., description="ISO date, e.g. 2023-01-01"),
    to_date: str = Query(..., description="ISO date, e.g. 2026-07-16"),
    n_contracts: int = Query(default=6, ge=1, le=12),
    data_loader: DataLoader = Depends(get_data_loader),  # noqa: B008
) -> CurveHistoryResponse:
    """Return monthly TermStructureSnapshots for {asset} over a date range.

    Sampling: first business day of each month between from_date and to_date.
    For a 5-year window: ~60 snapshots. For 1 year: ~12 snapshots.
    curve.points is omitted from history (too large); use /snapshot for that.
    """
    from src.commodity.curve import FuturesCurveBuilder  # noqa: PLC0415
    from src.commodity.term_structure import TermStructureAnalyzer  # noqa: PLC0415
    from src.core.config import Config  # noqa: PLC0415

    try:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid date format: {exc}"
        ) from exc

    if start >= end:
        raise HTTPException(
            status_code=422,
            detail="from_date must be strictly before to_date",
        )

    builder = FuturesCurveBuilder(Config.load())
    available = builder.available_assets()
    if asset not in available:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Asset '{asset}' has no processed contract data. "
                f"Available: {available}"
            ),
        )

    # Monthly sample dates — first business day of each month
    sample_dates: list[date] = []
    current = start.replace(day=1)
    while current <= end:
        bdate_range = pd.bdate_range(
            start=current,
            end=current + timedelta(days=10),
            freq="B",
        )
        if len(bdate_range) > 0:
            bd_date = bdate_range[0].date()
            if start <= bd_date <= end:
                sample_dates.append(bd_date)
        current = (
            current.replace(year=current.year + 1, month=1)
            if current.month == 12
            else current.replace(month=current.month + 1)
        )

    if not sample_dates:
        return CurveHistoryResponse(
            asset=asset,
            from_date=from_date,
            to_date=to_date,
            n_snapshots=0,
            snapshots=[],
        )

    try:
        curves = builder.build_historical_curves(
            asset=asset,
            dates=sample_dates,
            n_contracts=n_contracts,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Historical curve build failed: {exc}",
        ) from exc

    # Continuous OHLCV for per-date basis (aligned to sorted curves)
    ohlcv_close: pd.Series = pd.Series(dtype=float)
    try:
        ohlcv = data_loader.load(asset)
        ohlcv_close = ohlcv["close"].dropna()
    except Exception:
        pass

    continuous_closes: list[float] = []
    for curve in curves:
        obs_date = curve.observation_date
        try:
            mask = ohlcv_close.index.date <= obs_date  # type: ignore[attr-defined]
            continuous_closes.append(
                float(ohlcv_close[mask].iloc[-1]) if mask.any() else float("nan")
            )
        except Exception:
            continuous_closes.append(float("nan"))

    analyzer = TermStructureAnalyzer()
    try:
        snapshots = analyzer.analyze_series(
            curves=curves,
            continuous_closes=continuous_closes,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Series analysis failed: {exc}",
        ) from exc

    summaries = [
        TermStructureSnapshotSummary(
            observation_date=str(snap.observation_date),
            regime=str(snap.regime),
            annualized_slope_pct=snap.annualized_slope_pct,
            roll_yield_annualized=snap.roll_yield_annualized,
            basis=snap.basis,
            front_price=snap.front_price,
            n_contracts=snap.n_contracts,
        )
        for snap in snapshots
    ]

    return CurveHistoryResponse(
        asset=asset,
        from_date=from_date,
        to_date=to_date,
        n_snapshots=len(summaries),
        snapshots=summaries,
    )
