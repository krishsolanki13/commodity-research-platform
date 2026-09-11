"""Validation routes — statistical validation for strategy/asset combinations.

Endpoints:
  POST /api/validation/run             — async launch, returns validation_run_id
  GET  /api/validation/{id}/status     — queued | running | complete | failed
  GET  /api/validation/{id}/report     — ValidationReportResponse (when complete)
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.models import (
    TrainTestSplitResponse,
    ValidationLaunchRequest,
    ValidationReportResponse,
    ValidationStatusResponse,
    WalkForwardFoldResponse,
)
from src.core.provenance import as_json_fields

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/validation", tags=["validation"])

# ── State management ──────────────────────────────────────────────────────────
# Matches the register/update/get helper pattern from the portfolio router.
# Keys: status (queued|running|complete|failed), error (str|None), report (obj|None).

_validation_tasks: dict[str, dict] = {}


def _register(run_id: str) -> None:
    """Register a new validation run with initial queued status."""
    _validation_tasks[run_id] = {"status": "queued", "error": None, "report": None}


def _update(run_id: str, status: str, **kwargs: object) -> None:
    """Update task status and optional fields (error=, report=)."""
    if run_id in _validation_tasks:
        _validation_tasks[run_id]["status"] = status
        _validation_tasks[run_id].update(kwargs)


def _get(run_id: str) -> dict | None:
    """Return task state dict or None if not in memory."""
    return _validation_tasks.get(run_id)


# ── Validation artifacts directory ────────────────────────────────────────────
# Separate from data/runs/ — validation is not a backtest run.

_VALIDATION_DIR = Path("data/validation")


# ── Utilities ─────────────────────────────────────────────────────────────────


def _safe(v: object) -> object:
    """NaN → None for JSON serialization."""
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


# ── Background task ───────────────────────────────────────────────────────────


def _run_validation_task(
    validation_run_id: str,
    request: ValidationLaunchRequest,
) -> None:
    """Background task: run walk-forward validation and persist results to disk."""
    from src.core.config import Config  # noqa: PLC0415
    from src.validation.mlflow_client import get_trial_count  # noqa: PLC0415
    from src.validation.walk_forward import WalkForwardValidator  # noqa: PLC0415

    _update(validation_run_id, "running")
    try:
        config = Config.load("config/")
        n_trials = get_trial_count(request.asset, request.strategy_name)

        validator = WalkForwardValidator(config)
        report = validator.validate(
            asset=request.asset,
            strategy_name=request.strategy_name,
            parameters=request.parameters,
            n_splits=request.n_splits,
            embargo_bars=request.embargo_bars,
            n_trials=n_trials,
        )

        # Persist to disk before updating in-memory state (disk is authoritative)
        run_dir = _VALIDATION_DIR / validation_run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        _save_validation_report(report, run_dir)

        _update(validation_run_id, "complete", report=report)
        logger.info(
            "Validation complete: %s | DSR=%.4f | n_trials=%d",
            validation_run_id,
            report.dsr,
            report.n_trials,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Validation failed: %s — %s", validation_run_id, exc)
        _update(validation_run_id, "failed", error=str(exc))


# ── Persistence helpers ───────────────────────────────────────────────────────


def _save_validation_report(report: object, run_dir: Path) -> None:
    """Persist ValidationReport dataclass to disk as validation_report.json."""
    from src.core.types import ValidationReport, WalkForwardFold  # noqa: PLC0415

    assert isinstance(report, ValidationReport)

    folds_data = []
    for fold in report.folds:
        assert isinstance(fold, WalkForwardFold)
        folds_data.append(
            {
                "fold_idx": fold.split.fold_idx,
                "train_start": str(fold.split.train_start),
                "train_end": str(fold.split.train_end),
                "test_start": str(fold.split.test_start),
                "test_end": str(fold.split.test_end),
                "n_train_bars": fold.split.n_train_bars,
                "n_test_bars": fold.split.n_test_bars,
                "embargo_bars": fold.split.embargo_bars,
                "train_sharpe": _safe(fold.train_sharpe),
                "test_sharpe": _safe(fold.test_sharpe),
                "train_return": _safe(fold.train_return),
                "test_return": _safe(fold.test_return),
                "train_max_dd": _safe(fold.train_max_dd),
                "test_max_dd": _safe(fold.test_max_dd),
                "train_n_trades": fold.train_n_trades,
                "test_n_trades": fold.test_n_trades,
                "overfitting_ratio": _safe(fold.overfitting_ratio),
            }
        )

    data = {
        "validation_run_id": report.validation_run_id,
        "asset": report.asset,
        "strategy_name": report.strategy_name,
        "parameters": report.parameters,
        "n_splits": report.n_splits,
        "embargo_bars": report.embargo_bars,
        "computation_date": str(report.computation_date),
        "folds": folds_data,
        "insample_sharpe": _safe(report.insample_sharpe),
        "outsample_sharpe": _safe(report.outsample_sharpe),
        "insample_return": _safe(report.insample_return),
        "outsample_return": _safe(report.outsample_return),
        "overfitting_ratio": _safe(report.overfitting_ratio),
        "sharpe_se": _safe(report.sharpe_se),
        "psr": _safe(report.psr),
        "n_trials": report.n_trials,
        "sr_benchmark": _safe(report.sr_benchmark),
        "dsr": _safe(report.dsr),
        "is_significant": report.is_significant,
        "dsr_threshold": report.dsr_threshold,
        **as_json_fields(report),
    }
    (run_dir / "validation_report.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def _report_to_response(data: dict) -> ValidationReportResponse:
    """Convert a persisted dict (from disk or JSON round-trip) to response model."""
    folds = []
    for f in data.get("folds", []):
        split = TrainTestSplitResponse(
            fold_idx=f["fold_idx"],
            train_start=f["train_start"],
            train_end=f["train_end"],
            test_start=f["test_start"],
            test_end=f["test_end"],
            n_train_bars=f["n_train_bars"],
            n_test_bars=f["n_test_bars"],
            embargo_bars=f["embargo_bars"],
        )
        folds.append(
            WalkForwardFoldResponse(
                split=split,
                train_sharpe=f.get("train_sharpe"),
                test_sharpe=f.get("test_sharpe"),
                train_return=f.get("train_return"),
                test_return=f.get("test_return"),
                train_max_dd=f.get("train_max_dd"),
                test_max_dd=f.get("test_max_dd"),
                train_n_trades=f.get("train_n_trades", 0),
                test_n_trades=f.get("test_n_trades", 0),
                overfitting_ratio=f.get("overfitting_ratio"),
            )
        )

    return ValidationReportResponse(
        validation_run_id=data["validation_run_id"],
        asset=data["asset"],
        strategy_name=data["strategy_name"],
        parameters=data.get("parameters", {}),
        n_splits=data.get("n_splits", 0),
        embargo_bars=data.get("embargo_bars", 0),
        computation_date=data.get("computation_date", ""),
        folds=folds,
        insample_sharpe=data.get("insample_sharpe"),
        outsample_sharpe=data.get("outsample_sharpe"),
        insample_return=data.get("insample_return"),
        outsample_return=data.get("outsample_return"),
        overfitting_ratio=data.get("overfitting_ratio"),
        sharpe_se=data.get("sharpe_se"),
        psr=data.get("psr"),
        n_trials=data.get("n_trials", 1),
        sr_benchmark=data.get("sr_benchmark"),
        dsr=data.get("dsr"),
        is_significant=data.get("is_significant", False),
        dsr_threshold=data.get("dsr_threshold", 0.95),
        git_sha=data.get("git_sha", "unknown"),
        dirty_flag=bool(data.get("dirty_flag", False)),
        package_versions=data.get("package_versions") or {},
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/run", response_model=ValidationStatusResponse, status_code=202)
async def launch_validation(
    request: ValidationLaunchRequest,
    background_tasks: BackgroundTasks,
) -> ValidationStatusResponse:
    """Launch a walk-forward validation run asynchronously.

    Returns immediately with validation_run_id and status='queued'.
    Poll GET /api/validation/{id}/status to detect completion.
    Retrieve results with GET /api/validation/{id}/report once complete.
    """
    import datetime  # noqa: PLC0415

    now = datetime.datetime.now(datetime.UTC)
    validation_run_id = (
        f"{now.strftime('%Y%m%d_%H%M%S')}_validation_"
        f"{request.asset}_{request.strategy_name}"
    )

    _register(validation_run_id)
    background_tasks.add_task(
        _run_validation_task,
        validation_run_id=validation_run_id,
        request=request,
    )

    logger.info("Validation queued: %s", validation_run_id)
    return ValidationStatusResponse(
        validation_run_id=validation_run_id,
        status="queued",
    )


@router.get("/{validation_run_id}/status", response_model=ValidationStatusResponse)
async def get_validation_status(validation_run_id: str) -> ValidationStatusResponse:
    """Poll validation run status.

    Returns queued / running / complete / failed.
    Falls back to disk when run_id is not in memory (e.g. after server restart).
    """
    task = _get(validation_run_id)
    if task is not None:
        return ValidationStatusResponse(
            validation_run_id=validation_run_id,
            status=task["status"],
            error=task.get("error"),
        )

    # Disk fallback: completed runs survive server restarts
    report_path = _VALIDATION_DIR / validation_run_id / "validation_report.json"
    if report_path.exists():
        return ValidationStatusResponse(
            validation_run_id=validation_run_id,
            status="complete",
        )

    raise HTTPException(
        status_code=404,
        detail={
            "code": "VALIDATION_NOT_FOUND",
            "message": f"Validation run '{validation_run_id}' not found.",
        },
    )


@router.get("/{validation_run_id}/report", response_model=ValidationReportResponse)
async def get_validation_report(validation_run_id: str) -> ValidationReportResponse:
    """Return the full validation report.

    Returns 409 if the run exists but is not yet complete.
    Returns 404 if the run_id is not found in memory or on disk.
    Disk artifact is the authoritative source — always read from JSON on disk.
    """
    task = _get(validation_run_id)
    if task is not None:
        if task["status"] != "complete":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "VALIDATION_NOT_COMPLETE",
                    "message": (
                        f"Validation status is '{task['status']}', not complete."
                    ),
                },
            )
        # In-memory fast path: read from disk artifact (authoritative source)
        report_path = _VALIDATION_DIR / validation_run_id / "validation_report.json"
        if report_path.exists():
            data = json.loads(report_path.read_text(encoding="utf-8"))
            return _report_to_response(data)

    # Disk fallback
    report_path = _VALIDATION_DIR / validation_run_id / "validation_report.json"
    if report_path.exists():
        data = json.loads(report_path.read_text(encoding="utf-8"))
        return _report_to_response(data)

    raise HTTPException(
        status_code=404,
        detail={
            "code": "VALIDATION_NOT_FOUND",
            "message": f"Validation run '{validation_run_id}' not found.",
        },
    )
