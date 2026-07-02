"""Page 5: Performance Analysis — risk-adjusted metrics and rolling analytics.

Reads BacktestResult and PerformanceReport from session_state.
Requires Strategy Builder (page 3) to have been run first.

Consumes: Layers 3 and 4 output via session_state. No src/ computation.
See Architecture Section 13 (Dashboard Architecture, Page Map).

Note on initial_capital display: use report.initial_capital_usd as the
authoritative source (per Module 6 deviation 1). Do not use
report.scalar_metrics["initial_capital"] for display.
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
st.title("📐 Performance Analysis")

# -----------------------------------------------------------------------
# Session state guard
# -----------------------------------------------------------------------
if "performance_report" not in st.session_state:
    st.warning(
        "No backtest has been run yet. "
        "Use **Strategy Builder** to run a backtest first."
    )
    st.stop()

result: BacktestResult = st.session_state["backtest_result"]
report: PerformanceReport = st.session_state["performance_report"]

st.caption(
    f"Run ID: `{report.run_id}` · "
    f"Asset: **{st.session_state.get('last_run_asset', result.asset)}** · "
    f"Strategy: **{st.session_state.get('last_run_strategy', result.metadata.strategy_name)}**"
)

# -----------------------------------------------------------------------
# Top-level performance metrics
# -----------------------------------------------------------------------
st.subheader("Risk-Adjusted Metrics")

top_col1, top_col2, top_col3, top_col4, top_col5, top_col6 = st.columns(6)

sm = report.scalar_metrics

top_col1.metric(
    "Total Return",
    f"{sm['total_return']:+.2%}",
    help="(final_equity - initial_capital) / initial_capital",
)
top_col2.metric(
    "CAGR",
    f"{sm['cagr']:+.2%}",
    help="Annualized return assuming 252 trading days per year.",
)
top_col3.metric(
    "Sharpe Ratio",
    f"{sm['sharpe']:.3f}",
    help="Annualized Sharpe. > 1.0 strong, > 0.5 acceptable.",
)
top_col4.metric(
    "Sortino Ratio",
    f"{sm['sortino']:.3f}",
    help="Like Sharpe but penalizes only downside volatility.",
)
top_col5.metric(
    "Calmar Ratio",
    f"{sm['calmar']:.3f}",
    help="CAGR / |Max Drawdown|. Higher is better.",
)
top_col6.metric(
    "Max Drawdown",
    f"{sm['max_drawdown']:.2%}",
    help="Peak-to-trough decline as fraction of peak equity.",
)

st.divider()

# -----------------------------------------------------------------------
# Rolling metrics chart
# -----------------------------------------------------------------------
st.subheader("Rolling Metrics")

roll = report.rolling_metrics
if "rolling_sharpe_63" in roll and "rolling_drawdown" in roll:
    fig_rolling = render_rolling_metrics_chart(
        rolling_sharpe=roll["rolling_sharpe_63"],
        rolling_drawdown=roll["rolling_drawdown"],
        title="Rolling Performance (63-bar window)",
    )
    st.plotly_chart(fig_rolling, use_container_width=True)
    st.caption(
        "Dashed line at Sharpe = 0.5. NaN values during 63-bar warmup period "
        "are not plotted."
    )
else:
    st.info("Rolling metrics unavailable for this run.")

st.divider()

# -----------------------------------------------------------------------
# Full metrics table
# -----------------------------------------------------------------------
col_metrics, col_signal = st.columns([1, 1])

with col_metrics:
    st.subheader("All Scalar Metrics")
    # Use report.initial_capital_usd — authoritative source per Module 6 deviation 1
    metrics_df = build_metrics_dataframe(
        scalar_metrics=sm,
        initial_capital_usd=report.initial_capital_usd,
    )
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

with col_signal:
    st.subheader("Signal Quality Metrics")
    signal_df = build_signal_metrics_dataframe(report.signal_metrics)

    if signal_df is not None:
        st.dataframe(signal_df, use_container_width=True, hide_index=True)

        # IC interpretation
        ic_val = report.signal_metrics.get("ic", None)
        if ic_val is not None:
            if abs(ic_val) >= 0.05:
                st.success(
                    f"IC = {ic_val:.4f} — meaningful predictive content (|IC| ≥ 0.05)."
                )
            elif abs(ic_val) >= 0.02:
                st.warning(
                    f"IC = {ic_val:.4f} — weak signal (0.02 ≤ |IC| < 0.05). Investigate further."
                )
            else:
                st.error(
                    f"IC = {ic_val:.4f} — likely noise (|IC| < 0.02). Backtest results may not be reliable."
                )
    else:
        st.info(
            "Signal quality metrics not available for this run. "
            "Signal evaluation was not attached before computing PerformanceReport. "
            "This occurs when the Strategy Builder pipeline runs the backtest without "
            "IC evaluation — check data availability."
        )

st.divider()

# -----------------------------------------------------------------------
# Metadata
# -----------------------------------------------------------------------
with st.expander("Run Metadata"):
    meta = result.metadata
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        st.write(f"**Run ID:** `{meta.run_id}`")
        st.write(f"**Asset:** {meta.asset}")
        st.write(f"**Strategy:** {meta.strategy_name}")
        st.write(f"**Signal:** {meta.signal_name}")
        st.write(f"**Data source:** {meta.data_source}")
    with meta_col2:
        st.write(f"**Data start:** {meta.data_start}")
        st.write(f"**Data end:** {meta.data_end}")
        # Use report.initial_capital_usd — not scalar_metrics["initial_capital"]
        st.write(f"**Initial capital:** ${report.initial_capital_usd:,.0f}")
        st.write(
            f"**Git commit:** `{meta.git_commit_hash[:8] if meta.git_commit_hash != 'unknown' else 'unknown'}`"
        )
        st.write(
            f"**Executed at:** {meta.executed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
    st.write("**Parameters:**")
    st.json(meta.parameters)
    st.write("**Cost model:**")
    st.json(meta.cost_model_params)
    st.write("**Sizing model:**")
    st.json(meta.sizing_model_params)
