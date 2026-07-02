"""Unified chart theme for the Commodity Systematic Research Platform.

All chart components import COLOR constants and apply_base_layout() from
this module. One change here propagates to every chart in the dashboard.

Design principles:
    - Deep navy / slate primary palette — institutional, not consumer
    - Color encodes meaning: green=positive, red=negative, navy=primary series
    - Monospace font on all chart labels for numerical alignment
    - Thin gridlines — present but not visually dominant
    - No decorative elements

Usage in component files:
    from dashboard.components._theme import (
        NAVY, POSITIVE, NEGATIVE, CAUTION, GRID, FONT,
        apply_base_layout,
    )
"""

from __future__ import annotations

# ── Palette ──────────────────────────────────────────────────────────────────

NAVY = "#1a3a5c"  # primary series, strong borders, titles
STEEL = "#4a7fb5"  # secondary series, reference lines
SLATE = "#6c757d"  # muted text, axis labels, tertiary context
POSITIVE = "#2d6a4f"  # gains, long positions, IC pass (|IC| ≥ 0.05)
NEGATIVE = "#a61c00"  # losses, short positions, IC noise (|IC| < 0.02)
CAUTION = "#b5630a"  # IC weak zone, Sharpe < 0.5 band, warnings
GRID = "#e2e8f0"  # gridlines
SURFACE = "#f4f6f8"  # sidebar panel backgrounds, range selector
BG = "#ffffff"  # chart and page background

# Candlestick-specific colors (diverge from POSITIVE/NEGATIVE for readability)
CANDLE_UP = "#2d6a4f"
CANDLE_DOWN = "#a61c00"

# Long/short position band fills (translucent)
LONG_FILL = "rgba(45, 106, 79, 0.11)"
SHORT_FILL = "rgba(166, 28, 0, 0.11)"
LONG_LINE = POSITIVE
SHORT_LINE = NEGATIVE

# ── Typography ────────────────────────────────────────────────────────────────

FONT = "Courier New, Courier, monospace"
FONT_SIZE = 11

_AXIS_FONT = dict(family=FONT, size=10, color=SLATE)
_TITLE_FONT = dict(family=FONT, size=13, color=NAVY)

# ── Base layout (applied to every chart) ─────────────────────────────────────

_BASE_LAYOUT: dict = dict(
    font=dict(family=FONT, size=FONT_SIZE, color="#1c1c1e"),
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    margin=dict(t=52, b=40, l=72, r=24),
    legend=dict(
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor=GRID,
        borderwidth=1,
        font=dict(family=FONT, size=10),
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="left",
        x=0,
    ),
    hoverlabel=dict(
        bgcolor=NAVY,
        font_color="white",
        font_family=FONT,
        font_size=11,
        bordercolor=NAVY,
    ),
)

_AXIS_DEFAULTS: dict = dict(
    showgrid=True,
    gridcolor=GRID,
    gridwidth=0.5,
    zeroline=False,
    tickfont=_AXIS_FONT,
    title_font=_AXIS_FONT,
    linecolor=GRID,
    linewidth=1,
    showline=True,
)


def apply_base_layout(fig: object, title: str = "") -> None:
    """Apply the standard layout to any Plotly figure in-place.

    Call after adding all traces, before returning the figure.
    Modifies fig in-place; returns None.

    Args:
        fig: Plotly Figure instance.
        title: Chart title string. Left-aligned, navy, monospace.
    """
    fig.update_layout(
        title=dict(text=title, font=_TITLE_FONT, x=0, xanchor="left"),
        **_BASE_LAYOUT,
    )
    fig.update_xaxes(**_AXIS_DEFAULTS)
    fig.update_yaxes(**_AXIS_DEFAULTS)
