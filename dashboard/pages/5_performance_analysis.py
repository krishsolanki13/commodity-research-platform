"""Page 5: Performance Analysis — risk-adjusted metrics and rolling attribution.

Three-tier metric hierarchy:
    Tier 1: Sharpe, Max Drawdown, Total Return (read first by practitioners)
    Tier 2: CAGR, Sortino, Calmar, Win Rate
    Tier 3: Full grouped metrics table

Note on initial_capital display: use report.initial_capital_usd as the
authoritative source. Not scalar_metrics["initial_capital"]. See Module 6 notes.

Consumes: Layers 3, 4 output via session_state. No src/ computation.
See Architecture Section 13.
"""

from __future__ import annotations

import streamlit as st

from dashboard.components.equity_curve_chart import render_rolling_metrics_chart
from dashboard.components.metrics_table import (
    build_metrics_dataframe,
    build_signal_metrics_dataframe,
)
from src.core.types import BacktestResult, PerformanceReport

st.set_page_config(page_title="Performance Analysis", layout="wide")
st.title("Performance Analysis")

if "performance_report" not in st.session_state:
    st.warning(
        "No backtest has been run yet. "
        "Use **Strategy Builder** (page 3) to run a backtest first."
    )
    st.stop()

result: BacktestResult = st.session_state["backtest_result"]
report: PerformanceReport = st.session_state["performance_report"]

st.caption(
    f"Run ID: `{report.run_id}` · "
    f"Asset: **{st.session_state.get('last_run_asset', result.asset)}** · "
    f"Strategy: **{st.session_state.get('last_run_strategy', result.metadata.strategy_name)}**"
)

sm = report.scalar_metrics

# ── Tier 1 — Primary metrics ──────────────────────────────────────────────────
st.subheader("Risk-Adjusted Performance")
t1c1, t1c2, t1c3 = st.columns(3)
t1c1.metric(
    "Sharpe Ratio",
    f"{sm['sharpe']:.4f}",
    delta=f"{sm['sharpe'] - 0.5:+.4f} vs 0.5 threshold",
    help="Annualized: mean(daily_return) / std(daily_return) * sqrt(252). > 1.0: strong. > 0.5: adequate.",
)
t1c2.metric(
    "Max Drawdown",
    f"{sm['max_drawdown']:.2%}",
    help="Peak-to-trough decline as a fraction of peak equity.",
)
t1c3.metric(
    "Total Return",
    f"{sm['total_return']:+.2%}",
    help="(final_equity - initial_capital) / initial_capital.",
)

# ── Tier 2 — Secondary metrics ────────────────────────────────────────────────
st.divider()
t2c1, t2c2, t2c3, t2c4 = st.columns(4)
t2c1.metric(
    "CAGR",
    f"{sm['cagr']:+.2%}",
    help="Annualized return assuming 252 trading days/year.",
)
t2c2.metric(
    "Sortino Ratio",
    f"{sm['sortino']:.4f}",
    help="Like Sharpe but penalizes only downside volatility.",
)
t2c3.metric("Calmar Ratio", f"{sm['calmar']:.4f}", help="CAGR / |Max Drawdown|.")
t2c4.metric(
    "Win Rate",
    f"{sm['win_rate']:.1%}",
    help="Fraction of trades with positive net PnL.",
)

st.divider()

# ── Rolling metrics ───────────────────────────────────────────────────────────
st.subheader("Rolling Performance (63-bar window)")
roll = report.rolling_metrics
if "rolling_sharpe_63" in roll and "rolling_drawdown" in roll:
    fig_rolling = render_rolling_metrics_chart(
        rolling_sharpe=roll["rolling_sharpe_63"],
        rolling_drawdown=roll["rolling_drawdown"],
        title="Rolling Sharpe and Drawdown",
    )
    st.plotly_chart(fig_rolling, use_container_width=True)
    st.caption(
        "Rolling Sharpe color encoding: green >= 1.0 · amber 0.5–1.0 · red < 0.5. "
        "Shaded band marks the 0–0.5 inadequate zone. NaN during 63-bar warmup period."
    )
else:
    st.info("Rolling metrics unavailable for this run.")

st.divider()

# ── Full metrics table and signal metrics ─────────────────────────────────────
col_metrics, col_signal = st.columns([1, 1])

with col_metrics:
    st.subheader("All Metrics")
    # Uses report.initial_capital_usd — the authoritative source per Module 6 notes
    metrics_df = build_metrics_dataframe(
        scalar_metrics=sm,
        initial_capital_usd=report.initial_capital_usd,
    )
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

with col_signal:
    st.subheader("Signal Quality (IC Attribution)")
    signal_df = build_signal_metrics_dataframe(report.signal_metrics)
    if signal_df is not None:
        st.dataframe(signal_df, use_container_width=True, hide_index=True)
        ic_val = report.signal_metrics.get("ic")
        if ic_val is not None:
            if abs(ic_val) >= 0.05:
                st.success(
                    f"IC = {ic_val:.6f} — meaningful predictive content (|IC| >= 0.05)."
                )
            elif abs(ic_val) >= 0.02:
                st.warning(
                    f"IC = {ic_val:.6f} — weak signal. Results may be regime-dependent."
                )
            else:
                st.error(
                    f"IC = {ic_val:.6f} — noise level (|IC| < 0.02). "
                    "Backtest results may reflect chance rather than edge."
                )
    else:
        st.info(
            "Signal quality metrics not attached to this run. "
            "Run via Strategy Builder to attach IC evaluation. "
            "See ADR-007 for the IC-before-backtest architectural requirement."
        )

# ── Metadata ──────────────────────────────────────────────────────────────────
with st.expander("Run Metadata"):
    meta = result.metadata
    mc1, mc2 = st.columns(2)
    with mc1:
        st.write(f"**Run ID:** `{meta.run_id}`")
        st.write(f"**Asset:** {meta.asset}")
        st.write(f"**Strategy:** {meta.strategy_name}")
        st.write(f"**Signal:** {meta.signal_name}")
        st.write(f"**Data source:** {meta.data_source}")
    with mc2:
        st.write(f"**Data range:** {meta.data_start} to {meta.data_end}")
        # report.initial_capital_usd — not scalar_metrics["initial_capital"]
        st.write(f"**Initial capital:** ${report.initial_capital_usd:,.0f}")
        st.write(f"**Executed at:** {meta.executed_at.strftime('%Y-%m-%d %H:%M UTC')}")
        st.write(
            f"**Git commit:** `{meta.git_commit_hash[:8] if meta.git_commit_hash != 'unknown' else 'unknown'}`"
        )
    st.write("**Parameters:**")
    st.json(meta.parameters)
    st.write("**Cost model:**")
    st.json(meta.cost_model_params)
