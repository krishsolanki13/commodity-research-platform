"""Correlation heatmap and rolling correlation chart components.

Pure functions — return Plotly Figures. No st.* calls.
Consumes CorrelationReport from Layer 7 (CorrelationEngine).

Upper-triangle rolling lookup (TD-M17-A):
    rolling_correlations_63[a][b] only exists when a < b alphabetically.
    For any requested pair (x, y), always access via:
        a, b = min(x, y), max(x, y)
    Components handle this internally — callers may pass pairs in any order.

Realized volatility labeling:
    realized_vol_by_asset values are STRATEGY return vols (2-8%/yr for EMA 50/200)
    NOT commodity price vols (15-60%/yr). Labels explicitly say "Strategy Realized Vol".

See ADR-008 (Dashboard Architecture) and Module 17 handoff notes.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import plotly.graph_objects as go

from dashboard.components._theme import (
    SLATE,
    apply_base_layout,
)

if TYPE_CHECKING:
    from src.core.types import CorrelationReport


def render_correlation_heatmap(
    report: CorrelationReport,
    title: str = "Correlation Matrix",
    height: int = 460,
) -> go.Figure:
    """Render a symmetric pairwise correlation matrix as a Plotly heatmap.

    Color encoding:
        Teal-green (#00c896): high positive correlation
        Navy (#0e1628): near-zero correlation
        Red (#ff4757): high negative correlation

    Annotations: numeric correlation values displayed in each cell.
    Diagonal cells always show 1.00.

    Args:
        report: CorrelationReport from CorrelationEngine.compute().
        title: Chart title.
        height: Figure height in pixels.

    Returns:
        Plotly Figure. Render with: st.plotly_chart(fig)
    """
    fig = go.Figure()

    if not report.assets or not report.correlation_matrix:
        apply_base_layout(fig, title)
        fig.update_layout(height=height)
        fig.add_annotation(
            text="No correlation data available.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color=SLATE, size=12),
        )
        return fig

    assets = sorted(report.assets)

    # Build 2D matrix (sorted assets × sorted assets)
    z_matrix: list[list[float | None]] = []
    text_matrix: list[list[str]] = []

    for a in assets:
        z_row: list[float | None] = []
        text_row: list[str] = []
        for b in assets:
            val = report.get_correlation(a, b)
            z_row.append(val if not math.isnan(val) else None)
            text_row.append(f"{val:.2f}" if not math.isnan(val) else "n/a")
        z_matrix.append(z_row)
        text_matrix.append(text_row)

    # Diverging colorscale: red → navy → teal
    colorscale = [
        [0.0, "#ff4757"],  # strong negative
        [0.25, "#a0253d"],
        [0.5, "#162033"],  # near-zero (dark navy)
        [0.75, "#006b52"],
        [1.0, "#00c896"],  # strong positive
    ]

    fig.add_trace(
        go.Heatmap(
            z=z_matrix,
            x=assets,
            y=assets,
            text=text_matrix,
            texttemplate="%{text}",
            textfont=dict(size=11, color="white"),
            colorscale=colorscale,
            zmin=-1.0,
            zmax=1.0,
            zmid=0.0,
            showscale=True,
            colorbar=dict(
                title=dict(text="Corr", font=dict(color=SLATE, size=10)),
                thickness=12,
                len=0.8,
                tickvals=[-1, -0.5, 0, 0.5, 1],
                tickfont=dict(color=SLATE, size=10),
            ),
            hovertemplate=("<b>%{x} / %{y}</b><br>Correlation: %{text}<extra></extra>"),
        )
    )

    apply_base_layout(fig, title)
    fig.update_layout(
        height=height,
        xaxis=dict(tickfont=dict(size=10), side="bottom"),
        yaxis=dict(tickfont=dict(size=10), autorange="reversed"),
    )
    return fig


def render_rolling_correlation_chart(
    report: CorrelationReport,
    pairs: list[tuple[str, str]] | None = None,
    window: int = 63,
    title: str | None = None,
    height: int = 380,
) -> go.Figure:
    """Render rolling pairwise correlations over time as a line chart.

    Upper-triangle TD-M17-A: rolling_correlations_63[a][b] only exists
    when a < b alphabetically. This function handles pair order automatically —
    callers may pass pairs in any order; the lookup is always done correctly.

    Args:
        report: CorrelationReport from CorrelationEngine.compute().
        pairs: List of (asset_a, asset_b) pairs to plot. If None, plots
            the three most informative pairs: (gold, silver),
            (wti, brent), and (gold, wti).
        window: Rolling window size — 63 or 126. Must match one of the
            windows computed in CorrelationEngine.compute().
        title: Chart title. If None, auto-generated from window size.
        height: Figure height in pixels.

    Returns:
        Plotly Figure. Render with: st.plotly_chart(fig)
    """
    if title is None:
        title = f"Rolling {window}-Day Correlations"

    fig = go.Figure()

    # Default pairs: one same-sector, one crude pair, one cross-sector
    if pairs is None:
        candidate_pairs = [
            ("gold", "silver"),
            ("wti", "brent"),
            ("gold", "wti"),
        ]
        pairs = [
            (a, b)
            for a, b in candidate_pairs
            if a in report.assets and b in report.assets
        ]

    if not pairs:
        apply_base_layout(fig, title)
        fig.update_layout(height=height)
        fig.add_annotation(
            text="No asset pairs available for rolling correlation display.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color=SLATE, size=12),
        )
        return fig

    # Select the correct rolling dict based on window size
    if window == 63:
        rolling_dict = report.rolling_correlations_63
    elif window == 126:
        rolling_dict = report.rolling_correlations_126
    else:
        # Fall back to 63-day if unknown window requested
        rolling_dict = report.rolling_correlations_63

    # Series palette: teal, amber, red, blue, green, purple
    palette = ["#00c896", "#ffa502", "#ff4757", "#4a9eff", "#7bed9f", "#a29bfe"]

    for idx, (x, y) in enumerate(pairs):
        # TD-M17-A: always look up in sorted order (a < b alphabetically)
        a, b = (x, y) if x < y else (y, x)

        series = rolling_dict.get(a, {}).get(b)
        if series is None or series.empty:
            continue

        label = f"{x} / {y}"
        color = palette[idx % len(palette)]

        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode="lines",
                name=label,
                line=dict(color=color, width=1.5),
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "Date: %{x}<br>"
                    "Rolling Corr: %{y:.3f}<extra></extra>"
                ),
            )
        )

    # Zero line for reference
    fig.add_hline(y=0, line_color=SLATE, line_width=0.8, line_dash="dot")

    apply_base_layout(fig, title)
    fig.update_layout(
        height=height,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0.0,
            font=dict(size=10),
        ),
    )
    fig.update_yaxes(title_text="Correlation", range=[-1.05, 1.05], tickformat=".2f")
    fig.update_xaxes(title_text="Date")
    return fig
