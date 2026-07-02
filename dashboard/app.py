"""Commodity Systematic Research Platform — Streamlit home page.

Entry point for `streamlit run dashboard/app.py`. Streamlit automatically
discovers pages in dashboard/pages/ and adds them to the sidebar.

This file is the home/landing page only. All computation is in src/ modules.
See ADR-008 (Dashboard Architecture).
"""

import streamlit as st

st.set_page_config(
    page_title="Commodity Research Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 Commodity Systematic Research Platform")
st.markdown(
    "An institutional-style quantitative research environment for commodity futures markets."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📊 Research Workflow")
    st.markdown(
        """
        1. **Market Overview** — Commodity universe snapshot
        2. **Research Workbench** — Indicator and signal analysis
        3. **Strategy Builder** — Build and backtest strategies
        4. **Backtest Results** — Trade-level analysis
        5. **Performance Analysis** — Risk-adjusted metrics
        """
    )

with col2:
    st.subheader("🛢️ Covered Markets")
    st.markdown(
        """
        - Gold (GC=F · COMEX)
        - Silver (SI=F · COMEX)
        - Copper (HG=F · COMEX)
        - WTI Crude (CL=F · NYMEX)
        - Brent Crude (BZ=F · ICE)
        - Natural Gas (NG=F · NYMEX)
        """
    )

with col3:
    st.subheader("📐 Phase 1 Strategies")
    st.markdown(
        """
        - EMA Crossover *(trend)*
        - Momentum *(trend)*
        - RSI Reversion *(mean-reversion)*
        - Donchian Breakout *(breakout)*
        """
    )

st.divider()
st.info(
    "**Getting Started:** Navigate using the sidebar. "
    "Start with **Market Overview** to review commodity data, "
    "then use **Strategy Builder** to run a full backtest."
)
st.caption(
    "Architecture: Layer 0 (Data) → Layer 1 (Features) → Layer 2 (Signals) → "
    "Layer 3 (Backtesting) → Layer 4 (Performance) → Layer 8 (Dashboard)"
)
