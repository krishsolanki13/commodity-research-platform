"""Async regime attribution endpoints.

Pattern: POST /compute → poll /status → GET /result
Mirrors validation.py and sweeps.py async job pattern exactly.

The existing synchronous GET /api/runs/{run_id}/regime-attribution is
kept for backward compatibility. This router adds the async variant.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.models import (
    RegimeAttributionJobRequest,
    RegimeAttributionJobStatusResponse,
    RegimeAttributionResponse,
    RegimeMetricsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/regime-attribution", tags=["regime-attribution"])

_regime_tasks: dict[str, dict] = {}
_REGIME_DIR = Path("data/regime_attribution")


def _safe(v: object) -> object:
    """NaN → None for JSON serialization."""
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


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
            "sharpe": _safe(m.sharpe),
            "total_return": _safe(m.total_return),
            "max_drawdown": _safe(m.max_drawdown),
            "n_trades": m.n_trades,
            "win_rate": _safe(m.win_rate),
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
    }
    (job_dir / "result.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


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

        class _RunProxy:
            def __init__(self, d: dict, run_id: str, asset: str) -> None:
                self.run_id = run_id
                self.asset = asset
                self.pnl_series = d.get("pnl_series")
                self.equity_curve = d.get("equity_curve")
                self.trades = d.get("trades", [])
                params = d.get("params", {})
                # DEV-EM8-6: strategy_name key with fallback
                self.strategy_name = params.get(
                    "strategy_name", params.get("strategy", "unknown")
                )

        proxy = _RunProxy(run_data, request.run_id, request.asset)

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
