"""Tests for src/validation/ — walk-forward, inference, and MLflow client.

15 tests total:
  - 12 pure unit tests (no data dependency — always run)
  -  1 statistical helper test
  -  2 data-dependent integration tests (skip in CI)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.validation.inference import (
    _norm_cdf,
    _norm_ppf,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    sharpe_se,
)
from src.validation.walk_forward import walk_forward_split

# ── Fixtures ─────────────────────────────────────────────────────────────────

RNG = np.random.default_rng(42)

POSITIVE_RETURNS = pd.Series(RNG.normal(0.001, 0.01, 500))
"""500 daily returns with positive mean → annualized SR clearly positive."""

ZERO_MEAN_RETURNS = pd.Series([0.01, -0.01] * 250)
"""500 alternating returns with exact zero mean → SR = 0, PSR = 0.5."""

LARGE_DATE_RANGE = pd.date_range("2010-01-01", periods=1500, freq="B")
"""1500 business-day DatetimeIndex for split tests."""


# ── Walk-forward split tests ──────────────────────────────────────────────────


def test_walk_forward_split_produces_correct_n_splits() -> None:
    """walk_forward_split() returns exactly n_splits folds."""
    splits = walk_forward_split(
        LARGE_DATE_RANGE, n_splits=5, embargo_bars=5, min_train_bars=252
    )
    assert len(splits) == 5
    for i, split in enumerate(splits):
        assert split.fold_idx == i


def test_walk_forward_split_embargo_bars_excluded() -> None:
    """Embargo bars are excluded: test_start is embargo_bars+1 positions after train_end."""
    embargo = 10
    splits = walk_forward_split(
        LARGE_DATE_RANGE, n_splits=3, embargo_bars=embargo, min_train_bars=252
    )
    for split in splits:
        train_end_ts = pd.Timestamp(split.train_end)
        test_start_ts = pd.Timestamp(split.test_start)

        # Find bar positions in the index
        train_end_pos = LARGE_DATE_RANGE.searchsorted(train_end_ts)
        test_start_pos = LARGE_DATE_RANGE.searchsorted(test_start_ts)

        # test_start_idx = train_end_idx + 1 + embargo_bars  →  gap = embargo + 1 bars
        assert test_start_pos - train_end_pos == embargo + 1, (
            f"Fold {split.fold_idx}: expected gap {embargo + 1}, "
            f"got {test_start_pos - train_end_pos}"
        )


def test_walk_forward_split_raises_on_insufficient_data() -> None:
    """walk_forward_split() raises ValueError when there are too few bars."""
    tiny_dates = pd.date_range("2020-01-01", periods=100, freq="B")
    with pytest.raises(ValueError, match="Insufficient bars"):
        walk_forward_split(tiny_dates, n_splits=5, embargo_bars=10, min_train_bars=252)


def test_walk_forward_split_train_end_before_test_start() -> None:
    """train_end < test_start for every fold (no overlap, no leakage)."""
    splits = walk_forward_split(
        LARGE_DATE_RANGE, n_splits=4, embargo_bars=5, min_train_bars=252
    )
    for split in splits:
        assert split.train_end < split.test_start, (
            f"Fold {split.fold_idx}: train_end {split.train_end} "
            f">= test_start {split.test_start}"
        )


# ── Sharpe SE tests ───────────────────────────────────────────────────────────


def test_sharpe_se_normal_returns_approx_one_over_sqrt_t() -> None:
    """SE for zero-SR normally distributed returns is approximately sqrt(annual/T)."""
    # Zero-mean returns → SR ≈ 0 → SE ≈ sqrt(252/(T-1))
    n_bars = 2520  # 10 years daily
    returns = pd.Series(RNG.normal(0.0, 0.01, n_bars))
    se = sharpe_se(returns)
    expected = math.sqrt(252.0 / (n_bars - 1))
    # Allow ±30% tolerance — actual returns have non-zero mean and non-normal moments
    assert (
        expected * 0.7 < se < expected * 1.3
    ), f"sharpe_se={se:.4f}, expected≈{expected:.4f}"


def test_sharpe_se_nan_for_insufficient_data() -> None:
    """sharpe_se() returns NaN when fewer than 4 observations."""
    assert math.isnan(sharpe_se(pd.Series([0.01, -0.01, 0.005])))
    assert math.isnan(sharpe_se(pd.Series([], dtype=float)))


# ── PSR tests ─────────────────────────────────────────────────────────────────


def test_probabilistic_sharpe_ratio_positive_sr_above_half() -> None:
    """PSR > 0.5 when the observed SR is clearly positive."""
    psr = probabilistic_sharpe_ratio(POSITIVE_RETURNS, sr_benchmark=0.0)
    assert not math.isnan(psr), "PSR should not be NaN for 500-bar positive-SR series"
    assert 0.5 < psr <= 1.0, f"Expected PSR > 0.5 for positive-SR series, got {psr:.4f}"


def test_probabilistic_sharpe_ratio_zero_sr_is_half() -> None:
    """PSR ≈ 0.5 when the observed SR is exactly zero (alternating ±returns)."""
    psr = probabilistic_sharpe_ratio(ZERO_MEAN_RETURNS, sr_benchmark=0.0)
    assert not math.isnan(psr), "PSR should not be NaN for zero-mean series"
    # SR = 0 → z = 0 → PSR = Φ(0) = 0.5 exactly
    assert abs(psr - 0.5) < 1e-6, f"Expected PSR=0.5 for zero-SR series, got {psr:.6f}"


# ── DSR tests ─────────────────────────────────────────────────────────────────


def test_deflated_sharpe_ratio_lower_than_psr_for_many_trials() -> None:
    """DSR < PSR when n_trials > 1 (multiple-testing correction raises the benchmark)."""
    psr = probabilistic_sharpe_ratio(POSITIVE_RETURNS, sr_benchmark=0.0)
    dsr = deflated_sharpe_ratio(POSITIVE_RETURNS, n_trials=100)
    assert not math.isnan(dsr), "DSR should not be NaN"
    assert 0.0 <= dsr <= 1.0, f"DSR out of range: {dsr:.4f}"
    assert dsr < psr, f"DSR ({dsr:.4f}) should be < PSR ({psr:.4f}) for n_trials=100"


def test_expected_max_sharpe_increases_with_n_trials() -> None:
    """Expected max Sharpe is monotonically increasing in n_trials."""
    ems_1 = expected_max_sharpe(1)
    ems_10 = expected_max_sharpe(10)
    ems_100 = expected_max_sharpe(100)
    ems_1000 = expected_max_sharpe(1000)
    assert ems_1 < ems_10, f"E[max SR]: {ems_1:.4f} >= {ems_10:.4f} (n=1 vs n=10)"
    assert ems_10 < ems_100, f"E[max SR]: {ems_10:.4f} >= {ems_100:.4f} (n=10 vs n=100)"
    assert (
        ems_100 < ems_1000
    ), f"E[max SR]: {ems_100:.4f} >= {ems_1000:.4f} (n=100 vs n=1000)"


def test_expected_max_sharpe_zero_for_one_trial() -> None:
    """expected_max_sharpe(1) == 0.0 (no correction for a single trial)."""
    assert expected_max_sharpe(1) == 0.0


# ── _norm_ppf / _norm_cdf tests ───────────────────────────────────────────────


def test_norm_ppf_standard_values() -> None:
    """Beasley-Springer-Moro _norm_ppf accuracy at standard quantiles."""
    assert (
        abs(_norm_ppf(0.975) - 1.96) < 0.001
    ), f"_norm_ppf(0.975) = {_norm_ppf(0.975):.4f}, expected 1.96"
    assert (
        abs(_norm_ppf(0.5) - 0.0) < 0.001
    ), f"_norm_ppf(0.5) = {_norm_ppf(0.5):.4f}, expected 0.0"
    assert (
        abs(_norm_ppf(0.025) - (-1.96)) < 0.001
    ), f"_norm_ppf(0.025) = {_norm_ppf(0.025):.4f}, expected -1.96"
    # Round-trip: _norm_cdf(_norm_ppf(p)) ≈ p
    for p in [0.1, 0.25, 0.5, 0.75, 0.9, 0.975]:
        assert (
            abs(_norm_cdf(_norm_ppf(p)) - p) < 0.001
        ), f"Round-trip failed at p={p}: cdf(ppf(p))={_norm_cdf(_norm_ppf(p)):.4f}"


# ── Data-dependent integration tests (skip in CI) ────────────────────────────

_GOLD_PARQUET = Path("data/processed/continuous/gold.parquet")


@pytest.mark.skipif(
    not _GOLD_PARQUET.exists(),
    reason="Gold parquet not present — skipped in CI",
)
def test_walk_forward_validator_produces_n_folds() -> None:
    """WalkForwardValidator produces exactly n_splits folds and valid PSR/DSR."""
    from src.core.config import Config
    from src.validation.walk_forward import WalkForwardValidator

    config = Config.load("config/")
    validator = WalkForwardValidator(config)
    report = validator.validate(
        asset="gold",
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
        n_splits=5,
        embargo_bars=10,
        n_trials=1,
    )

    assert len(report.folds) == 5, f"Expected 5 folds, got {len(report.folds)}"
    assert 0.0 <= report.psr <= 1.0, f"PSR out of range: {report.psr}"
    assert 0.0 <= report.dsr <= 1.0, f"DSR out of range: {report.dsr}"
    assert (
        report.dsr <= report.psr + 1e-9
    ), f"DSR ({report.dsr:.4f}) should be <= PSR ({report.psr:.4f})"
    assert report.n_splits == 5
    assert report.embargo_bars == 10


@pytest.mark.skipif(
    not _GOLD_PARQUET.exists(),
    reason="Gold parquet not present — skipped in CI",
)
def test_walk_forward_validator_outsample_sharpe_is_mean_of_folds() -> None:
    """outsample_sharpe == mean of test_sharpe across valid folds."""
    from src.core.config import Config
    from src.validation.walk_forward import WalkForwardValidator

    config = Config.load("config/")
    validator = WalkForwardValidator(config)
    report = validator.validate(
        asset="gold",
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
        n_splits=3,
        embargo_bars=5,
        n_trials=1,
    )

    valid_folds = [f for f in report.folds if not math.isnan(f.test_sharpe)]
    if not valid_folds:
        pytest.skip("No valid folds produced — insufficient data window")

    expected_mean = sum(f.test_sharpe for f in valid_folds) / len(valid_folds)
    assert (
        abs(report.outsample_sharpe - expected_mean) < 1e-9
    ), f"outsample_sharpe {report.outsample_sharpe:.6f} != mean of folds {expected_mean:.6f}"


# ── MLflow client test ────────────────────────────────────────────────────────


def test_get_trial_count_falls_back_to_one_when_mlflow_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_trial_count returns 1 when MLflow raises any exception."""
    mock_mlflow = MagicMock()
    mock_mlflow.get_experiment_by_name.side_effect = RuntimeError(
        "MLflow connection refused"
    )
    monkeypatch.setitem(sys.modules, "mlflow", mock_mlflow)

    # Deferred import inside get_trial_count will pick up the mock from sys.modules
    from src.validation.mlflow_client import get_trial_count

    result = get_trial_count("gold", "ema_crossover")
    assert result == 1, f"Expected fallback n_trials=1, got {result}"
