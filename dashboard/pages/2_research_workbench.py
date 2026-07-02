"""Page 2: Research Workbench — indicator and signal quality analysis.

Provides: price chart with indicator overlays, signal generation,
IC evaluation display. Follows Architecture Section 10 (steps 1-4).

Consumes: Layers 0, 1, 2 via src/ functions only.
See Architecture Section 13 (Dashboard Architecture, Page Map).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.price_chart import render_price_chart
from dashboard.components.signal_chart import render_signal_chart
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


st.title("🔬 Research Workbench")
st.caption(
    "Indicator and signal quality analysis. IC analysis precedes backtesting per ADR-007."
)

# -----------------------------------------------------------------------
# Sidebar controls
# -----------------------------------------------------------------------
with st.sidebar:
    st.header("Controls")

    available = [k for k in ASSET_DISPLAY if _load_asset(k) is not None]
    if not available:
        st.error("No data available. See Market Overview for setup instructions.")
        st.stop()

    asset = st.selectbox(
        "Asset", options=available, format_func=lambda k: ASSET_DISPLAY[k]
    )
    lookback = st.slider("Lookback (bars)", 30, 252, 120, 10)
    selected_indicators = st.multiselect(
        "Indicator overlays", options=INDICATOR_OPTIONS, default=["EMA(50)", "EMA(200)"]
    )
    selected_signal = st.selectbox("Signal", options=SIGNAL_OPTIONS)
    signal_threshold = st.number_input(
        "Signal threshold (flat zone)",
        min_value=0.0,
        max_value=2.0,
        value=0.0,
        step=0.05,
    )

# -----------------------------------------------------------------------
# Load data and compute features
# -----------------------------------------------------------------------
ohlcv = _load_asset(asset)
if ohlcv is None:
    st.error(f"Could not load data for {ASSET_DISPLAY[asset]}.")
    st.stop()

# Build indicator list from selections
indicator_map = {
    "EMA(50)": EMA(period=50),
    "EMA(200)": EMA(period=200),
    "EMA(20)": EMA(period=20),
    "SMA(50)": SMA(period=50),
    "SMA(200)": SMA(period=200),
}
indicators = [indicator_map[s] for s in selected_indicators if s in indicator_map]

# Build signal generator from selection
signal_gen_map = {
    "EMA Crossover (50/200)": EMACrossoverSignal(fast_period=50, slow_period=200),
    "Momentum (20)": MomentumSignal(lookback=20, z_score_window=63),
    "RSI Reversion (14)": RSIReversionSignal(period=14),
    "Donchian Breakout (20)": DonchianBreakoutSignal(channel_period=20),
}

# Ensure EMA Crossover has required indicator columns
extra_indicators: list = []
if selected_signal == "EMA Crossover (50/200)":
    if EMA(50).column_name not in [i.column_name for i in indicators]:
        extra_indicators.append(EMA(50))
    if EMA(200).column_name not in [i.column_name for i in indicators]:
        extra_indicators.append(EMA(200))
elif selected_signal == "Momentum (20)":
    if Momentum(20).column_name not in [i.column_name for i in indicators]:
        extra_indicators.append(Momentum(20))
elif selected_signal == "RSI Reversion (14)":
    if RSI(14).column_name not in [i.column_name for i in indicators]:
        extra_indicators.append(RSI(14))

all_indicators = indicators + extra_indicators
ff = FeaturePipeline(all_indicators).compute(ohlcv, asset=asset)
indicator_cols = [i.column_name for i in indicators]

signal_gen = signal_gen_map[selected_signal]
try:
    raw_signal = signal_gen.generate(ff)
except KeyError as e:
    st.error(f"Signal generation failed: {e}")
    st.stop()

position_signal = PositionSignalConstructor().build(
    raw_signal, threshold=signal_threshold
)

# Slice to lookback
df_plot = ff.data.iloc[-lookback:]
raw_plot = raw_signal.iloc[-lookback:]
pos_plot = position_signal.iloc[-lookback:]

# -----------------------------------------------------------------------
# IC evaluation (Architecture Section 10, Step 4)
# -----------------------------------------------------------------------
with st.spinner("Computing IC..."):
    try:
        evaluator = SignalEvaluator(asset)
        evaluation = evaluator.evaluate(raw_signal, ohlcv)
        ic_available = True
    except ValueError:
        ic_available = False
        evaluation = None

# -----------------------------------------------------------------------
# IC metrics display
# -----------------------------------------------------------------------
st.subheader("Signal Quality (IC Analysis)")
ic_col1, ic_col2, ic_col3, ic_col4 = st.columns(4)

if ic_available and evaluation is not None:
    ic = evaluation.ic
    icir = evaluation.icir

    def ic_color(v: float) -> str:
        if abs(v) >= 0.05:
            return "normal"
        if abs(v) >= 0.02:
            return "off"
        return "inverse"

    ic_col1.metric(
        "IC (1-bar forward)",
        f"{ic:.4f}",
        help="|IC| ≥ 0.05: meaningful. 0.02–0.05: weak. < 0.02: likely noise.",
    )
    ic_col2.metric("ICIR", f"{icir:.4f}", help="ICIR ≥ 0.5: consistent signal.")
    ic_col3.metric(
        "Turnover",
        f"{evaluation.turnover:.4f}",
        help="Mean absolute daily position change from signal.",
    )
    ic_col4.metric(
        "IC Gate",
        "✅ PASS" if abs(ic) >= 0.05 else ("⚠️ WEAK" if abs(ic) >= 0.02 else "❌ NOISE"),
    )
else:
    st.warning("IC could not be computed — insufficient valid observations.")

# -----------------------------------------------------------------------
# IC decay bar chart
# -----------------------------------------------------------------------
if ic_available and evaluation is not None:
    decay_data = pd.DataFrame(
        {
            "Horizon (bars)": list(evaluation.ic_decay.keys()),
            "IC": list(evaluation.ic_decay.values()),
        }
    )
    st.caption("IC Decay — signal predictive power at increasing forecast horizons")
    st.bar_chart(decay_data.set_index("Horizon (bars)"), height=180)

st.divider()

# -----------------------------------------------------------------------
# Price chart with indicators
# -----------------------------------------------------------------------
st.subheader("Price & Indicators")
price_fig = render_price_chart(
    df_plot,
    title=f"{ASSET_DISPLAY[asset]} — Last {lookback} bars",
    indicator_columns=indicator_cols,
)
st.plotly_chart(price_fig, use_container_width=True)

# -----------------------------------------------------------------------
# Signal chart
# -----------------------------------------------------------------------
st.subheader("Signal")
sig_fig = render_signal_chart(
    close_prices=df_plot["close"],
    raw_signal=raw_plot,
    position_signal=pos_plot,
    title=f"{selected_signal} — Last {lookback} bars",
)
st.plotly_chart(sig_fig, use_container_width=True)
