"""Async regime attribution endpoints.

Pattern: POST /compute → poll /status → GET /result
Mirrors validation.py and sweeps.py async job pattern exactly.

The existing synchronous GET /api/runs/{run_id}/regime-attribution is
kept for backward compatibility. This router adds the async variant.
"""

from __future__ import annotations

import dataclasses as _dc
import datetime as _dt_dc
import json
import logging
import math as _math_dc
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.models import (
    PortfolioRegimeAttributionResponse,
    PortfolioRegimeJobRequest,
    RegimeAttributionJobRequest,
    RegimeAttributionJobStatusResponse,
    RegimeAttributionResponse,
    RegimeMetricsResponse,
)
from src.analytics.regime_attribution import (
    _make_run_proxy,
)
from src.core.provenance import as_json_fields

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/regime-attribution", tags=["regime-attribution"])

_regime_tasks: dict[str, dict] = {}
_REGIME_DIR = Path("data/regime_attribution")


def _make_json_safe(obj: object) -> object:
    """Recursively make an object JSON-safe.

    - float NaN → None
    - datetime.date → ISO string
    - dict, list → recurse
    - all other types → unchanged
    """
    if isinstance(obj, float) and _math_dc.isnan(obj):
        return None
    if isinstance(obj, _dt_dc.date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    return obj


def _regime_report_to_dict(report: object) -> dict:
    """Serialize RegimeAttributionReport to JSON-safe dict.

    Uses dataclasses.asdict() so any future field additions to
    RegimeAttributionReport are automatically included (TD-EM8-C-4).
    NaN values → None, datetime.date → ISO string for JSON safety.
    """
    from src.core.types import RegimeAttributionReport  # noqa: PLC0415

    assert isinstance(report, RegimeAttributionReport)
    raw = _dc.asdict(report)
    return _make_json_safe(raw)  # type: ignore[return-value]


def _mark_regime_attribution_complete(portfolio_run_id: str) -> None:
    """Set has_regime_attribution=True in portfolio_summary.json."""
    summary_path = Path("data/runs") / portfolio_run_id / "portfolio_summary.json"
    if not summary_path.exists():
        logger.warning(
            "Cannot update has_regime_attribution — summary not found: %s",
            summary_path,
        )
        return
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        data["has_regime_attribution"] = True
        summary_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(
            "has_regime_attribution=True written for portfolio run %s",
            portfolio_run_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not update has_regime_attribution flag: %s", exc)


def _save_regime_result(job_id: str, report: object) -> None:
    """Persist RegimeAttributionReport to disk."""
    # Import confirmed in Task 0
    from src.core.types import RegimeAttributionReport, RegimeMetrics  # noqa: PLC0415

    assert isinstance(report, RegimeAttributionReport)
    job_dir = _REGIME_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    regime_metrics_data = {}
    for regime_str, m in report.regime_metrics.items():
        assert isinstance(m, RegimeMetrics)
        regime_metrics_data[regime_str] = {
            "regime": m.regime,
            "n_days": m.n_days,
            "coverage": m.coverage,
            "sharpe": _make_json_safe(m.sharpe),
            "total_return": _make_json_safe(m.total_return),
            "max_drawdown": _make_json_safe(m.max_drawdown),
            "n_trades": m.n_trades,
            "win_rate": _make_json_safe(m.win_rate),
        }

    data = {
        "run_id": report.run_id,
        "asset": report.asset,
        "strategy_name": report.strategy_name,
        "n_contracts": report.n_contracts,
        "computation_date": str(report.computation_date),
        "regime_metrics": regime_metrics_data,
        "regime_coverage": report.regime_coverage,
        "dominant_regime": report.dominant_regime,
        "total_days_with_regime": report.total_days_with_regime,
        "total_days_in_run": report.total_days_in_run,
        **as_json_fields(report),
    }
    (job_dir / "result.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def _save_portfolio_regime_result(job_id: str, report: object) -> None:
    """Persist PortfolioRegimeAttributionReport to disk."""
    from src.core.types import PortfolioRegimeAttributionReport  # noqa: PLC0415

    assert isinstance(report, PortfolioRegimeAttributionReport)

    job_dir = _REGIME_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    portfolio_metrics_data = {
        regime: {
            "regime": m.regime,
            "n_days": m.n_days,
            "coverage": m.coverage,
            "sharpe": _make_json_safe(m.sharpe),
            "total_return": _make_json_safe(m.total_return),
            "max_drawdown": _make_json_safe(m.max_drawdown),
            "n_trades": m.n_trades,
            "win_rate": _make_json_safe(m.win_rate),
        }
        for regime, m in report.portfolio_regime_metrics.items()
    }

    data = {
        "result_type": "portfolio",
        "portfolio_run_id": report.portfolio_run_id,
        "n_assets_computed": report.n_assets_computed,
        "assets_computed": report.assets_computed,
        "computation_date": str(report.computation_date),
        "portfolio_regime_metrics": portfolio_metrics_data,
        "per_asset_metrics": {
            asset: _regime_report_to_dict(r)
            for asset, r in report.per_asset_metrics.items()
        },
        "dominant_regime": report.dominant_regime,
        "asset_weights": report.asset_weights,
        **as_json_fields(report),
    }
    (job_dir / "result.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    _mark_regime_attribution_complete(report.portfolio_run_id)


def _report_to_response(data: dict) -> RegimeAttributionResponse:
    """Convert disk dict to RegimeAttributionResponse."""
    regime_metrics = {
        k: RegimeMetricsResponse(
            regime=v["regime"],
            n_days=v.get("n_days", 0),
            coverage=v.get("coverage", 0.0),
            sharpe=v.get("sharpe"),
            total_return=v.get("total_return"),
            max_drawdown=v.get("max_drawdown"),
            n_trades=v.get("n_trades", 0),
            win_rate=v.get("win_rate"),
        )
        for k, v in data.get("regime_metrics", {}).items()
    }
    return RegimeAttributionResponse(
        run_id=data["run_id"],
        asset=data["asset"],
        strategy_name=data.get("strategy_name", ""),
        n_contracts=data.get("n_contracts", 4),
        computation_date=data.get("computation_date", ""),
        regime_metrics=regime_metrics,
        regime_coverage=data.get("regime_coverage", {}),
        dominant_regime=data.get("dominant_regime", ""),
        total_days_with_regime=data.get("total_days_with_regime", 0),
        total_days_in_run=data.get("total_days_in_run", 0),
        git_sha=data.get("git_sha", "unknown"),
        dirty_flag=bool(data.get("dirty_flag", False)),
        package_versions=data.get("package_versions") or {},
    )


def _run_regime_task(job_id: str, request: RegimeAttributionJobRequest) -> None:
    """Background task: compute regime attribution and persist result."""
    from src.analytics.regime_attribution import (
        RegimeAttributionEngine,  # noqa: PLC0415
    )
    from src.backtesting.run_manager import RunManager  # noqa: PLC0415
    from src.core.config import Config  # noqa: PLC0415

    _regime_tasks[job_id]["status"] = "running"
    try:
        config = Config.load()
        manager = RunManager(config)

        # DEV-EM8-1: load_run() → dict, no .load()
        run_data = manager.load_run(request.run_id)
        proxy = _make_run_proxy(run_data, request.run_id, request.asset)

        engine = RegimeAttributionEngine(config)
        report = engine.compute(
            backtest_result=proxy,
            asset=request.asset,
            n_contracts=request.n_contracts,
        )

        _save_regime_result(job_id, report)
        _regime_tasks[job_id].update(
            {
                "status": "complete",
                "report": report,
            }
        )
        logger.info(
            "Regime attribution complete: %s | dominant=%s",
            job_id,
            report.dominant_regime,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Regime attribution failed: %s — %s", job_id, exc)
        _regime_tasks[job_id].update(
            {
                "status": "failed",
                "error": str(exc),
            }
        )


def _run_portfolio_regime_task(job_id: str, request: PortfolioRegimeJobRequest) -> None:
    from src.analytics.regime_attribution import (
        RegimeAttributionEngine,  # noqa: PLC0415
    )
    from src.core.config import Config  # noqa: PLC0415

    _regime_tasks[job_id]["status"] = "running"
    try:
        config = Config.load()
        engine = RegimeAttributionEngine(config)
        report = engine.compute_portfolio(
            portfolio_run_id=request.portfolio_run_id,
            n_contracts=request.n_contracts,
        )
        _save_portfolio_regime_result(job_id, report)
        _regime_tasks[job_id].update({"status": "complete", "report": report})
        logger.info(
            "Portfolio regime complete: %s | dominant=%s",
            job_id,
            report.dominant_regime,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Portfolio regime failed: %s — %s", job_id, exc)
        _regime_tasks[job_id].update({"status": "failed", "error": str(exc)})


@router.post(
    "/compute", response_model=RegimeAttributionJobStatusResponse, status_code=202
)
async def compute_regime_attribution(
    request: RegimeAttributionJobRequest,
    background_tasks: BackgroundTasks,
) -> RegimeAttributionJobStatusResponse:
    """Launch async regime attribution computation."""
    import datetime as _dt  # noqa: PLC0415

    now = _dt.datetime.now(_dt.UTC)
    job_id = (
        f"{now.strftime('%Y%m%d_%H%M%S')}_regime_{request.asset}_{request.run_id[:12]}"
    )

    _regime_tasks[job_id] = {"status": "queued", "report": None, "error": None}
    background_tasks.add_task(
        _run_regime_task,
        job_id=job_id,
        request=request,
    )
    logger.info("Regime attribution queued: %s", job_id)
    return RegimeAttributionJobStatusResponse(job_id=job_id, status="queued")


@router.post(
    "/compute-portfolio",
    response_model=RegimeAttributionJobStatusResponse,
    status_code=202,
)
async def compute_portfolio_regime_attribution(
    request: PortfolioRegimeJobRequest,
    background_tasks: BackgroundTasks,
) -> RegimeAttributionJobStatusResponse:
    import datetime as _dt  # noqa: PLC0415

    now = _dt.datetime.now(_dt.UTC)
    job_id = (
        f"{now.strftime('%Y%m%d_%H%M%S')}_regime_portfolio_"
        f"{request.portfolio_run_id[:12]}"
    )
    _regime_tasks[job_id] = {"status": "queued", "report": None, "error": None}
    background_tasks.add_task(
        _run_portfolio_regime_task,
        job_id=job_id,
        request=request,
    )
    return RegimeAttributionJobStatusResponse(job_id=job_id, status="queued")


@router.get("/{job_id}/status", response_model=RegimeAttributionJobStatusResponse)
async def get_regime_attribution_status(
    job_id: str,
) -> RegimeAttributionJobStatusResponse:
    """Poll regime attribution job status."""
    task = _regime_tasks.get(job_id)
    if task is not None:
        return RegimeAttributionJobStatusResponse(
            job_id=job_id,
            status=task["status"],
            error=task.get("error"),
        )

    # Disk fallback (post-restart)
    result_path = _REGIME_DIR / job_id / "result.json"
    if result_path.exists():
        return RegimeAttributionJobStatusResponse(
            job_id=job_id,
            status="complete",
        )

    raise HTTPException(
        status_code=404,
        detail={
            "code": "JOB_NOT_FOUND",
            "message": f"Regime attribution job '{job_id}' not found.",
        },
    )


@router.get("/{job_id}/result", response_model=RegimeAttributionResponse)
async def get_regime_attribution_result(job_id: str) -> RegimeAttributionResponse:
    """Return regime attribution result when status is complete."""
    task = _regime_tasks.get(job_id)
    if task is not None and task["status"] != "complete":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "JOB_NOT_COMPLETE",
                "message": f"Job status is '{task['status']}', not complete.",
            },
        )

    # Disk path (in-memory or post-restart)
    result_path = _REGIME_DIR / job_id / "result.json"
    if result_path.exists():
        data = json.loads(result_path.read_text(encoding="utf-8"))
        return _report_to_response(data)

    raise HTTPException(
        status_code=404,
        detail={
            "code": "JOB_NOT_FOUND",
            "message": f"Regime attribution job '{job_id}' not found.",
        },
    )


@router.get(
    "/{job_id}/portfolio-result",
    response_model=PortfolioRegimeAttributionResponse,
)
async def get_portfolio_regime_result(
    job_id: str,
) -> PortfolioRegimeAttributionResponse:
    task = _regime_tasks.get(job_id)
    if task is not None and task["status"] != "complete":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "JOB_NOT_COMPLETE",
                "message": f"Job status is '{task['status']}', not complete.",
            },
        )

    result_path = _REGIME_DIR / job_id / "result.json"
    if result_path.exists():
        data = json.loads(result_path.read_text(encoding="utf-8"))
        regime_metrics = {
            k: RegimeMetricsResponse(**v)
            for k, v in data.get("portfolio_regime_metrics", {}).items()
        }
        return PortfolioRegimeAttributionResponse(
            portfolio_run_id=data["portfolio_run_id"],
            n_assets_computed=data.get("n_assets_computed", 0),
            assets_computed=data.get("assets_computed", []),
            computation_date=data.get("computation_date", ""),
            portfolio_regime_metrics=regime_metrics,
            dominant_regime=data.get("dominant_regime", ""),
            asset_weights=data.get("asset_weights", {}),
            git_sha=data.get("git_sha", "unknown"),
            dirty_flag=bool(data.get("dirty_flag", False)),
            package_versions=data.get("package_versions") or {},
        )

    raise HTTPException(
        status_code=404,
        detail={
            "code": "JOB_NOT_FOUND",
            "message": f"Portfolio regime job '{job_id}' not found.",
        },
    )
