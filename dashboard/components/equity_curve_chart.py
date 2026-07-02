"""Equity curve and drawdown chart components.

Pure functions — return Plotly Figures. No st.* calls.
See ADR-008 (Dashboard Architecture).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_equity_curve_chart(
    equity_curve: pd.Series,
    initial_capital: float,
    title: str = "Equity Curve",
    height: int = 420,
) -> go.Figure:
    """Render equity curve (top) with drawdown shading (bottom).

    Args:
        equity_curve: From BacktestResult.equity_curve.
        initial_capital: From PerformanceReport.initial_capital_usd.
            Use the top-level field, not scalar_metrics["initial_capital"].
        title: Chart title.
        height: Total chart height in pixels.

    Returns:
        Plotly Figure with two subplots: equity (70%) and drawdown (30%).
    """
    rolling_max = equity_curve.cummax()
    drawdown_pct = (equity_curve - rolling_max) / rolling_max * 100.0

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.04,
        subplot_titles=["Equity (USD)", "Drawdown (%)"],
    )

    fig.add_trace(
        go.Scatter(
            x=equity_curve.index,
            y=equity_curve.values,
            name="Equity",
            line={"color": "#1f77b4", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(31, 119, 180, 0.08)",
        ),
        row=1,
        col=1,
    )

    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color="#aaaaaa",
        line_width=1,
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=drawdown_pct.index,
            y=drawdown_pct.values,
            name="Drawdown (%)",
            line={"color": "#ef5350", "width": 1},
            fill="tozeroy",
            fillcolor="rgba(239, 83, 80, 0.15)",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=title,
        height=height,
        showlegend=False,
        template="plotly_white",
        margin={"t": 50, "b": 20, "l": 20, "r": 20},
    )
    fig.update_yaxes(title_text="USD", row=1, col=1)
    fig.update_yaxes(title_text="Pct", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)

    return fig


def render_rolling_metrics_chart(
    rolling_sharpe: pd.Series,
    rolling_drawdown: pd.Series,
    title: str = "Rolling Metrics",
    height: int = 380,
) -> go.Figure:
    """Render rolling Sharpe (top) and rolling drawdown (bottom).

    Args:
        rolling_sharpe: From PerformanceReport.rolling_metrics["rolling_sharpe_63"].
        rolling_drawdown: From PerformanceReport.rolling_metrics["rolling_drawdown"].
        title: Chart title.
        height: Total chart height in pixels.

    Returns:
        Plotly Figure with two subplots.
    """
    dd_pct = rolling_drawdown * 100.0

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.5],
        vertical_spacing=0.06,
        subplot_titles=["Rolling Sharpe (63-bar)", "Rolling Drawdown (%)"],
    )

    fig.add_trace(
        go.Scatter(
            x=rolling_sharpe.index,
            y=rolling_sharpe.values,
            name="Rolling Sharpe",
            line={"color": "#2ca02c", "width": 1.5},
        ),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=0, line_dash="dash", line_color="#aaaaaa", line_width=1, row=1, col=1
    )
    fig.add_hline(
        y=0.5, line_dash="dot", line_color="#1f77b4", line_width=1, row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=dd_pct.index,
            y=dd_pct.values,
            name="Drawdown (%)",
            line={"color": "#ef5350", "width": 1},
            fill="tozeroy",
            fillcolor="rgba(239, 83, 80, 0.12)",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=title,
        height=height,
        showlegend=False,
        template="plotly_white",
        margin={"t": 50, "b": 20, "l": 20, "r": 20},
    )
    fig.update_yaxes(title_text="Sharpe", row=1, col=1)
    fig.update_yaxes(title_text="Pct", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)

    return fig
