"""Sweep routes — parameter sweep infrastructure for strategy research.

Endpoints:
  POST /api/sweeps                    — launch sweep (async)
  GET  /api/sweeps/{sweep_id}/status  — queued|running|complete|failed
  GET  /api/sweeps/{sweep_id}/results — full results, sortable by Sharpe
  GET  /api/sweeps                    — list recent sweeps from disk
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from api.models import (
    SweepLaunchRequest,
    SweepListItem,
    SweepListResponse,
    SweepResultResponse,
    SweepRunSummaryResponse,
    SweepStatusResponse,
)
from src.core.provenance import as_json_fields

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sweeps", tags=["sweeps"])

# Module-level task state — same pattern as validation router
_sweep_tasks: dict[str, dict] = {}

# Sweep artifacts directory
_SWEEPS_DIR = Path("data/sweeps")


def _safe(v: object) -> object:
    """NaN → None for JSON serialization."""
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _save_sweep_result(sweep_id: str, result: object) -> None:
    """Persist SweepResult to data/sweeps/{sweep_id}/sweep_result.json."""
    from src.core.types import SweepResult, SweepRunSummary  # noqa: PLC0415

    assert isinstance(result, SweepResult)

    run_dir = _SWEEPS_DIR / sweep_id
    run_dir.mkdir(parents=True, exist_ok=True)

    runs_data = []
    for run in result.runs:
        assert isinstance(run, SweepRunSummary)
        runs_data.append(
            {
                "sweep_id": run.sweep_id,
                "run_id": run.run_id,
                "parameters": run.parameters,
                "sharpe": _safe(run.sharpe),
                "total_return": _safe(run.total_return),
                "max_drawdown": _safe(run.max_drawdown),
                "n_trades": run.n_trades,
                "status": run.status,
                "error": run.error,
            }
        )

    data = {
        "sweep_id": result.sweep_id,
        "asset": result.asset,
        "strategy_name": result.strategy_name,
        "param_grid": result.param_grid,
        "n_combinations": result.n_combinations,
        "n_complete": result.n_complete,
        "n_failed": result.n_failed,
        "computation_date": str(result.computation_date),
        "runs": runs_data,
        **as_json_fields(result),
    }
    (run_dir / "sweep_result.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def _run_sweep_task(
    sweep_id: str,
    request: SweepLaunchRequest,
) -> None:
    """Background task: run the full sweep and persist results."""
    from src.backtesting.sweep_runner import SweepRunner  # noqa: PLC0415
    from src.core.config import Config  # noqa: PLC0415

    _sweep_tasks[sweep_id]["status"] = "running"
    try:
        config = Config.load("config/")
        runner = SweepRunner(config)

        def on_progress(n_complete: int) -> None:
            _sweep_tasks[sweep_id]["n_complete"] = n_complete

        result = runner.run_sweep(
            asset=request.asset,
            strategy_name=request.strategy_name,
            param_grid=request.param_grid,
            sweep_id=sweep_id,
            progress_callback=on_progress,
        )
        _save_sweep_result(sweep_id, result)
        _sweep_tasks[sweep_id].update(
            {
                "status": "complete",
                "result": result,
                "n_complete": result.n_complete,
                "n_failed": result.n_failed,
            }
        )
        logger.info(
            "Sweep complete: %s — %d/%d succeeded",
            sweep_id,
            result.n_complete,
            result.n_combinations,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Sweep failed: %s — %s", sweep_id, exc)
        _sweep_tasks[sweep_id].update(
            {
                "status": "failed",
                "error": str(exc),
            }
        )


def _load_sweep_from_disk(sweep_id: str) -> dict | None:
    """Load a sweep result from disk. Returns None if not found."""
    path = _SWEEPS_DIR / sweep_id / "sweep_result.json"
    if not path.exists():
        return None
    try:
        data: dict = json.loads(path.read_text(encoding="utf-8"))
        return data
    except Exception:  # noqa: BLE001
        return None


def _result_to_response(
    data: dict,
    sort_by: str = "sharpe",
    sort_dir: str = "desc",
) -> SweepResultResponse:
    """Convert sweep result dict to SweepResultResponse with sorting."""
    runs = [
        SweepRunSummaryResponse(
            sweep_id=r.get("sweep_id", data["sweep_id"]),
            run_id=r.get("run_id", ""),
            parameters=r.get("parameters", {}),
            sharpe=r.get("sharpe"),
            total_return=r.get("total_return"),
            max_drawdown=r.get("max_drawdown"),
            n_trades=r.get("n_trades", 0),
            status=r.get("status", "complete"),
            error=r.get("error"),
        )
        for r in data.get("runs", [])
    ]

    # Sort: failed runs always last; within each group sort by metric
    def _sort_key(run: SweepRunSummaryResponse) -> tuple:
        is_failed = run.status != "complete"
        if sort_by == "sharpe":
            val = run.sharpe if run.sharpe is not None else float("-inf")
        elif sort_by == "total_return":
            val = run.total_return if run.total_return is not None else float("-inf")
        elif sort_by == "max_drawdown":
            val = run.max_drawdown if run.max_drawdown is not None else float("-inf")
        else:
            val = run.sharpe if run.sharpe is not None else float("-inf")
        return (is_failed, val)

    runs.sort(key=_sort_key, reverse=(sort_dir == "desc"))

    return SweepResultResponse(
        sweep_id=data["sweep_id"],
        asset=data["asset"],
        strategy_name=data["strategy_name"],
        param_grid=data.get("param_grid", {}),
        n_combinations=data.get("n_combinations", 0),
        n_complete=data.get("n_complete", 0),
        n_failed=data.get("n_failed", 0),
        computation_date=data.get("computation_date", ""),
        runs=runs,
        git_sha=data.get("git_sha", "unknown"),
        dirty_flag=bool(data.get("dirty_flag", False)),
        package_versions=data.get("package_versions") or {},
    )


# CRITICAL — list route declared BEFORE parameterised routes
@router.get("", response_model=SweepListResponse)
async def list_sweeps(
    limit: int = Query(default=20, ge=1, le=100),
) -> SweepListResponse:
    """List recent sweep runs from disk, newest first.

    Scans data/sweeps/ for directories containing sweep_result.json.
    Returns summary items only (not full run details).
    """
    if not _SWEEPS_DIR.exists():
        return SweepListResponse(sweeps=[], total=0)

    items: list[SweepListItem] = []
    try:
        candidates = sorted(
            (d for d in _SWEEPS_DIR.iterdir() if d.is_dir()),
            key=lambda d: d.name,
            reverse=True,
        )
    except PermissionError:
        return SweepListResponse(sweeps=[], total=0)

    for sweep_dir in candidates:
        if len(items) >= limit:
            break
        data = _load_sweep_from_disk(sweep_dir.name)
        if data is None:
            continue
        items.append(
            SweepListItem(
                sweep_id=data.get("sweep_id", sweep_dir.name),
                asset=data.get("asset", ""),
                strategy_name=data.get("strategy_name", ""),
                n_combinations=data.get("n_combinations", 0),
                n_complete=data.get("n_complete", 0),
                n_failed=data.get("n_failed", 0),
                computation_date=data.get("computation_date", ""),
            )
        )

    return SweepListResponse(sweeps=items, total=len(items))


@router.post("", response_model=SweepStatusResponse, status_code=202)
async def launch_sweep(
    request: SweepLaunchRequest,
    background_tasks: BackgroundTasks,
) -> SweepStatusResponse:
    """Launch a parameter sweep asynchronously.

    Generates all combinations from param_grid (itertools.product order),
    runs each as an independent backtest, tags each in MLflow with sweep_id.

    Returns immediately with sweep_id and total combination count.
    Poll GET /api/sweeps/{sweep_id}/status for completion.
    """
    import datetime as _dt  # noqa: PLC0415
    import itertools  # noqa: PLC0415

    param_values = list(request.param_grid.values())
    n_combinations = len(list(itertools.product(*param_values))) if param_values else 1

    if n_combinations == 0:
        raise HTTPException(
            status_code=422,
            detail="param_grid produces 0 combinations — check that all lists are non-empty.",
        )

    now = _dt.datetime.now(_dt.UTC)
    sweep_id = (
        f"{now.strftime('%Y%m%d_%H%M%S')}_sweep_{request.strategy_name}_{request.asset}"
    )

    _sweep_tasks[sweep_id] = {
        "status": "queued",
        "n_combinations": n_combinations,
        "n_complete": 0,
        "n_failed": 0,
        "result": None,
        "error": None,
    }
    background_tasks.add_task(
        _run_sweep_task,
        sweep_id=sweep_id,
        request=request,
    )
    logger.info("Sweep queued: %s (%d combinations)", sweep_id, n_combinations)

    return SweepStatusResponse(
        sweep_id=sweep_id,
        status="queued",
        n_combinations=n_combinations,
    )


@router.get("/{sweep_id}/status", response_model=SweepStatusResponse)
async def get_sweep_status(sweep_id: str) -> SweepStatusResponse:
    """Poll sweep status."""
    task = _sweep_tasks.get(sweep_id)
    if task is not None:
        return SweepStatusResponse(
            sweep_id=sweep_id,
            status=task["status"],
            n_combinations=task.get("n_combinations", 0),
            n_complete=task.get("n_complete", 0),
            n_failed=task.get("n_failed", 0),
            error=task.get("error"),
        )

    data = _load_sweep_from_disk(sweep_id)
    if data:
        return SweepStatusResponse(
            sweep_id=sweep_id,
            status="complete",
            n_combinations=data.get("n_combinations", 0),
            n_complete=data.get("n_complete", 0),
            n_failed=data.get("n_failed", 0),
        )

    raise HTTPException(
        status_code=404,
        detail={"code": "SWEEP_NOT_FOUND", "message": f"Sweep '{sweep_id}' not found."},
    )


@router.get("/{sweep_id}/results", response_model=SweepResultResponse)
async def get_sweep_results(
    sweep_id: str,
    sort_by: str = Query(
        default="sharpe", pattern="^(sharpe|total_return|max_drawdown)$"
    ),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> SweepResultResponse:
    """Return complete sweep results when status is complete.

    Results are sorted by the specified metric (default: Sharpe, descending).
    Failed runs always appear last regardless of sort order.

    Query parameters:
        sort_by:  sharpe (default) | total_return | max_drawdown
        sort_dir: desc (default) | asc
    """
    task = _sweep_tasks.get(sweep_id)
    if task is not None and task["status"] != "complete":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SWEEP_NOT_COMPLETE",
                "message": f"Sweep status is '{task['status']}', not complete.",
            },
        )

    data = _load_sweep_from_disk(sweep_id)
    if data:
        return _result_to_response(data, sort_by=sort_by, sort_dir=sort_dir)

    raise HTTPException(
        status_code=404,
        detail={"code": "SWEEP_NOT_FOUND", "message": f"Sweep '{sweep_id}' not found."},
    )
