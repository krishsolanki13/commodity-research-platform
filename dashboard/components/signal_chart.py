"""Signal chart and IC decay chart components.

Pure functions — return Plotly Figures. No st.* calls.
See ADR-008 (Dashboard Architecture).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.components._theme import (
    CAUTION,
    FONT,
    LONG_FILL,
    LONG_LINE,
    NAVY,
    NEGATIVE,
    POSITIVE,
    SHORT_FILL,
    SHORT_LINE,
    SLATE,
    apply_base_layout,
)


def render_signal_chart(
    close_prices: pd.Series,
    raw_signal: pd.Series,
    position_signal: pd.Series | None = None,
    title: str = "Signal Analysis",
    height: int = 440,
) -> go.Figure:
    """Render close price with holding period bands (top) and raw signal (bottom).

    Position signal is rendered as translucent holding period bands rather than
    scatter markers — the standard institutional convention for showing trade
    entry/exit on price charts. Green bands for long periods, red for short.
    Individual scatter markers are unreadable when 50+ trades are displayed.

    Args:
        close_prices: Close price Series from NormalizedOHLCV["close"].
        raw_signal: RawSignal pd.Series from SignalGenerator.generate().
        position_signal: Optional PositionSignal {-1, 0, +1} Series.
        title: Chart title.
        height: Chart height in pixels.

    Returns:
        Plotly Figure with price (top) and signal (bottom) subplots.
    """
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.04,
        subplot_titles=["Close Price + Holding Periods", "Raw Signal"],
    )

    # Close price line
    fig.add_trace(
        go.Scatter(
            x=close_prices.index,
            y=close_prices.values,
            name="Close",
            line=dict(color=SLATE, width=1.2),
            showlegend=True,
        ),
        row=1,
        col=1,
    )

    # Holding period bands (institutional style)
    if position_signal is not None and len(position_signal) > 0:
        _add_holding_period_bands(fig, close_prices, position_signal, row=1, col=1)

    # Raw signal with +/- 1 std reference bands
    fig.add_trace(
        go.Scatter(
            x=raw_signal.index,
            y=raw_signal.values,
            name="Raw Signal",
            line=dict(color=NAVY, width=1.5),
            fill="tozeroy",
            fillcolor="rgba(26, 58, 92, 0.08)",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color=SLATE,
        line_width=0.8,
        row=2,
        col=1,
    )

    # +/- 1 standard deviation reference
    valid_signal = raw_signal.dropna()
    if len(valid_signal) > 1:
        std = float(valid_signal.std())
        for y_val, color in [(std, POSITIVE), (-std, NEGATIVE)]:
            fig.add_hline(
                y=y_val,
                line_dash="dot",
                line_color=color,
                line_width=0.7,
                annotation_text=f"±1σ ({y_val:+.3f})",
                annotation_font=dict(size=8, color=SLATE),
                row=2,
                col=1,
            )

    apply_base_layout(fig, title)
    fig.update_layout(height=height, showlegend=True)
    fig.update_yaxes(title_text="Price (USD)", tickformat=",.2f", row=1, col=1)
    fig.update_yaxes(title_text="Signal", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    return fig


def render_ic_decay_chart(
    ic_decay: dict[int, float],
    height: int = 250,
) -> go.Figure:
    """Render IC decay bar chart with color encoding by IC magnitude threshold.

    Color encoding:
        Green  (POSITIVE) : |IC| >= 0.05 (meaningful)
        Amber  (CAUTION)  : 0.02 <= |IC| < 0.05 (weak)
        Red    (NEGATIVE) : |IC| < 0.02 (noise)

    Args:
        ic_decay: Dict mapping forward horizon (int) to IC at that horizon.
            Keys: {1, 2, 5, 10, 20} per SignalEvaluation.ic_decay contract.
        height: Chart height in pixels.

    Returns:
        Plotly Figure. Render with: st.plotly_chart(fig, use_container_width=True)
    """
    horizons = sorted(ic_decay.keys())
    values = [ic_decay[h] for h in horizons]
    colors = [
        POSITIVE
        if v >= 0.05
        else (
            CAUTION
            if v >= 0.02
            else (NEGATIVE if v > -0.02 else (CAUTION if v > -0.05 else NEGATIVE))
        )
        for v in values
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[f"{h}b" for h in horizons],
            y=values,
            marker_color=colors,
            marker_line_color="white",
            marker_line_width=0.5,
            text=[f"{v:.4f}" for v in values],
            textposition="outside",
            textfont=dict(family=FONT, size=10),
        )
    )
    fig.add_hline(y=0, line_color=SLATE, line_width=0.8)
    fig.add_hline(y=0.05, line_dash="dot", line_color=POSITIVE, line_width=0.7)
    fig.add_hline(y=-0.05, line_dash="dot", line_color=POSITIVE, line_width=0.7)
    fig.add_hline(y=0.02, line_dash="dot", line_color=CAUTION, line_width=0.7)
    fig.add_hline(y=-0.02, line_dash="dot", line_color=CAUTION, line_width=0.7)

    apply_base_layout(fig, "IC Decay by Forward Horizon")
    fig.update_layout(height=height, showlegend=False)
    fig.update_xaxes(title_text="Forward Horizon")
    fig.update_yaxes(title_text="IC", tickformat=".4f")
    return fig


def _add_holding_period_bands(
    fig: go.Figure,
    close_prices: pd.Series,
    position_signal: pd.Series,
    row: int,
    col: int,
) -> None:
    """Add translucent holding period bands to a price chart subplot.

    Long periods: translucent green band.
    Short periods: translucent red band.
    Operates on the aligned index of close_prices and position_signal.
    """
    if position_signal.empty:
        return

    aligned, _ = position_signal.align(close_prices, join="inner")
    if aligned.empty:
        return

    prev_dir = 0
    trade_start: pd.Timestamp | None = None
    legend_shown = {"long": False, "short": False}

    for timestamp, direction in aligned.items():
        direction = int(direction)
        if direction != prev_dir:
            # Close the previous band
            if prev_dir != 0 and trade_start is not None:
                fill = LONG_FILL if prev_dir == 1 else SHORT_FILL
                line = LONG_LINE if prev_dir == 1 else SHORT_LINE
                name = "Long" if prev_dir == 1 else "Short"
                show = not legend_shown[name.lower()]
                legend_shown[name.lower()] = True
                fig.add_vrect(
                    x0=trade_start,
                    x1=timestamp,
                    fillcolor=fill,
                    line_width=0.8,
                    line_color=line,
                    name=name,
                    showlegend=show,
                    row=row,
                    col=col,
                )
            trade_start = timestamp if direction != 0 else None
            prev_dir = direction

    # Close any open band at the end of the series
    if prev_dir != 0 and trade_start is not None:
        last_ts = aligned.index[-1]
        fill = LONG_FILL if prev_dir == 1 else SHORT_FILL
        line = LONG_LINE if prev_dir == 1 else SHORT_LINE
        fig.add_vrect(
            x0=trade_start,
            x1=last_ts,
            fillcolor=fill,
            line_width=0.8,
            line_color=line,
            showlegend=False,
            row=row,
            col=col,
        )
