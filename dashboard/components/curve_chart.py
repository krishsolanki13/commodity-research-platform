"""Futures curve and term structure history chart components.

Pure functions — return Plotly Figures. No st.* calls.
Consumes FuturesCurve and list[TermStructureSnapshot] from Layer 5.
See ADR-008 (Dashboard Architecture).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.components._theme import (
    NAVY,
    NEGATIVE,
    POSITIVE,
    SLATE,
    STEEL,
    apply_base_layout,
)

if TYPE_CHECKING:
    from src.core.types import FuturesCurve, TermStructureSnapshot


def render_forward_curve_chart(
    curve: FuturesCurve,
    title: str = "Forward Curve",
    height: int = 380,
) -> go.Figure:
    """Render the futures forward curve as a bar chart with line overlay.

    Each bar represents one delivery contract's closing price. The line
    overlay shows the curve shape. Bar color encodes position:
      Navy  = nearest delivery contract (front month)
      Steel = deferred contracts

    Args:
        curve: FuturesCurve from FuturesCurveBuilder.build().
            May be empty (no contracts available) — returns blank chart.
        title: Chart title.
        height: Chart height in pixels.

    Returns:
        Plotly Figure. Render with: st.plotly_chart(fig)
    """
    fig = go.Figure()

    if curve.is_empty:
        apply_base_layout(fig, title)
        fig.update_layout(height=height)
        fig.add_annotation(
            text="No contract data available for this asset.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color=SLATE, size=12),
        )
        return fig

    tickers = [
        f"{p.metadata.month_code}{str(p.metadata.contract_year)[-2:]}"
        for p in curve.points
    ]
    prices = curve.prices
    dtds = [p.days_to_delivery for p in curve.points]

    line_color = POSITIVE if curve.is_contango else NEGATIVE
    colors = [NAVY] + [STEEL] * (len(prices) - 1)

    fig.add_trace(
        go.Bar(
            x=tickers,
            y=prices,
            marker_color=colors,
            marker_line_color="rgba(255,255,255,0.2)",
            marker_line_width=0.5,
            name="Contract Price",
            customdata=dtds,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Price: $%{y:,.2f}<br>"
                "Days to delivery: %{customdata}<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=tickers,
            y=prices,
            mode="lines+markers",
            line=dict(color=line_color, width=2),
            marker=dict(size=7, color=line_color, symbol="circle"),
            name="Curve",
            showlegend=False,
            hovertemplate="<b>%{x}</b>: $%{y:,.2f}<extra></extra>",
        )
    )

    apply_base_layout(fig, title)
    fig.update_layout(height=height, showlegend=False)
    fig.update_xaxes(title_text="Contract")
    fig.update_yaxes(title_text="Price (USD)", tickformat="$,.2f")
    return fig


def render_term_structure_history_chart(
    snapshots: list[TermStructureSnapshot],
    title: str = "Term Structure History",
    height: int = 380,
) -> go.Figure:
    """Render historical term structure analytics as a dual-subplot chart.

    Top panel: annualized contango/backwardation slope (% per year).
        Positive bars (green) = contango.
        Negative bars (red) = backwardation.

    Bottom panel: annualized roll yield (% per year).
        Positive bars (green) = backwardation (tailwind for longs).
        Negative bars (red) = contango (headwind for longs).

    Args:
        snapshots: List of TermStructureSnapshot from analyze_series().
            Snapshots with NaN metrics produce gaps in the chart.
        title: Chart title.
        height: Total chart height in pixels.

    Returns:
        Plotly Figure with two subplots.
    """
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.04,
        subplot_titles=["Annualized Slope (%/yr)", "Roll Yield (%/yr)"],
    )

    if not snapshots:
        apply_base_layout(fig, title)
        fig.update_layout(height=height)
        return fig

    dates = [s.observation_date for s in snapshots]

    slopes_pct = [
        s.annualized_slope_pct * 100.0
        if not math.isnan(s.annualized_slope_pct)
        else None
        for s in snapshots
    ]
    roll_yields_pct = [
        s.roll_yield_annualized * 100.0
        if not math.isnan(s.roll_yield_annualized)
        else None
        for s in snapshots
    ]

    slope_colors = [
        POSITIVE if (v is not None and v > 0) else NEGATIVE for v in slopes_pct
    ]
    roll_colors = [
        POSITIVE if (v is not None and v > 0) else NEGATIVE for v in roll_yields_pct
    ]

    fig.add_trace(
        go.Bar(
            x=dates,
            y=slopes_pct,
            marker_color=slope_colors,
            name="Slope",
            showlegend=False,
            hovertemplate="<b>%{x}</b><br>Slope: %{y:.2f}%/yr<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_hline(y=0, line_color=SLATE, line_width=0.8, row=1, col=1)

    fig.add_trace(
        go.Bar(
            x=dates,
            y=roll_yields_pct,
            marker_color=roll_colors,
            name="Roll Yield",
            showlegend=False,
            hovertemplate="<b>%{x}</b><br>Roll Yield: %{y:.2f}%/yr<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=0, line_color=SLATE, line_width=0.8, row=2, col=1)

    apply_base_layout(fig, title)
    fig.update_layout(height=height)
    fig.update_yaxes(title_text="%/yr", row=1, col=1)
    fig.update_yaxes(title_text="%/yr", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    return fig
