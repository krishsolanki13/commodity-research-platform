"""Backend tests for CarrySignal.

6 tests:
  - 2 pure unit tests (always run)
  - 4 data-dependent (skip in CI — require contract Parquet files)

RawSignal is a pd.Series type alias (src/core/types.py). CarrySignal.generate()
returns a named pd.Series — no RawSignal dataclass constructor involved.

CarrySignal uses FuturesCurveBuilder which requires data in
data/processed/contracts/{asset}/. Tests use SKIP_NO_CONTRACT guard
for CI compatibility.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Skip guard for contract data (different from continuous OHLCV)
CONTRACT_PATH = Path("data/processed/contracts")
HAS_CONTRACT_DATA = CONTRACT_PATH.exists() and any(CONTRACT_PATH.iterdir())
SKIP_NO_CONTRACT = pytest.mark.skipif(
    not HAS_CONTRACT_DATA,
    reason="Contract Parquet files not available in CI environment",
)


@pytest.fixture(scope="module")
def carry_signal_gold():
    """CarrySignal instance configured for Gold."""
    from src.core.config import Config
    from src.signal.carry import CarrySignal

    config = Config.load("config/")
    return CarrySignal(config=config, threshold=0.0, n_contracts=4)


@pytest.fixture(scope="module")
def minimal_feature_frame_gold():
    """Minimal FeatureFrame for Gold — only data.index and .asset needed."""
    from src.core.config import Config
    from src.data.loader import DataLoader
    from src.research.pipeline import FeaturePipeline

    config = Config.load("config/")
    ohlcv = DataLoader(config).load("gold")
    pipeline = FeaturePipeline([])
    return pipeline.compute(ohlcv, asset="gold")


# ── Pure unit tests (always run) ──────────────────────────────────────────────


def test_carry_signal_name() -> None:
    """CarrySignal.name must equal 'carry' for pipeline registration."""
    from src.signal.carry import CarrySignal

    mock_config = MagicMock()
    signal = CarrySignal(config=mock_config, threshold=0.0)
    assert signal.name == "carry"


def test_carry_signal_returns_flat_when_no_contract_data() -> None:
    """CarrySignal returns all-zero signal when asset has no contract data."""
    from src.signal.carry import CarrySignal

    mock_config = MagicMock()
    signal = CarrySignal(config=mock_config, threshold=0.0)

    mock_frame = MagicMock()
    mock_frame.asset = "__fake_asset_no_data__"
    n = 50
    idx = pd.bdate_range("2024-01-02", periods=n, freq="B", tz="UTC")
    mock_frame.data = pd.DataFrame(index=idx)

    with patch(
        "src.commodity.curve.FuturesCurveBuilder.available_assets",
        return_value=["gold", "silver"],
    ):
        raw_signal = signal.generate(mock_frame)

    assert isinstance(
        raw_signal, pd.Series
    ), f"Expected pd.Series, got {type(raw_signal).__name__}"
    assert (
        raw_signal == 0.0
    ).all(), "CarrySignal must return flat signal when asset has no contract data"
    assert raw_signal.name == "carry"


# ── Data-dependent tests ──────────────────────────────────────────────────────


@SKIP_NO_CONTRACT
def test_carry_signal_returns_raw_signal_type(
    carry_signal_gold, minimal_feature_frame_gold
) -> None:
    """CarrySignal.generate() returns a named pd.Series (RawSignal type alias)."""
    raw_signal = carry_signal_gold.generate(minimal_feature_frame_gold)

    assert isinstance(
        raw_signal, pd.Series
    ), f"Expected pd.Series (RawSignal), got {type(raw_signal).__name__}"
    assert raw_signal.name == "carry"
    assert len(raw_signal) == len(minimal_feature_frame_gold.data.index)


@SKIP_NO_CONTRACT
def test_carry_signal_values_are_valid(
    carry_signal_gold, minimal_feature_frame_gold
) -> None:
    """CarrySignal values must be in {+1.0, 0.0, -1.0} — no other values."""
    raw_signal = carry_signal_gold.generate(minimal_feature_frame_gold)
    valid_values = {-1.0, 0.0, 1.0}
    actual_values = set(raw_signal.unique())

    assert actual_values.issubset(
        valid_values
    ), f"CarrySignal values must be subset of {{-1.0, 0.0, 1.0}}, got: {actual_values}"
    assert (raw_signal != 0.0).any(), (
        "CarrySignal on Gold should produce at least some non-zero signal "
        "— check that roll yield is being computed correctly."
    )


@SKIP_NO_CONTRACT
def test_carry_signal_index_matches_feature_frame(
    carry_signal_gold, minimal_feature_frame_gold
) -> None:
    """CarrySignal output index must match feature_frame.data.index exactly."""
    raw_signal = carry_signal_gold.generate(minimal_feature_frame_gold)

    assert raw_signal.index.equals(minimal_feature_frame_gold.data.index), (
        "CarrySignal.index must match feature_frame.data.index exactly. "
        "Misaligned index would cause silent P&L errors in the engine."
    )


@SKIP_NO_CONTRACT
def test_carry_signal_threshold_reduces_non_zero_bars(
    minimal_feature_frame_gold,
) -> None:
    """Higher threshold produces fewer non-zero signal bars."""
    from src.core.config import Config
    from src.signal.carry import CarrySignal

    config = Config.load("config/")
    signal_low = CarrySignal(config=config, threshold=0.0)
    signal_high = CarrySignal(config=config, threshold=0.10)

    raw_low = signal_low.generate(minimal_feature_frame_gold)
    raw_high = signal_high.generate(minimal_feature_frame_gold)

    n_active_low = int((raw_low != 0.0).sum())
    n_active_high = int((raw_high != 0.0).sum())

    assert n_active_high <= n_active_low, (
        f"Higher threshold ({n_active_high} active bars) must produce "
        f"<= active bars than lower threshold ({n_active_low} active bars). "
        "Threshold is not filtering correctly."
    )
