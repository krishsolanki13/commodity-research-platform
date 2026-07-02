"""Page 2: Research Workbench — indicator and signal quality analysis.

Follows Architecture Section 10 (Signal Research Workflow) Steps 1-4.
IC analysis (Step 4) is computed before any backtest and displayed here.
See ADR-007: IC evaluation is a precondition for backtesting.

Consumes: Layers 0, 1, 2 via src/ functions only. No computation in this file.
See Architecture Section 13.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.price_chart import render_price_chart
from dashboard.components.signal_chart import render_ic_decay_chart, render_signal_chart
from src.core.config import Config
from src.data.loader import DataLoader
from src.research.momentum import Momentum
from src.research.moving_averages import EMA, SMA
from src.research.oscillators import RSI
from src.research.pipeline import FeaturePipeline
from src.signal.breakout import DonchianBreakoutSignal
from src.signal.evaluation import SignalEvaluator
from src.signal.position import PositionSignalConstructor
from src.signal.reversion import RSIReversionSignal
from src.signal.trend import EMACrossoverSignal, MomentumSignal

st.set_page_config(page_title="Research Workbench", layout="wide")

ASSET_DISPLAY: dict[str, str] = {
    "gold": "Gold (GC=F)",
    "silver": "Silver (SI=F)",
    "copper": "Copper (HG=F)",
    "wti": "WTI Crude (CL=F)",
    "brent": "Brent Crude (BZ=F)",
    "natural_gas": "Natural Gas (NG=F)",
}

INDICATOR_OPTIONS = ["EMA(50)", "EMA(200)", "EMA(20)", "SMA(50)", "SMA(200)"]
SIGNAL_OPTIONS = [
    "EMA Crossover (50/200)",
    "Momentum (20)",
    "RSI Reversion (14)",
    "Donchian Breakout (20)",
]


@st.cache_resource
def _get_config() -> Config:
    return Config.load("config/")


@st.cache_data(ttl=3600)
def _load_asset(asset: str) -> pd.DataFrame | None:
    try:
        return DataLoader(_get_config()).load(asset)
    except Exception:  # noqa: BLE001
        return None


st.title("Research Workbench")
st.caption(
    "Signal quality analysis (IC/ICIR) per ADR-007. "
    "IC evaluation precedes backtesting — a positive IC is a precondition, not a post-hoc diagnostic."
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Controls")
    available = [k for k in ASSET_DISPLAY if _load_asset(k) is not None]
    if not available:
        st.error("No data available. Run: python scripts/acquire_data.py")
        st.stop()

    asset = st.selectbox(
        "Asset", options=available, format_func=lambda k: ASSET_DISPLAY[k]
    )
    lookback = st.slider("Display lookback (bars)", 30, 504, 252, 20)
    selected_indicators = st.multiselect(
        "Price chart overlays",
        options=INDICATOR_OPTIONS,
        default=["EMA(50)", "EMA(200)"],
    )
    selected_signal = st.selectbox("Signal", options=SIGNAL_OPTIONS)
    signal_threshold = st.number_input(
        "Discretization threshold",
        min_value=0.0,
        max_value=2.0,
        value=0.0,
        step=0.05,
        help="Values within [-threshold, +threshold] produce flat (0) position.",
    )

# ── Data and feature computation ──────────────────────────────────────────────
ohlcv = _load_asset(asset)
if ohlcv is None:
    st.error(f"Could not load data for {ASSET_DISPLAY[asset]}.")
    st.stop()

indicator_map = {
    "EMA(50)": EMA(period=50),
    "EMA(200)": EMA(period=200),
    "EMA(20)": EMA(period=20),
    "SMA(50)": SMA(period=50),
    "SMA(200)": SMA(period=200),
}
display_indicators = [
    indicator_map[s] for s in selected_indicators if s in indicator_map
]

# Signal generators and their required pipeline indicators
signal_gen_map = {
    "EMA Crossover (50/200)": (
        EMACrossoverSignal(fast_period=50, slow_period=200),
        [EMA(50), EMA(200)],
    ),
    "Momentum (20)": (
        MomentumSignal(lookback=20, z_score_window=63),
        [Momentum(20)],
    ),
    "RSI Reversion (14)": (
        RSIReversionSignal(period=14),
        [RSI(14)],
    ),
    "Donchian Breakout (20)": (
        DonchianBreakoutSignal(channel_period=20),
        [],  # Reads OHLCV directly
    ),
}
signal_gen, required_indicators = signal_gen_map[selected_signal]

# Merge display and required indicators without duplicates
all_columns = {i.column_name for i in display_indicators}
extra = [i for i in required_indicators if i.column_name not in all_columns]
all_indicators = display_indicators + extra

ff = FeaturePipeline(all_indicators).compute(ohlcv, asset=asset)
display_cols = [i.column_name for i in display_indicators]

try:
    raw_signal = signal_gen.generate(ff)
except KeyError as e:
    st.error(f"Signal generation failed: {e}")
    st.stop()

position_signal = PositionSignalConstructor().build(
    raw_signal, threshold=signal_threshold
)

# ── IC evaluation (ADR-007 Step 4) ───────────────────────────────────────────
with st.spinner("Computing IC..."):
    try:
        evaluation = SignalEvaluator(asset).evaluate(raw_signal, ohlcv)
        ic_available = True
    except ValueError:
        evaluation = None
        ic_available = False

# ── Signal quality display ────────────────────────────────────────────────────
st.subheader("Signal Quality (IC Analysis)")
st.caption(
    "IC interpretation: |IC| < 0.02 = noise · 0.02–0.05 = weak · ≥ 0.05 = meaningful signal. "
    "ICIR ≥ 0.5 indicates consistency across time."
)

ic_col1, ic_col2, ic_col3, ic_col4 = st.columns(4)
if ic_available and evaluation is not None:
    ic = evaluation.ic
    icir = evaluation.icir

    ic_col1.metric("IC (1-bar forward)", f"{ic:.6f}")
    ic_col2.metric("ICIR", f"{icir:.6f}")
    ic_col3.metric("Turnover (signal)", f"{evaluation.turnover:.6f}")

    if abs(ic) >= 0.05:
        ic_col4.success("PASS — meaningful signal")
    elif abs(ic) >= 0.02:
        ic_col4.warning("WEAK — investigate further")
    else:
        ic_col4.error("NOISE — |IC| below 0.02")

    # IC decay chart (Plotly, not st.bar_chart)
    st.caption(
        "IC decay shows how predictive power diminishes at longer forecast horizons. "
        "A well-structured signal retains IC at short horizons and decays at long ones."
    )
    decay_fig = render_ic_decay_chart(evaluation.ic_decay)
    st.plotly_chart(decay_fig, use_container_width=True)
else:
    for col in (ic_col1, ic_col2, ic_col3, ic_col4):
        col.metric("—", "—")
    st.warning(
        "IC could not be computed. Possible causes: fewer than 10 aligned observations, "
        "all-NaN signal, or data too short for the selected indicator."
    )

st.divider()

# ── Price chart with indicators ───────────────────────────────────────────────
st.subheader("Price Chart")
df_plot = ff.data.iloc[-lookback:]
price_fig = render_price_chart(
    df_plot,
    title=f"{ASSET_DISPLAY[asset]}",
    indicator_columns=display_cols,
)
st.plotly_chart(price_fig, use_container_width=True)

# ── Signal chart ──────────────────────────────────────────────────────────────
st.subheader("Signal")
sig_fig = render_signal_chart(
    close_prices=df_plot["close"],
    raw_signal=raw_signal.iloc[-lookback:],
    position_signal=position_signal.iloc[-lookback:],
    title=f"{selected_signal} — {ASSET_DISPLAY[asset]}",
)
st.plotly_chart(sig_fig, use_container_width=True)
