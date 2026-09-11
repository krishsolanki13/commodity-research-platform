"""PortfolioPerformanceEngine: portfolio-level performance analytics.

Computes portfolio-level metrics from MultiAssetBacktestResult and
assembles a PortfolioPerformanceReport.

Architecture: Layer 4 (Performance and Attribution) — Phase 3 addition.
The portfolio engine is the multi-asset counterpart to PerformanceEngine:
    PerformanceEngine.compute(BacktestResult) → PerformanceReport
    PortfolioPerformanceEngine.compute(MultiAssetBacktestResult) → PortfolioPerformanceReport

Does NOT compute:
    - Risk analytics (VaR, ES, notional exposure) — Module 16
    - Cross-asset correlation — Module 17
    - RunManager persistence — deferred to pre-M19 housekeeping

See Architecture Section 5 (Layer 4) and ADR-010.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from src.core.types import (
    BacktestResult,
    MultiAssetBacktestResult,
    PerformanceReport,
    PortfolioPerformanceReport,
)
from src.performance.report import PerformanceEngine

if TYPE_CHECKING:
    from src.core.types import CorrelationReport, RiskReport


class PortfolioPerformanceEngine:
    """Computes portfolio-level performance from MultiAssetBacktestResult.

    Runs PerformanceEngine.compute() on each per-asset BacktestResult,
    then derives portfolio-level scalars from the aggregated portfolio
    equity curve and PnL series produced by MultiAssetRunner.

    Usage:
        engine = PortfolioPerformanceEngine()
        report = engine.compute(multi_result)
        print(f"Portfolio Sharpe: {report.portfolio_sharpe:.4f}")
        print(f"Max Drawdown:     {report.portfolio_max_drawdown:.2%}")
        print(f"Per-asset contributions: {report.asset_contributions}")
    """

    def __init__(self) -> None:
        """Initialise PortfolioPerformanceEngine (stateless)."""
        self._engine = PerformanceEngine()
        self._logger = logging.getLogger(__name__)

    def compute(
        self,
        multi_result: MultiAssetBacktestResult,
    ) -> PortfolioPerformanceReport:
        """Compute portfolio-level performance analytics.

        Steps:
            1. Run PerformanceEngine on each per-asset BacktestResult
            2. Extract initial capital from per-asset reports
            3. Compute portfolio-level scalar metrics from portfolio equity
            4. Compute per-asset P&L contribution fractions
            5. Extract portfolio date range from equity curve index
            6. Assemble and return PortfolioPerformanceReport

        Args:
            multi_result: MultiAssetBacktestResult from MultiAssetRunner.run().

        Returns:
            PortfolioPerformanceReport with portfolio metrics, per-asset
            reports, and attribution fractions.

        Raises:
            ValueError: If multi_result.asset_results is empty (no successful
                assets to compute metrics from).
        """
        if not multi_result.asset_results:
            raise ValueError(
                "PortfolioPerformanceEngine.compute(): no asset results to analyse. "
                "MultiAssetBacktestResult.asset_results is empty."
            )

        # Step 1: Per-asset PerformanceReport
        per_asset_reports: dict[str, PerformanceReport] = {}
        for asset, bt_result in multi_result.asset_results.items():
            try:
                per_asset_reports[asset] = self._engine.compute(bt_result)
                self._logger.debug(
                    "PortfolioPerformanceEngine: %s — Sharpe=%.4f MaxDD=%.2f%%",
                    asset,
                    per_asset_reports[asset].scalar_metrics.get("sharpe", float("nan")),
                    per_asset_reports[asset].scalar_metrics.get(
                        "max_drawdown", float("nan")
                    )
                    * 100,
                )
            except Exception as exc:  # noqa: BLE001
                self._logger.warning(
                    "PortfolioPerformanceEngine: %s PerformanceEngine failed — %s: %s",
                    asset,
                    type(exc).__name__,
                    exc,
                )

        if not per_asset_reports:
            raise ValueError(
                "PortfolioPerformanceEngine: PerformanceEngine failed for all assets."
            )

        # Step 2: Initial capital (from first successful per-asset report)
        first_report = next(iter(per_asset_reports.values()))
        initial_capital_per_asset = first_report.initial_capital_usd
        initial_capital_total = initial_capital_per_asset * len(multi_result.assets)

        # Step 3: Portfolio scalar metrics
        portfolio_metrics = self._compute_portfolio_metrics(
            portfolio_equity=multi_result.portfolio_equity_curve,
            portfolio_pnl=multi_result.portfolio_pnl_series,
            initial_capital_total=initial_capital_total,
        )

        # Step 4: Asset contributions
        asset_contributions = self._compute_asset_contributions(
            multi_result.asset_results,
            multi_result.portfolio_pnl_series,
        )

        # Absolute PnL per asset (always stable regardless of portfolio total PnL)
        absolute_pnl_by_asset = {
            asset: float(
                bt_result.pnl_series.reindex(
                    multi_result.portfolio_pnl_series.index, fill_value=0.0
                ).sum()
            )
            for asset, bt_result in multi_result.asset_results.items()
        }

        # Step 5: Portfolio date range
        idx = multi_result.portfolio_equity_curve.index
        portfolio_date_range = (
            idx[0].date() if hasattr(idx[0], "date") else idx[0],
            idx[-1].date() if hasattr(idx[-1], "date") else idx[-1],
        )

        self._logger.info(
            "PortfolioPerformanceEngine: %s — %d assets, "
            "portfolio Sharpe=%.4f, max_dd=%.2f%%, return=%.2f%%",
            multi_result.run_id,
            len(per_asset_reports),
            portfolio_metrics.get("sharpe", float("nan")),
            portfolio_metrics.get("max_drawdown", float("nan")) * 100,
            portfolio_metrics.get("total_return", float("nan")) * 100,
        )

        return PortfolioPerformanceReport(
            strategy_name=multi_result.strategy_name,
            run_id=multi_result.run_id,
            assets=multi_result.assets,
            skipped_assets=multi_result.skipped_assets,
            initial_capital_per_asset=initial_capital_per_asset,
            initial_capital_total=initial_capital_total,
            portfolio_date_range=portfolio_date_range,
            portfolio_metrics=portfolio_metrics,
            asset_contributions=asset_contributions,
            absolute_pnl_by_asset=absolute_pnl_by_asset,
            per_asset_reports=per_asset_reports,
            asset_run_ids={
                asset: result.run_id
                for asset, result in multi_result.asset_results.items()
            },
        )

    def _compute_portfolio_metrics(
        self,
        portfolio_equity: pd.Series,
        portfolio_pnl: pd.Series,
        initial_capital_total: float,
    ) -> dict[str, float]:
        """Compute portfolio-level scalar metrics.

        Args:
            portfolio_equity: Sum of per-asset equity curves.
            portfolio_pnl: Sum of per-asset daily PnL series.
            initial_capital_total: Total initial capital across all assets.

        Returns:
            Dict of metric_name → float value. Uses NaN for
            any metric that cannot be computed (insufficient data, etc.)
        """
        n_days = len(portfolio_equity)

        if n_days == 0 or initial_capital_total <= 0:
            return {
                k: float("nan")
                for k in [
                    "total_return",
                    "cagr",
                    "sharpe",
                    "sortino",
                    "calmar",
                    "max_drawdown",
                    "portfolio_vol",
                    "n_trading_days",
                ]
            }

        # Total return
        total_return = (
            portfolio_equity.iloc[-1] - initial_capital_total
        ) / initial_capital_total

        # CAGR (252 trading days per year)
        years = n_days / 252.0
        final_equity = float(portfolio_equity.iloc[-1])
        if years > 0 and final_equity > 0:
            cagr = (final_equity / initial_capital_total) ** (1.0 / years) - 1.0
        else:
            cagr = float("nan")

        # Daily returns expressed as fraction of total initial capital
        daily_returns = portfolio_pnl / initial_capital_total
        daily_returns = daily_returns.dropna()

        if len(daily_returns) < 2:
            return {
                "total_return": float(total_return),
                "cagr": float(cagr),
                "sharpe": float("nan"),
                "sortino": float("nan"),
                "calmar": float("nan"),
                "max_drawdown": float("nan"),
                "portfolio_vol": float("nan"),
                "n_trading_days": float(n_days),
            }

        daily_std = float(daily_returns.std())
        daily_mean = float(daily_returns.mean())

        # Annualized portfolio volatility
        portfolio_vol = daily_std * math.sqrt(252) if daily_std > 0 else float("nan")

        # Sharpe ratio
        if not math.isnan(portfolio_vol) and portfolio_vol > 0 and daily_std > 0:
            sharpe = (daily_mean / daily_std) * math.sqrt(252)
        else:
            sharpe = float("nan")

        # Sortino ratio (downside deviation)
        negative_returns = daily_returns[daily_returns < 0]
        if len(negative_returns) >= 2:
            downside_std = float(negative_returns.std())
            sortino = (
                (daily_mean / downside_std) * math.sqrt(252)
                if downside_std > 0
                else float("nan")
            )
        else:
            sortino = float("nan")

        # Max drawdown (peak-to-trough / peak)
        running_peak = portfolio_equity.cummax()
        drawdown = (portfolio_equity - running_peak) / running_peak
        max_drawdown = float(drawdown.min())  # always <= 0

        # Calmar ratio (CAGR / |max_drawdown|)
        if not math.isnan(max_drawdown) and max_drawdown < 0 and not math.isnan(cagr):
            calmar = cagr / abs(max_drawdown)
        else:
            calmar = float("nan")

        return {
            "total_return": float(total_return),
            "cagr": float(cagr),
            "sharpe": float(sharpe),
            "sortino": float(sortino),
            "calmar": float(calmar),
            "max_drawdown": float(max_drawdown),
            "portfolio_vol": float(portfolio_vol),
            "n_trading_days": float(n_days),
        }

    def _compute_asset_contributions(
        self,
        asset_results: dict[str, BacktestResult],
        portfolio_pnl: pd.Series,
    ) -> dict[str, float]:
        """Compute each asset's fractional contribution to total portfolio P&L.

        Contribution = sum(asset_pnl) / sum(portfolio_pnl).
        Positive: asset contributed profits. Negative: asset contributed losses.
        Values sum to approximately 1.0 when total portfolio P&L is non-zero.

        Returns NaN for all assets when total portfolio P&L is zero.

        Args:
            asset_results: Dict of asset → BacktestResult.
            portfolio_pnl: Aggregated portfolio PnL series.

        Returns:
            Dict of asset → contribution fraction.
        """
        total_pnl = float(portfolio_pnl.sum())

        if total_pnl == 0.0 or math.isnan(total_pnl):
            return {asset: float("nan") for asset in asset_results}

        contributions: dict[str, float] = {}
        for asset, bt_result in asset_results.items():
            # Align to portfolio_pnl index (inner-join dates from aggregation)
            aligned_pnl = bt_result.pnl_series.reindex(portfolio_pnl.index).fillna(0.0)
            asset_total_pnl = float(aligned_pnl.sum())
            contributions[asset] = asset_total_pnl / total_pnl

        return contributions


def save_portfolio_summary(
    report: PortfolioPerformanceReport,
    run_dir: Path,
) -> Path:
    """Save portfolio-level performance summary to portfolio_summary.json.

    Includes per_asset_metrics (scalar_metrics per asset) so the
    /api/portfolio/{run_id}/assets route can serve per-asset data
    without requiring RunManager.save() per asset.

    NaN values in scalar_metrics are serialized as JSON null.
    """

    def _nan_safe(v: object) -> object:
        """Convert math.nan to None for JSON null; leave other values as-is."""
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    summary: dict = {
        "run_id": report.run_id,
        "strategy_name": report.strategy_name,
        "assets": report.assets,
        "skipped_assets": report.skipped_assets,
        "initial_capital_per_asset": report.initial_capital_per_asset,
        "initial_capital_total": report.initial_capital_total,
        "portfolio_date_range": [str(d) for d in report.portfolio_date_range],
        "portfolio_metrics": {
            k: _nan_safe(v) for k, v in report.portfolio_metrics.items()
        },
        "asset_contributions": {
            k: _nan_safe(v) for k, v in report.asset_contributions.items()
        },
        "absolute_pnl_by_asset": report.absolute_pnl_by_asset,
        # Per-asset scalar metrics for /api/portfolio/{run_id}/assets
        # Contains full PerformanceReport.scalar_metrics per asset:
        # sharpe, sortino, calmar, max_drawdown, total_return, etc.
        "per_asset_metrics": {
            asset: {k: _nan_safe(v) for k, v in per_rpt.scalar_metrics.items()}
            for asset, per_rpt in report.per_asset_reports.items()
        },
        "asset_run_ids": report.asset_run_ids,
        "has_regime_attribution": False,
    }

    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "portfolio_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out_path


def save_portfolio_equity(
    multi_result: MultiAssetBacktestResult,
    run_dir: Path,
) -> Path:
    """Save portfolio equity curve and daily PnL series to parquet.

    Persists multi_result.portfolio_equity_curve → portfolio_equity.parquet
    and multi_result.portfolio_pnl_series       → portfolio_pnl.parquet

    Both are required by GET /api/portfolio/{run_id}/equity (PortfolioEquityResponse
    contains portfolio_equity and portfolio_pnl as separate columnar fields).

    Args:
        multi_result: MultiAssetBacktestResult from MultiAssetRunner.run().
        run_dir: Portfolio run artifacts directory (data/runs/{run_id}/).

    Returns:
        Path to portfolio_equity.parquet (primary artifact path).
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    equity_path = run_dir / "portfolio_equity.parquet"
    multi_result.portfolio_equity_curve.to_frame(name="equity").to_parquet(
        equity_path, engine="pyarrow"
    )
    pnl_path = run_dir / "portfolio_pnl.parquet"
    multi_result.portfolio_pnl_series.to_frame(name="pnl").to_parquet(
        pnl_path, engine="pyarrow"
    )
    return equity_path


def save_risk_report(
    risk_report: RiskReport,
    run_dir: Path,
) -> Path:
    """Save RiskReport scalars and per-asset dicts to portfolio_risk.json.

    Persists all RiskReport fields so that
    GET /api/portfolio/{run_id}/risk can be served after server restart.

    NaN values are converted to None (JSON null) using the same
    _nan_safe() pattern as save_portfolio_summary().

    Args:
        risk_report: RiskReport from RiskEngine.compute().
        run_dir: Portfolio run artifacts directory.

    Returns:
        Path to the written JSON file.
    """
    import json as _json  # noqa: PLC0415

    run_dir.mkdir(parents=True, exist_ok=True)

    def _nan_safe(v: object) -> object:
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    data: dict = {
        "strategy_name": risk_report.strategy_name,
        "run_id": risk_report.run_id,
        "assets": risk_report.assets,
        "computation_date": str(risk_report.computation_date),
        "lookback_days": risk_report.lookback_days,
        "initial_capital_total": risk_report.initial_capital_total,
        "portfolio_var_95": _nan_safe(risk_report.portfolio_var_95),
        "portfolio_var_99": _nan_safe(risk_report.portfolio_var_99),
        "portfolio_var_95_pct": _nan_safe(risk_report.portfolio_var_95_pct),
        "portfolio_var_99_pct": _nan_safe(risk_report.portfolio_var_99_pct),
        "portfolio_es_95": _nan_safe(risk_report.portfolio_es_95),
        "portfolio_es_99": _nan_safe(risk_report.portfolio_es_99),
        "asset_var_95": {k: _nan_safe(v) for k, v in risk_report.asset_var_95.items()},
        "asset_var_99": {k: _nan_safe(v) for k, v in risk_report.asset_var_99.items()},
        "avg_gross_notional_by_asset": {
            k: _nan_safe(v) for k, v in risk_report.avg_gross_notional_by_asset.items()
        },
        "avg_net_notional_by_asset": {
            k: _nan_safe(v) for k, v in risk_report.avg_net_notional_by_asset.items()
        },
        "total_avg_gross_notional": _nan_safe(risk_report.total_avg_gross_notional),
        "total_avg_net_notional": _nan_safe(risk_report.total_avg_net_notional),
        # EM4 — Kupiec backtesting + contribution to strategy vol
        "n_backtesting_days": risk_report.n_backtesting_days,
        "exceptions_95": risk_report.exceptions_95,
        "exceptions_99": risk_report.exceptions_99,
        "exception_rate_95": _nan_safe(risk_report.exception_rate_95),
        "exception_rate_99": _nan_safe(risk_report.exception_rate_99),
        "kupiec_lr_99": _nan_safe(risk_report.kupiec_lr_99),
        "kupiec_pvalue_99": _nan_safe(risk_report.kupiec_pvalue_99),
        "asset_contribution_to_vol": {
            k: _nan_safe(v) for k, v in risk_report.asset_contribution_to_vol.items()
        },
        "asset_contribution_to_vol_pct": {
            k: _nan_safe(v)
            for k, v in risk_report.asset_contribution_to_vol_pct.items()
        },
    }

    if not risk_report.asset_contribution_to_vol_pct:
        logging.getLogger(__name__).warning(
            "save_risk_report: empty asset_contribution_to_vol_pct for run %s. "
            "RiskEngine.compute() was likely called without corr_report. "
            "Use src.analytics.correlation.compute_correlation_and_risk().",
            risk_report.run_id,
        )

    out_path = run_dir / "portfolio_risk.json"
    out_path.write_text(_json.dumps(data, indent=2), encoding="utf-8")
    return out_path


def save_correlation_report(
    corr_report: CorrelationReport,
    run_dir: Path,
) -> Path:
    """Save CorrelationReport to disk — scalars to JSON, rolling series to Parquet.

    Three files:
      portfolio_correlation.json    — matrix, vol, pairwise scalars
      portfolio_rolling_63.parquet  — 63-day rolling correlations (wide format)
      portfolio_rolling_126.parquet — 126-day rolling correlations (wide format)

    Rolling parquets are in wide format: date index, columns are
    "{asset_a}__{asset_b}" (double-underscore separator, upper-triangle pairs only,
    a < b alphabetically — matching CorrelationReport.rolling_correlations_63 structure).

    Note: _symmetrize_rolling() is applied at read time in the API handler,
    not at save time. Upper-triangle storage is canonical.

    Args:
        corr_report: CorrelationReport from CorrelationEngine.compute().
        run_dir: Portfolio run artifacts directory.

    Returns:
        Path to the written JSON file (primary artifact).
    """
    import json as _json  # noqa: PLC0415

    run_dir.mkdir(parents=True, exist_ok=True)

    def _nan_safe(v: object) -> object:
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    data: dict = {
        "strategy_name": corr_report.strategy_name,
        "run_id": corr_report.run_id,
        "assets": corr_report.assets,
        "computation_date": str(corr_report.computation_date),
        "correlation_matrix": {
            a: {b: _nan_safe(v) for b, v in row.items()}
            for a, row in corr_report.correlation_matrix.items()
        },
        "realized_vol_by_asset": {
            k: _nan_safe(v) for k, v in corr_report.realized_vol_by_asset.items()
        },
        "portfolio_realized_vol": _nan_safe(corr_report.portfolio_realized_vol),
        "avg_pairwise_correlation": _nan_safe(corr_report.avg_pairwise_correlation),
        "most_correlated_pair": [
            corr_report.most_correlated_pair[0],
            corr_report.most_correlated_pair[1],
            _nan_safe(corr_report.most_correlated_pair[2]),
        ],
        "least_correlated_pair": [
            corr_report.least_correlated_pair[0],
            corr_report.least_correlated_pair[1],
            _nan_safe(corr_report.least_correlated_pair[2]),
        ],
    }

    out_path = run_dir / "portfolio_correlation.json"
    out_path.write_text(_json.dumps(data, indent=2), encoding="utf-8")

    def _rolling_to_df(
        rolling_dict: dict[str, dict[str, pd.Series]],
    ) -> pd.DataFrame:
        """Convert nested rolling dict to wide DataFrame.
        Columns: '{asset_a}__{asset_b}' (upper-triangle pairs only).
        """
        frames: dict[str, pd.Series] = {}
        for a, inner in rolling_dict.items():
            for b, series in inner.items():
                frames[f"{a}__{b}"] = series
        if not frames:
            import pandas as _pd  # noqa: PLC0415

            return _pd.DataFrame()
        import pandas as _pd  # noqa: PLC0415

        return _pd.DataFrame(frames)

    for window, rolling_dict in [
        (63, corr_report.rolling_correlations_63),
        (126, corr_report.rolling_correlations_126),
    ]:
        df = _rolling_to_df(rolling_dict)
        if not df.empty:
            df.to_parquet(
                run_dir / f"portfolio_rolling_{window}.parquet",
                engine="pyarrow",
            )

    return out_path
