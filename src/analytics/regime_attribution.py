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
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.core.types import RegimeAttributionReport

logger = logging.getLogger(__name__)

# Minimum trading days per regime for meaningful statistics
_MIN_REGIME_DAYS = 20


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
