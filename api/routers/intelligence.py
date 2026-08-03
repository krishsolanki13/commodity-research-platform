"""Intelligence routes — commodity analytics beyond basic backtesting.

Extends the existing /api/intelligence/curves surface with:
  GET /api/intelligence/pca  — forward curve PCA (Level/Slope/Curvature)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from api.models import CurvePCAResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.get("/pca", response_model=CurvePCAResponse)
async def get_curve_pca(
    asset: str = Query(..., description="Asset identifier, e.g. 'gold'"),
    n_components: int = Query(default=3, ge=1, le=6, description="Number of PCs"),
    n_contracts: int = Query(default=4, ge=2, le=12, description="Contracts in curve"),
    from_date: str | None = Query(default=None, description="Start date YYYY-MM-DD"),
    to_date: str | None = Query(default=None, description="End date YYYY-MM-DD"),
) -> CurvePCAResponse:
    """Forward curve PCA for a commodity asset.

    Computes principal components of the forward curve shape over time.
    Results are computed on-demand — not cached.

    The three standard PCs for commodity curves:
      PC1 (Level):     parallel shift of the entire curve
      PC2 (Slope):     steepening or flattening
      PC3 (Curvature): bowing of the middle relative to ends

    Query parameters:
      asset:        Asset identifier (e.g. 'gold'). Must have contract data.
      n_components: Number of PCs to compute (default 3).
      n_contracts:  Number of forward contracts to include (default 4).
      from_date:    Optional start date filter (ISO 8601: YYYY-MM-DD).
      to_date:      Optional end date filter (ISO 8601: YYYY-MM-DD).
    """
    import datetime as _dt  # noqa: PLC0415

    from src.commodity.pca import CurvePCAEngine  # noqa: PLC0415
    from src.core.config import Config  # noqa: PLC0415

    # Parse optional date filters
    parsed_from: _dt.date | None = None
    parsed_to: _dt.date | None = None
    if from_date:
        try:
            parsed_from = _dt.date.fromisoformat(from_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid from_date format: '{from_date}'. Use YYYY-MM-DD.",
            ) from exc
    if to_date:
        try:
            parsed_to = _dt.date.fromisoformat(to_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid to_date format: '{to_date}'. Use YYYY-MM-DD.",
            ) from exc

    # DEV-EM10-1: Config.load() — no arguments
    config = Config.load()
    engine = CurvePCAEngine(config)

    try:
        result = engine.compute(
            asset=asset,
            n_components=n_components,
            n_contracts=n_contracts,
            from_date=parsed_from,
            to_date=parsed_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Curve PCA failed for '%s': %s", asset, exc)
        raise HTTPException(
            status_code=500,
            detail=f"PCA computation failed: {exc}",
        ) from exc

    return CurvePCAResponse(
        asset=result.asset,
        n_components=result.n_components,
        n_contracts=result.n_contracts,
        n_observation_dates=result.n_observation_dates,
        computation_date=str(result.computation_date),
        explained_variance_ratio=result.explained_variance_ratio,
        cumulative_variance_ratio=result.cumulative_variance_ratio,
        loadings=result.loadings,
        factor_series=result.factor_series,
        factor_index_epoch_ms=result.factor_index_epoch_ms,
        pc_labels=result.pc_labels,
    )
