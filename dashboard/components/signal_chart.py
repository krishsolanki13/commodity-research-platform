"""Signal visualization chart component.

Pure function — returns a Plotly Figure. No st.* calls.
See ADR-008 (Dashboard Architecture).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_signal_chart(
    close_prices: pd.Series,
    raw_signal: pd.Series,
    position_signal: pd.Series | None = None,
    title: str = "Signal Analysis",
    height: int = 420,
) -> go.Figure:
    """Render close price (top) and raw signal (bottom) with position markers.

    Args:
        close_prices: Close price Series from NormalizedOHLCV["close"].
        raw_signal: RawSignal pd.Series from SignalGenerator.generate().
        position_signal: Optional PositionSignal {-1, 0, +1} Series.
            Long markers (▲) and short markers (▽) overlaid on price.
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
        vertical_spacing=0.06,
        subplot_titles=["Close Price + Positions", "Raw Signal"],
    )

    fig.add_trace(
        go.Scatter(
            x=close_prices.index,
            y=close_prices.values,
            name="Close",
            line={"color": "#555555", "width": 1.2},
        ),
        row=1,
        col=1,
    )

    if position_signal is not None:
        long_mask = position_signal == 1
        short_mask = position_signal == -1
        if long_mask.any():
            fig.add_trace(
                go.Scatter(
                    x=close_prices.index[long_mask],
                    y=close_prices.values[long_mask],
                    mode="markers",
                    name="Long",
                    marker={
                        "color": "#26a69a",
                        "size": 6,
                        "symbol": "triangle-up",
                    },
                ),
                row=1,
                col=1,
            )
        if short_mask.any():
            fig.add_trace(
                go.Scatter(
                    x=close_prices.index[short_mask],
                    y=close_prices.values[short_mask],
                    mode="markers",
                    name="Short",
                    marker={
                        "color": "#ef5350",
                        "size": 6,
                        "symbol": "triangle-down",
                    },
                ),
                row=1,
                col=1,
            )

    fig.add_trace(
        go.Scatter(
            x=raw_signal.index,
            y=raw_signal.values,
            name="Raw Signal",
            line={"color": "#1f77b4", "width": 1.5},
            fill="tozeroy",
            fillcolor="rgba(31, 119, 180, 0.10)",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(
        y=0, line_dash="dash", line_color="#aaaaaa", line_width=1, row=2, col=1
    )

    fig.update_layout(
        title=title,
        height=height,
        showlegend=True,
        template="plotly_white",
        margin={"t": 50, "b": 20, "l": 20, "r": 20},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
    fig.update_yaxes(title_text="Signal", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)

    return fig
