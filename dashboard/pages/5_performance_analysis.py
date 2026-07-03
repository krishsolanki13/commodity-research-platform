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

from dashboard.components._theme import (
    inject_global_css,
    render_kpi_row,
    section_header,
)
from dashboard.components.equity_curve_chart import render_rolling_metrics_chart
from dashboard.components.metrics_table import (
    build_metrics_dataframe,
    build_signal_metrics_dataframe,
)
from src.core.types import BacktestResult, PerformanceReport

st.set_page_config(page_title="Performance Analysis", layout="wide")
inject_global_css()
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
section_header("Risk-Adjusted Performance")
render_kpi_row(
    [
        (
            "Sharpe Ratio",
            f"{sm['sharpe']:.4f}",
            f"{sm['sharpe'] - 0.5:+.4f} vs 0.5 threshold",
        ),
        (
            "Max Drawdown",
            f"{sm['max_drawdown']:.2%}",
            "Peak-to-trough / peak equity",
        ),
        (
            "Total Return",
            f"{sm['total_return']:+.2%}",
            f"Initial: ${report.initial_capital_usd:,.0f}",
        ),
    ]
)

# ── Tier 2 — Secondary metrics ────────────────────────────────────────────────
st.divider()
render_kpi_row(
    [
        ("CAGR", f"{sm['cagr']:+.2%}", "Annualized · 252 days/yr"),
        ("Sortino", f"{sm['sortino']:.4f}", "Downside deviation only"),
        ("Calmar", f"{sm['calmar']:.4f}", "CAGR / |Max Drawdown|"),
        (
            "Win Rate",
            f"{sm['win_rate']:.1%}",
            f"{report.trade_statistics.get('n_winning', 0)}/{report.trade_statistics.get('n_trades', 0)} trades",
        ),
    ]
)

st.divider()

# ── Rolling metrics ───────────────────────────────────────────────────────────
section_header("Rolling Performance — 63-bar window")
roll = report.rolling_metrics
if "rolling_sharpe_63" in roll and "rolling_drawdown" in roll:
    fig_rolling = render_rolling_metrics_chart(
        rolling_sharpe=roll["rolling_sharpe_63"],
        rolling_drawdown=roll["rolling_drawdown"],
        title="Rolling Sharpe and Drawdown",
    )
    st.plotly_chart(fig_rolling)
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
    st.dataframe(metrics_df, hide_index=True)

with col_signal:
    st.subheader("Signal Quality (IC Attribution)")
    signal_df = build_signal_metrics_dataframe(report.signal_metrics)
    if signal_df is not None:
        st.dataframe(signal_df, hide_index=True)
        ic_val = report.signal_metrics.get("ic")
        if ic_val is not None:
            abs_ic = abs(ic_val)
            if abs_ic >= 0.05 and ic_val > 0:
                st.success(
                    f"IC = {ic_val:.6f} — Strong positive signal (|IC| ≥ 0.05). "
                    f"Signal predicts forward returns in the expected direction."
                )
            elif abs_ic >= 0.05 and ic_val < 0:
                st.warning(
                    f"IC = {ic_val:.6f} — Strong inverse signal (|IC| ≥ 0.05, negative direction). "
                    f"Signal is predictive but in the opposite direction from the hypothesis. "
                    f"Consider inverting the signal or reviewing the entry/exit logic."
                )
            elif 0.02 <= abs_ic < 0.05 and ic_val > 0:
                st.warning(
                    f"IC = {ic_val:.6f} — Weak positive signal (0.02 ≤ |IC| < 0.05). "
                    f"Some predictive content but regime-dependent."
                )
            elif 0.02 <= abs_ic < 0.05 and ic_val < 0:
                st.warning(
                    f"IC = {ic_val:.6f} — Weak inverse signal. "
                    f"Some predictive content in the opposite direction."
                )
            else:
                st.error(
                    f"IC = {ic_val:.6f} — Noise (|IC| < 0.02). "
                    f"No meaningful predictive content detected. "
                    f"Backtest results may reflect chance rather than genuine edge."
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
