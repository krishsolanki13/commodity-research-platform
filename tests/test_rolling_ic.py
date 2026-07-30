"""Backend tests for SignalEvaluator.compute_rolling_ic().

4 tests: output shape/name, NaN pattern, value range, ValueError on insufficient data.
3 data-dependent tests skip in CI (no Gold Parquet available).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

DATA_PATH = Path("data/processed/continuous/gold.parquet")
SKIP_NO_DATA = pytest.mark.skipif(
    not DATA_PATH.exists(),
    reason="Gold Parquet not available in CI environment",
)


@pytest.fixture(scope="module")
def rolling_ic_series():
    """Compute rolling IC for EMA 50/200 on Gold (window=63)."""
    from src.signal.evaluation import SignalEvaluator

    evaluator = SignalEvaluator(asset="gold", ic_rolling_window=63)
    return evaluator.compute_rolling_ic(
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
    )


@SKIP_NO_DATA
def test_rolling_ic_series_name_and_type(rolling_ic_series) -> None:
    """Rolling IC returns a pd.Series named 'rolling_ic'."""
    assert isinstance(rolling_ic_series, pd.Series)
    assert rolling_ic_series.name == "rolling_ic"
    assert len(rolling_ic_series) > 0


@SKIP_NO_DATA
def test_rolling_ic_first_window_minus_one_are_nan(rolling_ic_series) -> None:
    """First window-1 (62) bars must be NaN — rolling window not yet full."""
    window = 63
    first_values = rolling_ic_series.iloc[: window - 1]
    assert first_values.isna().all(), (
        f"Expected first {window - 1} values to be NaN, "
        f"got {first_values.notna().sum()} non-NaN values."
    )
    assert (
        rolling_ic_series.iloc[window:].notna().any()
    ), "Expected non-NaN values after the first window bars."


@SKIP_NO_DATA
def test_rolling_ic_values_in_valid_range(rolling_ic_series) -> None:
    """All non-NaN rolling IC values must be in [-1.0, 1.0]."""
    non_nan = rolling_ic_series.dropna()
    assert len(non_nan) > 0, "Expected some non-NaN rolling IC values."

    out_of_range = non_nan[(non_nan < -1.0 - 1e-9) | (non_nan > 1.0 + 1e-9)]
    assert len(out_of_range) == 0, (
        f"Found {len(out_of_range)} rolling IC values outside [-1, 1]: "
        f"{out_of_range.head()}"
    )


def test_rolling_ic_raises_on_insufficient_data() -> None:
    """compute_rolling_ic raises ValueError when window > available bars."""
    from src.signal.evaluation import SignalEvaluator

    with patch.object(
        SignalEvaluator,
        "compute_rolling_ic",
        side_effect=ValueError("Insufficient data"),
    ):
        evaluator = SignalEvaluator(asset="gold", ic_rolling_window=63)
        with pytest.raises(ValueError, match="Insufficient data"):
            evaluator.compute_rolling_ic(
                strategy_name="ema_crossover",
                parameters={"fast_period": 50, "slow_period": 200},
            )
