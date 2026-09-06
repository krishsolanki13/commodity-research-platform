"""Live curve-coverage dates for curve-dependent strategies (Carry).

Computes the earliest date an asset's futures curve has >= 2 points,
cached in memory until invalidate_curve_coverage_cache() is called
(e.g. after a contract-data acquisition run).
"""

from __future__ import annotations

import datetime
import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)

_coverage_cache: dict[tuple[str, int], datetime.date | None] = {}


def invalidate_curve_coverage_cache(asset: str | None = None) -> None:
    """Drop cached coverage dates. Pass asset to invalidate one name."""
    if asset is None:
        _coverage_cache.clear()
        return
    for key in [k for k in _coverage_cache if k[0] == asset]:
        del _coverage_cache[key]


def get_curve_coverage_start(asset: str, n_contracts: int = 4) -> datetime.date | None:
    """Return cached earliest usable curve date, computing it on first miss."""
    key = (asset, n_contracts)
    if key not in _coverage_cache:
        _coverage_cache[key] = compute_curve_coverage_start(asset, n_contracts)
    return _coverage_cache[key]


def compute_curve_coverage_start(
    asset: str, n_contracts: int = 4
) -> datetime.date | None:
    """Find the earliest date this asset's curve has >= 2 valid points.

    Binary-searches trading days in the continuous OHLCV index. Result
    moves earlier automatically as accumulated contract history grows.
    """
    from src.commodity.curve import FuturesCurveBuilder  # noqa: PLC0415
    from src.core.config import Config  # noqa: PLC0415
    from src.data.loader import DataLoader  # noqa: PLC0415

    config = Config.load()
    ohlcv = DataLoader(config).load(asset)
    if ohlcv.empty:
        return None

    dates = [ts.date() for ts in ohlcv.index]
    builder = FuturesCurveBuilder(config)

    def _usable(obs: datetime.date) -> bool:
        try:
            curve = builder.build(asset, observation_date=obs, n_contracts=n_contracts)
            return curve.n_points >= 2
        except Exception:  # noqa: BLE001
            return False

    lo, hi = 0, len(dates) - 1
    found: datetime.date | None = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if _usable(dates[mid]):
            found = dates[mid]
            hi = mid - 1
        else:
            lo = mid + 1

    logger.info(
        "curve coverage start for %s (n_contracts=%d): %s",
        asset,
        n_contracts,
        found,
    )
    return found


def raise_if_insufficient_curve_coverage(
    strategy: str,
    asset: str,
    from_date: str | None,
    n_contracts: int = 4,
) -> None:
    """Raise 400 INSUFFICIENT_CURVE_COVERAGE for Carry windows that start too early.

    No-op for non-Carry strategies. Missing from_date is left to the caller
    (full-history requests); only an explicit from_date before coverage errors.
    """
    if strategy != "carry":
        return

    coverage_start = get_curve_coverage_start(asset, n_contracts)
    if coverage_start is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INSUFFICIENT_CURVE_COVERAGE",
                "message": f"No usable curve data found for {asset} at any date.",
                "curve_coverage_start": None,
            },
        )

    if not from_date:
        return

    parsed = datetime.date.fromisoformat(from_date)
    if parsed < coverage_start:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INSUFFICIENT_CURVE_COVERAGE",
                "message": (
                    f"Requested window starts {from_date}, but curve "
                    f"data for {asset} is only available from "
                    f"{coverage_start} onward."
                ),
                "curve_coverage_start": str(coverage_start),
            },
        )
