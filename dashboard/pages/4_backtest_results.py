"""Page 4: Backtest Results — trade log, equity curve, daily PnL.

Reads BacktestResult from session_state set by Strategy Builder (page 3).
No computation — all data from session_state.

Consumes: Layer 3 output via session_state. No src/ computation.
See Architecture Section 13.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.equity_curve_chart import render_equity_curve_chart
from src.core.types import BacktestResult, PerformanceReport

st.set_page_config(page_title="Backtest Results", layout="wide")
st.title("Backtest Results")

if "backtest_result" not in st.session_state:
    st.warning(
        "No backtest has been run yet. "
        "Use **Strategy Builder** (page 3) to run a backtest first."
    )
    st.stop()

result: BacktestResult = st.session_state["backtest_result"]
report: PerformanceReport = st.session_state["performance_report"]

st.caption(
    f"Run ID: `{result.run_id}` · "
    f"Asset: **{st.session_state.get('last_run_asset', result.asset)}** · "
    f"Strategy: **{st.session_state.get('last_run_strategy', result.metadata.strategy_name)}** · "
    f"Trades: **{len(result.trades)}**"
)

# ── Top metrics ───────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
sm = report.scalar_metrics
m1.metric("Total Return", f"{sm['total_return']:+.2%}")
m2.metric("Sharpe Ratio", f"{sm['sharpe']:.4f}")
m3.metric("Max Drawdown", f"{sm['max_drawdown']:.2%}")
m4.metric("Win Rate", f"{sm['win_rate']:.1%}")
m5.metric("Trades", len(result.trades))

st.divider()

# ── Equity curve ──────────────────────────────────────────────────────────────
st.subheader("Equity Curve")
fig_equity = render_equity_curve_chart(
    equity_curve=result.equity_curve,
    initial_capital=report.initial_capital_usd,
    title="Equity and Drawdown",
)
st.plotly_chart(fig_equity, use_container_width=True)

# ── Daily PnL ─────────────────────────────────────────────────────────────────
st.subheader("Daily Net PnL")
pnl_df = result.pnl_series.rename("Daily PnL (USD)").to_frame()
st.bar_chart(pnl_df, height=180)

st.divider()

# ── Trade log ─────────────────────────────────────────────────────────────────
st.subheader("Trade Log")

if not result.trades:
    st.info(
        "No trades were executed. The PositionSignal was flat throughout the backtest period. "
        "This can occur when the signal never crosses the discretization threshold, "
        "or when indicator warmup periods exceed the data length."
    )
else:
    # Default view: 5 core columns
    default_data = [
        {
            "Direction": "Long" if t.direction == 1 else "Short",
            "Entry Date": str(t.entry_date),
            "Exit Date": str(t.exit_date),
            "Net PnL (USD)": f"{t.net_pnl:+,.2f}",
            "Return (%)": f"{t.return_pct:+.2%}",
        }
        for t in result.trades
    ]
    trade_df = pd.DataFrame(default_data)

    def _color_pnl(val: str) -> str:
        try:
            num = float(val.replace("+", "").replace(",", ""))
            return (
                "color: #2d6a4f; font-weight: 600"
                if num > 0
                else ("color: #a61c00; font-weight: 600" if num < 0 else "")
            )
        except ValueError:
            return ""

    styled_trades = trade_df.style.map(
        _color_pnl, subset=["Net PnL (USD)", "Return (%)"]
    )
    st.dataframe(styled_trades, use_container_width=True, hide_index=True)

    # Full detail in expander
    with st.expander("Full trade detail (all fields)"):
        full_data = [
            {
                "Direction": "Long" if t.direction == 1 else "Short",
                "Entry Date": str(t.entry_date),
                "Exit Date": str(t.exit_date),
                "Entry Price": f"{t.entry_price:,.4f}",
                "Exit Price": f"{t.exit_price:,.4f}",
                "Duration (bars)": t.duration_bars,
                "Size (USD)": f"{t.size_notional:,.0f}",
                "Gross PnL": f"{t.gross_pnl:+,.2f}",
                "Cost (USD)": f"{t.transaction_cost:.2f}",
                "Net PnL (USD)": f"{t.net_pnl:+,.2f}",
                "Return (%)": f"{t.return_pct:+.2%}",
                "Force Closed": "Yes" if t.force_closed else "No",
            }
            for t in result.trades
        ]
        st.dataframe(pd.DataFrame(full_data), use_container_width=True, hide_index=True)

    with st.expander("Trade statistics"):
        ts = report.trade_statistics
        tc1, tc2, tc3, tc4, tc5 = st.columns(5)
        tc1.metric("Total trades", ts.get("n_trades", 0))
        tc2.metric("Winning", ts.get("n_winning", 0))
        tc3.metric("Losing", ts.get("n_losing", 0))
        tc4.metric("Max consec. wins", ts.get("max_consecutive_wins", 0))
        tc5.metric("Max consec. losses", ts.get("max_consecutive_losses", 0))

with st.expander("Position series (USD notional)"):
    pos_df = result.positions.rename("Position (USD)").to_frame()
    st.line_chart(pos_df, height=160)
