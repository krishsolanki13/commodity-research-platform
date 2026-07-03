"""Metrics table components: structured display of PerformanceReport data.

Pure functions — return pd.DataFrame or pd.Styler objects. No st.* calls.
Caller passes the result to st.dataframe() or st.table().

Note on initial_capital: use PerformanceReport.initial_capital_usd as the
authoritative source. Do not use scalar_metrics["initial_capital"].
See Module 6 implementation notes for the rationale.
See ADR-008 (Dashboard Architecture).
"""

from __future__ import annotations

import pandas as pd

# ── Metric display configuration ─────────────────────────────────────────────
# Format: {key: (display_label, format_string)}
# Keys match PerformanceReport.scalar_metrics exactly.

_METRIC_GROUPS: dict[str, list[tuple[str, str, str]]] = {
    "Risk-Adjusted Performance": [
        ("sharpe", "Sharpe Ratio", "{:.4f}"),
        ("sortino", "Sortino Ratio", "{:.4f}"),
        ("calmar", "Calmar Ratio", "{:.4f}"),
    ],
    "Return": [
        ("total_return", "Total Return", "{:+.2%}"),
        ("cagr", "CAGR", "{:+.2%}"),
    ],
    "Drawdown": [
        ("max_drawdown", "Max Drawdown", "{:.2%}"),
        ("avg_drawdown", "Avg Drawdown", "{:.2%}"),
    ],
    "Trade Statistics": [
        ("win_rate", "Win Rate", "{:.1%}"),
        ("profit_factor", "Profit Factor", "{:.4f}"),
        ("avg_trade_duration_bars", "Avg Trade Duration (bars)", "{:.1f}"),
        ("avg_win", "Avg Win (USD)", "${:>12,.2f}"),
        ("avg_loss", "Avg Loss (USD)", "${:>12,.2f}"),
        ("largest_win", "Largest Win (USD)", "${:>12,.2f}"),
        ("largest_loss", "Largest Loss (USD)", "${:>12,.2f}"),
    ],
    "Portfolio Activity": [
        ("turnover", "Portfolio Turnover", "{:.6f}"),
    ],
}


def build_metrics_dataframe(
    scalar_metrics: dict[str, float],
    initial_capital_usd: float,
) -> pd.DataFrame:
    """Build a display-ready scalar metrics DataFrame.

    Groups metrics into sections. Risk-Adjusted Performance appears first.
    Initial Capital uses the top-level report field, not scalar_metrics.

    Args:
        scalar_metrics: From PerformanceReport.scalar_metrics.
        initial_capital_usd: From PerformanceReport.initial_capital_usd.
            This is the authoritative source — not scalar_metrics["initial_capital"].

    Returns:
        pd.DataFrame with columns ["Metric", "Value"].
        Use with: st.dataframe(df, hide_index=True)
    """
    rows: list[dict[str, str]] = []

    # Initial capital — from top-level field
    rows.append(
        {
            "Metric": "Initial Capital (USD)",
            "Value": f"${initial_capital_usd:>14,.0f}",
        }
    )

    for group_name, metrics in _METRIC_GROUPS.items():
        rows.append({"Metric": f"— {group_name} —", "Value": ""})
        for key, label, fmt in metrics:
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
    """Build a display-ready signal metrics DataFrame.

    Args:
        signal_metrics: From PerformanceReport.signal_metrics.
            May be empty dict if signal_evaluation was None.

    Returns:
        pd.DataFrame with columns ["Metric", "Value"],
        or None if signal_metrics is empty.
    """
    if not signal_metrics:
        return None

    rows: list[dict[str, str]] = [
        {
            "Metric": "IC (1-bar forward)",
            "Value": f"{signal_metrics.get('ic', float('nan')):.6f}",
        },
        {"Metric": "ICIR", "Value": f"{signal_metrics.get('icir', float('nan')):.6f}"},
    ]
    for horizon in (1, 2, 5, 10, 20):
        key = f"signal_decay_{horizon}"
        if key in signal_metrics:
            rows.append(
                {
                    "Metric": f"IC Decay ({horizon}-bar forward)",
                    "Value": f"{signal_metrics[key]:.6f}",
                }
            )

    return pd.DataFrame(rows)


def style_return_series(df: pd.DataFrame, columns: list[str]) -> object:
    """Apply color styling to return columns in a summary DataFrame.

    Args:
        df: DataFrame containing numeric-string return columns.
        columns: Column names to apply color to.

    Returns:
        pandas Styler object ready for st.dataframe().
    """

    def _color(val: str) -> str:
        try:
            num = float(
                str(val)
                .replace("+", "")
                .replace("%", "")
                .replace("—", "0")
                .replace(",", "")
                .strip()
            )
            if num > 0:
                return "color: #2d6a4f; font-weight: 600"
            if num < 0:
                return "color: #a61c00; font-weight: 600"
        except ValueError:
            pass
        return ""

    return df.style.map(_color, subset=columns)
