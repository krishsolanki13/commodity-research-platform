"""Page 7: Cross-Asset Analytics — portfolio performance, risk, and correlation.

Surfaces all Phase 3 analytics:
    - Portfolio equity curve and performance KPIs (MultiAssetRunner + PortfolioPerformanceEngine)
    - Per-asset attribution using absolute_pnl_by_asset (always stable)
    - Risk metrics: VaR, ES, diversification benefit (RiskEngine)
    - Pairwise correlation matrix heatmap and rolling correlations (CorrelationEngine)
    - Strategy realized volatility per asset (strategy vol, not price vol)

Architecture: pure presentation layer per ADR-008.
No computation in this file — all analytics called through src/ layer APIs.
Data manipulation in dashboard code is a violation of ADR-008.

Computation model: user-triggered (Run Portfolio Analysis button), results
stored in st.session_state. Results persist until parameters change and
analysis is re-run.

Portfolio persistence: save_portfolio_summary() writes portfolio_summary.json
after each run. This fulfills the ADR-009 Phase 3 portfolio persistence
commitment (from Module 15 Q2 ruling, implemented here per Module 19 scope).

See Architecture Section 13 (Dashboard Page 7) and ADR-008.
"""

from __future__ import annotations

import contextlib
import math
from itertools import combinations
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.components._theme import (
    inject_global_css,
    render_kpi_row,
    section_header,
)
from dashboard.components.correlation_heatmap import (
    render_correlation_heatmap,
    render_rolling_correlation_chart,
)
from dashboard.components.equity_curve_chart import render_equity_curve_chart
from src.analytics.correlation import compute_correlation_and_risk
from src.backtesting.multi_asset import MultiAssetRunner
from src.backtesting.sizing import FixedNotionalSizer, VolatilityScaledSizer
from src.core.config import Config
from src.performance.portfolio import PortfolioPerformanceEngine, save_portfolio_summary

st.set_page_config(page_title="Cross-Asset Analytics", layout="wide")
inject_global_css()

ASSET_DISPLAY: dict[str, str] = {
    "gold": "Gold",
    "silver": "Silver",
    "copper": "Copper",
    "wti": "WTI Crude",
    "brent": "Brent Crude",
    "natural_gas": "Natural Gas",
}

STRATEGY_DISPLAY: dict[str, str] = {
    "ema_crossover": "EMA Crossover",
    "momentum": "Momentum",
    "rsi_reversion": "RSI Reversion",
    "donchian_breakout": "Donchian Breakout",
}

DEFAULT_PARAMETERS: dict[str, dict] = {
    "ema_crossover": {"fast_period": 50, "slow_period": 200},
    "momentum": {"lookback_period": 20, "z_score_window": 63},
    "rsi_reversion": {"period": 14},
    "donchian_breakout": {"channel_period": 20},
}

ALL_ASSETS = ["gold", "silver", "copper", "wti", "brent", "natural_gas"]


@st.cache_resource
def _get_config() -> Config:
    return Config.load("config/")


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Portfolio Configuration")

    selected_assets = st.multiselect(
        "Assets",
        options=ALL_ASSETS,
        default=ALL_ASSETS,
        format_func=lambda k: ASSET_DISPLAY.get(k, k),
        help="Select 2 or more assets for portfolio analysis.",
    )

    strategy_name = st.selectbox(
        "Strategy",
        options=list(STRATEGY_DISPLAY.keys()),
        format_func=lambda k: STRATEGY_DISPLAY.get(k, k),
    )

    st.caption("Strategy parameters")
    params = DEFAULT_PARAMETERS[strategy_name].copy()
    if strategy_name == "ema_crossover":
        params["fast_period"] = st.slider("Fast EMA", 5, 100, params["fast_period"], 5)
        params["slow_period"] = st.slider(
            "Slow EMA", 50, 500, params["slow_period"], 10
        )
    elif strategy_name == "momentum":
        params["lookback_period"] = st.slider(
            "Lookback", 5, 60, params["lookback_period"]
        )
        params["z_score_window"] = st.slider(
            "Z-Score Window", 20, 126, params["z_score_window"]
        )
    elif strategy_name == "rsi_reversion":
        params["period"] = st.slider("RSI Period", 5, 30, params["period"])
    elif strategy_name == "donchian_breakout":
        params["channel_period"] = st.slider(
            "Channel Period", 5, 60, params["channel_period"]
        )

    sizer_choice = st.radio(
        "Position Sizing",
        options=["Fixed Notional ($100K)", "Volatility Scaled (1%/yr)"],
    )

    rolling_window = st.radio(
        "Rolling Correlation Window",
        options=[63, 126],
        format_func=lambda w: f"{w}-day (~{'3' if w == 63 else '6'} months)",
        horizontal=True,
    )

    run_analysis = st.button(
        "Run Portfolio Analysis",
        type="primary",
        disabled=len(selected_assets) < 2,
        help="Select at least 2 assets to run portfolio analysis.",
    )

# ── Page header ───────────────────────────────────────────────────────────────

st.title("Cross-Asset Analytics")
st.caption(
    "Portfolio performance, risk metrics, and correlation structure across "
    "the commodity futures universe. Computation is triggered by the "
    "Run Portfolio Analysis button — results persist until parameters change."
)

# ── Pipeline execution (on button press) ──────────────────────────────────────

if run_analysis:
    if len(selected_assets) < 2:
        st.error("Select at least 2 assets to run portfolio analysis.")
        st.stop()

    sizer = (
        FixedNotionalSizer(notional_usd=100_000.0)
        if sizer_choice.startswith("Fixed")
        else VolatilityScaledSizer(target_annual_vol=0.01, lookback_days=63)
    )

    with st.spinner("Running portfolio analysis across all assets..."):
        config = _get_config()
        runner = MultiAssetRunner(config)

        try:
            multi_result = runner.run(
                assets=selected_assets,
                strategy_name=strategy_name,
                parameters=params,
                sizer=sizer,
            )
        except ValueError as exc:
            st.error(f"Portfolio analysis failed: {exc}")
            st.stop()

        perf_engine = PortfolioPerformanceEngine()
        perf_report = perf_engine.compute(multi_result)

        corr_report, risk_report = compute_correlation_and_risk(
            multi_result, lookback_days=252
        )

        # Portfolio persistence (ADR-009 Phase 3)
        run_dir = Path(config.paths["runs"]) / multi_result.run_id
        with contextlib.suppress(Exception):
            save_portfolio_summary(perf_report, run_dir)

    st.session_state["m19_multi_result"] = multi_result
    st.session_state["m19_perf_report"] = perf_report
    st.session_state["m19_risk_report"] = risk_report
    st.session_state["m19_corr_report"] = corr_report
    st.session_state["m19_rolling_window"] = rolling_window

# ── Guard: no results yet ─────────────────────────────────────────────────────

if "m19_perf_report" not in st.session_state:
    st.info(
        "Configure your portfolio parameters in the sidebar and click "
        "**Run Portfolio Analysis** to begin."
    )
    st.caption(
        "This page runs all Phase 3 analytics simultaneously: "
        "MultiAssetRunner → PortfolioPerformanceEngine → RiskEngine → CorrelationEngine."
    )
    st.stop()

# ── Unpack results from session state ─────────────────────────────────────────

multi_result = st.session_state["m19_multi_result"]
perf_report = st.session_state["m19_perf_report"]
risk_report = st.session_state["m19_risk_report"]
corr_report = st.session_state["m19_corr_report"]

# ── Section 1: Portfolio Performance KPIs ─────────────────────────────────────

section_header("Portfolio Performance")

pm = perf_report.portfolio_metrics

sharpe_str = (
    f"{pm.get('sharpe', float('nan')):.4f}"
    if not math.isnan(pm.get("sharpe", float("nan")))
    else "n/a"
)
mdd_str = (
    f"{pm.get('max_drawdown', float('nan')):.2%}"
    if not math.isnan(pm.get("max_drawdown", float("nan")))
    else "n/a"
)
ret_str = (
    f"{pm.get('total_return', float('nan')):+.2%}"
    if not math.isnan(pm.get("total_return", float("nan")))
    else "n/a"
)
cagr_str = (
    f"{pm.get('cagr', float('nan')):+.2%}"
    if not math.isnan(pm.get("cagr", float("nan")))
    else "n/a"
)
vol_str = (
    f"{pm.get('portfolio_vol', float('nan')):.2%}"
    if not math.isnan(pm.get("portfolio_vol", float("nan")))
    else "n/a"
)
n_days = int(pm.get("n_trading_days", 0))

render_kpi_row(
    [
        ("Sharpe Ratio", sharpe_str, "Annualized"),
        ("Max Drawdown", mdd_str, "Peak-to-trough"),
        ("Total Return", ret_str, f"{n_days} trading days"),
        ("CAGR", cagr_str, "Annualized compound"),
        ("Portfolio Vol", vol_str, "Annualized"),
    ]
)

st.caption(
    f"Portfolio: {perf_report.n_assets} assets — {', '.join(perf_report.assets)}. "
    f"Date range: {perf_report.portfolio_date_range[0]} → {perf_report.portfolio_date_range[1]}. "
    f"Initial capital: ${perf_report.initial_capital_total:,.0f}."
)
if perf_report.skipped_assets:
    st.warning(
        f"Skipped assets (insufficient data): {', '.join(perf_report.skipped_assets)}"
    )

# ── Section 2: Portfolio Equity Curve ─────────────────────────────────────────

section_header("Portfolio Equity Curve")

fig_equity = render_equity_curve_chart(
    equity_curve=multi_result.portfolio_equity_curve,
    initial_capital=perf_report.initial_capital_total,
    title=f"Portfolio Equity Curve — {STRATEGY_DISPLAY.get(multi_result.strategy_name, multi_result.strategy_name)}",
)
st.plotly_chart(fig_equity)

# ── Section 3: Asset Attribution ──────────────────────────────────────────────

section_header("Asset Attribution")

# Use absolute_pnl_by_asset (always stable, regardless of total PnL magnitude)
total_pnl = sum(perf_report.absolute_pnl_by_asset.values())
use_fractional = (
    abs(total_pnl) / perf_report.initial_capital_total > 0.01
    if perf_report.initial_capital_total > 0
    else False
)

attribution_rows = []
for asset in perf_report.assets:
    abs_pnl = perf_report.absolute_pnl_by_asset.get(asset, float("nan"))
    frac = perf_report.asset_contributions.get(asset, float("nan"))
    per_asset_sharpe = (
        perf_report.per_asset_reports[asset].scalar_metrics.get("sharpe", float("nan"))
        if asset in perf_report.per_asset_reports
        else float("nan")
    )
    attribution_rows.append(
        {
            "Asset": ASSET_DISPLAY.get(asset, asset),
            "Total P&L": f"${abs_pnl:+,.0f}" if not math.isnan(abs_pnl) else "n/a",
            "Contribution": f"{frac:+.1%}"
            if (use_fractional and not math.isnan(frac))
            else "—",
            "Asset Sharpe": f"{per_asset_sharpe:.4f}"
            if not math.isnan(per_asset_sharpe)
            else "n/a",
        }
    )

st.dataframe(pd.DataFrame(attribution_rows), hide_index=True)

if not use_fractional:
    st.caption(
        "Contribution % is not shown when total portfolio P&L is < 1% of capital "
        "(fractional contributions become numerically unstable near zero). "
        "Use Total P&L for attribution analysis."
    )

# ── Section 4: Risk Summary ────────────────────────────────────────────────────

section_header("Portfolio Risk")

var95_str = (
    f"${risk_report.portfolio_var_95:,.0f}"
    if not math.isnan(risk_report.portfolio_var_95)
    else "n/a"
)
var99_str = (
    f"${risk_report.portfolio_var_99:,.0f}"
    if not math.isnan(risk_report.portfolio_var_99)
    else "n/a"
)
es99_str = (
    f"${risk_report.portfolio_es_99:,.0f}"
    if not math.isnan(risk_report.portfolio_es_99)
    else "n/a"
)
db_val = risk_report.portfolio_diversification_benefit
db_str = f"{db_val:.2f}x" if not math.isnan(db_val) else "n/a"

render_kpi_row(
    [
        (
            "VaR 95% (Daily)",
            var95_str,
            f"{risk_report.portfolio_var_95_pct:.3%} of capital"
            if not math.isnan(risk_report.portfolio_var_95_pct)
            else "",
        ),
        (
            "VaR 99% (Daily)",
            var99_str,
            f"{risk_report.portfolio_var_99_pct:.3%} of capital"
            if not math.isnan(risk_report.portfolio_var_99_pct)
            else "",
        ),
        ("ES 99% (Daily)", es99_str, "Expected tail loss"),
        ("Diversif. Benefit", db_str, "Sum(asset VaR99) / Portfolio VaR99"),
    ]
)

st.caption(
    f"Historical simulation VaR over {risk_report.lookback_days}-day lookback window. "
    f"Avg gross notional: ${risk_report.total_avg_gross_notional:,.0f}. "
    "All values are daily USD loss magnitudes (positive = amount at risk)."
)

# ── Section 5: Correlation Matrix Heatmap ─────────────────────────────────────

section_header("Correlation Matrix")

fig_heatmap = render_correlation_heatmap(
    corr_report,
    title=f"Strategy Return Correlations — {STRATEGY_DISPLAY.get(multi_result.strategy_name, multi_result.strategy_name)}",
)
st.plotly_chart(fig_heatmap)

avg_corr = corr_report.avg_pairwise_correlation
most = corr_report.most_correlated_pair
least = corr_report.least_correlated_pair
st.caption(
    f"Average pairwise correlation: {avg_corr:.4f}. "
    f"Most correlated: {most[0]} / {most[1]} ({most[2]:.4f}). "
    f"Least correlated: {least[0]} / {least[1]} ({least[2]:.4f})."
)
st.info(
    "Note: these are **strategy return** correlations (P&L / initial capital), "
    "not commodity price return correlations. Strategies with frequent flat periods "
    "will show lower static correlation than the underlying price series. "
    "Rolling correlation charts below give a cleaner picture of the structural relationship."
)

# ── Section 6: Rolling Correlations ───────────────────────────────────────────

section_header("Rolling Correlations")

# Let user select pairs to display
available_pairs = [
    (a, b)
    for a, b in combinations(sorted(corr_report.assets), 2)
    if a in (corr_report.rolling_correlations_63 or {})
    and b in (corr_report.rolling_correlations_63.get(a, {}))
]
pair_labels = [f"{a} / {b}" for a, b in available_pairs]

if pair_labels:
    default_selection = pair_labels[:3] if len(pair_labels) >= 3 else pair_labels
    selected_pair_labels = st.multiselect(
        "Pairs to display",
        options=pair_labels,
        default=default_selection,
    )
    selected_pairs = [tuple(label.split(" / ")) for label in selected_pair_labels]

    if selected_pairs:
        fig_rolling = render_rolling_correlation_chart(
            corr_report,
            pairs=selected_pairs,
            window=rolling_window,
            title=f"Rolling {rolling_window}-Day Strategy Return Correlation",
        )
        st.plotly_chart(fig_rolling)
    else:
        st.info("Select one or more asset pairs to display rolling correlations.")
else:
    st.info(
        "Insufficient data to compute rolling correlations for the selected assets."
    )

# ── Section 7: Strategy Realized Volatility ───────────────────────────────────

section_header("Strategy Realized Volatility")

vol_rows = []
for asset in corr_report.assets:
    strat_vol = corr_report.realized_vol_by_asset.get(asset, float("nan"))
    vol_rows.append(
        {
            "Asset": ASSET_DISPLAY.get(asset, asset),
            "Strategy Realized Vol": f"{strat_vol:.2%}/yr"
            if not math.isnan(strat_vol)
            else "n/a",
        }
    )

# Add portfolio row
port_vol = corr_report.portfolio_realized_vol
vol_rows.append(
    {
        "Asset": "Portfolio (aggregate)",
        "Strategy Realized Vol": f"{port_vol:.2%}/yr"
        if not math.isnan(port_vol)
        else "n/a",
    }
)

st.dataframe(pd.DataFrame(vol_rows), hide_index=True)
st.caption(
    "Strategy Realized Vol = annualized standard deviation of strategy daily P&L "
    "as a fraction of initial capital. This measures the strategy's P&L volatility, "
    "not the commodity price volatility. For EMA 50/200, strategy vol (2–8%/yr) is "
    "significantly below commodity price vol (15–60%/yr) due to extended flat periods."
)
