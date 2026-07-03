"""Commodity Systematic Research Platform — Streamlit home page.

Entry point for the dashboard launcher scripts.
Streamlit discovers pages in dashboard/pages/ automatically.

Run with:
    Windows:   .\\launch_dashboard.ps1
    Mac/Linux: ./launch_dashboard.sh

Architecture: Layer 0 (Data) → Layer 1 (Features) → Layer 2 (Signals)
              → Layer 3 (Backtesting) → Layer 4 (Performance) → Layer 8 (Dashboard)
See ADR-008 for the dashboard architecture constraints.
"""

import streamlit as st

st.set_page_config(
    page_title="Commodity Research Platform",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.components._theme import inject_global_css  # noqa: E402

inject_global_css()

st.title("Commodity Systematic Research Platform")
st.markdown(
    "Institutional-style quantitative research infrastructure for commodity futures markets. "
    "Built following the systematic research workflow: signal evaluation precedes backtesting."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Research Workflow")
    st.markdown(
        """
        1. **Market Overview** — Commodity universe and price data
        2. **Research Workbench** — Indicator and signal quality analysis
        3. **Strategy Builder** — Backtest configuration and execution
        4. **Backtest Results** — Trade log and equity curve
        5. **Performance Analysis** — Risk-adjusted metrics and attribution
        """
    )

with col2:
    st.subheader("Covered Markets")
    st.markdown(
        """
        - Gold (GC=F · COMEX · USD/troy oz)
        - Silver (SI=F · COMEX · USD/troy oz)
        - Copper (HG=F · COMEX · USD/lb)
        - WTI Crude (CL=F · NYMEX · USD/barrel)
        - Brent Crude (BZ=F · ICE · USD/barrel)
        - Natural Gas (NG=F · NYMEX · USD/MMBtu)
        """
    )

with col3:
    st.subheader("Phase 1 Strategies")
    st.markdown(
        """
        - EMA Crossover *(trend-following)*
        - Momentum *(trend-following)*
        - RSI Reversion *(mean-reversion)*
        - Donchian Breakout *(breakout)*
        """
    )

st.divider()

st.info(
    "**Getting started:** Navigate using the sidebar. "
    "Begin with **Market Overview** to review available data, "
    "then use **Strategy Builder** to run a complete research pipeline."
)

st.caption(
    "Data: Yahoo Finance continuous futures series (not back-adjusted — see ADR-001). "
    "Signal evaluation via IC/ICIR precedes backtesting per ADR-007. "
    "Execution timing: signal generated at Close[t], executed at Open[t+1] per ADR-002."
)
