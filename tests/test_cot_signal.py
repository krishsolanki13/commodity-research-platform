"""Backend tests for COTPositioningSignal.

5 tests: 2 pure unit (always run), 3 data-dependent (skip if no COT data).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.signal.cot import COTPositioningSignal

pytestmark_skip = pytest.mark.skipif(
    not Path("data/processed/cot/gold.parquet").exists(),
    reason="COT data not acquired — run scripts/acquire_cot_data.py",
)


@pytest.fixture
def config():
    from src.core.config import Config

    return Config.load()


@pytest.fixture
def ohlcv_gold(config):
    from src.data.loader import DataLoader

    return DataLoader(config).load("gold")


def test_cot_signal_name() -> None:
    """COTPositioningSignal.name is 'cot_positioning' (DEV-EM7-1)."""
    sig = COTPositioningSignal(config=MagicMock())
    assert sig.name == "cot_positioning"


def test_cot_signal_returns_flat_when_no_data() -> None:
    """Missing COT data returns flat zero series named cot_positioning."""
    from src.data.cot_loader import COTDataLoader

    sig = COTPositioningSignal(config=MagicMock())
    mock_frame = MagicMock()
    mock_frame.asset = "brent"
    mock_frame.data.index = pd.bdate_range("2024-01-02", periods=10, freq="B", tz="UTC")

    with patch.object(COTDataLoader, "load", return_value=pd.DataFrame()):
        result = sig.generate(mock_frame)

    assert (result == 0.0).all()
    assert result.name == "cot_positioning"


@pytestmark_skip
def test_cot_signal_values_are_valid(config, ohlcv_gold) -> None:
    """Generated signal values are only in {-1.0, 0.0, 1.0}."""
    from src.research.pipeline import FeaturePipeline

    feature_frame = FeaturePipeline([]).compute(ohlcv_gold, asset="gold")
    result = COTPositioningSignal(config=config).generate(feature_frame)

    assert set(result.unique()).issubset({-1.0, 0.0, 1.0})


@pytestmark_skip
def test_cot_signal_index_matches_feature_frame(config, ohlcv_gold) -> None:
    """Signal index equals feature_frame.data.index."""
    from src.research.pipeline import FeaturePipeline

    feature_frame = FeaturePipeline([]).compute(ohlcv_gold, asset="gold")
    result = COTPositioningSignal(config=config).generate(feature_frame)

    assert result.index.equals(feature_frame.data.index)


@pytestmark_skip
def test_cot_percentile_thresholds_produce_signals(config, ohlcv_gold) -> None:
    """Tight thresholds force non-zero signal entries."""
    from src.research.pipeline import FeaturePipeline

    feature_frame = FeaturePipeline([]).compute(ohlcv_gold, asset="gold")
    result = COTPositioningSignal(
        config=config, upper_pct=50.0, lower_pct=50.0
    ).generate(feature_frame)

    assert (result != 0).sum() > 0
