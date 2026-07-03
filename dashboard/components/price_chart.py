"""Price chart component: OHLCV candlestick with indicator overlays and volume.

Pure function — returns a Plotly Figure. No st.* calls.
See ADR-008 (Dashboard Architecture).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.components._theme import (
    CANDLE_DOWN,
    CANDLE_UP,
    FONT,
    NAVY,
    SLATE,
    STEEL,
    SURFACE,
    apply_base_layout,
)

_INDICATOR_COLORS = [NAVY, STEEL, "#9467bd", "#ff7f0e", "#17becf"]


def render_price_chart(
    ohlcv: pd.DataFrame,
    title: str = "Price",
    indicator_columns: list[str] | None = None,
    height: int = 520,
) -> go.Figure:
    """Render OHLCV candlestick chart with indicator overlays and volume subplot.

    Args:
        ohlcv: NormalizedOHLCV DataFrame from DataLoader.load() or
            FeatureFrame.data (contains OHLCV plus indicator columns).
        title: Chart title.
        indicator_columns: Column names in ohlcv to overlay as lines.
            Columns not present in ohlcv are silently skipped.
        height: Total chart height in pixels.

    Returns:
        Plotly Figure. Render with: st.plotly_chart(fig)
    """
    indicator_columns = indicator_columns or []
    has_volume = "volume" in ohlcv.columns

    if has_volume:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.80, 0.20],
            vertical_spacing=0.02,
        )
        price_row, vol_row = 1, 2
    else:
        fig = go.Figure()
        price_row, vol_row = None, None

    # Candlestick
    candle_kwargs = dict(
        x=ohlcv.index,
        open=ohlcv["open"],
        high=ohlcv["high"],
        low=ohlcv["low"],
        close=ohlcv["close"],
        name="Price",
        increasing_line_color=CANDLE_UP,
        decreasing_line_color=CANDLE_DOWN,
        increasing_fillcolor=CANDLE_UP,
        decreasing_fillcolor=CANDLE_DOWN,
        showlegend=False,
        line_width=1,
    )
    if has_volume:
        fig.add_trace(go.Candlestick(**candle_kwargs), row=price_row, col=1)
    else:
        fig.add_trace(go.Candlestick(**candle_kwargs))

    # Indicator overlays
    for i, col in enumerate(indicator_columns):
        if col not in ohlcv.columns:
            continue
        overlay_kwargs = dict(
            x=ohlcv.index,
            y=ohlcv[col],
            name=col.upper().replace("_", " "),
            line=dict(
                color=_INDICATOR_COLORS[i % len(_INDICATOR_COLORS)],
                width=1.5,
            ),
            opacity=0.90,
        )
        if has_volume:
            fig.add_trace(go.Scatter(**overlay_kwargs), row=price_row, col=1)
        else:
            fig.add_trace(go.Scatter(**overlay_kwargs))

    # Volume bars
    if has_volume:
        fig.add_trace(
            go.Bar(
                x=ohlcv.index,
                y=ohlcv["volume"],
                name="Volume",
                marker_color=SLATE,
                marker_opacity=0.45,
                showlegend=False,
            ),
            row=vol_row,
            col=1,
        )
        fig.update_yaxes(title_text="Volume", row=vol_row, col=1)
        fig.update_yaxes(
            title_text="Price (USD)",
            tickformat=",.2f",
            row=price_row,
            col=1,
        )
    else:
        fig.update_yaxes(title_text="Price (USD)", tickformat=",.2f")

    # Range selector on the bottom x-axis
    range_selector = dict(
        buttons=[
            dict(count=1, label="1M", step="month", stepmode="backward"),
            dict(count=3, label="3M", step="month", stepmode="backward"),
            dict(count=6, label="6M", step="month", stepmode="backward"),
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(step="all", label="All"),
        ],
        bgcolor=SURFACE,
        activecolor=NAVY,
        bordercolor="#cccccc",
        borderwidth=1,
        font=dict(family=FONT, size=10),
        x=0,
        y=1.0,
    )
    if has_volume:
        fig.update_xaxes(
            rangeselector=range_selector,
            rangeslider_visible=False,
            row=vol_row,
            col=1,
        )
    else:
        fig.update_xaxes(rangeselector=range_selector, rangeslider_visible=False)

    apply_base_layout(fig, title)
    fig.update_layout(
        height=height,
        showlegend=len(indicator_columns) > 0,
    )
    return fig
