"""Rolling performance metrics for PerformanceReport.

Rolling metrics show how performance evolves over time, enabling detection
of strategy degradation, regime changes, and volatility clustering.
See Architecture Section 7 (PerformanceReport rolling_metrics keys).
"""

from __future__ import annotations

import math

import pandas as pd

from src.core.types import BacktestResult
from src.performance.metrics import compute_daily_returns


def compute_rolling_metrics(
    backtest_result: BacktestResult,
) -> dict[str, pd.Series]:
    """Compute all rolling performance metrics from BacktestResult.

    Args:
        backtest_result: Complete BacktestResult from VectorizedBacktester.run().

    Returns:
        Dict of named pd.Series, each sharing the equity_curve index.
        Keys: rolling_sharpe_63, rolling_sharpe_126, rolling_vol_63,
              rolling_drawdown.
        NaN values appear in the warmup periods of rolling windows.
    """
    equity = backtest_result.equity_curve
    pnl = backtest_result.pnl_series
    daily_return = compute_daily_returns(pnl, equity)

    return {
        "rolling_sharpe_63": _rolling_sharpe(daily_return, window=63),
        "rolling_sharpe_126": _rolling_sharpe(daily_return, window=126),
        "rolling_vol_63": _rolling_vol(daily_return, window=63),
        "rolling_drawdown": _rolling_drawdown(equity),
    }


def _rolling_sharpe(daily_return: pd.Series, window: int) -> pd.Series:
    """Annualized rolling Sharpe ratio.

    NaN for the first (window - 1) bars. Returns 0.0 in windows where
    std is effectively zero (constant-return periods).
    """
    roll_mean = daily_return.rolling(window=window, min_periods=window).mean()
    roll_std = daily_return.rolling(window=window, min_periods=window).std()
    result = roll_mean / roll_std * math.sqrt(252)
    result[roll_std < 1e-10] = 0.0
    return result.rename(f"rolling_sharpe_{window}")


def _rolling_vol(daily_return: pd.Series, window: int) -> pd.Series:
    """Annualized rolling volatility.

    NaN for the first (window - 1) bars.
    """
    vol = daily_return.rolling(window=window, min_periods=window).std() * math.sqrt(252)
    return vol.rename(f"rolling_vol_{window}")


def _rolling_drawdown(equity: pd.Series) -> pd.Series:
    """Rolling drawdown from peak at each bar.

    0.0 when at equity peak. Negative when below peak.
    rolling_drawdown[t] = (equity[t] - cummax(equity)[t]) / cummax(equity)[t]
    """
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max
    return drawdown.rename("rolling_drawdown")
