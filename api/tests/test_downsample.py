from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from api.downsample import lttb_ohlcv


@pytest.fixture
def ohlcv_5000() -> pd.DataFrame:
    """5,000-bar synthetic OHLCV DataFrame for downsampler tests."""
    rng = np.random.default_rng(42)
    idx = pd.date_range("2010-01-01", periods=5_000, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": rng.uniform(900, 1_100, 5_000),
            "high": rng.uniform(1_050, 1_150, 5_000),
            "low": rng.uniform(850, 950, 5_000),
            "close": rng.uniform(900, 1_100, 5_000),
            "volume": rng.uniform(1e5, 1e7, 5_000),
        },
        index=idx,
    )


def test_lttb_reduces_to_threshold(ohlcv_5000: pd.DataFrame) -> None:
    result = lttb_ohlcv(ohlcv_5000, threshold=3_000)
    assert len(result) == 3_000


def test_lttb_preserves_first_and_last(ohlcv_5000: pd.DataFrame) -> None:
    result = lttb_ohlcv(ohlcv_5000, threshold=3_000)
    assert result.index[0] == ohlcv_5000.index[0]
    assert result.index[-1] == ohlcv_5000.index[-1]
