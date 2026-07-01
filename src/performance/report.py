"""PerformanceEngine: Layer 4 entry point for performance metric computation.

Consumes BacktestResult from Layer 3 (VectorizedBacktester).
Produces PerformanceReport for Layer 8 (dashboard).
See Architecture Section 5 (Layer 4 Responsibilities) and Section 7
(PerformanceReport layer contract).
"""

from __future__ import annotations

import logging

from src.core.types import BacktestResult, PerformanceReport, SignalEvaluation
from src.performance.metrics import compute_scalar_metrics, compute_trade_statistics
from src.performance.rolling import compute_rolling_metrics


class PerformanceEngine:
    """Assembles PerformanceReport from BacktestResult.

    Single entry point for Layer 4. Does not perform backtesting,
    chart rendering, or any data persistence. Persistence is handled
    by RunManager.save_metrics() in src/backtesting/run_manager.py.

    Usage:
        engine = PerformanceEngine()
        report = engine.compute(backtest_result)
        run_manager.save_metrics(backtest_result.run_id, report)
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def compute(self, backtest_result: BacktestResult) -> PerformanceReport:
        """Compute all performance metrics and assemble PerformanceReport.

        Args:
            backtest_result: BacktestResult from VectorizedBacktester.run().
                signal_evaluation may be None (signal metrics will be empty
                dict) or populated by the orchestration layer that connects
                Modules 4 + 5 + 6.

        Returns:
            PerformanceReport with all four metric dicts populated.
        """
        self._logger.info(
            "PerformanceEngine: computing metrics for run %s (%d trades)",
            backtest_result.run_id,
            len(backtest_result.trades),
        )

        scalar_metrics = compute_scalar_metrics(backtest_result)
        rolling_metrics = compute_rolling_metrics(backtest_result)
        trade_statistics = compute_trade_statistics(backtest_result.trades)
        signal_metrics = self._extract_signal_metrics(backtest_result.signal_evaluation)

        self._logger.info(
            "PerformanceEngine: Sharpe=%.4f, MaxDD=%.4f, WinRate=%.4f, Trades=%d",
            scalar_metrics.get("sharpe", 0.0),
            scalar_metrics.get("max_drawdown", 0.0),
            scalar_metrics.get("win_rate", 0.0),
            len(backtest_result.trades),
        )

        return PerformanceReport(
            run_id=backtest_result.run_id,
            initial_capital_usd=backtest_result.metadata.initial_capital_usd,
            scalar_metrics=scalar_metrics,
            rolling_metrics=rolling_metrics,
            trade_statistics=trade_statistics,
            signal_metrics=signal_metrics,
        )

    def _extract_signal_metrics(
        self,
        signal_evaluation: SignalEvaluation | None,
    ) -> dict[str, float]:
        """Extract signal quality metrics from SignalEvaluation.

        Returns empty dict if signal_evaluation is None (signal metrics
        not available). Architecture Section 7: source is
        backtest_result.signal_evaluation if present; empty dict if None.

        Args:
            signal_evaluation: From BacktestResult.signal_evaluation.

        Returns:
            Dict with keys: ic, icir, signal_decay_1, signal_decay_2,
            signal_decay_5, signal_decay_10, signal_decay_20.
            Or empty dict if signal_evaluation is None.
        """
        if signal_evaluation is None:
            return {}

        metrics: dict[str, float] = {
            "ic": signal_evaluation.ic,
            "icir": signal_evaluation.icir,
        }
        for horizon, ic_at_horizon in signal_evaluation.ic_decay.items():
            metrics[f"signal_decay_{horizon}"] = ic_at_horizon

        return metrics
