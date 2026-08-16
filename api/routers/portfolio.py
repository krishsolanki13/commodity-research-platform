from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from api import state
from api.exceptions import ApiError
from api.models import (
    CorrelationReportResponse,
    DeleteResponse,
    PortfolioAssetHeadline,
    PortfolioAssetsResponse,
    PortfolioEquityResponse,
    PortfolioLaunchRequest,
    PortfolioRunListItem,
    PortfolioRunListResponse,
    PortfolioSummaryResponse,
    RiskReportResponse,
    RollingCorrSeries,
    TaskLaunchResponse,
    TaskStatusResponse,
    series_to_columnar,
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

logger = logging.getLogger(__name__)

_DEFAULT_ASSETS = [
    "gold",
    "silver",
    "copper",
    "wti",
    "brent",
    "natural_gas",
]


# ── Rolling correlation symmetrization ────────────────────────────────────────


def _symmetrize_rolling(
    rolling: dict[str, dict[str, Any]],
) -> dict[str, dict[str, RollingCorrSeries]]:
    """Symmetrize upper-triangle rolling correlations (TD-M17-A resolution).

    The backend CorrelationReport stores only rolling[a][b] where a < b
    alphabetically. The API adds [b][a] for every pair so the client can
    treat the result as a fully symmetric matrix.
    """
    import pandas as pd  # noqa: PLC0415

    result: dict[str, dict[str, RollingCorrSeries]] = {}
    for a, b_dict in rolling.items():
        for b, series in b_dict.items():
            if not isinstance(series, pd.Series):
                continue
            corr_ab = RollingCorrSeries(
                asset_a=a,
                asset_b=b,
                data=series_to_columnar(series, col_name="value"),
            )
            corr_ba = RollingCorrSeries(
                asset_a=b,
                asset_b=b,
                data=series_to_columnar(series, col_name="value"),
            )
            result.setdefault(a, {})[b] = corr_ab
            result.setdefault(b, {})[a] = corr_ba
    return result


# ── Portfolio artifact helpers ─────────────────────────────────────────────────


def _portfolio_runs_dir() -> Path:
    from src.core.config import Config  # noqa: PLC0415

    cfg = Config.load()
    return Path(cfg.paths["runs"])


RUNS_DIR = _portfolio_runs_dir()


def resolve_artifact_id(run_id: str) -> str:
    """Strip the poll_ prefix used by the frontend polling lifecycle.

    The frontend prefixes run IDs with 'poll_' during active polling.
    Portfolio run artifacts are always written to disk without this prefix.

    Example:
        resolve_artifact_id("poll_20260722_120000_portfolio_ema")
        → "20260722_120000_portfolio_ema"
        resolve_artifact_id("20260722_120000_portfolio_ema")
        → "20260722_120000_portfolio_ema"  (no-op for direct IDs)
    """
    return run_id.removeprefix("poll_")


def _load_portfolio_summary(run_dir: Path) -> dict[str, Any]:
    """Load portfolio_summary.json artifact."""
    p = run_dir / "portfolio_summary.json"
    if not p.exists():
        raise ApiError(
            code="PORTFOLIO_SUMMARY_NOT_FOUND",
            message="Portfolio summary not found. Run may still be in progress.",
            status=404,
        )
    return cast(dict[str, Any], json.loads(p.read_text(encoding="utf-8")))


def _artifact_dir(run_id: str) -> Path:
    """Resolve on-disk run directory for a poll_ or bare run_id."""
    artifact_run_id = state.get_artifact_id(run_id) or resolve_artifact_id(run_id)
    return RUNS_DIR / artifact_run_id


# ── Background task ────────────────────────────────────────────────────────────


def _run_portfolio_task(
    polling_run_id: str,
    request: PortfolioLaunchRequest,
) -> None:
    """Background task: multi-asset pipeline + portfolio analytics."""
    try:
        state.update(polling_run_id, "running")

        from src.analytics.correlation import CorrelationEngine  # noqa: PLC0415
        from src.backtesting.multi_asset import MultiAssetRunner  # noqa: PLC0415
        from src.backtesting.sizing import (  # noqa: PLC0415
            FixedNotionalSizer,
            VolatilityScaledSizer,
        )
        from src.core.config import Config  # noqa: PLC0415
        from src.core.registry import PositionSizer  # noqa: PLC0415
        from src.performance.portfolio import (  # noqa: PLC0415
            PortfolioPerformanceEngine,
            save_portfolio_summary,
        )
        from src.risk.risk_engine import RiskEngine  # noqa: PLC0415

        cfg = Config.load()
        assets = request.assets or _DEFAULT_ASSETS

        if request.sizing_method == "volatility_scaled":
            sizer: PositionSizer = VolatilityScaledSizer(target_annual_vol=0.15)
        else:
            sizer = FixedNotionalSizer(notional_usd=request.notional_usd)

        runner = MultiAssetRunner(cfg)
        multi_result = runner.run(
            assets=assets,
            strategy_name=request.strategy,
            parameters=request.params,
            sizer=sizer,
            signal_threshold=request.signal_threshold,
        )

        # Save individual per-asset run artifacts so /api/runs/{assetRunId}
        # is resolvable. Non-fatal — portfolio result is not affected if
        # an individual asset save fails.
        try:
            from src.backtesting.run_manager import RunManager  # noqa: PLC0415
            from src.performance.report import PerformanceEngine  # noqa: PLC0415

            _manager = RunManager(cfg)
            _perf_engine = PerformanceEngine()
            for _asset, _br in multi_result.asset_results.items():
                try:
                    _manager.save(_br)
                    _asset_report = _perf_engine.compute(_br)
                    _manager.save_metrics(_br.run_id, _asset_report)
                except Exception as _asset_exc:
                    logger.warning(
                        "Could not save per-asset run for %s: %s",
                        _asset,
                        _asset_exc,
                    )
        except Exception as _save_exc:
            logger.warning("Per-asset artifact save block failed: %s", _save_exc)

        port_engine = PortfolioPerformanceEngine()
        port_report = port_engine.compute(multi_result)

        run_id = multi_result.run_id
        run_dir = Path(cfg.paths["runs"]) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        state.update(polling_run_id, "persisting")
        save_portfolio_summary(port_report, run_dir)

        corr_report = CorrelationEngine().compute(multi_result)
        risk_report = RiskEngine().compute(
            multi_result,
            lookback_days=252,
            corr_report=corr_report,
        )

        # EM3: persist equity, risk, and correlation to disk for post-restart access
        try:
            from src.performance.portfolio import (  # noqa: PLC0415
                save_correlation_report,
                save_portfolio_equity,
                save_risk_report,
            )

            save_portfolio_equity(multi_result, run_dir)
            save_risk_report(risk_report, run_dir)
            save_correlation_report(corr_report, run_dir)
        except Exception as _e:  # noqa: BLE001
            logger.warning("EM3: failed to persist portfolio artifacts: %s", _e)

        state.set_artifact_id(polling_run_id, run_id)

        import api.state as _state_module  # noqa: PLC0415

        with _state_module._lock:
            _state_module._store[polling_run_id]["risk_report"] = risk_report
            _state_module._store[polling_run_id]["corr_report"] = corr_report
            _state_module._store[polling_run_id]["port_report"] = port_report
            _state_module._store[polling_run_id]["multi_result"] = multi_result
            # Alias under bare artifact id so clients that strip poll_ still
            # resolve in-memory reports (same dict — shared status/reports).
            _state_module._store[run_id] = _state_module._store[polling_run_id]

        import datetime as dt  # noqa: PLC0415

        executed_at = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
        state.update(polling_run_id, "complete", executed_at=executed_at)
        # Bare-id alias shares the same dict — status is already complete.

    except Exception as e:
        state.update(
            polling_run_id,
            "failed",
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()[:800]}",
        )


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post("/run", response_model=TaskLaunchResponse, status_code=202)
def launch_portfolio(
    request: PortfolioLaunchRequest,
    background_tasks: BackgroundTasks,
) -> TaskLaunchResponse:
    """Launch a portfolio backtest asynchronously."""
    import datetime as dt  # noqa: PLC0415

    ts = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    polling_run_id = f"poll_{ts}_portfolio_{request.strategy}"
    state.register(polling_run_id)
    background_tasks.add_task(_run_portfolio_task, polling_run_id, request)
    return TaskLaunchResponse(run_id=polling_run_id, status="queued")


@router.get("/runs", response_model=PortfolioRunListResponse)
async def list_portfolio_runs(
    limit: int = Query(default=20, ge=1, le=100),
) -> PortfolioRunListResponse:
    """List recent portfolio runs from disk.

    Scans RUNS_DIR for directories containing portfolio_summary.json.
    Returns runs sorted newest-first by directory name (which encodes
    execution timestamp: YYYYMMDD_HHMMSS_portfolio_{strategy}).

    Replaces the frontend portfolioHistory Zustand+localStorage store
    with a proper server-side run list.
    """
    import json as json_mod  # noqa: PLC0415

    if not RUNS_DIR.exists():
        return PortfolioRunListResponse(runs=[], total=0)

    items: list[PortfolioRunListItem] = []
    try:
        candidates = sorted(
            (d for d in RUNS_DIR.iterdir() if d.is_dir()),
            key=lambda d: d.name,
            reverse=True,  # newest first (YYYYMMDD_HHMMSS prefix)
        )
    except PermissionError:
        return PortfolioRunListResponse(runs=[], total=0)

    for run_dir in candidates:
        if len(items) >= limit:
            break
        summary_path = run_dir / "portfolio_summary.json"
        if not summary_path.exists():
            continue
        try:
            summary = json_mod.loads(summary_path.read_text(encoding="utf-8"))
            metrics = summary.get("portfolio_metrics", {})
            items.append(
                PortfolioRunListItem(
                    run_id=summary.get("run_id", run_dir.name),
                    strategy_name=summary.get("strategy_name", ""),
                    assets=summary.get("assets", []),
                    skipped_assets=summary.get("skipped_assets", []),
                    total_return=metrics.get("total_return"),
                    sharpe=metrics.get("sharpe"),
                    max_drawdown=metrics.get("max_drawdown"),
                    portfolio_vol=metrics.get("portfolio_vol"),
                    initial_capital_total=summary.get("initial_capital_total"),
                    portfolio_date_range=summary.get("portfolio_date_range", []),
                )
            )
        except Exception:  # noqa: BLE001
            continue  # skip malformed summary files

    return PortfolioRunListResponse(runs=items, total=len(items))


@router.get("/{run_id}/status", response_model=TaskStatusResponse)
def get_portfolio_status(run_id: str) -> TaskStatusResponse:
    """Poll portfolio run status."""
    task = state.get(run_id)
    if task is None:
        raise ApiError(
            code="RUN_NOT_FOUND",
            message=f"Portfolio run '{run_id}' not found.",
            status=404,
        )
    return TaskStatusResponse(
        run_id=run_id,
        status=task["status"],
        error=task.get("error"),
        executed_at=task.get("executed_at"),
    )


def _get_task_or_404(run_id: str) -> dict[str, Any]:
    """Load a completed in-memory portfolio task.

    Tries the request id, then the poll_-stripped artifact id, then reverse
    lookup via the polling→artifact map so both poll_* and bare ids work.
    """
    candidates = [run_id]
    bare = resolve_artifact_id(run_id)
    if bare not in candidates:
        candidates.append(bare)

    import api.state as _state_module  # noqa: PLC0415

    with _state_module._lock:
        for poll_id, art_id in _state_module._artifact_map.items():
            if art_id in (run_id, bare) and poll_id not in candidates:
                candidates.append(poll_id)

    for key in candidates:
        task = state.get(key)
        if task is not None and task["status"] == "complete":
            return task

    raise ApiError(
        code="RUN_NOT_FOUND",
        message=f"Portfolio run '{run_id}' not found or not yet complete.",
        status=404,
    )


def _summary_from_disk(run_id: str) -> PortfolioSummaryResponse | None:
    """Build PortfolioSummaryResponse from portfolio_summary.json if present."""
    run_dir = _artifact_dir(run_id)
    summary_path = run_dir / "portfolio_summary.json"
    if not summary_path.exists():
        return None

    summary = cast(dict[str, Any], json.loads(summary_path.read_text(encoding="utf-8")))
    metrics_raw = summary.get("portfolio_metrics") or {}
    metrics = {k: (float(v) if v is not None else None) for k, v in metrics_raw.items()}
    date_range = summary.get("portfolio_date_range") or ["", ""]
    per_asset = summary.get("per_asset_metrics") or {}
    abs_pnl = summary.get("absolute_pnl_by_asset") or {}
    headlines = [
        PortfolioAssetHeadline(
            asset=asset,
            sharpe=(m or {}).get("sharpe"),
            max_drawdown=(m or {}).get("max_drawdown"),
            total_return=(m or {}).get("total_return"),
            cagr=(m or {}).get("cagr"),
            n_trades=None,
            absolute_pnl=abs_pnl.get(asset),
        )
        for asset, m in per_asset.items()
    ]

    total_pnl = sum(float(v) for v in abs_pnl.values()) if abs_pnl else 0.0
    capital = float(summary.get("initial_capital_total") or 0.0)
    contributions = summary.get("asset_contributions")
    if capital > 0 and abs(total_pnl) / capital < 0.01:
        contributions = None

    n_days = metrics.get("n_trading_days")
    return PortfolioSummaryResponse(
        run_id=run_id,
        strategy=summary.get("strategy_name") or summary.get("strategy") or "",
        assets=list(summary.get("assets") or []),
        skipped_assets=list(summary.get("skipped_assets") or []),
        portfolio_date_range_from=str(date_range[0]) if date_range else "",
        portfolio_date_range_to=str(date_range[1]) if len(date_range) > 1 else "",
        portfolio_date_range_bars=int(n_days) if n_days is not None else 0,
        initial_capital_per_asset=float(
            summary.get("initial_capital_per_asset") or 0.0
        ),
        initial_capital_total=capital,
        portfolio_metrics=metrics,
        absolute_pnl_by_asset={k: float(v) for k, v in abs_pnl.items()},
        asset_contributions=(
            {k: float(v) for k, v in contributions.items()}
            if isinstance(contributions, dict)
            else None
        ),
        per_asset_headlines=headlines,
    )


@router.get("/{run_id}/summary", response_model=PortfolioSummaryResponse)
def get_portfolio_summary(run_id: str) -> PortfolioSummaryResponse:
    """Portfolio performance summary."""
    try:
        task = _get_task_or_404(run_id)
    except ApiError:
        disk = _summary_from_disk(run_id)
        if disk is not None:
            return disk
        raise

    port_report = task.get("port_report")
    if port_report is None:
        disk = _summary_from_disk(run_id)
        if disk is not None:
            return disk
        raise ApiError(
            code="REPORT_NOT_FOUND",
            message="Portfolio report not available.",
            status=404,
        )

    total_pnl = sum(port_report.absolute_pnl_by_asset.values())
    if abs(total_pnl) / port_report.initial_capital_total < 0.01:
        asset_contributions = None
    else:
        asset_contributions = getattr(port_report, "asset_contributions", None)

    headlines = []
    per_asset = getattr(port_report, "per_asset_reports", {})
    for asset, rep in per_asset.items():
        sm = rep.scalar_metrics if hasattr(rep, "scalar_metrics") else {}
        ts = rep.trade_statistics if hasattr(rep, "trade_statistics") else {}
        headlines.append(
            PortfolioAssetHeadline(
                asset=asset,
                sharpe=sm.get("sharpe"),
                max_drawdown=sm.get("max_drawdown"),
                total_return=sm.get("total_return"),
                cagr=sm.get("cagr"),
                n_trades=int(ts["n_trades"])
                if ts.get("n_trades") is not None
                else None,
                absolute_pnl=port_report.absolute_pnl_by_asset.get(asset),
            )
        )

    dr = port_report.portfolio_date_range
    return PortfolioSummaryResponse(
        run_id=run_id,
        strategy=port_report.strategy_name,
        assets=port_report.assets,
        skipped_assets=port_report.skipped_assets,
        portfolio_date_range_from=str(dr[0]) if dr else "",
        portfolio_date_range_to=str(dr[1]) if dr else "",
        portfolio_date_range_bars=int(
            port_report.portfolio_metrics.get("n_trading_days", 0)
        ),
        initial_capital_per_asset=port_report.initial_capital_per_asset,
        initial_capital_total=port_report.initial_capital_total,
        portfolio_metrics={
            k: (float(v) if v is not None else None)
            for k, v in port_report.portfolio_metrics.items()
        },
        absolute_pnl_by_asset=port_report.absolute_pnl_by_asset,
        asset_contributions=asset_contributions,
        per_asset_headlines=headlines,
    )


def _derive_diversification_benefit(
    asset_var_99: dict,
    portfolio_var_99: float | None,
) -> float | None:
    """Replicate RiskReport.portfolio_diversification_benefit from stored values.

    Defined as sum(asset_var_99.values()) / portfolio_var_99.
    Returns None when portfolio_var_99 is None, zero, or NaN.
    """
    if not portfolio_var_99:
        return None
    total = sum(asset_var_99.values())
    return total / portfolio_var_99


def _risk_from_disk(run_id: str) -> RiskReportResponse | None:
    """Build RiskReportResponse from portfolio_risk.json if present."""
    # EM3 disk fallback — serves after server restart
    artifact_run_id = resolve_artifact_id(run_id)
    risk_path = RUNS_DIR / artifact_run_id / "portfolio_risk.json"
    if not risk_path.exists():
        return None
    import json as _json  # noqa: PLC0415

    d = _json.loads(risk_path.read_text(encoding="utf-8"))
    return RiskReportResponse(
        run_id=run_id,
        portfolio_var_95=d.get("portfolio_var_95"),
        portfolio_var_99=d.get("portfolio_var_99"),
        portfolio_var_95_pct=d.get("portfolio_var_95_pct"),
        portfolio_var_99_pct=d.get("portfolio_var_99_pct"),
        portfolio_es_95=d.get("portfolio_es_95"),
        portfolio_es_99=d.get("portfolio_es_99"),
        asset_var_95=d.get("asset_var_95", {}),
        asset_var_99=d.get("asset_var_99", {}),
        avg_gross_notional_by_asset=d.get("avg_gross_notional_by_asset", {}),
        avg_net_notional_by_asset=d.get("avg_net_notional_by_asset", {}),
        total_avg_gross_notional=d.get("total_avg_gross_notional"),
        total_avg_net_notional=d.get("total_avg_net_notional"),
        portfolio_diversification_benefit=_derive_diversification_benefit(
            d.get("asset_var_99", {}), d.get("portfolio_var_99")
        ),
        lookback_days=d.get("lookback_days", 252),
        # EM4 — backward-compatible; pre-EM4 runs return 0/null/empty
        n_backtesting_days=d.get("n_backtesting_days", 0),
        exceptions_95=d.get("exceptions_95", 0),
        exceptions_99=d.get("exceptions_99", 0),
        exception_rate_95=d.get("exception_rate_95"),
        exception_rate_99=d.get("exception_rate_99"),
        kupiec_lr_99=d.get("kupiec_lr_99"),
        kupiec_pvalue_99=d.get("kupiec_pvalue_99"),
        asset_contribution_to_vol=d.get("asset_contribution_to_vol", {}),
        asset_contribution_to_vol_pct=d.get("asset_contribution_to_vol_pct", {}),
    )


def _correlation_from_disk(run_id: str) -> CorrelationReportResponse | None:
    """Build CorrelationReportResponse from disk artifacts if present."""
    # EM3 disk fallback — serves after server restart
    artifact_run_id = resolve_artifact_id(run_id)
    corr_path = RUNS_DIR / artifact_run_id / "portfolio_correlation.json"
    if not corr_path.exists():
        return None
    import json as _json  # noqa: PLC0415

    import pandas as _pd  # noqa: PLC0415

    d = _json.loads(corr_path.read_text(encoding="utf-8"))

    # Reconstruct upper-triangle rolling dicts from wide-format parquet
    raw_63: dict = {}
    raw_126: dict = {}
    for window, target in [(63, raw_63), (126, raw_126)]:
        rp = RUNS_DIR / artifact_run_id / f"portfolio_rolling_{window}.parquet"
        if rp.exists():
            df = _pd.read_parquet(rp, engine="pyarrow")
            for col in df.columns:
                parts = col.split("__", 1)
                if len(parts) == 2:
                    a, b = parts
                    target.setdefault(a, {})[b] = df[col]

    # Symmetrize matches in-memory handler exactly
    rolling_63 = _symmetrize_rolling(raw_63)
    rolling_126 = _symmetrize_rolling(raw_126)

    def _req_float(v: Any, default: float = 0.0) -> float:
        # Disk JSON may store NaN as null via _nan_safe(); response model requires float
        return float(v) if v is not None else default

    most = d.get("most_correlated_pair", ["", "", 0.0])
    least = d.get("least_correlated_pair", ["", "", 0.0])

    return CorrelationReportResponse(
        run_id=run_id,
        correlation_matrix=d.get("correlation_matrix", {}),
        rolling_correlations_63=rolling_63,
        rolling_correlations_126=rolling_126,
        realized_vol_by_asset=d.get("realized_vol_by_asset", {}),
        portfolio_realized_vol=_req_float(d.get("portfolio_realized_vol")),
        avg_pairwise_correlation=_req_float(d.get("avg_pairwise_correlation")),
        most_correlated_pair=(
            str(most[0]),
            str(most[1]),
            _req_float(most[2] if len(most) > 2 else None),
        ),
        least_correlated_pair=(
            str(least[0]),
            str(least[1]),
            _req_float(least[2] if len(least) > 2 else None),
        ),
    )


def _equity_from_disk(run_id: str) -> PortfolioEquityResponse | None:
    """Build PortfolioEquityResponse from equity/pnl parquets if present."""
    # EM3 disk fallback — serves after server restart
    artifact_run_id = resolve_artifact_id(run_id)
    equity_path = RUNS_DIR / artifact_run_id / "portfolio_equity.parquet"
    pnl_path = RUNS_DIR / artifact_run_id / "portfolio_pnl.parquet"
    if not (equity_path.exists() and pnl_path.exists()):
        return None
    import pandas as _pd  # noqa: PLC0415

    equity_series = _pd.read_parquet(equity_path, engine="pyarrow")["equity"]
    pnl_series = _pd.read_parquet(pnl_path, engine="pyarrow")["pnl"]
    return PortfolioEquityResponse(
        run_id=run_id,
        portfolio_equity=series_to_columnar(equity_series, col_name="value"),
        portfolio_pnl=series_to_columnar(pnl_series, col_name="value"),
    )


@router.get("/{run_id}/risk", response_model=RiskReportResponse)
def get_portfolio_risk(run_id: str) -> RiskReportResponse:
    """Portfolio risk analytics: VaR, ES, notional exposure."""
    try:
        task = _get_task_or_404(run_id)
    except ApiError:
        disk = _risk_from_disk(run_id)
        if disk is not None:
            return disk
        raise

    risk = task.get("risk_report")
    if risk is None:
        disk = _risk_from_disk(run_id)
        if disk is not None:
            return disk
        raise ApiError(
            code="REPORT_NOT_FOUND",
            message="Risk report not available.",
            status=404,
        )

    def _safe(v: Any) -> float | None:
        import math  # noqa: PLC0415

        if v is None:
            return None
        try:
            f = float(v)
            return None if math.isnan(f) else f
        except (TypeError, ValueError):
            return None

    return RiskReportResponse(
        run_id=run_id,
        portfolio_var_95=_safe(risk.portfolio_var_95),
        portfolio_var_99=_safe(risk.portfolio_var_99),
        portfolio_var_95_pct=_safe(risk.portfolio_var_95_pct),
        portfolio_var_99_pct=_safe(risk.portfolio_var_99_pct),
        portfolio_es_95=_safe(risk.portfolio_es_95),
        portfolio_es_99=_safe(risk.portfolio_es_99),
        asset_var_95={k: _safe(v) for k, v in risk.asset_var_95.items()},
        asset_var_99={k: _safe(v) for k, v in risk.asset_var_99.items()},
        avg_gross_notional_by_asset=risk.avg_gross_notional_by_asset,
        avg_net_notional_by_asset=risk.avg_net_notional_by_asset,
        total_avg_gross_notional=float(risk.total_avg_gross_notional),
        total_avg_net_notional=float(risk.total_avg_net_notional),
        portfolio_diversification_benefit=_safe(risk.portfolio_diversification_benefit),
        lookback_days=252,
        # EM4 — Kupiec VaR backtesting
        n_backtesting_days=risk.n_backtesting_days,
        exceptions_95=risk.exceptions_95,
        exceptions_99=risk.exceptions_99,
        exception_rate_95=_safe(risk.exception_rate_95),
        exception_rate_99=_safe(risk.exception_rate_99),
        kupiec_lr_99=_safe(risk.kupiec_lr_99),
        kupiec_pvalue_99=_safe(risk.kupiec_pvalue_99),
        # EM4 — Contribution to strategy volatility
        asset_contribution_to_vol=risk.asset_contribution_to_vol,
        asset_contribution_to_vol_pct=risk.asset_contribution_to_vol_pct,
    )


@router.get("/{run_id}/correlation", response_model=CorrelationReportResponse)
def get_portfolio_correlation(run_id: str) -> CorrelationReportResponse:
    """Cross-asset correlation report with symmetrized rolling correlations."""
    try:
        task = _get_task_or_404(run_id)
    except ApiError:
        disk = _correlation_from_disk(run_id)
        if disk is not None:
            return disk
        raise

    corr = task.get("corr_report")
    if corr is None:
        disk = _correlation_from_disk(run_id)
        if disk is not None:
            return disk
        raise ApiError(
            code="REPORT_NOT_FOUND",
            message="Correlation report not available.",
            status=404,
        )

    rolling_63 = _symmetrize_rolling(getattr(corr, "rolling_correlations_63", {}))
    rolling_126 = _symmetrize_rolling(getattr(corr, "rolling_correlations_126", {}))

    most = getattr(corr, "most_correlated_pair", ("", "", 0.0))
    least = getattr(corr, "least_correlated_pair", ("", "", 0.0))

    return CorrelationReportResponse(
        run_id=run_id,
        correlation_matrix=corr.correlation_matrix,
        rolling_correlations_63=rolling_63,
        rolling_correlations_126=rolling_126,
        realized_vol_by_asset=corr.realized_vol_by_asset,
        portfolio_realized_vol=float(corr.portfolio_realized_vol),
        avg_pairwise_correlation=float(corr.avg_pairwise_correlation),
        most_correlated_pair=(str(most[0]), str(most[1]), float(most[2])),
        least_correlated_pair=(str(least[0]), str(least[1]), float(least[2])),
    )


@router.get("/{run_id}/equity", response_model=PortfolioEquityResponse)
def get_portfolio_equity(run_id: str) -> PortfolioEquityResponse:
    """Portfolio equity curve and daily PnL series."""
    try:
        task = _get_task_or_404(run_id)
    except ApiError:
        disk = _equity_from_disk(run_id)
        if disk is not None:
            return disk
        raise

    multi = task.get("multi_result")
    if multi is None:
        disk = _equity_from_disk(run_id)
        if disk is not None:
            return disk
        raise ApiError(
            code="REPORT_NOT_FOUND",
            message="Portfolio equity not available.",
            status=404,
        )

    return PortfolioEquityResponse(
        run_id=run_id,
        portfolio_equity=series_to_columnar(
            multi.portfolio_equity_curve, col_name="value"
        ),
        portfolio_pnl=series_to_columnar(multi.portfolio_pnl_series, col_name="value"),
    )


@router.get("/{run_id}/assets", response_model=PortfolioAssetsResponse)
async def get_portfolio_assets(run_id: str) -> PortfolioAssetsResponse:
    """Return per-asset performance metrics for a completed portfolio run.

    Reads from portfolio_summary.json (written by save_portfolio_summary).
    The per_asset_metrics field is populated since the fix to
    save_portfolio_summary() — runs completed before this fix will return
    a 404 with a clear re-run message.
    """
    # Launch returns a poll_* id; artifacts are stored under the real run_id.
    artifact_run_id = state.get_artifact_id(run_id) or resolve_artifact_id(run_id)
    summary_path = RUNS_DIR / artifact_run_id / "portfolio_summary.json"
    if not summary_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "code": "RUN_NOT_FOUND",
                "message": f"Portfolio run '{run_id}' not found.",
            },
        )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    per_asset_metrics = summary.get("per_asset_metrics")

    if per_asset_metrics is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "RUN_NOT_FOUND",
                "message": (
                    f"Portfolio run '{run_id}' pre-dates per-asset metrics. "
                    "Re-run the portfolio analysis to populate this field."
                ),
            },
        )

    return PortfolioAssetsResponse(
        run_id=artifact_run_id,
        assets=summary["assets"],
        asset_metrics=per_asset_metrics,
        asset_run_ids=summary.get("asset_run_ids", {}),
    )


@router.delete("/{run_id}", response_model=DeleteResponse)
def delete_portfolio_run(run_id: str) -> DeleteResponse:
    """Remove portfolio run artifacts from state."""
    task = state.get(run_id)
    if task is None:
        raise ApiError(
            code="RUN_NOT_FOUND",
            message=f"Portfolio run '{run_id}' not found.",
            status=404,
        )
    artifact_id = state.get_artifact_id(run_id) or run_id
    import api.state as _state_module  # noqa: PLC0415

    with _state_module._lock:
        _state_module._store.pop(run_id, None)
        _state_module._artifact_map.pop(run_id, None)
    return DeleteResponse(deleted=True, run_id=artifact_id)
