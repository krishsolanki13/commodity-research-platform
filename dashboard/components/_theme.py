"""Unified chart theme for the Commodity Systematic Research Platform.

All chart components import COLOR constants and apply_base_layout() from
this module. One change here propagates to every chart in the dashboard.

Design principles:
    - Deep navy background — institutional financial terminal aesthetic
    - Bright teal-green / red for P&L encoding — visible on dark backgrounds
    - Monospace font throughout for numerical alignment
    - Thin gridlines — present but not visually dominant
    - No decorative elements, no emoji, no consumer-grade styling

Usage in component files:
    from dashboard.components._theme import (
        NAVY, POSITIVE, NEGATIVE, CAUTION, GRID, FONT,
        apply_base_layout,
    )

Usage in page files (call once after set_page_config):
    from dashboard.components._theme import inject_global_css, section_header
    inject_global_css()
"""

from __future__ import annotations

# ── Palette (dark institutional theme) ───────────────────────────────────────

NAVY = "#4a9eff"  # primary accent — electric blue, visible on dark bg
STEEL = "#6bb3ff"  # secondary accent, reference lines
SLATE = "#7a9cbf"  # muted text, axis labels, tertiary context
POSITIVE = "#00c896"  # gains, long positions, IC pass — bright teal-green
NEGATIVE = "#ff4757"  # losses, short positions, IC noise — bright red
CAUTION = "#ffa502"  # IC weak zone, Sharpe < 0.5 band, warnings — amber
GRID = "#1e3355"  # gridlines — subtle on dark background
SURFACE = "#162033"  # panel backgrounds, sidebar, range selector
BG = "#0e1628"  # page and chart background — deep navy

# Candlestick-specific (bright for visibility on dark background)
CANDLE_UP = "#00c896"
CANDLE_DOWN = "#ff4757"

# Long/short position band fills (translucent overlays on price chart)
LONG_FILL = "rgba(0, 200, 150, 0.12)"
SHORT_FILL = "rgba(255, 71, 87, 0.12)"
LONG_LINE = POSITIVE
SHORT_LINE = NEGATIVE

# ── Typography ────────────────────────────────────────────────────────────────

FONT = "Courier New, Courier, monospace"
FONT_SIZE = 11

_AXIS_FONT = dict(family=FONT, size=10, color=SLATE)
_TITLE_FONT = dict(family=FONT, size=13, color="#dce8f5")

# ── Base layout (applied to every chart) ─────────────────────────────────────

_BASE_LAYOUT: dict = dict(
    font=dict(family=FONT, size=FONT_SIZE, color="#dce8f5"),
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    margin=dict(t=52, b=40, l=72, r=24),
    legend=dict(
        bgcolor="rgba(22, 32, 51, 0.92)",
        bordercolor=GRID,
        borderwidth=1,
        font=dict(family=FONT, size=10, color="#dce8f5"),
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="left",
        x=0,
    ),
    hoverlabel=dict(
        bgcolor="#162033",
        font_color="#dce8f5",
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
    tickfont=dict(family=FONT, size=10, color=SLATE),
    title_font=dict(family=FONT, size=10, color=SLATE),
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
        title: Chart title string. Left-aligned, light, monospace.
    """
    fig.update_layout(
        title=dict(text=title, font=_TITLE_FONT, x=0, xanchor="left"),
        **_BASE_LAYOUT,
    )
    fig.update_xaxes(**_AXIS_DEFAULTS)
    fig.update_yaxes(**_AXIS_DEFAULTS)


def inject_global_css() -> None:
    """Inject CSS to override Streamlit default styling.

    Call once at the top of each page file, immediately after
    st.set_page_config(). Covers: page background, sidebar, headers,
    inputs, buttons, metric boxes, dataframes, alerts, expanders.

    This function imports streamlit locally so that component files
    that import from _theme.py remain importable without a running
    Streamlit server (required for the component smoke test gate).
    """
    import streamlit as st

    st.markdown(
        """
<style>
/* ── Page background ──────────────────────────────────────────────── */
.stApp {
    background-color: #0e1628;
}
.main {
    background-color: #0e1628;
}
.main .block-container {
    padding-top: 1.25rem !important;
    padding-bottom: 0.75rem !important;
    max-width: 100%;
}

/* ── Sidebar ──────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #162033 !important;
    border-right: 1px solid #1e3355 !important;
}
[data-testid="stSidebar"] * {
    color: #dce8f5 !important;
}
[data-testid="stSidebar"] label {
    font-size: 10px !important;
    font-family: "Courier New", monospace !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: #7a9cbf !important;
}
[data-testid="stSidebar"] hr {
    border-color: #1e3355 !important;
}

/* ── Headers ──────────────────────────────────────────────────────── */
h1 {
    font-family: "Courier New", monospace !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #dce8f5 !important;
    letter-spacing: -0.01em !important;
    border-bottom: 1px solid #1e3355 !important;
    padding-bottom: 8px !important;
    margin-bottom: 16px !important;
}
h2 {
    font-family: "Courier New", monospace !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #7a9cbf !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    margin-top: 20px !important;
    margin-bottom: 8px !important;
}
h3 {
    font-family: "Courier New", monospace !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #dce8f5 !important;
}

/* ── Body text ────────────────────────────────────────────────────── */
p, li {
    font-family: "Courier New", monospace !important;
    color: #dce8f5 !important;
    font-size: 12px !important;
}

/* ── st.metric() — remove default box styling ─────────────────────── */
[data-testid="stMetric"] {
    background: none !important;
    border: none !important;
    padding: 0 !important;
}
[data-testid="stMetricValue"] {
    font-family: "Courier New", monospace !important;
    color: #dce8f5 !important;
    font-size: 20px !important;
}
[data-testid="stMetricLabel"] {
    font-family: "Courier New", monospace !important;
    color: #7a9cbf !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stMetricDelta"] {
    font-family: "Courier New", monospace !important;
    font-size: 11px !important;
}

/* ── Buttons ──────────────────────────────────────────────────────── */
.stButton > button {
    background-color: #162033 !important;
    color: #4a9eff !important;
    border: 1px solid #4a9eff !important;
    border-radius: 3px !important;
    font-family: "Courier New", monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.06em !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    padding: 6px 16px !important;
}
.stButton > button[kind="primary"] {
    background-color: #4a9eff !important;
    color: #0e1628 !important;
    border: none !important;
}
.stButton > button:hover {
    background-color: #4a9eff !important;
    color: #0e1628 !important;
    border-color: #4a9eff !important;
    opacity: 0.9;
}

/* ── Dataframes ───────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    font-family: "Courier New", monospace !important;
    font-size: 12px !important;
}
[data-testid="stDataFrame"] th {
    background-color: #162033 !important;
    color: #7a9cbf !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    border-bottom: 1px solid #1e3355 !important;
    padding: 6px 12px !important;
}
[data-testid="stDataFrame"] td {
    background-color: #0e1628 !important;
    color: #dce8f5 !important;
    border-bottom: 1px solid #1e3355 !important;
    padding: 5px 12px !important;
}

/* ── Captions ─────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] p {
    font-family: "Courier New", monospace !important;
    font-size: 10px !important;
    color: #7a9cbf !important;
}

/* ── Alerts (info / warning / error / success) ────────────────────── */
[data-testid="stAlert"] {
    border-radius: 2px !important;
    font-family: "Courier New", monospace !important;
    font-size: 12px !important;
    border-left-width: 3px !important;
}
div[data-baseweb="notification"] {
    background-color: #162033 !important;
}
.stSuccess {
    background-color: rgba(0, 200, 150, 0.10) !important;
    border-left-color: #00c896 !important;
    color: #dce8f5 !important;
}
.stWarning {
    background-color: rgba(255, 165, 2, 0.10) !important;
    border-left-color: #ffa502 !important;
    color: #dce8f5 !important;
}
.stError {
    background-color: rgba(255, 71, 87, 0.10) !important;
    border-left-color: #ff4757 !important;
    color: #dce8f5 !important;
}
.stInfo {
    background-color: rgba(74, 158, 255, 0.10) !important;
    border-left-color: #4a9eff !important;
    color: #dce8f5 !important;
}

/* ── Dividers ─────────────────────────────────────────────────────── */
hr {
    border-color: #1e3355 !important;
    margin: 12px 0 !important;
}

/* ── Expanders ────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #1e3355 !important;
    border-radius: 3px !important;
    background-color: #162033 !important;
}
[data-testid="stExpander"] summary {
    font-family: "Courier New", monospace !important;
    font-size: 11px !important;
    color: #7a9cbf !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    background-color: #162033 !important;
}
[data-testid="stExpander"] summary:hover {
    color: #dce8f5 !important;
}

/* ── Spinner ──────────────────────────────────────────────────────── */
[data-testid="stSpinner"] p {
    font-family: "Courier New", monospace !important;
    color: #7a9cbf !important;
    font-size: 11px !important;
}

/* ── Select / number input / text input ───────────────────────────── */
[data-baseweb="select"] {
    background-color: #162033 !important;
    border-color: #1e3355 !important;
}
[data-baseweb="select"] * {
    background-color: #162033 !important;
    color: #dce8f5 !important;
    font-family: "Courier New", monospace !important;
    font-size: 12px !important;
}
[data-baseweb="input"] {
    background-color: #162033 !important;
    border-color: #1e3355 !important;
    color: #dce8f5 !important;
    font-family: "Courier New", monospace !important;
}
[data-baseweb="menu"] {
    background-color: #162033 !important;
    border-color: #1e3355 !important;
}
[data-baseweb="menu"] li {
    background-color: #162033 !important;
    color: #dce8f5 !important;
    font-family: "Courier New", monospace !important;
    font-size: 12px !important;
}
[data-baseweb="menu"] li:hover {
    background-color: #1e3355 !important;
}

/* ── Slider ───────────────────────────────────────────────────────── */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background-color: #4a9eff !important;
    border-color: #4a9eff !important;
}

/* ── Markdown info boxes ──────────────────────────────────────────── */
.stMarkdown code {
    background-color: #162033 !important;
    color: #4a9eff !important;
    font-family: "Courier New", monospace !important;
    border: 1px solid #1e3355 !important;
    border-radius: 2px !important;
    padding: 1px 4px !important;
}

/* ── Tab navigation (if used) ─────────────────────────────────────── */
[data-baseweb="tab-list"] {
    background-color: #0e1628 !important;
    border-bottom: 1px solid #1e3355 !important;
}
[data-baseweb="tab"] {
    font-family: "Courier New", monospace !important;
    font-size: 11px !important;
    color: #7a9cbf !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #4a9eff !important;
    border-bottom: 2px solid #4a9eff !important;
}

/* ── Column separators ────────────────────────────────────────────── */
[data-testid="column"] {
    background-color: transparent !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str) -> None:
    """Render a section divider with an uppercase label.

    Replaces the st.divider() + st.subheader() pattern.
    Produces a thin top border with a muted uppercase label above it.
    Standard institutional section separator pattern.

    Args:
        title: Section label. Will be rendered in uppercase monospace.

    Usage:
        section_header("Risk-Adjusted Performance")
        # renders metrics below...
        section_header("Rolling Metrics")
        # renders chart below...
    """
    import streamlit as st

    st.markdown(
        f"""
<div style="
    border-top: 1px solid #1e3355;
    margin: 20px 0 10px 0;
    padding-top: 8px;
    font-family: 'Courier New', monospace;
    font-size: 10px;
    font-weight: 600;
    color: #7a9cbf;
    text-transform: uppercase;
    letter-spacing: 0.08em;
">{title}</div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row(
    metrics: list[tuple[str, str, str | None]],
) -> None:
    """Render a row of KPI metrics as a styled HTML table.

    Replaces st.metric() widget boxes throughout the dashboard.
    Produces a compact, dark-themed key metrics display with monospace
    font, uppercase labels, and optional context line below each value.

    Why not st.metric(): Streamlit's metric widget has an instantly
    recognizable visual signature (large number, gray delta text, no border)
    that identifies the project as a Streamlit app to any practitioner.
    This function renders metrics in a style consistent with institutional
    research tools — no Streamlit UI fingerprint.

    Args:
        metrics: List of (label, value, context) tuples.
            label:   Short uppercase label (e.g., "Sharpe Ratio").
                     Will be rendered in uppercase monospace at 10px.
            value:   Pre-formatted value string (e.g., "1.2341", "+28.4%").
                     Will be rendered at 24px bold monospace.
            context: Optional muted context line below the value
                     (e.g., "+0.74 vs 0.5 threshold"). Pass None to omit.

    Usage:
        render_kpi_row([
            ("Sharpe Ratio",  "1.2341",  "+0.7341 vs 0.5 threshold"),
            ("Max Drawdown",  "-14.23%", None),
            ("Total Return",  "+28.41%", None),
        ])
    """
    import streamlit as st

    n = len(metrics)
    if n == 0:
        return

    col_pct = 100 // n

    cells = ""
    for i, (label, value, context) in enumerate(metrics):
        border_right = "border-right: 1px solid #1e3355;" if i < n - 1 else ""
        context_html = (
            f'<div style="'
            f"font-size:10px; color:#7a9cbf; margin-top:3px; "
            f"font-family:'Courier New',monospace; letter-spacing:0.02em"
            f'">{context}</div>'
            if context
            else ""
        )
        cells += f"""
        <td style="
            width: {col_pct}%;
            padding: 14px 20px;
            {border_right}
            vertical-align: top;
            background: #162033;
        ">
            <div style="
                font-size: 10px;
                color: #7a9cbf;
                font-family: 'Courier New', monospace;
                text-transform: uppercase;
                letter-spacing: 0.07em;
                margin-bottom: 5px;
                font-weight: 600;
            ">{label}</div>
            <div style="
                font-size: 24px;
                font-weight: 700;
                color: #dce8f5;
                font-family: 'Courier New', monospace;
                line-height: 1.1;
            ">{value}</div>
            {context_html}
        </td>
        """

    html = f"""
<table style="
    width: 100%;
    border-collapse: collapse;
    border: 1px solid #1e3355;
    border-radius: 3px;
    margin-bottom: 16px;
    overflow: hidden;
"><tr>{cells}</tr></table>
    """
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)
