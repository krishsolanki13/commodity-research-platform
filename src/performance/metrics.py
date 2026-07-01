"""Scalar performance metrics computation for PerformanceReport.

All metrics derived from BacktestResult components. See Architecture
Section 7 (PerformanceReport layer contract) and Implementation Roadmap
Module 6 for the metric formula specifications.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from src.core.types import BacktestResult, TradeRecord


def compute_daily_returns(
    pnl_series: pd.Series,
    equity_curve: pd.Series,
) -> pd.Series:
    """Compute daily return on capital: pnl[t] / equity[t-1].

    Architecture Section 7: daily_return[t] = pnl_series[t] / equity_curve[t-1].
    Returns 0.0 for bar 0 (equity[t-1] is undefined; pnl[0] is always 0
    per ADR-002 — bar 0 is always flat).

    Args:
        pnl_series: Daily net PnL series from BacktestResult.
        equity_curve: Cumulative equity series from BacktestResult.

    Returns:
        pd.Series of fractional daily returns. Same index as pnl_series.
    """
    prev_equity = equity_curve.shift(1).replace(0.0, float("nan"))
    daily_return = pnl_series / prev_equity
    return daily_return.fillna(0.0)


def compute_scalar_metrics(
    backtest_result: BacktestResult,
) -> dict[str, float]:
    """Compute all scalar performance metrics from a BacktestResult.

    All values are guaranteed finite (no NaN, no inf) for any valid
    BacktestResult with equity_curve[0] = initial_capital_usd.

    Args:
        backtest_result: Complete BacktestResult from VectorizedBacktester.run().

    Returns:
        Dict mapping metric name to float. See Architecture Section 7 for
        the complete list of expected keys.
    """
    equity = backtest_result.equity_curve
    pnl = backtest_result.pnl_series
    trades = backtest_result.trades
    initial_capital = backtest_result.metadata.initial_capital_usd

    daily_return = compute_daily_returns(pnl, equity)

    total_return = _total_return(equity, initial_capital)
    n_bars = len(equity)
    cagr = _cagr(total_return, n_bars)
    sharpe = _sharpe(daily_return)
    sortino = _sortino(daily_return)
    max_dd = _max_drawdown(equity)
    avg_dd = _avg_drawdown(equity)
    calmar = cagr / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    win_rate = _win_rate(trades)
    profit_factor = _profit_factor(trades)
    avg_duration = _avg_duration(trades)
    turnover = _turnover(backtest_result.positions)
    avg_win, avg_loss, largest_win, largest_loss = _trade_pnl_stats(trades)

    return {
        "initial_capital": initial_capital,
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_dd,
        "avg_drawdown": avg_dd,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade_duration_bars": avg_duration,
        "turnover": turnover,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
    }


def compute_trade_statistics(trades: list[TradeRecord]) -> dict[str, Any]:
    """Compute trade-level summary statistics.

    Args:
        trades: List of TradeRecord from BacktestResult.

    Returns:
        Dict with keys: n_trades, n_winning, n_losing, n_flat,
        max_consecutive_wins, max_consecutive_losses.
    """
    if not trades:
        return {
            "n_trades": 0,
            "n_winning": 0,
            "n_losing": 0,
            "n_flat": 0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
        }

    net_pnls = [t.net_pnl for t in trades]
    n_winning = sum(1 for p in net_pnls if p > 0)
    n_losing = sum(1 for p in net_pnls if p < 0)
    n_flat = sum(1 for p in net_pnls if abs(p) < 1e-10)

    return {
        "n_trades": len(trades),
        "n_winning": n_winning,
        "n_losing": n_losing,
        "n_flat": n_flat,
        "max_consecutive_wins": _max_consecutive(net_pnls, target="positive"),
        "max_consecutive_losses": _max_consecutive(net_pnls, target="negative"),
    }


def _total_return(equity: pd.Series, initial_capital: float) -> float:
    return (float(equity.iloc[-1]) - initial_capital) / initial_capital


def _cagr(total_return: float, n_bars: int) -> float:
    if n_bars == 0:
        return 0.0
    base = 1.0 + total_return
    if base <= 0.0:
        return -1.0
    return float(base ** (252.0 / n_bars) - 1.0)


def _sharpe(daily_return: pd.Series) -> float:
    std = float(daily_return.std())
    if std < 1e-10:
        return 0.0
    return float(daily_return.mean() / std * math.sqrt(252))


def _sortino(daily_return: pd.Series) -> float:
    negative = daily_return[daily_return < 0]
    if len(negative) == 0:
        return 0.0
    std = float(negative.std())
    if std < 1e-10:
        return 0.0
    return float(daily_return.mean() / std * math.sqrt(252))


def _max_drawdown(equity: pd.Series) -> float:
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max
    return float(drawdown.min())


def _avg_drawdown(equity: pd.Series) -> float:
    """Mean drawdown across all bars below equity peak.

    Phase 1 implementation: bar-level mean (average of (equity[t] - peak[t]) / peak[t]
    across all bars below peak). Some institutions compute average drawdown as the mean
    of discrete drawdown periods (trough-to-recovery cycles), which produces a less
    negative number. Current approach is simpler and defensible for Phase 1 research.
    """
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max
    below_peak = drawdown[drawdown < 0]
    if len(below_peak) == 0:
        return 0.0
    return float(below_peak.mean())


def _win_rate(trades: list[TradeRecord]) -> float:
    if not trades:
        return 0.0
    return sum(1 for t in trades if t.net_pnl > 0) / len(trades)


def _profit_factor(trades: list[TradeRecord]) -> float:
    if not trades:
        return 0.0
    winning = sum(t.net_pnl for t in trades if t.net_pnl > 0)
    losing = abs(sum(t.net_pnl for t in trades if t.net_pnl < 0))
    if losing < 1e-10:
        return winning if winning > 0 else 0.0
    return winning / losing


def _avg_duration(trades: list[TradeRecord]) -> float:
    if not trades:
        return 0.0
    return float(sum(t.duration_bars for t in trades) / len(trades))


def _turnover(positions: pd.Series) -> float:
    """Mean absolute change in position sign ({-1, 0, +1}) per bar.

    Reconstructs position direction from notional exposure series.
    Architecture Section 7: turnover = mean(|PositionSignal[t] - PositionSignal[t-1]|).
    Maximum value = 2.0 (reversal from -1 to +1 or vice versa).

    Note: this is a portfolio activity metric computed post-backtest.
    It differs from SignalEvaluator.evaluate() turnover which is computed
    pre-backtest from the raw signal — they measure different things and
    should not be conflated. See Module 6 Transfer Package Section 7.1.
    """
    position_sign = pd.Series(
        np.sign(positions.values), index=positions.index, dtype="float64"
    )
    return float(position_sign.diff().abs().mean())


def _trade_pnl_stats(
    trades: list[TradeRecord],
) -> tuple[float, float, float, float]:
    """Return (avg_win, avg_loss, largest_win, largest_loss). All 0.0 if no trades."""
    if not trades:
        return 0.0, 0.0, 0.0, 0.0
    net_pnls = [t.net_pnl for t in trades]
    winners = [p for p in net_pnls if p > 0]
    losers = [p for p in net_pnls if p < 0]
    avg_win = float(sum(winners) / len(winners)) if winners else 0.0
    avg_loss = float(sum(losers) / len(losers)) if losers else 0.0
    largest_win = float(max(net_pnls))
    largest_loss = float(min(net_pnls))
    return avg_win, avg_loss, largest_win, largest_loss


def _max_consecutive(values: list[float], target: str) -> int:
    """Count maximum consecutive run of positive (target='positive') or negative values."""
    check = (lambda v: v > 0) if target == "positive" else (lambda v: v < 0)
    max_run = current = 0
    for v in values:
        if check(v):
            current += 1
            max_run = max(max_run, current)
        else:
            current = 0
    return max_run
