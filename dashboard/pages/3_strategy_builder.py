"""Page 3: Strategy Builder — full pipeline orchestration and backtest trigger.

This page connects all Phase 1 layers into a single end-to-end workflow:
    Layer 0 (Data) → Layer 1 (Features) → Layer 2 (Signals + IC)
    → Layer 3 (Backtest) → Layer 4 (Performance) → session_state

Signal evaluation is attached to BacktestResult before PerformanceEngine.compute()
per ADR-007: IC analysis is a precondition for backtest evaluation.

Orchestration is permitted in dashboard code because Layer 8 is the only
layer that composes outputs from multiple layers (Architecture Section 4).
All computation remains in src/ functions — this page only calls them in sequence.

Consumes: Layers 0, 1, 2, 3, 4 via src/ functions only.
See Architecture Section 13 (Dashboard Architecture, Page Map) and
Architecture Section 10 (Signal Research Workflow).
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.backtesting.engine import VectorizedBacktester
from src.backtesting.run_manager import RunManager
from src.core.config import Config
from src.core.types import BacktestResult, PerformanceReport
from src.data.loader import DataLoader
from src.performance.report import PerformanceEngine
from src.research.momentum import Momentum
from src.research.moving_averages import EMA
from src.research.oscillators import RSI
from src.research.pipeline import FeaturePipeline
from src.signal.breakout import DonchianBreakoutSignal
from src.signal.evaluation import SignalEvaluator
from src.signal.position import PositionSignalConstructor
from src.signal.reversion import RSIReversionSignal
from src.signal.trend import EMACrossoverSignal, MomentumSignal

st.set_page_config(page_title="Strategy Builder", layout="wide")

ASSET_DISPLAY: dict[str, str] = {
    "gold": "Gold (GC=F)",
    "silver": "Silver (SI=F)",
    "copper": "Copper (HG=F)",
    "wti": "WTI Crude (CL=F)",
    "brent": "Brent Crude (BZ=F)",
    "natural_gas": "Natural Gas (NG=F)",
}

STRATEGY_DISPLAY: dict[str, str] = {
    "ema_crossover": "EMA Crossover (trend)",
    "momentum": "Momentum (trend)",
    "rsi_reversion": "RSI Reversion (mean-reversion)",
    "donchian_breakout": "Donchian Breakout (breakout)",
}


@st.cache_resource
def _get_config() -> Config:
    return Config.load("config/")


def _get_indicators(strategy_name: str, params: dict[str, Any]) -> list:
    """Return list of Indicator instances required for this strategy.

    Called from _run_full_pipeline(). Returns src/ Indicator objects only.
    No computation — indicator objects are factory-created here.
    """
    if strategy_name == "ema_crossover":
        return [EMA(period=params["fast_period"]), EMA(period=params["slow_period"])]
    if strategy_name == "momentum":
        return [Momentum(lookback=params["lookback_period"])]
    if strategy_name == "rsi_reversion":
        return [RSI(period=params["period"])]
    if strategy_name == "donchian_breakout":
        return []  # Donchian reads OHLCV columns directly — no pre-computed indicators
    return []


def _get_signal_generator(strategy_name: str, params: dict[str, Any]):
    """Return a SignalGenerator instance for this strategy and parameters.

    Called from _run_full_pipeline(). Returns a src/ SignalGenerator object.
    No computation — signal generator is factory-created here.
    """
    if strategy_name == "ema_crossover":
        return EMACrossoverSignal(
            fast_period=params["fast_period"],
            slow_period=params["slow_period"],
        )
    if strategy_name == "momentum":
        return MomentumSignal(
            lookback=params["lookback_period"],
            z_score_window=params.get("z_score_window", 63),
        )
    if strategy_name == "rsi_reversion":
        return RSIReversionSignal(period=params["period"])
    if strategy_name == "donchian_breakout":
        return DonchianBreakoutSignal(channel_period=params["channel_period"])
    raise ValueError(f"Unknown strategy: {strategy_name}")


def _run_full_pipeline(
    asset: str,
    strategy_name: str,
    params: dict[str, Any],
    config: Config,
) -> tuple[BacktestResult, PerformanceReport]:
    """Execute the complete Phase 1 research pipeline.

    Follows Architecture Section 10 (Signal Research Workflow) exactly:
        Step 1: Load asset data (Layer 0)
        Step 2: Build feature frame (Layer 1)
        Step 3: Generate raw signal (Layer 2)
        Step 4: Evaluate signal quality — ADR-007 precondition (Layer 2)
        Step 5: Construct position signal (Layer 2)
        Step 6: Run backtest (Layer 3)
        Step 7: Attach signal evaluation to result (orchestration)
        Step 8: Compute performance (Layer 4)
        Step 9: Persist run artifacts (Layer 3)

    This function calls only src/ layer functions. All computation is
    performed by the called functions. This function is the orchestration
    layer permitted by Architecture Section 4 (only Layer 8 may compose
    multiple layers simultaneously).

    Args:
        asset: Asset identifier (e.g., "gold").
        strategy_name: Strategy key from STRATEGY_DISPLAY.
        params: Parameter dict from Streamlit sidebar widgets.
        config: Loaded Config instance.

    Returns:
        (BacktestResult, PerformanceReport) tuple. BacktestResult.signal_evaluation
        is populated if IC evaluation succeeded; None otherwise.
    """
    # Step 1: Load data (Layer 0)
    ohlcv = DataLoader(config).load(asset)

    # Step 2: Build feature frame (Layer 1)
    indicators = _get_indicators(strategy_name, params)
    ff = FeaturePipeline(indicators).compute(ohlcv, asset=asset)

    # Step 3: Generate raw signal (Layer 2)
    signal_gen = _get_signal_generator(strategy_name, params)
    raw_signal = signal_gen.generate(ff)

    # Step 4: Evaluate signal quality — ADR-007: this is a precondition, not optional
    try:
        signal_evaluation = SignalEvaluator(asset).evaluate(raw_signal, ohlcv)
    except ValueError:
        # Insufficient valid observations (< 10 aligned bars after NaN removal)
        signal_evaluation = None

    # Step 5: Construct position signal (Layer 2)
    threshold = float(params.get("signal_threshold", 0.0))
    position_signal = PositionSignalConstructor().build(raw_signal, threshold=threshold)

    # Step 6: Run backtest (Layer 3)
    backtester = VectorizedBacktester(
        asset=asset,
        strategy_name=strategy_name,
        signal_name=signal_gen.name,
        config=config,
        parameters=params,
    )
    result = backtester.run(position_signal, ohlcv)

    # Step 7: Attach signal evaluation to result (orchestration)
    # VectorizedBacktester.run() always sets signal_evaluation=None.
    # This is the only place in the platform where signal_evaluation is
    # attached to a BacktestResult for use by PerformanceEngine.
    result.signal_evaluation = signal_evaluation

    # Step 8: Compute performance (Layer 4)
    report = PerformanceEngine().compute(result)

    # Step 9: Persist run artifacts (Layer 3)
    manager = RunManager(config)
    manager.save(result)
    manager.save_metrics(result.run_id, report)

    return result, report


# -----------------------------------------------------------------------
# Page layout
# -----------------------------------------------------------------------
st.title("⚙️ Strategy Builder")
st.caption(
    "Runs the full pipeline: Data → Features → Signal (IC eval) → Backtest → Performance. "
    "Results are stored and accessible on pages 4 and 5."
)

# -----------------------------------------------------------------------
# Sidebar: strategy configuration
# -----------------------------------------------------------------------
config = _get_config()

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
        st.error("No data available. See Market Overview for setup.")
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
            "Signal threshold", 0.0, 100.0, 0.0
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
    run_button = st.button("▶ Run Backtest", type="primary", use_container_width=True)

# -----------------------------------------------------------------------
# Main panel: description + run status
# -----------------------------------------------------------------------
col_desc, col_status = st.columns([1, 1])

with col_desc:
    st.subheader("Strategy Description")
    descriptions = {
        "ema_crossover": (
            f"**EMA Crossover (trend)** — Long when EMA({params.get('fast_period', 50)}) > "
            f"EMA({params.get('slow_period', 200)}), short otherwise. "
            "Classic trend-following signal."
        ),
        "momentum": (
            f"**Momentum (trend)** — Z-scored {params.get('lookback_period', 20)}-bar "
            "rate of change. Positive momentum → long, negative → short."
        ),
        "rsi_reversion": (
            f"**RSI Reversion** — Long when RSI({params.get('period', 14)}) < 50 "
            "(oversold), short when RSI > 50 (overbought). Mean-reversion."
        ),
        "donchian_breakout": (
            f"**Donchian Breakout** — Position based on close price relative to "
            f"{params.get('channel_period', 20)}-bar high/low channel midpoint. "
            "Breakout trend signal."
        ),
    }
    st.markdown(descriptions.get(strategy, ""))

with col_status:
    if "last_run_strategy" in st.session_state:
        st.success(
            f"Last run: **{STRATEGY_DISPLAY.get(st.session_state['last_run_strategy'], '')}** "
            f"on **{ASSET_DISPLAY.get(st.session_state['last_run_asset'], '')}**. "
            "See pages 4 and 5 for results."
        )

# -----------------------------------------------------------------------
# Execute pipeline on button click
# -----------------------------------------------------------------------
if run_button:
    # Validate parameter consistency
    if strategy == "ema_crossover" and params["fast_period"] >= params["slow_period"]:
        st.error(
            f"Fast EMA ({params['fast_period']}) must be less than Slow EMA ({params['slow_period']})."
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

    # Quick summary after successful run
    st.success(f"Run complete — ID: `{result.run_id}`")

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

    ic_value = (
        result.signal_evaluation.ic if result.signal_evaluation is not None else None
    )
    summary_col1.metric(
        "IC",
        f"{ic_value:.4f}" if ic_value is not None else "n/a",
        help="IC < 0.02: noise. 0.02-0.05: weak. ≥ 0.05: meaningful.",
    )
    summary_col2.metric("Sharpe", f"{report.scalar_metrics['sharpe']:.3f}")
    summary_col3.metric("Max Drawdown", f"{report.scalar_metrics['max_drawdown']:.2%}")
    summary_col4.metric("Trades", len(result.trades))

    st.caption(
        "Navigate to **Backtest Results** or **Performance Analysis** to view full output."
    )
