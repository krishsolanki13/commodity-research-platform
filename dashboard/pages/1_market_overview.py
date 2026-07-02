"""Page 1: Market Overview — commodity universe snapshot.

Displays latest prices, returns, and price charts for all 6 Phase 1 assets.
Handles missing data files gracefully with setup instructions.

Consumes: Layer 0 (DataLoader) via src/ functions only. No computation.
See Architecture Section 13 (Dashboard Architecture, Page Map).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.metrics_table import style_return_series
from dashboard.components.price_chart import render_price_chart
from src.core.config import Config
from src.data.loader import DataLoader

st.set_page_config(page_title="Market Overview", layout="wide")

ASSET_DISPLAY: dict[str, str] = {
    "gold": "Gold (GC=F · COMEX)",
    "silver": "Silver (SI=F · COMEX)",
    "copper": "Copper (HG=F · COMEX)",
    "wti": "WTI Crude (CL=F · NYMEX)",
    "brent": "Brent Crude (BZ=F · ICE)",
    "natural_gas": "Natural Gas (NG=F · NYMEX)",
}


@st.cache_resource
def _get_config() -> Config:
    return Config.load("config/")


@st.cache_data(ttl=3600)
def _load_asset(asset: str) -> pd.DataFrame | None:
    try:
        return DataLoader(_get_config()).load(asset)
    except Exception:  # noqa: BLE001
        return None


st.title("Market Overview")
st.caption(
    "Continuous futures series sourced from Yahoo Finance. "
    "Not back-adjusted — roll gaps appear at contract transitions. See ADR-001."
)

# ── Universe summary table ────────────────────────────────────────────────────
st.subheader("Commodity Universe")

rows: list[dict] = []
for key, display in ASSET_DISPLAY.items():
    df = _load_asset(key)
    if df is not None and len(df) >= 2:
        last_close = float(df["close"].iloc[-1])
        r1d = (df["close"].iloc[-1] / df["close"].iloc[-2] - 1.0) * 100.0
        r1w = (
            (df["close"].iloc[-1] / df["close"].iloc[-6] - 1.0) * 100.0
            if len(df) >= 6
            else None
        )
        r1m = (
            (df["close"].iloc[-1] / df["close"].iloc[-22] - 1.0) * 100.0
            if len(df) >= 22
            else None
        )
        rows.append(
            {
                "Asset": display,
                "Last Close": f"{last_close:,.3f}",
                "1D Ret (%)": f"{r1d:+.2f}",
                "1W Ret (%)": f"{r1w:+.2f}" if r1w is not None else "—",
                "1M Ret (%)": f"{r1m:+.2f}" if r1m is not None else "—",
                "Last Date": str(df.index[-1].date()),
                "Bars": f"{len(df):,}",
            }
        )
    else:
        rows.append(
            {
                "Asset": display,
                "Last Close": "—",
                "1D Ret (%)": "—",
                "1W Ret (%)": "—",
                "1M Ret (%)": "—",
                "Last Date": "—",
                "Bars": "0",
            }
        )

summary_df = pd.DataFrame(rows)
styled = style_return_series(summary_df, ["1D Ret (%)", "1W Ret (%)", "1M Ret (%)"])
st.dataframe(styled, use_container_width=True, hide_index=True)

available_assets = [k for k in ASSET_DISPLAY if _load_asset(k) is not None]

if not available_assets:
    st.warning(
        "No commodity data found in `data/raw/continuous/`. "
        "Acquire data with: `python scripts/acquire_data.py`. "
        "Or copy the test fixture for Gold: "
        "`cp tests/fixtures/gold_sample.csv data/raw/continuous/gold.csv`"
    )
    st.stop()

# ── Price chart ───────────────────────────────────────────────────────────────
st.subheader("Price Chart")

sel_col, bar_col = st.columns([2, 1])
with sel_col:
    selected = st.selectbox(
        "Asset",
        options=available_assets,
        format_func=lambda k: ASSET_DISPLAY[k],
    )
with bar_col:
    lookback = st.slider(
        "Lookback (bars)", min_value=20, max_value=504, value=252, step=20
    )

df_sel = _load_asset(selected)
if df_sel is not None and len(df_sel) > 0:
    df_plot = df_sel.iloc[-lookback:]
    fig = render_price_chart(df_plot, title=ASSET_DISPLAY[selected])
    st.plotly_chart(fig, use_container_width=True)
