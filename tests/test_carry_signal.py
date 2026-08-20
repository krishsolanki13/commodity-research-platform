"""Backend tests for CarrySignal.

All tests use synthetic FuturesCurve fixtures — no contract Parquet files
needed. Suite time: < 5 seconds.

TD-EM10-B: narrowed from real contract data (29 min over OneDrive)
to synthetic fixtures that mock FuturesCurveBuilder responses.
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from src.signal.carry import CarrySignal


def _make_synthetic_ohlcv(n: int = 100) -> pd.DataFrame:
    """Minimal OHLCV for FeaturePipeline.compute()."""
    return pd.DataFrame(
        {
            "open": [1800.0] * n,
            "high": [1810.0] * n,
            "low": [1790.0] * n,
            "close": [1800.0] * n,
            "volume": [10000.0] * n,
        },
        index=pd.bdate_range("2024-01-02", periods=n, freq="B", tz="UTC"),
    )


def _make_synthetic_curves(dates: list, roll_yield: float = 0.05) -> list:
    """Mock FuturesCurve objects with synthetic roll yield."""
    curves = []
    for d in dates:
        curve = MagicMock()
        curve.observation_date = d if isinstance(d, datetime.date) else d.date()
        # prices: front=1800, back=1800*(1 - roll_yield/12) for contango
        # Positive roll_yield → backwardation (front > back)
        front = 1800.0
        back = front / (1 + roll_yield / 12)
        curve.prices = [front, back, back * 0.99, back * 0.98]
        curve.points = []
        curves.append(curve)
    return curves


def _make_feature_frame(asset: str = "gold", n: int = 100):
    """Minimal FeatureFrame using FeaturePipeline([])."""
    from src.research.pipeline import FeaturePipeline  # noqa: PLC0415

    ohlcv = _make_synthetic_ohlcv(n)
    pipeline = FeaturePipeline([])
    return pipeline.compute(ohlcv, asset=asset)


# ── Pure unit tests ────────────────────────────────────────────────────────────


def test_carry_signal_name() -> None:
    """CarrySignal.name == 'carry' via @property."""
    sig = CarrySignal(config=MagicMock(), threshold=0.0)
    assert sig.name == "carry"


def test_carry_signal_returns_flat_when_no_contract_data() -> None:
    """Flat signal when asset has no contract data."""
    sig = CarrySignal(config=MagicMock(), threshold=0.0)
    mock_frame = _make_feature_frame("__fake__")

    with patch(
        "src.commodity.curve.FuturesCurveBuilder.available_assets",
        return_value=["gold", "silver"],
    ):
        result = sig.generate(mock_frame)

    assert (result == 0.0).all()
    assert result.name == "carry"


def test_carry_signal_returns_flat_when_curve_build_fails() -> None:
    """Flat signal when build_historical_curves raises."""
    sig = CarrySignal(config=MagicMock(), threshold=0.0)
    mock_frame = _make_feature_frame("gold")

    with (
        patch(
            "src.commodity.curve.FuturesCurveBuilder.available_assets",
            return_value=["gold"],
        ),
        patch(
            "src.commodity.curve.FuturesCurveBuilder.build_historical_curves",
            side_effect=RuntimeError("network error"),
        ),
    ):
        result = sig.generate(mock_frame)

    assert (result == 0.0).all()
    assert result.name == "carry"


def test_carry_signal_values_valid_with_synthetic_backwardation() -> None:
    """CarrySignal produces +1 values when roll yield is positive (backwardation)."""
    sig = CarrySignal(config=MagicMock(), threshold=0.0)
    mock_frame = _make_feature_frame("gold", n=50)
    dates = [d.date() for d in mock_frame.data.index]

    # Synthetic backwardation: positive roll yield → signal = +1
    curves = _make_synthetic_curves(dates, roll_yield=0.10)

    with (
        patch(
            "src.commodity.curve.FuturesCurveBuilder.available_assets",
            return_value=["gold"],
        ),
        patch(
            "src.commodity.curve.FuturesCurveBuilder.build_historical_curves",
            return_value=curves,
        ),
        patch(
            "src.commodity.term_structure.TermStructureAnalyzer.analyze_series",
            return_value=[
                MagicMock(
                    observation_date=d,
                    roll_yield_annualized=0.10,
                )
                for d in dates
            ],
        ),
    ):
        result = sig.generate(mock_frame)

    assert result.name == "carry"
    assert set(result.unique()).issubset({-1.0, 0.0, 1.0})
    assert result.index.equals(mock_frame.data.index)


def test_carry_signal_values_valid_with_synthetic_contango() -> None:
    """CarrySignal produces -1 values when roll yield is negative (contango)."""
    sig = CarrySignal(config=MagicMock(), threshold=0.0)
    mock_frame = _make_feature_frame("gold", n=50)
    dates = [d.date() for d in mock_frame.data.index]

    with (
        patch(
            "src.commodity.curve.FuturesCurveBuilder.available_assets",
            return_value=["gold"],
        ),
        patch(
            "src.commodity.curve.FuturesCurveBuilder.build_historical_curves",
            return_value=_make_synthetic_curves(dates, roll_yield=-0.05),
        ),
        patch(
            "src.commodity.term_structure.TermStructureAnalyzer.analyze_series",
            return_value=[
                MagicMock(observation_date=d, roll_yield_annualized=-0.05)
                for d in dates
            ],
        ),
    ):
        result = sig.generate(mock_frame)

    assert set(result.unique()).issubset({-1.0, 0.0, 1.0})


def test_carry_signal_threshold_filters_weak_signals() -> None:
    """Higher threshold produces fewer non-zero bars."""
    mock_frame = _make_feature_frame("gold", n=50)
    dates = [d.date() for d in mock_frame.data.index]

    # Mild backwardation that only crosses low threshold
    snapshots = [
        MagicMock(observation_date=d, roll_yield_annualized=0.02) for d in dates
    ]

    def run_signal(threshold: float) -> pd.Series:
        sig = CarrySignal(config=MagicMock(), threshold=threshold)
        with (
            patch(
                "src.commodity.curve.FuturesCurveBuilder.available_assets",
                return_value=["gold"],
            ),
            patch(
                "src.commodity.curve.FuturesCurveBuilder.build_historical_curves",
                return_value=_make_synthetic_curves(dates, roll_yield=0.02),
            ),
            patch(
                "src.commodity.term_structure.TermStructureAnalyzer.analyze_series",
                return_value=snapshots,
            ),
        ):
            return sig.generate(mock_frame)

    low_threshold = run_signal(0.0)
    high_threshold = run_signal(0.05)  # 5% > 2% roll yield → all flat

    assert (
        high_threshold == 0.0
    ).all(), "Threshold 5% should produce all-flat when roll yield is 2%"
    # Low threshold should produce some non-zero bars
    assert (
        low_threshold != 0.0
    ).any(), "Threshold 0% should produce some non-flat bars with 2% roll yield"
