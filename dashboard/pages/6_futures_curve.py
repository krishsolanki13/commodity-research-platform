"""Page 6: Futures Curve — term structure analysis and roll analytics.

Displays the current forward price curve for commodity futures, the term
structure regime (contango/backwardation/flat), annualized roll yield,
basis (continuous vs front contract), and historical evolution of all metrics.

Research context: A commodity strategy that looks attractive in signal-and-
backtest analysis (Pages 2-5) may have different risk characteristics depending
on term structure regime. In steep contango, rolling a long futures position
costs 4-6%/yr in roll yield drag. In backwardation, rolling earns a premium.
Page 6 makes this structural context visible alongside the signal research.

Consumes: Layer 5 (FuturesCurveBuilder, TermStructureAnalyzer) and
          Layer 0 (DataLoader for continuous close basis computation).
See Architecture Section 13 (Dashboard Page Map, Phase 2).
See ADR-001 (contract series for term structure, continuous for research).
See ADR-008 (no computation in dashboard code).
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
import streamlit as st

from dashboard.components._theme import (
    inject_global_css,
    render_kpi_row,
    section_header,
)
from dashboard.components.curve_chart import (
    render_forward_curve_chart,
    render_term_structure_history_chart,
)
from src.commodity.curve import FuturesCurveBuilder
from src.commodity.term_structure import TermStructureAnalyzer
from src.core.config import Config
from src.core.types import TermStructureRegime
from src.data.loader import DataLoader

st.set_page_config(page_title="Futures Curve", layout="wide")
inject_global_css()

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


@st.cache_resource
def _get_builder() -> FuturesCurveBuilder:
    return FuturesCurveBuilder(_get_config())


@st.cache_data(ttl=3600)
def _load_continuous_close(asset: str) -> float | None:
    """Load the latest continuous close price for basis computation."""
    try:
        df = DataLoader(_get_config()).load(asset)
        return float(df["close"].iloc[-1])
    except Exception:  # noqa: BLE001
        return None


@st.cache_data(ttl=300)
def _build_curve(asset: str, n_contracts: int) -> object:
    """Build current forward curve. Cached for 5 minutes."""
    try:
        return _get_builder().build(asset, n_contracts=n_contracts)
    except ValueError:
        return None


@st.cache_data(ttl=300)
def _build_historical_snapshots(
    asset: str,
    lookback_days: int,
    n_contracts: int,
    sample_every: int = 5,
) -> list:
    """Build historical term structure snapshots. Cached for 5 minutes."""
    try:
        end_date = date.today()
        all_dates = pd.bdate_range(
            end=pd.Timestamp(end_date),
            periods=lookback_days,
            freq="B",
        )
        sampled_dates = [d.date() for d in all_dates[::sample_every]]
        continuous_close = _load_continuous_close(asset)

        curves = _get_builder().build_historical_curves(
            asset, dates=sampled_dates, n_contracts=n_contracts
        )
        analyzer = TermStructureAnalyzer()
        cc = continuous_close if continuous_close is not None else float("nan")
        return analyzer.analyze_series(
            curves,
            continuous_closes=[cc] * len(curves),
        )
    except Exception:  # noqa: BLE001
        return []


# ── Page header ───────────────────────────────────────────────────────────────

st.title("Futures Curve")
st.caption(
    "Forward price term structure, regime classification, and roll yield analytics. "
    "Consumes contract-level OHLCV data per ADR-001. "
    "Run scripts/acquire_contract_data.py to update contract data."
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

builder = _get_builder()
available_assets = builder.available_assets()

if not available_assets:
    st.warning(
        "No contract data found in `data/processed/contracts/`. "
        "Acquire contract data first: "
        "`python scripts/acquire_contract_data.py`"
    )
    st.stop()

with st.sidebar:
    st.header("Configuration")

    asset = st.selectbox(
        "Asset",
        options=available_assets,
        format_func=lambda k: ASSET_DISPLAY.get(k, k),
    )

    n_contracts = st.slider(
        "Contracts (curve points)",
        min_value=2,
        max_value=12,
        value=6,
        step=1,
        help="Number of delivery months to include in the forward curve.",
    )

    lookback_days = st.slider(
        "Historical lookback (trading days)",
        min_value=20,
        max_value=504,
        value=90,
        step=10,
        help="Trading days of history for the term structure evolution charts.",
    )

    if st.button("Refresh Data", help="Clear cache and reload contract data."):
        st.cache_data.clear()
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────

curve = _build_curve(asset, n_contracts)
continuous_close = _load_continuous_close(asset)

if curve is None:
    st.error(
        f"No contract data available for {ASSET_DISPLAY.get(asset, asset)}. "
        f"Run: `python scripts/acquire_contract_data.py --assets {asset}`"
    )
    st.stop()

# Compute current analytics
analyzer = TermStructureAnalyzer()
cc_float = continuous_close if continuous_close is not None else float("nan")
snapshot = analyzer.analyze(curve, continuous_close=cc_float)

# ── Section 1: Current Term Structure KPIs ────────────────────────────────────

section_header("Current Term Structure")

regime_label = {
    TermStructureRegime.CONTANGO: "Contango",
    TermStructureRegime.BACKWARDATION: "Backwardation",
    TermStructureRegime.FLAT: "Flat",
}.get(snapshot.regime, snapshot.regime.value.title())

slope_str = (
    f"{snapshot.annualized_slope_pct:+.2%}/yr"
    if not math.isnan(snapshot.annualized_slope_pct)
    else "n/a"
)

roll_str = (
    f"{snapshot.roll_yield_annualized:+.2%}/yr"
    if not math.isnan(snapshot.roll_yield_annualized)
    else "n/a"
)

basis_str = f"{snapshot.basis:+.2f}" if not math.isnan(snapshot.basis) else "n/a"
basis_pct_context = (
    f"{snapshot.basis_pct:+.2%} of continuous"
    if not math.isnan(snapshot.basis_pct)
    else None
)

render_kpi_row(
    [
        ("Regime", regime_label, f"{curve.n_points} contracts"),
        (
            "Front Price",
            f"${curve.front_price:,.2f}",
            curve.tickers[0] if curve.tickers else "",
        ),
        ("Slope", slope_str, "Positive = contango"),
        ("Roll Yield", roll_str, "Positive = backwardation"),
        ("Basis", basis_str, basis_pct_context),
    ]
)

# Regime interpretation
if snapshot.regime == TermStructureRegime.CONTANGO:
    st.info(
        f"**{ASSET_DISPLAY.get(asset, asset)} is in contango.** "
        f"Deferred delivery is priced above near-term delivery "
        f"({snapshot.annualized_slope_pct:+.2%}/yr annualized slope). "
        f"Rolling a long futures position incurs approximately "
        f"{abs(snapshot.roll_yield_annualized):.2%}/yr in roll drag."
        if not math.isnan(snapshot.roll_yield_annualized)
        else f"({snapshot.annualized_slope_pct:+.2%}/yr annualized slope)."
    )
elif snapshot.regime == TermStructureRegime.BACKWARDATION:
    st.success(
        f"**{ASSET_DISPLAY.get(asset, asset)} is in backwardation.** "
        f"Near-term delivery is priced above deferred delivery "
        f"({snapshot.annualized_slope_pct:+.2%}/yr annualized slope). "
        f"Rolling a long futures position earns approximately "
        f"{abs(snapshot.roll_yield_annualized):.2%}/yr in roll return."
        if not math.isnan(snapshot.roll_yield_annualized)
        else f"({snapshot.annualized_slope_pct:+.2%}/yr annualized slope)."
    )
else:
    st.warning(
        f"**{ASSET_DISPLAY.get(asset, asset)} term structure is flat** "
        f"(annualized slope ≤ 0.5%/yr). "
        f"Roll costs and roll income are negligible at current curve shape."
    )

# ── Section 2: Forward Curve Chart ───────────────────────────────────────────

section_header("Forward Curve")

structure_label = (
    "contango"
    if curve.is_contango
    else "backwardation"
    if curve.is_backwardation
    else "flat"
)
fig_curve = render_forward_curve_chart(
    curve,
    title=f"{ASSET_DISPLAY.get(asset, asset)} — Forward Curve ({structure_label})",
)
st.plotly_chart(fig_curve)

st.caption(
    f"Front contract: {curve.tickers[0] if curve.tickers else 'n/a'} "
    f"(${curve.front_price:,.2f}) · "
    f"Back contract: {curve.tickers[-1] if len(curve.tickers) > 1 else 'n/a'} "
    f"(${curve.back_price:,.2f}) · "
    f"Spread: ${curve.spread():+.2f}"
    if not math.isnan(curve.spread()) and curve.n_points >= 2
    else f"Front: {curve.tickers[0] if curve.tickers else 'n/a'} (${curve.front_price:,.2f})"
)

# ── Section 3: Basis ──────────────────────────────────────────────────────────

if not math.isnan(snapshot.basis):
    section_header("Basis")
    st.caption(
        "Basis = continuous front-month price − nearest contract price. "
        "Reflects roll methodology artifacts from the continuous series (ADR-001 — pseudo-basis). "
        "Positive basis: continuous series trades above the individual contract."
    )

    basis_col1, basis_col2 = st.columns(2)
    with basis_col1:
        st.metric(
            "Continuous Close",
            f"${continuous_close:,.2f}" if continuous_close is not None else "n/a",
        )
    with basis_col2:
        st.metric(
            "Basis (Continuous − Front)",
            f"${snapshot.basis:+,.2f}",
            delta=f"{snapshot.basis_pct:+.2%} of continuous",
        )

# ── Section 4: Historical Term Structure ──────────────────────────────────────

section_header(f"Term Structure History — Last {lookback_days} Trading Days")

with st.spinner("Loading historical term structure..."):
    snapshots = _build_historical_snapshots(asset, lookback_days, n_contracts)

if snapshots:
    fig_history = render_term_structure_history_chart(
        snapshots,
        title=f"{ASSET_DISPLAY.get(asset, asset)} — Term Structure History",
    )
    st.plotly_chart(fig_history)

    regime_counts = {
        "contango": sum(
            1 for s in snapshots if s.regime == TermStructureRegime.CONTANGO
        ),
        "backwardation": sum(
            1 for s in snapshots if s.regime == TermStructureRegime.BACKWARDATION
        ),
        "flat": sum(1 for s in snapshots if s.regime == TermStructureRegime.FLAT),
    }
    total_snaps = len(snapshots)
    st.caption(
        f"Regime distribution over {total_snaps} snapshots: "
        f"contango {regime_counts['contango'] / total_snaps:.0%} · "
        f"backwardation {regime_counts['backwardation'] / total_snaps:.0%} · "
        f"flat {regime_counts['flat'] / total_snaps:.0%}"
    )
else:
    st.info(
        "Historical term structure data not available. "
        "This may occur if contract data covers fewer dates than the selected lookback period."
    )

# ── Section 5: Data Quality ───────────────────────────────────────────────────

with st.expander("Contract Data Details"):
    contracts = builder._loader.list_contracts(asset)
    if contracts:
        data_rows = [
            {
                "Ticker": m.ticker,
                "Delivery": f"{m.contract_year}-{m.contract_month:02d}",
                "Bars": m.n_bars,
            }
            for m in contracts
        ]
        st.dataframe(pd.DataFrame(data_rows), hide_index=True)
        st.caption(
            f"{len(contracts)} contracts · "
            f"earliest: {contracts[0].ticker} · "
            f"latest: {contracts[-1].ticker}"
        )
    else:
        st.info("No contract metadata available.")
