"""Backend tests for WTIBrentSpreadSignal.

4 tests: 2 pure unit (always run), 2 data-dependent (skip if no OHLCV).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SKIP_NO_DATA = pytest.mark.skipif(
    not Path("data/processed/continuous/wti.parquet").exists(),
    reason="WTI Parquet not available in CI",
)


def test_adf_test_stationary_series() -> None:
    """_adf_test() correctly identifies a stationary (mean-reverting) series."""
    from src.signal.spread import WTIBrentSpreadSignal

    rng = np.random.default_rng(42)
    n = 500
    y = np.zeros(n)
    for i in range(1, n):
        y[i] = 0.5 * y[i - 1] + rng.normal(0, 1)
    series = pd.Series(y)

    is_coint, adf_stat, pval = WTIBrentSpreadSignal._adf_test(series)
    assert (
        is_coint
    ), f"Strong AR(1) series should be stationary. ADF={adf_stat:.4f}, p={pval:.4f}"
    assert (
        adf_stat < -2.0
    ), f"ADF stat {adf_stat:.4f} should be < -2.0 for stationary series"
    assert pval < 0.10, f"p-value {pval:.4f} should be < 0.10 for stationary series"


def test_adf_test_random_walk_not_stationary() -> None:
    """_adf_test() correctly identifies a random walk (non-stationary) series."""
    from src.signal.spread import WTIBrentSpreadSignal

    rng = np.random.default_rng(99)
    n = 500
    y = np.cumsum(rng.normal(0, 1, n))
    series = pd.Series(y)

    is_coint, adf_stat, pval = WTIBrentSpreadSignal._adf_test(series)
    assert (
        not is_coint
    ), f"Random walk should NOT be stationary. ADF={adf_stat:.4f}, p={pval:.4f}"
    assert pval >= 0.10, f"p-value {pval:.4f} should be >= 0.10 for random walk"


@SKIP_NO_DATA
def test_spread_signal_returns_series_on_wti() -> None:
    """WTIBrentSpreadSignal.generate() returns named pd.Series on WTI."""
    from src.core.config import Config
    from src.data.loader import DataLoader
    from src.research.pipeline import FeaturePipeline
    from src.signal.spread import WTIBrentSpreadSignal

    config = Config.load()
    signal = WTIBrentSpreadSignal(config=config, lookback=63)

    ohlcv = DataLoader(config).load("wti")
    frame = FeaturePipeline([]).compute(ohlcv, asset="wti")

    result = signal.generate(frame)

    assert isinstance(result, pd.Series)
    assert result.name == "wti_brent_spread"
    assert len(result) == len(frame.data.index)
    assert result.index.equals(frame.data.index)


@SKIP_NO_DATA
def test_spread_signal_raises_on_non_wti_asset() -> None:
    """WTIBrentSpreadSignal raises ValueError when called on non-WTI asset."""
    from src.core.config import Config
    from src.data.loader import DataLoader
    from src.research.pipeline import FeaturePipeline
    from src.signal.spread import WTIBrentSpreadSignal

    config = Config.load()
    signal = WTIBrentSpreadSignal(config=config)

    ohlcv = DataLoader(config).load("gold")
    frame = FeaturePipeline([]).compute(ohlcv, asset="gold")

    with pytest.raises(ValueError, match="wti"):
        signal.generate(frame)
