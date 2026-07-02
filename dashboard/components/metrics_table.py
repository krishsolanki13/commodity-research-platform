"""Metrics table component: formats PerformanceReport scalar metrics for display.

Pure function — returns a pd.DataFrame. No st.* calls.
See ADR-008 (Dashboard Architecture).

Note: use report.initial_capital_usd as the authoritative source for initial
capital, not scalar_metrics["initial_capital"]. See Module 6 deviation 1.
"""

from __future__ import annotations

import pandas as pd

_METRIC_FORMAT: dict[str, tuple[str, str]] = {
    "total_return": ("Total Return", "{:+.2%}"),
    "cagr": ("CAGR", "{:+.2%}"),
    "sharpe": ("Sharpe Ratio", "{:.3f}"),
    "sortino": ("Sortino Ratio", "{:.3f}"),
    "calmar": ("Calmar Ratio", "{:.3f}"),
    "max_drawdown": ("Max Drawdown", "{:.2%}"),
    "avg_drawdown": ("Avg Drawdown", "{:.2%}"),
    "win_rate": ("Win Rate", "{:.1%}"),
    "profit_factor": ("Profit Factor", "{:.2f}"),
    "avg_trade_duration_bars": ("Avg Trade Duration (bars)", "{:.1f}"),
    "turnover": ("Portfolio Turnover", "{:.4f}"),
    "avg_win": ("Avg Win (USD)", "${:,.2f}"),
    "avg_loss": ("Avg Loss (USD)", "${:,.2f}"),
    "largest_win": ("Largest Win (USD)", "${:,.2f}"),
    "largest_loss": ("Largest Loss (USD)", "${:,.2f}"),
}


def build_metrics_dataframe(
    scalar_metrics: dict[str, float],
    initial_capital_usd: float,
) -> pd.DataFrame:
    """Build a display-ready metrics DataFrame.

    Args:
        scalar_metrics: From PerformanceReport.scalar_metrics (16 keys).
        initial_capital_usd: From PerformanceReport.initial_capital_usd.
            This is the authoritative source — do not use
            scalar_metrics["initial_capital"] for display.

    Returns:
        pd.DataFrame with columns ["Metric", "Value"].
        Suitable for st.dataframe(df, hide_index=True).
    """
    rows: list[dict[str, str]] = []

    rows.append(
        {
            "Metric": "Initial Capital (USD)",
            "Value": f"${initial_capital_usd:,.0f}",
        }
    )

    for key, (label, fmt) in _METRIC_FORMAT.items():
        if key not in scalar_metrics:
            continue
        val = scalar_metrics[key]
        try:
            formatted = fmt.format(val)
        except (ValueError, TypeError):
            formatted = str(round(val, 6))
        rows.append({"Metric": label, "Value": formatted})

    return pd.DataFrame(rows)


def build_signal_metrics_dataframe(
    signal_metrics: dict[str, float],
) -> pd.DataFrame | None:
    """Build a display-ready signal metrics DataFrame from PerformanceReport.signal_metrics.

    Args:
        signal_metrics: From PerformanceReport.signal_metrics. May be empty dict.

    Returns:
        pd.DataFrame with columns ["Metric", "Value"], or None if signal_metrics is empty.
    """
    if not signal_metrics:
        return None

    rows: list[dict[str, str]] = []
    rows.append(
        {
            "Metric": "IC (1-bar forward)",
            "Value": f"{signal_metrics.get('ic', float('nan')):.4f}",
        }
    )
    rows.append(
        {"Metric": "ICIR", "Value": f"{signal_metrics.get('icir', float('nan')):.4f}"}
    )

    for horizon in (1, 2, 5, 10, 20):
        key = f"signal_decay_{horizon}"
        if key in signal_metrics:
            rows.append(
                {
                    "Metric": f"IC Decay ({horizon}-bar)",
                    "Value": f"{signal_metrics[key]:.4f}",
                }
            )

    return pd.DataFrame(rows)
