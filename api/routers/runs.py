from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Query

from api import state
from api.exceptions import ApiError
from api.models import (
    AlignedRunSeries,
    CompareRequest,
    CompareResponse,
    CompareRunSummary,
    DeleteResponse,
    ProvenanceInfo,
    RunDetailResponse,
    RunListItem,
    RunListResponse,
    SeriesResponse,
    TradeRecord,
    TradesPageResponse,
    TradeStats,
    series_to_columnar,
)

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _runs_dir() -> Path:
    from src.core.config import Config  # noqa: PLC0415

    cfg = Config.load()
    return Path(cfg.paths["runs"])


def _load_params(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "params.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def _load_metrics(run_dir: Path) -> dict[str, float | None]:
    p = run_dir / "metrics.json"
    if not p.exists():
        return {}
    raw = json.loads(p.read_text())
    metrics: dict[str, float | None] = {}
    for section in ("scalar_metrics", "signal_metrics"):
        for k, v in raw.get(section, {}).items():
            metrics[k] = float(v) if v is not None else None
    trade_stats = raw.get("trade_statistics", {})
    if "n_trades" in trade_stats:
        metrics["n_trades"] = float(trade_stats["n_trades"])
    return metrics


def _param_date(params: dict[str, Any], start: bool) -> str:
    if start:
        return params.get("data_start") or params.get("from_date", "")
    return params.get("data_end") or params.get("to_date", "")


def _trade_direction(val: object) -> str:
    if val in ("long", "short"):
        return val  # type: ignore[return-value]
    if val in (1, 1.0, "1"):
        return "long"
    if val in (-1, -1.0, "-1"):
        return "short"
    return "long"


def _load_parquet_series(run_dir: Path, name: str) -> pd.Series:
    """Load a single-column parquet artifact as a Series."""
    parquet_map = {
        "equity_curve": "equity_curve.parquet",
        "pnl": "pnl_series.parquet",
        "positions": "positions.parquet",
    }
    fname = parquet_map.get(name)
    if fname is None:
        raise ApiError(
            code="INVALID_SERIES_NAME",
            message=(
                f"Series '{name}' is not valid. Use: equity_curve, pnl, positions."
            ),
            status=400,
        )
    path = run_dir / fname
    if not path.exists():
        raise ApiError(
            code="SERIES_NOT_FOUND",
            message=f"Series '{name}' not found for this run.",
            status=404,
        )
    df = pd.read_parquet(path)
    col = df.columns[0]
    return df[col]


def _list_all_runs() -> list[dict[str, Any]]:
    """Scan data/runs/ and return list of run metadata dicts."""
    rd = _runs_dir()
    if not rd.exists():
        return []
    runs = []
    for params_file in sorted(rd.glob("*/params.json"), reverse=True):
        run_id = params_file.parent.name
        params = _load_params(params_file.parent)
        metrics = _load_metrics(params_file.parent)
        task = state.get(run_id)
        status = task["status"] if task else "complete"
        runs.append(
            {
                "run_id": run_id,
                "params": params,
                "metrics": metrics,
                "status": status,
            }
        )
    return runs


def _build_provenance(params: dict[str, Any]) -> ProvenanceInfo:
    """Extract provenance from params.json BacktestMetadata fields."""
    git_sha = params.get("git_sha") or params.get("git_commit_hash", "unknown")
    return ProvenanceInfo(
        git_sha=str(git_sha)[:8],
        dirty_flag=bool(params.get("dirty_flag", False)),
        package_versions=params.get("package_versions", {}),
    )


@router.get("", response_model=RunListResponse)
def list_runs(
    strategy: str | None = Query(None),
    asset: str | None = Query(None),
    sort: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> RunListResponse:
    """List all completed backtest runs with headline metrics."""
    del sort  # reserved for future sort options
    all_runs = _list_all_runs()

    items: list[RunListItem] = []
    for r in all_runs:
        p = r["params"]
        m = r["metrics"]
        run_asset = p.get("asset", "")
        run_strategy = p.get("strategy_name") or p.get("strategy", "")

        if asset and run_asset != asset:
            continue
        if strategy and run_strategy != strategy:
            continue
        if q and q.lower() not in r["run_id"].lower():
            continue

        ic = m.get("ic")
        items.append(
            RunListItem(
                run_id=r["run_id"],
                asset=run_asset,
                strategy=run_strategy,
                status=r["status"],
                from_date=_param_date(p, start=True),
                to_date=_param_date(p, start=False),
                sharpe=m.get("sharpe"),
                max_drawdown=m.get("max_drawdown"),
                total_return=m.get("total_return"),
                cagr=m.get("cagr"),
                win_rate=m.get("win_rate"),
                n_trades=int(m["n_trades"]) if m.get("n_trades") is not None else None,
                ic=ic,
                ic_band=m.get("ic_band"),
                executed_at=p.get("executed_at", r["run_id"]),
            )
        )

    total = len(items)
    start = (page - 1) * page_size
    page_items = items[start : start + page_size]

    return RunListResponse(
        runs=page_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run_detail(run_id: str) -> RunDetailResponse:
    """Full run detail: params, metrics, provenance."""
    artifact_id = state.get_artifact_id(run_id) or run_id
    run_dir = _runs_dir() / artifact_id
    if not run_dir.exists():
        raise ApiError(
            code="RUN_NOT_FOUND",
            message=f"Run '{run_id}' not found.",
            status=404,
        )
    params = _load_params(run_dir)
    metrics = _load_metrics(run_dir)
    provenance = _build_provenance(params)

    return RunDetailResponse(
        run_id=artifact_id,
        asset=params.get("asset", ""),
        strategy=params.get("strategy_name") or params.get("strategy", ""),
        status="complete",
        from_date=_param_date(params, start=True),
        to_date=_param_date(params, start=False),
        params=params,
        metrics=metrics,
        provenance=provenance,
        signal_evaluation=None,
    )


@router.get("/{run_id}/series/{name}", response_model=SeriesResponse)
def get_run_series(run_id: str, name: str) -> SeriesResponse:
    """Return one time series artifact (equity_curve, pnl, positions)."""
    artifact_id = state.get_artifact_id(run_id) or run_id
    run_dir = _runs_dir() / artifact_id
    if not run_dir.exists():
        raise ApiError(
            code="RUN_NOT_FOUND",
            message=f"Run '{run_id}' not found.",
            status=404,
        )
    series = _load_parquet_series(run_dir, name)
    return SeriesResponse(
        run_id=artifact_id,
        name=name,  # type: ignore[arg-type]
        data=series_to_columnar(series, col_name="value"),
    )


@router.get("/{run_id}/trades", response_model=TradesPageResponse)
def get_run_trades(
    run_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    direction: str | None = Query(None),
    force_closed: bool | None = Query(None),
) -> TradesPageResponse:
    """Paginated trade log for a run."""
    artifact_id = state.get_artifact_id(run_id) or run_id
    run_dir = _runs_dir() / artifact_id
    if not run_dir.exists():
        raise ApiError(
            code="RUN_NOT_FOUND",
            message=f"Run '{run_id}' not found.",
            status=404,
        )

    trades_path = run_dir / "trades.parquet"
    if not trades_path.exists():
        return TradesPageResponse(
            run_id=artifact_id,
            trades=[],
            page=page,
            page_size=page_size,
            total=0,
            stats=TradeStats(
                n_trades=0,
                avg_duration_bars=None,
                avg_win=None,
                avg_loss=None,
                largest_win=None,
                largest_loss=None,
            ),
        )

    df = pd.read_parquet(trades_path)

    if direction is not None and "direction" in df.columns:
        df = df[df["direction"] == direction]
    if force_closed is not None and "force_closed" in df.columns:
        df = df[df["force_closed"] == force_closed]

    total = len(df)
    start = (page - 1) * page_size
    page_df = df.iloc[start : start + page_size]

    trades: list[TradeRecord] = []
    for _, row in page_df.iterrows():
        trades.append(
            TradeRecord(
                direction=_trade_direction(row.get("direction", "long")),
                entry_date=str(row.get("entry_date", "")),
                exit_date=str(row.get("exit_date", "")),
                entry_price=float(row.get("entry_price", 0)),
                exit_price=float(row.get("exit_price", 0)),
                duration_bars=int(row.get("duration_bars", 0)),
                gross_pnl=float(row.get("gross_pnl", 0)),
                cost=float(row.get("transaction_cost", row.get("cost", 0))),
                net_pnl=float(row.get("net_pnl", 0)),
                return_pct=float(row.get("return_pct", 0)),
                force_closed=bool(row.get("force_closed", False)),
            )
        )

    metrics = _load_metrics(run_dir)
    stats = TradeStats(
        n_trades=total,
        avg_duration_bars=metrics.get("avg_trade_duration_bars"),
        avg_win=metrics.get("avg_win"),
        avg_loss=metrics.get("avg_loss"),
        largest_win=metrics.get("largest_win"),
        largest_loss=metrics.get("largest_loss"),
    )

    return TradesPageResponse(
        run_id=artifact_id,
        trades=trades,
        page=page,
        page_size=page_size,
        total=total,
        stats=stats,
    )


@router.post("/compare", response_model=CompareResponse)
def compare_runs(request: CompareRequest) -> CompareResponse:
    """Compare multiple runs: aligned equity curves + metric matrix."""
    rd = _runs_dir()
    summaries: list[CompareRunSummary] = []
    series_list: list[AlignedRunSeries] = []
    equity_series: dict[str, pd.Series] = {}

    for run_id in request.ids:
        artifact_id = state.get_artifact_id(run_id) or run_id
        run_dir = rd / artifact_id
        if not run_dir.exists():
            raise ApiError(
                code="RUN_NOT_FOUND",
                message=f"Run '{run_id}' not found.",
                status=404,
            )
        params = _load_params(run_dir)
        metrics = _load_metrics(run_dir)
        summaries.append(
            CompareRunSummary(
                run_id=artifact_id,
                asset=params.get("asset", ""),
                strategy=params.get("strategy_name") or params.get("strategy", ""),
                params=params,
                metrics=metrics,
                from_date=_param_date(params, start=True),
                to_date=_param_date(params, start=False),
            )
        )

        ec_path = run_dir / "equity_curve.parquet"
        if ec_path.exists():
            ec_df = pd.read_parquet(ec_path)
            equity_series[artifact_id] = ec_df.iloc[:, 0]

    if len(equity_series) >= 2:
        common_idx = equity_series[list(equity_series.keys())[0]].index
        for s in equity_series.values():
            common_idx = common_idx.intersection(s.index)
        intersection_from = (
            common_idx[0].date().isoformat() if len(common_idx) else None
        )
        intersection_to = common_idx[-1].date().isoformat() if len(common_idx) else None
        intersection_bars = len(common_idx) if len(common_idx) else None

        for rid, s in equity_series.items():
            aligned = s.loc[common_idx]
            start_val = aligned.iloc[0] if len(aligned) else 1.0
            normalized = (aligned / start_val - 1.0) * 100.0
            series_list.append(
                AlignedRunSeries(
                    run_id=rid,
                    equity_normalized=series_to_columnar(normalized, "value"),
                    rolling_sharpe_63=series_to_columnar(
                        pd.Series(0.0, index=common_idx), "value"
                    ),
                )
            )
    else:
        intersection_from = None
        intersection_to = None
        intersection_bars = None

    assets = [s.asset for s in summaries]
    mixed_assets = len(set(assets)) > 1

    return CompareResponse(
        runs=summaries,
        aligned_series=series_list,
        intersection_from=intersection_from,
        intersection_to=intersection_to,
        intersection_bars=intersection_bars,
        mixed_assets=mixed_assets,
    )


@router.delete("/{run_id}", response_model=DeleteResponse)
def delete_run(run_id: str) -> DeleteResponse:
    """Delete a run's artifacts from disk."""
    from src.backtesting.run_manager import RunManager  # noqa: PLC0415
    from src.core.config import Config  # noqa: PLC0415

    artifact_id = state.get_artifact_id(run_id) or run_id
    cfg = Config.load()
    rm = RunManager(cfg)

    try:
        rm.delete_run(artifact_id)
    except Exception as e:
        raise ApiError(
            code="DELETE_FAILED",
            message=f"Could not delete run '{artifact_id}': {e}",
            status=500,
        ) from e

    return DeleteResponse(deleted=True, run_id=artifact_id)
