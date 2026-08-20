"""Regime-conditional performance attribution for commodity strategy backtests.

Conditions strategy P&L on futures term structure regime (CONTANGO /
BACKWARDATION / FLAT) at each trading day, using TermStructureAnalyzer
snapshots from individual contract data.

The analysis is computed on-demand for any completed BacktestResult — no
pre-computation or caching in run artifacts is required.

ADR-001: continuous OHLCV (P&L source) and contract data (regime source)
are never mixed within a single computation. Each is consumed separately.
"""

from __future__ import annotations

import datetime
import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.core.types import (
        PortfolioRegimeAttributionReport,
        RegimeAttributionReport,
    )

logger = logging.getLogger(__name__)

# Minimum trading days per regime for meaningful statistics
_MIN_REGIME_DAYS = 20


@dataclass
class _TradeProxy:
    entry_date: object
    net_pnl: float


@dataclass
class _RunProxy:
    run_id: str
    asset: str
    strategy_name: str
    pnl_series: pd.Series | None
    equity_curve: pd.Series | None
    trades: list  # list of _TradeProxy objects


def _convert_trades(trades_raw: pd.DataFrame | list | None) -> list:
    """Convert a trades DataFrame or list into _TradeProxy objects."""
    import pandas as _pd  # noqa: PLC0415

    if trades_raw is None:
        return []
    if isinstance(trades_raw, _pd.DataFrame):
        if trades_raw.empty:
            return []
        return [
            _TradeProxy(
                entry_date=row.get("entry_date"),
                net_pnl=float(row.get("net_pnl", 0.0)),
            )
            for row in trades_raw.to_dict("records")
        ]
    return list(trades_raw)


def _make_run_proxy(run_data: dict, run_id: str, asset: str) -> _RunProxy:
    """Construct a _RunProxy from load_run() dict output."""
    params = run_data.get("params", {})
    return _RunProxy(
        run_id=run_id,
        asset=asset,
        strategy_name=params.get("strategy_name", params.get("strategy", "unknown")),
        pnl_series=run_data.get("pnl_series"),
        equity_curve=run_data.get("equity_curve"),
        trades=_convert_trades(run_data.get("trades")),
    )


class RegimeAttributionEngine:
    """Computes regime-conditional performance metrics for a backtest result.

    Usage:
        engine = RegimeAttributionEngine(config)
        report = engine.compute(
            backtest_result=result,
            asset='gold',
            n_contracts=4,
        )
    """

    def __init__(self, config: object) -> None:
        self._config = config

    def compute(
        self,
        backtest_result: object,
        asset: str,
        n_contracts: int = 4,
    ) -> RegimeAttributionReport:
        """Compute regime-conditional attribution for a BacktestResult.

        Loads the regime time series from individual contract data
        (FuturesCurveBuilder + TermStructureAnalyzer), aligns it with
        the backtest's daily P&L series, and computes conditional metrics
        per regime.

        Args:
            backtest_result: BacktestResult from VectorizedBacktester.run().
            asset: Asset identifier (e.g. 'gold'). Used to load contract data.
            n_contracts: Number of contracts for curve construction.

        Returns:
            RegimeAttributionReport with per-regime metrics.
            Returns a report with empty regime_metrics if contract data
            is unavailable for the asset.
        """
        from src.commodity.curve import FuturesCurveBuilder  # noqa: PLC0415
        from src.commodity.term_structure import TermStructureAnalyzer  # noqa: PLC0415
        from src.core.types import (  # noqa: PLC0415
            RegimeAttributionReport,
            RegimeMetrics,
        )

        run_id = getattr(backtest_result, "run_id", "unknown")
        strategy_name = getattr(backtest_result, "strategy_name", "unknown")

        logger.info(
            "RegimeAttributionEngine: computing for run_id=%s, asset=%s",
            run_id,
            asset,
        )

        # ── Step 1: Load regime time series from contract data ────────────
        builder = FuturesCurveBuilder(self._config)  # type: ignore[arg-type]

        pnl_series = getattr(backtest_result, "pnl_series", pd.Series(dtype=float))
        if pnl_series is None or len(pnl_series) == 0:
            logger.warning(
                "RegimeAttributionEngine: pnl_series is empty for run_id=%s", run_id
            )
            return RegimeAttributionReport(
                run_id=run_id,
                asset=asset,
                strategy_name=strategy_name,
                n_contracts=n_contracts,
                computation_date=datetime.date.today(),
            )

        dates = [d.date() for d in pnl_series.index]

        if asset not in builder.available_assets():
            logger.warning(
                "RegimeAttributionEngine: no contract data for '%s' — "
                "returning empty attribution.",
                asset,
            )
            return RegimeAttributionReport(
                run_id=run_id,
                asset=asset,
                strategy_name=strategy_name,
                n_contracts=n_contracts,
                computation_date=datetime.date.today(),
                total_days_in_run=len(dates),
            )

        try:
            curves = builder.build_historical_curves(
                asset=asset,
                dates=dates,
                n_contracts=n_contracts,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "RegimeAttributionEngine: curve build failed for '%s': %s",
                asset,
                exc,
            )
            return RegimeAttributionReport(
                run_id=run_id,
                asset=asset,
                strategy_name=strategy_name,
                n_contracts=n_contracts,
                computation_date=datetime.date.today(),
                total_days_in_run=len(dates),
            )

        analyzer = TermStructureAnalyzer()
        # ADR-001: do not pass continuous closes into regime classification
        snapshots = analyzer.analyze_series(curves=curves)

        # Map date → regime string
        regime_map: dict[datetime.date, str] = {
            snap.observation_date: str(snap.regime) for snap in snapshots
        }

        # ── Step 2: Align regime with P&L series ─────────────────────────
        regime_series = pd.Series(
            [regime_map.get(d) for d in dates],
            index=pnl_series.index,
        )

        n_with_regime = regime_series.notna().sum()
        logger.info(
            "RegimeAttributionEngine: %d / %d bars have regime data",
            n_with_regime,
            len(dates),
        )

        # ── Step 3: Compute per-regime metrics ────────────────────────────
        trades = getattr(backtest_result, "trades", []) or []
        equity_curve = getattr(backtest_result, "equity_curve", pd.Series(dtype=float))

        all_regimes = self._get_regime_values()
        regime_metrics: dict[str, RegimeMetrics] = {}
        regime_coverage: dict[str, float] = {}
        total_days = len(dates)

        for regime_str in all_regimes:
            mask = regime_series == regime_str
            n_days = int(mask.sum())
            coverage = n_days / total_days if total_days > 0 else 0.0
            regime_coverage[regime_str] = coverage

            if n_days < _MIN_REGIME_DAYS:
                regime_metrics[regime_str] = RegimeMetrics(
                    regime=regime_str,
                    n_days=n_days,
                    coverage=coverage,
                    sharpe=float("nan"),
                    total_return=float("nan"),
                    max_drawdown=float("nan"),
                    n_trades=0,
                    win_rate=float("nan"),
                )
                continue

            # P&L in this regime
            regime_pnl = pnl_series[mask]

            # Annualized Sharpe from daily P&L
            # Convert P&L to returns relative to initial capital
            # (use equity_curve to get the base for each bar)
            initial_capital = (
                float(equity_curve.iloc[0]) if len(equity_curve) > 0 else 1.0
            )
            regime_returns = regime_pnl / initial_capital
            sharpe = self._compute_sharpe(regime_returns)

            # Total return in regime (sum of daily P&L / initial capital)
            total_return = float(regime_pnl.sum() / initial_capital)

            # Max drawdown within the equity curve during this regime
            if len(equity_curve) > 0:
                regime_equity = equity_curve[mask]
                max_dd = self._compute_max_drawdown(regime_equity)
            else:
                max_dd = float("nan")

            # Trades that entered during this regime
            regime_trade_count, win_rate = self._compute_trade_stats(
                trades=trades,
                regime_series=regime_series,
                regime_str=regime_str,
            )

            regime_metrics[regime_str] = RegimeMetrics(
                regime=regime_str,
                n_days=n_days,
                coverage=coverage,
                sharpe=sharpe,
                total_return=total_return,
                max_drawdown=max_dd,
                n_trades=regime_trade_count,
                win_rate=win_rate,
            )

        # Dominant regime
        dominant = max(regime_coverage, key=lambda r: regime_coverage[r])

        return RegimeAttributionReport(
            run_id=run_id,
            asset=asset,
            strategy_name=strategy_name,
            n_contracts=n_contracts,
            computation_date=datetime.date.today(),
            regime_metrics=regime_metrics,
            regime_coverage=regime_coverage,
            dominant_regime=dominant,
            total_days_with_regime=int(n_with_regime),
            total_days_in_run=total_days,
        )

    def _get_regime_values(self) -> list[str]:
        """Return the canonical set of regime strings.

        Uses str(TermStructureRegime.X) which equals "X" for str,Enum.
        Task 0a confirms the actual enum values — adjust if needed.
        """
        try:
            from src.core.types import TermStructureRegime  # noqa: PLC0415

            return [str(r) for r in TermStructureRegime]
        except Exception:  # noqa: BLE001
            # Fallback to known values from Phase 2
            return ["contango", "backwardation", "flat"]

    def _compute_sharpe(self, returns: pd.Series) -> float:
        """Compute annualized Sharpe from daily return series.
        Uses sqrt(252) annualization. Returns NaN for < 2 non-NaN values.
        """
        clean = returns.dropna()
        if len(clean) < 2:
            return float("nan")
        std = float(clean.std(ddof=1))
        if std <= 0:
            return float("nan")
        return float(clean.mean() / std * math.sqrt(252))

    def _compute_max_drawdown(self, equity_curve: pd.Series) -> float:
        """Compute maximum drawdown from equity curve subset."""
        if len(equity_curve) < 2:
            return float("nan")
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        return float(drawdown.min())

    def _compute_trade_stats(
        self,
        trades: list,
        regime_series: pd.Series,
        regime_str: str,
    ) -> tuple[int, float]:
        """Count trades entering in this regime and compute win rate.

        A trade 'enters' in a regime when its entry date falls in a bar
        labeled with that regime. Win rate = profitable trades / total trades.
        Returns (0, NaN) if no trades entered in this regime.
        """
        if not trades:
            return 0, float("nan")

        regime_dates = set(
            d.date() if hasattr(d, "date") else d
            for d, label in zip(regime_series.index, regime_series, strict=True)
            if label == regime_str
        )

        regime_trades = []
        for trade in trades:
            entry_date = getattr(trade, "entry_date", None)
            if entry_date is None:
                continue
            if hasattr(entry_date, "date"):
                entry_date = entry_date.date()
            if entry_date in regime_dates:
                regime_trades.append(trade)

        if not regime_trades:
            return 0, float("nan")

        wins = sum(1 for t in regime_trades if getattr(t, "net_pnl", 0) > 0)
        win_rate = wins / len(regime_trades)
        return len(regime_trades), win_rate

    def compute_portfolio(
        self,
        portfolio_run_id: str,
        n_contracts: int = 4,
    ) -> PortfolioRegimeAttributionReport:
        """Portfolio-level regime attribution aggregated across all assets."""
        import json as _json  # noqa: PLC0415
        import math as _math  # noqa: PLC0415
        from pathlib import Path as _Path  # noqa: PLC0415

        from src.backtesting.run_manager import RunManager  # noqa: PLC0415
        from src.core.types import (  # noqa: PLC0415
            PortfolioRegimeAttributionReport,
            RegimeMetrics,
        )

        summary_path = _Path("data/runs") / portfolio_run_id / "portfolio_summary.json"
        if not summary_path.exists():
            raise ValueError(
                f"Portfolio summary not found for '{portfolio_run_id}'. "
                "Run portfolio analysis first."
            )

        summary = _json.loads(summary_path.read_text(encoding="utf-8"))
        asset_run_ids: dict[str, str] = summary.get("asset_run_ids", {})

        if not asset_run_ids:
            raise ValueError(
                f"No asset_run_ids in portfolio summary for '{portfolio_run_id}'. "
                "Re-run portfolio analysis to generate per-asset run IDs."
            )

        manager = RunManager(self._config)  # type: ignore[arg-type]
        per_asset: dict[str, RegimeAttributionReport] = {}
        per_asset_pnl: dict[str, float] = {}

        for asset, asset_run_id in asset_run_ids.items():
            try:
                run_data = manager.load_run(asset_run_id)
                proxy = _make_run_proxy(run_data, asset_run_id, asset)
                report = self.compute(proxy, asset=asset, n_contracts=n_contracts)
                per_asset[asset] = report
                pnl = run_data.get("pnl_series")
                per_asset_pnl[asset] = float(pnl.sum()) if pnl is not None else 0.0
            except Exception as exc:  # noqa: BLE001
                logger.warning("Portfolio regime: skipping '%s' — %s", asset, exc)

        if not per_asset:
            return PortfolioRegimeAttributionReport(
                portfolio_run_id=portfolio_run_id,
                n_assets_computed=0,
            )

        total_pnl = sum(abs(v) for v in per_asset_pnl.values()) or 1.0
        weights = {a: abs(v) / total_pnl for a, v in per_asset_pnl.items()}

        all_regimes: set[str] = set()
        for report in per_asset.values():
            all_regimes.update(report.regime_metrics.keys())

        portfolio_metrics: dict[str, RegimeMetrics] = {}
        for regime in all_regimes:
            regime_reports = [
                per_asset[a].regime_metrics[regime]
                for a in per_asset
                if regime in per_asset[a].regime_metrics
            ]

            # CORRECTION 3: float() cast — RegimeMetrics.sharpe is float | None
            valid_sharpes: list[float] = []
            for a in per_asset:
                if regime not in per_asset[a].regime_metrics:
                    continue
                m = per_asset[a].regime_metrics[regime]
                if m.sharpe is None or _math.isnan(m.sharpe):
                    continue
                valid_sharpes.append(weights.get(a, 0.0) * float(m.sharpe))
            weighted_sharpe = sum(valid_sharpes) if valid_sharpes else float("nan")
            mean_coverage = sum(r.coverage for r in regime_reports) / max(
                len(regime_reports), 1
            )

            weighted_returns = 0.0
            for a in per_asset:
                m = per_asset[a].regime_metrics.get(
                    regime, RegimeMetrics(regime=regime)
                )
                tr = m.total_return
                weighted_returns += weights.get(a, 0.0) * float(
                    0.0 if tr is None else tr
                )

            dd_values = [
                float(r.max_drawdown)
                for r in regime_reports
                if r.max_drawdown is not None and not _math.isnan(r.max_drawdown)
            ]
            max_dd = min(dd_values) if dd_values else float("nan")

            portfolio_metrics[regime] = RegimeMetrics(
                regime=regime,
                n_days=max((r.n_days for r in regime_reports), default=0),
                coverage=mean_coverage,
                sharpe=weighted_sharpe,
                total_return=weighted_returns,
                max_drawdown=max_dd,
                n_trades=sum(r.n_trades for r in regime_reports),
                win_rate=float("nan"),  # not meaningful at portfolio level
            )

        dominant = max(portfolio_metrics, key=lambda r: portfolio_metrics[r].coverage)

        return PortfolioRegimeAttributionReport(
            portfolio_run_id=portfolio_run_id,
            n_assets_computed=len(per_asset),
            assets_computed=list(per_asset.keys()),
            computation_date=datetime.date.today(),
            portfolio_regime_metrics=portfolio_metrics,
            per_asset_metrics=dict(per_asset),
            dominant_regime=dominant,
            asset_weights=weights,
        )
