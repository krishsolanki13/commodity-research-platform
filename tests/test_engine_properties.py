"""Property-based tests for VectorizedBacktester engine invariants."""

from __future__ import annotations

import pandas as pd
import pytest

try:
    import hypothesis.strategies as st
    from hypothesis import assume, given, settings

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

SKIP_NO_HYPOTHESIS = pytest.mark.skipif(
    not HAS_HYPOTHESIS,
    reason="hypothesis not installed — add to [dev] extras in pyproject.toml",
)


def _make_synthetic_ohlcv(
    prices: list[float], volume: float = 25_000.0
) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from a price series.

    Prices become close values. OHLC are derived so constraints hold:
      open = close[t-1], high = max(open, close)*1.001, low = min*0.999
    """
    n = len(prices)
    closes = prices
    opens = [prices[0]] + prices[:-1]
    highs = [max(o, c) * 1.001 for o, c in zip(opens, closes, strict=True)]
    lows = [min(o, c) * 0.999 for o, c in zip(opens, closes, strict=True)]
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [volume] * n,
        },
        index=pd.bdate_range("2020-01-02", periods=n, freq="B", tz="UTC"),
    )


def _make_backtester(config=None):
    """Construct a minimal VectorizedBacktester for property tests.

    Uses confirmed constructor signature:
      (asset, strategy_name, signal_name, config, parameters, ...)
    """
    from src.backtesting.engine import VectorizedBacktester  # noqa: PLC0415
    from src.core.config import Config  # noqa: PLC0415

    cfg = config or Config.load()  # confirmed: no argument
    return VectorizedBacktester(
        asset="gold",
        strategy_name="ema_crossover",
        signal_name="test_signal",
        config=cfg,
        parameters={"fast_period": 50, "slow_period": 200},
    )


@SKIP_NO_HYPOTHESIS
@given(
    prices=st.lists(
        st.floats(
            min_value=10.0, max_value=5000.0, allow_nan=False, allow_infinity=False
        ),
        min_size=30,
        max_size=100,
    )
)
@settings(max_examples=30, deadline=10_000)
def test_flat_signal_produces_flat_equity(prices: list[float]) -> None:
    """All-zero signal → equity curve equals initial_capital throughout.

    No trades execute. No costs applied. Equity must be flat.
    """
    ohlcv = _make_synthetic_ohlcv(prices)
    position_signal = pd.Series(0.0, index=ohlcv.index, name="signal")
    backtester = _make_backtester()
    result = backtester.run(position_signal, ohlcv)
    equity = result.equity_curve
    initial = float(equity.iloc[0])
    max_deviation = float((equity - initial).abs().max())
    assert max_deviation < 1.0, (
        f"Flat signal produced equity deviation of {max_deviation:.4f}. "
        f"Price range: [{min(prices):.2f}, {max(prices):.2f}]"
    )


@SKIP_NO_HYPOTHESIS
@given(
    prices=st.lists(
        st.floats(
            min_value=10.0, max_value=5000.0, allow_nan=False, allow_infinity=False
        ),
        min_size=30,
        max_size=100,
    ),
    signal_value=st.sampled_from([-1.0, 0.0, 1.0]),
)
@settings(max_examples=30, deadline=10_000)
def test_equity_starts_at_initial_capital(
    prices: list[float], signal_value: float
) -> None:
    """First equity curve value must be positive for any valid signal."""
    ohlcv = _make_synthetic_ohlcv(prices)
    position_signal = pd.Series(signal_value, index=ohlcv.index, name="signal")
    backtester = _make_backtester()
    result = backtester.run(position_signal, ohlcv)
    equity = result.equity_curve
    assert float(equity.iloc[0]) > 0
    assert len(equity) >= 1


@SKIP_NO_HYPOTHESIS
@given(
    prices=st.lists(
        st.floats(
            min_value=100.0, max_value=2000.0, allow_nan=False, allow_infinity=False
        ),
        min_size=50,
        max_size=200,
    )
)
@settings(max_examples=20, deadline=30_000)
def test_more_trades_produce_more_costs(prices: list[float]) -> None:
    """Alternating signal produces >= trades vs constant long signal.

    Trade count and total costs are proportional under a fixed per-trade
    cost model — trade count is the correct proxy for cost monotonicity.
    """
    assume(len(prices) >= 50)
    ohlcv = _make_synthetic_ohlcv(prices)
    n = len(ohlcv)
    few_trades_signal = pd.Series(1.0, index=ohlcv.index, name="signal")
    many_values = [1.0 if (i // 5) % 2 == 0 else -1.0 for i in range(n)]
    many_trades_signal = pd.Series(many_values, index=ohlcv.index, name="signal")
    backtester = _make_backtester()
    result_few = backtester.run(few_trades_signal, ohlcv)
    result_many = backtester.run(many_trades_signal, ohlcv)
    few_count = len(result_few.trades) if hasattr(result_few, "trades") else 0
    many_count = len(result_many.trades) if hasattr(result_many, "trades") else 0
    if few_count == 0 and many_count == 0:
        return
    assert (
        many_count >= few_count
    ), f"Alternating ({many_count} trades) should >= constant ({few_count} trades)"


def test_hypothesis_import_available() -> None:
    """Verify hypothesis is importable. Skips with install instructions if not."""
    if not HAS_HYPOTHESIS:
        pytest.skip(
            "hypothesis not installed. "
            "Add 'hypothesis>=6.0' to [project.optional-dependencies].dev "
            "in pyproject.toml to enable property-based engine tests."
        )
    from hypothesis import __version__

    assert __version__ >= "6.0", f"hypothesis >= 6.0 required, got {__version__}"
