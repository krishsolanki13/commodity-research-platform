"""Page 4: Backtest Results — trade log, equity curve, daily PnL.

Reads BacktestResult from session_state. Requires Strategy Builder
(page 3) to have been run first.

Consumes: Layer 3 output via session_state. No src/ computation.
See Architecture Section 13 (Dashboard Architecture, Page Map).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.equity_curve_chart import render_equity_curve_chart
from src.core.types import BacktestResult, PerformanceReport

st.set_page_config(page_title="Backtest Results", layout="wide")
st.title("📈 Backtest Results")

# -----------------------------------------------------------------------
# Session state guard
# -----------------------------------------------------------------------
if "backtest_result" not in st.session_state:
    st.warning(
        "No backtest has been run yet. "
        "Use **Strategy Builder** to run a backtest first."
    )
    st.stop()

result: BacktestResult = st.session_state["backtest_result"]
report: PerformanceReport = st.session_state["performance_report"]
asset_label = st.session_state.get("last_run_asset", result.asset)
strategy_label = st.session_state.get(
    "last_run_strategy", result.metadata.strategy_name
)

st.caption(
    f"Run ID: `{result.run_id}` · "
    f"Asset: **{asset_label}** · "
    f"Strategy: **{strategy_label}** · "
    f"Trades: **{len(result.trades)}**"
)

# -----------------------------------------------------------------------
# Equity curve + drawdown
# -----------------------------------------------------------------------
st.subheader("Equity Curve")
fig_equity = render_equity_curve_chart(
    equity_curve=result.equity_curve,
    initial_capital=report.initial_capital_usd,
    title="Equity Curve and Drawdown",
)
st.plotly_chart(fig_equity, use_container_width=True)

# -----------------------------------------------------------------------
# Daily PnL bar chart
# -----------------------------------------------------------------------
st.subheader("Daily Net PnL")
pnl_df = result.pnl_series.to_frame(name="Daily PnL (USD)")
st.bar_chart(pnl_df, height=200)

# -----------------------------------------------------------------------
# Summary statistics
# -----------------------------------------------------------------------
st.subheader("Summary")
sum_col1, sum_col2, sum_col3, sum_col4, sum_col5 = st.columns(5)
sum_col1.metric("Total Return", f"{report.scalar_metrics['total_return']:+.2%}")
sum_col2.metric("Sharpe", f"{report.scalar_metrics['sharpe']:.3f}")
sum_col3.metric("Max Drawdown", f"{report.scalar_metrics['max_drawdown']:.2%}")
sum_col4.metric("Win Rate", f"{report.scalar_metrics['win_rate']:.1%}")
sum_col5.metric("Trades", len(result.trades))

# -----------------------------------------------------------------------
# Trade log table
# -----------------------------------------------------------------------
st.subheader("Trade Log")

if not result.trades:
    st.info(
        "No trades were executed. The PositionSignal was flat throughout the entire period."
    )
else:
    trades_data = [
        {
            "Direction": "Long" if t.direction == 1 else "Short",
            "Entry Date": str(t.entry_date),
            "Exit Date": str(t.exit_date),
            "Entry Price": f"{t.entry_price:.2f}",
            "Exit Price": f"{t.exit_price:.2f}",
            "Duration (bars)": t.duration_bars,
            "Gross PnL (USD)": f"{t.gross_pnl:+,.2f}",
            "Cost (USD)": f"{t.transaction_cost:.2f}",
            "Net PnL (USD)": f"{t.net_pnl:+,.2f}",
            "Return (%)": f"{t.return_pct:+.2%}",
            "Force Closed": "Yes" if t.force_closed else "No",
        }
        for t in result.trades
    ]
    trade_df = pd.DataFrame(trades_data)
    st.dataframe(trade_df, use_container_width=True, hide_index=True)

    # Trade statistics summary
    with st.expander("Trade statistics"):
        ts = report.trade_statistics
        ts_col1, ts_col2, ts_col3 = st.columns(3)
        ts_col1.metric("Total trades", ts.get("n_trades", 0))
        ts_col2.metric("Winning trades", ts.get("n_winning", 0))
        ts_col3.metric("Losing trades", ts.get("n_losing", 0))
        ts_col1.metric("Max consecutive wins", ts.get("max_consecutive_wins", 0))
        ts_col2.metric("Max consecutive losses", ts.get("max_consecutive_losses", 0))

# -----------------------------------------------------------------------
# Position series
# -----------------------------------------------------------------------
with st.expander("Position series (USD notional)"):
    pos_df = result.positions.to_frame(name="Position (USD)")
    st.line_chart(pos_df, height=180)
