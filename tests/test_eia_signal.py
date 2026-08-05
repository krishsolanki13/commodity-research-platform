"""Backend tests for EIAInventorySignal.

4 tests: 2 pure unit (always run), 2 data-dependent (skip if no EIA data).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.signal.eia import EIAInventorySignal

pytestmark_skip = pytest.mark.skipif(
    not Path("data/processed/eia/wti.parquet").exists(),
    reason="EIA data not acquired — run scripts/acquire_eia_data.py",
)


@pytest.fixture
def config():
    from src.core.config import Config

    return Config.load()


@pytest.fixture
def ohlcv_wti(config):
    from src.data.loader import DataLoader

    return DataLoader(config).load("wti")


def test_eia_signal_name() -> None:
    """EIAInventorySignal.name is 'eia_inventory' (DEV-EM7-1)."""
    sig = EIAInventorySignal(config=MagicMock())
    assert sig.name == "eia_inventory"


def test_eia_signal_returns_flat_for_non_crude_asset() -> None:
    """Non-crude assets return flat zero series without loading EIA data."""
    sig = EIAInventorySignal(config=MagicMock())
    mock_frame = MagicMock()
    mock_frame.asset = "gold"
    mock_frame.data.index = pd.bdate_range("2024-01-02", periods=10, freq="B", tz="UTC")

    result = sig.generate(mock_frame)

    assert (result == 0.0).all()
    assert result.name == "eia_inventory"


@pytestmark_skip
def test_eia_signal_values_are_valid_for_wti(config, ohlcv_wti) -> None:
    """Generated WTI signal values are only in {-1.0, 0.0, 1.0}."""
    from src.research.pipeline import FeaturePipeline

    feature_frame = FeaturePipeline([]).compute(ohlcv_wti, asset="wti")
    result = EIAInventorySignal(config=config).generate(feature_frame)

    assert set(result.unique()).issubset({-1.0, 0.0, 1.0})


@pytestmark_skip
def test_eia_signal_index_matches_feature_frame(config, ohlcv_wti) -> None:
    """Signal index equals feature_frame.data.index."""
    from src.research.pipeline import FeaturePipeline

    feature_frame = FeaturePipeline([]).compute(ohlcv_wti, asset="wti")
    result = EIAInventorySignal(config=config).generate(feature_frame)

    assert result.index.equals(feature_frame.data.index)
