"""Equity curve and rolling metrics chart components.

Pure functions — return Plotly Figures. No st.* calls.
See ADR-008 (Dashboard Architecture).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.components._theme import (
    CAUTION,
    NAVY,
    NEGATIVE,
    POSITIVE,
    SLATE,
    apply_base_layout,
)


def render_equity_curve_chart(
    equity_curve: pd.Series,
    initial_capital: float,
    title: str = "Equity Curve",
    height: int = 440,
) -> go.Figure:
    """Render equity curve (70%) with drawdown (30%) subplot.

    Args:
        equity_curve: From BacktestResult.equity_curve.
        initial_capital: From PerformanceReport.initial_capital_usd.
            Use the top-level field — not scalar_metrics["initial_capital"].
        title: Chart title.
        height: Total chart height in pixels.

    Returns:
        Plotly Figure with equity (top) and drawdown percentage (bottom).
    """
    rolling_max = equity_curve.cummax()
    drawdown_pct = (equity_curve - rolling_max) / rolling_max * 100.0
    avg_dd_pct = (
        float(drawdown_pct[drawdown_pct < 0].mean())
        if (drawdown_pct < 0).any()
        else 0.0
    )

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.68, 0.32],
        vertical_spacing=0.04,
        subplot_titles=["Equity (USD)", "Drawdown (%)"],
    )

    # Equity curve
    fig.add_trace(
        go.Scatter(
            x=equity_curve.index,
            y=equity_curve.values,
            name="Equity",
            line=dict(color=NAVY, width=2),
            fill="tozeroy",
            fillcolor="rgba(26, 58, 92, 0.06)",
        ),
        row=1,
        col=1,
    )
    # Initial capital reference line
    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color=SLATE,
        line_width=1,
        annotation_text=f"Initial ${initial_capital:,.0f}",
        annotation_font=dict(size=9, color=SLATE),
        row=1,
        col=1,
    )

    # Drawdown
    fig.add_trace(
        go.Scatter(
            x=drawdown_pct.index,
            y=drawdown_pct.values,
            name="Drawdown",
            line=dict(color=NEGATIVE, width=1),
            fill="tozeroy",
            fillcolor="rgba(166, 28, 0, 0.12)",
        ),
        row=2,
        col=1,
    )
    # Average drawdown reference line
    if avg_dd_pct < 0:
        fig.add_hline(
            y=avg_dd_pct,
            line_dash="dot",
            line_color=CAUTION,
            line_width=1,
            annotation_text=f"Avg {avg_dd_pct:.1f}%",
            annotation_font=dict(size=9, color=CAUTION),
            row=2,
            col=1,
        )

    apply_base_layout(fig, title)
    fig.update_layout(height=height, showlegend=False)
    fig.update_yaxes(title_text="USD", tickformat="$,.0f", row=1, col=1)
    fig.update_yaxes(title_text="%", tickformat=".1f", row=2, col=1)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    return fig


def render_rolling_metrics_chart(
    rolling_sharpe: pd.Series,
    rolling_drawdown: pd.Series,
    title: str = "Rolling Performance",
    height: int = 400,
) -> go.Figure:
    """Render rolling Sharpe (62%) and rolling drawdown (38%) with zone encoding.

    Rolling Sharpe is color-coded by performance zone:
        Green  (POSITIVE) : Sharpe >= 1.0
        Amber  (CAUTION)  : 0.5 <= Sharpe < 1.0
        Red    (NEGATIVE) : Sharpe < 0.5

    Args:
        rolling_sharpe: From PerformanceReport.rolling_metrics["rolling_sharpe_63"].
        rolling_drawdown: From PerformanceReport.rolling_metrics["rolling_drawdown"].
        title: Chart title.
        height: Total chart height in pixels.

    Returns:
        Plotly Figure with two subplots.
    """
    dd_pct = rolling_drawdown * 100.0
    sharpe_valid = rolling_sharpe.dropna()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.62, 0.38],
        vertical_spacing=0.04,
        subplot_titles=["Rolling Sharpe (63-bar)", "Rolling Drawdown (%)"],
    )

    # Shaded inadequate Sharpe band [0, 0.5]
    fig.add_hrect(
        y0=0,
        y1=0.5,
        fillcolor="rgba(181, 99, 10, 0.06)",
        line_width=0,
        row=1,
        col=1,
    )

    # Color-segmented rolling Sharpe
    for threshold_high, threshold_low, color, label in [
        (None, 1.0, POSITIVE, "Sharpe >= 1.0"),
        (1.0, 0.5, CAUTION, "Sharpe 0.5-1.0"),
        (0.5, None, NEGATIVE, "Sharpe < 0.5"),
    ]:
        if threshold_high is not None and threshold_low is not None:
            mask = (sharpe_valid >= threshold_low) & (sharpe_valid < threshold_high)
        elif threshold_high is None:
            mask = sharpe_valid >= threshold_low
        else:
            mask = sharpe_valid < threshold_high

        segment = sharpe_valid.where(mask)
        fig.add_trace(
            go.Scatter(
                x=segment.index,
                y=segment.values,
                name=label,
                line=dict(color=color, width=1.5),
                connectgaps=False,
                showlegend=bool(segment.notna().any()),
            ),
            row=1,
            col=1,
        )

    # Reference lines on Sharpe panel
    for y_val, dash, color, _ in [
        (0.0, "dash", SLATE, None),
        (0.5, "dot", CAUTION, "0.5 threshold"),
        (1.0, "dot", POSITIVE, "1.0 threshold"),
    ]:
        fig.add_hline(
            y=y_val,
            line_dash=dash,
            line_color=color,
            line_width=0.8,
            row=1,
            col=1,
        )

    # Rolling drawdown
    fig.add_trace(
        go.Scatter(
            x=dd_pct.index,
            y=dd_pct.values,
            name="Drawdown",
            line=dict(color=NEGATIVE, width=1),
            fill="tozeroy",
            fillcolor="rgba(166, 28, 0, 0.10)",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    apply_base_layout(fig, title)
    fig.update_layout(height=height)
    fig.update_yaxes(title_text="Sharpe", row=1, col=1)
    fig.update_yaxes(title_text="%", tickformat=".1f", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    return fig
