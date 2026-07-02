"""Price chart component: OHLCV candlestick with indicator line overlays.

Pure function — returns a Plotly Figure. No st.* calls.
All data pre-computed by src/ layer calls before this function is invoked.
See ADR-008 (Dashboard Architecture).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

_INDICATOR_COLORS = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
]


def render_price_chart(
    ohlcv: pd.DataFrame,
    title: str = "Price Chart",
    indicator_columns: list[str] | None = None,
    height: int = 500,
) -> go.Figure:
    """Render OHLCV candlestick chart with optional indicator overlays.

    Args:
        ohlcv: NormalizedOHLCV DataFrame from DataLoader.load(), or
            FeatureFrame.data (which contains all OHLCV columns plus indicators).
        title: Chart title string.
        indicator_columns: Column names present in ohlcv to overlay as lines.
            Typically EMA/SMA column names from FeatureFrame.data.
            Columns not found in ohlcv are silently skipped.
        height: Chart height in pixels.

    Returns:
        Plotly Figure. Render with: st.plotly_chart(fig, use_container_width=True)
    """
    indicator_columns = indicator_columns or []

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=ohlcv.index,
            open=ohlcv["open"],
            high=ohlcv["high"],
            low=ohlcv["low"],
            close=ohlcv["close"],
            name="OHLCV",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
            showlegend=True,
        )
    )

    for i, col in enumerate(indicator_columns):
        if col not in ohlcv.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=ohlcv.index,
                y=ohlcv[col],
                name=col.upper().replace("_", " "),
                line={
                    "color": _INDICATOR_COLORS[i % len(_INDICATOR_COLORS)],
                    "width": 1.5,
                },
                opacity=0.85,
            )
        )

    fig.update_layout(
        title=title,
        height=height,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        template="plotly_white",
        margin={"t": 50, "b": 20, "l": 20, "r": 20},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    fig.update_xaxes(title="Date")
    fig.update_yaxes(title="Price (USD)")

    return fig
