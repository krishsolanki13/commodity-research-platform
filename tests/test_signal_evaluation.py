"""Tests for SignalEvaluator: IC, ICIR, decay, and turnover.

Verifies correctness of signal quality metrics per ADR-007.
IC analysis is a precondition for backtesting — these tests validate
the gatekeeping mechanism of the signal research workflow.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.types import SignalEvaluation
from src.signal.evaluation import SignalEvaluator


def test_ic_perfect_signal_approximately_one(gold_ohlcv: pd.DataFrame) -> None:
    """IC of a perfect signal (signal[t] = forward_return[t+1]) is approximately 1.0."""
    close = gold_ohlcv["close"]
    log_close = np.log(close)

    # forward_return[t] = log(close[t+1] / close[t])
    forward_return = log_close.diff(1).shift(-1)
    # Perfect signal: signal[t] equals what we are trying to predict
    perfect_signal = forward_return.rename("perfect_signal")

    evaluator = SignalEvaluator("gold")
    result = evaluator.evaluate(perfect_signal, gold_ohlcv)

    assert (
        abs(result.ic - 1.0) < 0.001
    ), f"IC of perfect signal should be ≈ 1.0, got {result.ic:.6f}"


def test_ic_random_signal_near_zero(gold_ohlcv: pd.DataFrame) -> None:
    """IC of a random signal is close to zero (no predictive content)."""
    rng = np.random.default_rng(seed=42)
    random_signal = pd.Series(
        rng.normal(0, 1, len(gold_ohlcv)),
        index=gold_ohlcv.index,
        name="random_noise",
    )

    evaluator = SignalEvaluator("gold")
    result = evaluator.evaluate(random_signal, gold_ohlcv)

    # Random signal IC should be near 0; generous tolerance for small samples
    assert (
        abs(result.ic) < 0.20
    ), f"IC of random signal should be near 0, got {result.ic:.4f}"


def test_icir_is_finite_float(gold_ohlcv: pd.DataFrame) -> None:
    """ICIR is a finite float for a well-behaved signal."""
    close = gold_ohlcv["close"]
    # Use lagged returns as a simple non-random signal
    signal = np.log(close).diff().shift(1).rename("lagged_return")

    evaluator = SignalEvaluator("gold")
    result = evaluator.evaluate(signal, gold_ohlcv)

    assert isinstance(result.icir, float), "ICIR must be a float"
    assert np.isfinite(result.icir), f"ICIR must be finite, got {result.icir}"


def test_ic_decay_has_correct_horizons(gold_ohlcv: pd.DataFrame) -> None:
    """ic_decay dict contains exactly the keys {1, 2, 5, 10, 20}."""
    close = gold_ohlcv["close"]
    signal = np.log(close).diff().shift(1).rename("test_signal")

    evaluator = SignalEvaluator("gold")
    result = evaluator.evaluate(signal, gold_ohlcv)

    assert set(result.ic_decay.keys()) == {
        1,
        2,
        5,
        10,
        20,
    }, f"ic_decay keys must be {{1,2,5,10,20}}, got {set(result.ic_decay.keys())}"


def test_signal_evaluation_returns_correct_types(gold_ohlcv: pd.DataFrame) -> None:
    """SignalEvaluator.evaluate() returns a SignalEvaluation with correct field types."""
    close = gold_ohlcv["close"]
    signal = np.log(close).diff().shift(1).rename("typed_test")

    evaluator = SignalEvaluator("gold")
    result = evaluator.evaluate(signal, gold_ohlcv)

    assert isinstance(
        result, SignalEvaluation
    ), f"Expected SignalEvaluation, got {type(result).__name__}"
    assert isinstance(result.ic, float)
    assert isinstance(result.icir, float)
    assert isinstance(result.turnover, float)
    assert isinstance(result.ic_decay, dict)
    assert result.asset == "gold"
    assert result.signal_name == "typed_test"
