"""Tests for FeaturePipeline: Layer 1 orchestration.

Verifies that FeaturePipeline correctly combines multiple Indicators into a
FeatureFrame with the correct columns, FeatureSpec metadata, and value preservation.
See ADR-006 for the FeatureFrame and FeaturePipeline design.
"""

from __future__ import annotations

import pandas as pd

from src.core.types import FeatureSpec
from src.research.feature_frame import FeatureFrame
from src.research.momentum import Momentum
from src.research.moving_averages import EMA, SMA
from src.research.oscillators import RSI
from src.research.pipeline import FeaturePipeline


def test_pipeline_returns_feature_frame(gold_ohlcv: pd.DataFrame) -> None:
    """FeaturePipeline.compute() returns a FeatureFrame instance."""
    ff = FeaturePipeline([EMA(50), RSI(14)]).compute(gold_ohlcv, asset="gold")
    assert isinstance(
        ff, FeatureFrame
    ), f"Expected FeatureFrame, got {type(ff).__name__}"


def test_pipeline_asset_attribute(gold_ohlcv: pd.DataFrame) -> None:
    """FeatureFrame.asset matches the asset argument passed to compute()."""
    ff = FeaturePipeline([EMA(50)]).compute(gold_ohlcv, asset="gold")
    assert ff.asset == "gold"


def test_pipeline_adds_indicator_columns(gold_ohlcv: pd.DataFrame) -> None:
    """Pipeline adds indicator columns; original OHLCV columns are preserved."""
    ff = FeaturePipeline([EMA(50), EMA(200), RSI(14)]).compute(gold_ohlcv, asset="gold")
    for col in ["open", "high", "low", "close", "volume"]:
        assert col in ff.data.columns, f"OHLCV column '{col}' missing"
    assert "ema_50" in ff.data.columns
    assert "ema_200" in ff.data.columns
    assert "rsi_14" in ff.data.columns


def test_pipeline_feature_specs_count(gold_ohlcv: pd.DataFrame) -> None:
    """feature_specs length equals the number of Indicators."""
    indicators = [EMA(50), RSI(14), Momentum(20)]
    ff = FeaturePipeline(indicators).compute(gold_ohlcv, asset="gold")
    assert len(ff.feature_specs) == len(indicators)


def test_pipeline_feature_specs_metadata(gold_ohlcv: pd.DataFrame) -> None:
    """Each FeatureSpec has correct column_name, asset, and parameters."""
    ff = FeaturePipeline([EMA(50), RSI(14), Momentum(20)]).compute(
        gold_ohlcv, asset="gold"
    )
    column_names = [s.column_name for s in ff.feature_specs]
    assert "ema_50" in column_names
    assert "rsi_14" in column_names
    assert "momentum_20" in column_names
    for spec in ff.feature_specs:
        assert isinstance(spec, FeatureSpec)
        assert spec.asset == "gold"
        assert isinstance(spec.parameters, dict)
        assert (
            len(spec.parameters) > 0
        ), f"FeatureSpec.parameters must be non-empty for {spec.column_name}"


def test_pipeline_preserves_ohlcv_values(gold_ohlcv: pd.DataFrame) -> None:
    """Pipeline does not modify the original close price values."""
    ff = FeaturePipeline([EMA(50)]).compute(gold_ohlcv, asset="gold")
    pd.testing.assert_series_equal(ff.data["close"], gold_ohlcv["close"])


def test_pipeline_indicator_dtype_float64(gold_ohlcv: pd.DataFrame) -> None:
    """All computed indicator columns have float64 dtype."""
    ff = FeaturePipeline([SMA(20), EMA(50), RSI(14), Momentum(20)]).compute(
        gold_ohlcv, asset="gold"
    )
    for col in ["sma_20", "ema_50", "rsi_14", "momentum_20"]:
        assert (
            ff.data[col].dtype == "float64"
        ), f"'{col}' dtype is {ff.data[col].dtype}, expected float64"


def test_pipeline_empty_indicator_list(gold_ohlcv: pd.DataFrame) -> None:
    """Empty indicator list returns FeatureFrame with only OHLCV columns."""
    ff = FeaturePipeline([]).compute(gold_ohlcv, asset="gold")
    assert len(ff.feature_specs) == 0
    assert list(ff.data.columns) == list(gold_ohlcv.columns)
