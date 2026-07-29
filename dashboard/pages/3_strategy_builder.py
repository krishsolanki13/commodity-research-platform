"""Page 3: Strategy Builder — full pipeline orchestration and backtest execution.

This page is the only location where BacktestResult.signal_evaluation is
attached. VectorizedBacktester.run() always sets it to None. _run_full_pipeline()
attaches the SignalEvaluation from Step 4 before calling PerformanceEngine.
This satisfies ADR-007: IC evaluation as a precondition for backtesting.

Consumes: Layers 0, 1, 2, 3, 4 via src/ functions. No computation in this file.
See Architecture Section 13 and Architecture Section 10 (Signal Research Workflow).
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from dashboard.components._theme import inject_global_css, render_kpi_row
from src.backtesting.engine import VectorizedBacktester
from src.backtesting.pipeline_builder import build_pipeline_components
from src.backtesting.run_manager import RunManager
from src.core.config import Config
from src.core.types import BacktestResult, PerformanceReport
from src.data.loader import DataLoader
from src.performance.report import PerformanceEngine
from src.research.pipeline import FeaturePipeline
from src.signal.evaluation import SignalEvaluator
from src.signal.position import PositionSignalConstructor

st.set_page_config(page_title="Strategy Builder", layout="wide")

inject_global_css()

ASSET_DISPLAY: dict[str, str] = {
    "gold": "Gold (GC=F)",
    "silver": "Silver (SI=F)",
    "copper": "Copper (HG=F)",
    "wti": "WTI Crude (CL=F)",
    "brent": "Brent Crude (BZ=F)",
    "natural_gas": "Natural Gas (NG=F)",
}

STRATEGY_DISPLAY: dict[str, str] = {
    "ema_crossover": "EMA Crossover (trend-following)",
    "momentum": "Momentum (trend-following)",
    "rsi_reversion": "RSI Reversion (mean-reversion)",
    "donchian_breakout": "Donchian Breakout (breakout)",
}


@st.cache_resource
def _get_config() -> Config:
    return Config.load("config/")


def _run_full_pipeline(
    asset: str,
    strategy_name: str,
    params: dict[str, Any],
    config: Config,
) -> tuple[BacktestResult, PerformanceReport]:
    """Execute the complete Phase 1 research pipeline.

    Architecture Section 10 (Signal Research Workflow):
        Step 1: Load data                         (Layer 0)
        Step 2: Build feature frame               (Layer 1)
        Step 3: Generate raw signal               (Layer 2)
        Step 4: Evaluate signal quality — IC gate (Layer 2 · ADR-007)
        Step 5: Construct position signal         (Layer 2)
        Step 6: Run backtest                      (Layer 3)
        Step 7: Attach signal evaluation          (orchestration)
        Step 8: Compute performance               (Layer 4)
        Step 9: Persist artifacts                 (Layer 3)
    """
    ohlcv = DataLoader(config).load(asset)
    indicators, signal_gen = build_pipeline_components(
        strategy_name=strategy_name,
        parameters=params,
        config=config,
    )
    ff = FeaturePipeline(indicators).compute(ohlcv, asset=asset)
    raw_signal = signal_gen.generate(ff)

    try:
        signal_evaluation = SignalEvaluator(asset).evaluate(raw_signal, ohlcv)
    except ValueError:
        signal_evaluation = None  # Insufficient data — proceeds without IC

    threshold = float(params.get("signal_threshold", 0.0))
    position_signal = PositionSignalConstructor().build(raw_signal, threshold=threshold)

    result = VectorizedBacktester(
        asset=asset,
        strategy_name=strategy_name,
        signal_name=signal_gen.name,
        config=config,
        parameters=params,
    ).run(position_signal, ohlcv)

    # Attach IC evaluation — the only location in the platform where this field is set
    result.signal_evaluation = signal_evaluation

    report = PerformanceEngine().compute(result)
    manager = RunManager(config)
    manager.save(result)
    manager.save_metrics(result.run_id, report)

    return result, report


# ── Page layout ───────────────────────────────────────────────────────────────
st.title("Strategy Builder")
st.caption(
    "Runs the complete pipeline: Data → Features → Signal (IC evaluation) → "
    "Backtest → Performance Attribution. Results are stored and visible on pages 4 and 5."
)

config = _get_config()

# ── Sidebar: configuration ────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")

    available_assets = []
    for key in ASSET_DISPLAY:
        try:
            DataLoader(config).load(key)
            available_assets.append(key)
        except Exception:  # noqa: BLE001
            pass

    if not available_assets:
        st.error("No data available. Run: python scripts/acquire_data.py")
        st.stop()

    asset = st.selectbox(
        "Asset", options=available_assets, format_func=lambda k: ASSET_DISPLAY[k]
    )
    strategy = st.selectbox(
        "Strategy",
        options=list(STRATEGY_DISPLAY.keys()),
        format_func=lambda k: STRATEGY_DISPLAY[k],
    )

    st.divider()
    st.subheader("Parameters")

    params: dict[str, Any] = {}
    if strategy == "ema_crossover":
        params["fast_period"] = st.slider("Fast EMA period", 5, 100, 50)
        params["slow_period"] = st.slider("Slow EMA period", 50, 500, 200)
        params["signal_threshold"] = st.number_input(
            "Signal threshold (flat zone)", 0.0, 200.0, 0.0
        )
    elif strategy == "momentum":
        params["lookback_period"] = st.slider("Lookback period (bars)", 5, 60, 20)
        params["z_score_window"] = st.slider("Z-score window (bars)", 20, 126, 63)
        params["signal_threshold"] = st.number_input(
            "Signal threshold", 0.0, 2.0, 0.5, step=0.1
        )
    elif strategy == "rsi_reversion":
        params["period"] = st.slider("RSI period", 5, 30, 14)
        params["signal_threshold"] = st.number_input(
            "Signal threshold", 0.0, 1.0, 0.0, step=0.05
        )
    elif strategy == "donchian_breakout":
        params["channel_period"] = st.slider("Channel period (bars)", 5, 60, 20)
        params["signal_threshold"] = st.number_input(
            "Signal threshold", 0.0, 1.0, 0.0, step=0.05
        )

    st.divider()
    run_button = st.button("Run Backtest", type="primary")

# ── Main panel ────────────────────────────────────────────────────────────────
desc_col, status_col = st.columns([1, 1])

with desc_col:
    st.subheader("Strategy Description")
    descriptions = {
        "ema_crossover": (
            f"**EMA Crossover (trend-following)** — Long when EMA({params.get('fast_period', 50)}) "
            f"exceeds EMA({params.get('slow_period', 200)}), short when below. "
            "Signal = EMA(fast) - EMA(slow), a continuous raw signal before discretization."
        ),
        "momentum": (
            f"**Momentum (trend-following)** — Z-scored {params.get('lookback_period', 20)}-bar "
            "rate of change. Positive momentum implies continued price appreciation."
        ),
        "rsi_reversion": (
            f"**RSI Reversion (mean-reversion)** — Generates a long signal when RSI({params.get('period', 14)}) "
            "indicates oversold conditions (RSI < 50), short when overbought. "
            "Raw signal = -(RSI - 50) / 50, bounded in [-1, +1]."
        ),
        "donchian_breakout": (
            f"**Donchian Breakout** — Position based on close price relative to "
            f"{params.get('channel_period', 20)}-bar high/low channel midpoint. "
            "Channel computed on prior bars to avoid look-ahead bias per ADR-002."
        ),
    }
    st.markdown(descriptions.get(strategy, ""))

with status_col:
    if "last_run_strategy" in st.session_state:
        st.success(
            f"Last run: **{STRATEGY_DISPLAY.get(st.session_state['last_run_strategy'], '')}** "
            f"on **{ASSET_DISPLAY.get(st.session_state['last_run_asset'], '')}**. "
            "Pages 4 and 5 show the results."
        )

# ── Run ───────────────────────────────────────────────────────────────────────
if run_button:
    if strategy == "ema_crossover" and params["fast_period"] >= params["slow_period"]:
        st.error(
            f"Fast EMA ({params['fast_period']}) must be less than "
            f"Slow EMA ({params['slow_period']})."
        )
        st.stop()

    with st.spinner(
        f"Running {STRATEGY_DISPLAY[strategy]} on {ASSET_DISPLAY[asset]}..."
    ):
        try:
            result, report = _run_full_pipeline(asset, strategy, params, config)
            st.session_state["backtest_result"] = result
            st.session_state["performance_report"] = report
            st.session_state["last_run_asset"] = asset
            st.session_state["last_run_strategy"] = strategy
        except Exception as exc:  # noqa: BLE001
            st.error(f"Pipeline failed: {type(exc).__name__}: {exc}")
            st.stop()

    st.success(f"Run complete — ID: `{result.run_id}`")

    ic_val = (
        result.signal_evaluation.ic if result.signal_evaluation is not None else None
    )
    ic_display = f"{ic_val:.6f}" if ic_val is not None else "n/a"
    ic_context: str | None = None
    if ic_val is not None:
        if ic_val >= 0.05:
            ic_context = "Meaningful positive"
        elif ic_val <= -0.05:
            ic_context = "Meaningful inverse"
        elif abs(ic_val) >= 0.02:
            ic_context = "Weak signal"
        else:
            ic_context = "Noise"

    render_kpi_row(
        [
            ("IC", ic_display, ic_context),
            ("Sharpe", f"{report.scalar_metrics['sharpe']:.4f}", None),
            ("Max Drawdown", f"{report.scalar_metrics['max_drawdown']:.2%}", None),
            ("Win Rate", f"{report.scalar_metrics['win_rate']:.1%}", None),
            ("Trades", str(len(result.trades)), None),
        ]
    )

    st.caption(
        "Navigate to **Backtest Results** (page 4) or **Performance Analysis** (page 5) for full output."
    )
