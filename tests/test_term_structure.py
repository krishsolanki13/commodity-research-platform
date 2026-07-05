"""Tests for Module 10: Term Structure Analytics.

Tests TermStructureRegime, TermStructureSnapshot, and TermStructureAnalyzer
using synthetic FuturesCurve objects constructed directly. No network calls,
no data loading, no ContractParquetStore access required.

See Architecture Section 5 (Layer 5 Responsibilities) and ADR-001.
"""

from __future__ import annotations

import math
from datetime import date

import pytest

from src.commodity.term_structure import TermStructureAnalyzer
from src.core.types import (
    ContractMetadata,
    CurvePoint,
    FuturesCurve,
    TermStructureRegime,
    TermStructureSnapshot,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_curve(
    prices: list[float],
    months: list[int],
    year: int = 2026,
    observation_date: date | None = None,
    asset: str = "gold",
    root: str = "GC",
) -> FuturesCurve:
    """Build a synthetic FuturesCurve for testing.

    Args:
        prices: Close prices in delivery-date order (nearest first).
        months: Delivery months (1-12). Must match len(prices).
        year: Delivery year for all contracts. Default 2026.
        observation_date: Curve anchor date. Default 2026-07-01.
        asset: Asset identifier. Default 'gold'.
        root: CME root symbol. Default 'GC'.

    Returns:
        FuturesCurve with points sorted nearest delivery first.
    """
    if observation_date is None:
        observation_date = date(2026, 7, 1)

    points: list[CurvePoint] = []
    for price, month in zip(prices, months, strict=True):
        meta = ContractMetadata(
            ticker=f"{root}{month:02d}{str(year)[-2:]}",
            asset=asset,
            contract_root=root,
            contract_month=month,
            contract_year=year,
        )
        delivery_start = date(year, month, 1)
        days_to_delivery = (delivery_start - observation_date).days
        points.append(
            CurvePoint(
                metadata=meta,
                close=price,
                volume=25000.0,
                observation_date=observation_date,
                data_date=observation_date,
                days_to_delivery=days_to_delivery,
            )
        )

    points.sort(key=lambda p: (p.metadata.contract_year, p.metadata.contract_month))
    return FuturesCurve(asset=asset, observation_date=observation_date, points=points)


# ---------------------------------------------------------------------------
# TermStructureRegime tests (2 tests)
# ---------------------------------------------------------------------------


def test_regime_enum_has_expected_values() -> None:
    """TermStructureRegime has exactly CONTANGO, BACKWARDATION, and FLAT."""
    assert TermStructureRegime.CONTANGO.value == "contango"
    assert TermStructureRegime.BACKWARDATION.value == "backwardation"
    assert TermStructureRegime.FLAT.value == "flat"
    all_values = {r.value for r in TermStructureRegime}
    assert all_values == {"contango", "backwardation", "flat"}


def test_regime_enum_is_string_serializable() -> None:
    """TermStructureRegime inherits from str — JSON and string comparison work."""
    regime = TermStructureRegime.CONTANGO
    assert str(regime) == "contango"
    assert regime == "contango"  # str equality without .value access


# ---------------------------------------------------------------------------
# classify_regime tests (3 tests)
# ---------------------------------------------------------------------------


def test_classify_regime_contango_curve() -> None:
    """classify_regime returns CONTANGO for sharply rising curve."""
    # Aug 2026 at 2450, Dec 2026 at 2600 — ~6% annualized contango
    curve = _make_curve([2450.0, 2500.0, 2550.0, 2600.0], [8, 9, 10, 12])
    analyzer = TermStructureAnalyzer()
    assert analyzer.classify_regime(curve) == TermStructureRegime.CONTANGO


def test_classify_regime_backwardation_curve() -> None:
    """classify_regime returns BACKWARDATION for sharply falling curve."""
    # WTI-style backwardation: front 90, back 80
    curve = _make_curve(
        [90.0, 87.0, 84.0, 81.0], [8, 9, 10, 12], asset="wti", root="CL"
    )
    analyzer = TermStructureAnalyzer()
    assert analyzer.classify_regime(curve) == TermStructureRegime.BACKWARDATION


def test_classify_regime_flat_curve() -> None:
    """classify_regime returns FLAT for negligible slope or empty curve."""
    # All prices nearly identical — slope well below 0.5%/year threshold
    curve = _make_curve([2450.0, 2450.5, 2451.0], [8, 9, 12])
    analyzer = TermStructureAnalyzer()
    assert analyzer.classify_regime(curve) == TermStructureRegime.FLAT

    # Empty curve also returns FLAT
    empty = FuturesCurve(asset="gold", observation_date=date(2026, 7, 1), points=[])
    assert analyzer.classify_regime(empty) == TermStructureRegime.FLAT


# ---------------------------------------------------------------------------
# contango_slope_annualized tests (2 tests)
# ---------------------------------------------------------------------------


def test_contango_slope_annualized_positive_for_contango() -> None:
    """contango_slope_annualized returns a positive decimal for rising prices."""
    curve = _make_curve([2450.0, 2500.0, 2600.0], [8, 9, 12])
    analyzer = TermStructureAnalyzer()
    slope_pct = analyzer.contango_slope_annualized(curve)
    assert not math.isnan(slope_pct)
    assert slope_pct > 0, f"Expected positive slope_pct for contango, got {slope_pct}"


def test_contango_slope_annualized_negative_for_backwardation() -> None:
    """contango_slope_annualized returns a negative decimal for falling prices."""
    curve = _make_curve([90.0, 85.0, 80.0], [8, 9, 12], asset="wti", root="CL")
    analyzer = TermStructureAnalyzer()
    slope_pct = analyzer.contango_slope_annualized(curve)
    assert not math.isnan(slope_pct)
    assert (
        slope_pct < 0
    ), f"Expected negative slope_pct for backwardation, got {slope_pct}"


# ---------------------------------------------------------------------------
# roll_yield_annualized tests (3 tests)
# ---------------------------------------------------------------------------


def test_roll_yield_negative_in_contango() -> None:
    """roll_yield_annualized is negative in contango — headwind for long holders."""
    # Front 2450, second 2500 — rolling costs money for longs
    curve = _make_curve([2450.0, 2500.0, 2550.0], [8, 9, 12])
    analyzer = TermStructureAnalyzer()
    roll = analyzer.roll_yield_annualized(curve)
    assert not math.isnan(roll), "Roll yield must not be NaN for 3-contract curve"
    assert roll < 0, f"Expected negative roll yield in contango, got {roll}"


def test_roll_yield_positive_in_backwardation() -> None:
    """roll_yield_annualized is positive in backwardation — tailwind for long holders."""
    # Front 90, second 85 — rolling earns profit for longs
    curve = _make_curve([90.0, 85.0, 80.0], [8, 9, 12], asset="wti", root="CL")
    analyzer = TermStructureAnalyzer()
    roll = analyzer.roll_yield_annualized(curve)
    assert not math.isnan(roll), "Roll yield must not be NaN for 3-contract curve"
    assert roll > 0, f"Expected positive roll yield in backwardation, got {roll}"


def test_roll_yield_nan_for_single_contract_curve() -> None:
    """roll_yield_annualized is NaN when fewer than 2 contracts."""
    single = _make_curve([2450.0], [8])
    analyzer = TermStructureAnalyzer()
    assert math.isnan(analyzer.roll_yield_annualized(single))

    empty = FuturesCurve(asset="gold", observation_date=date(2026, 7, 1), points=[])
    assert math.isnan(analyzer.roll_yield_annualized(empty))


# ---------------------------------------------------------------------------
# compute_basis tests (2 tests)
# ---------------------------------------------------------------------------


def test_compute_basis_continuous_minus_front() -> None:
    """compute_basis = continuous_close - front_contract_price."""
    curve = _make_curve([2450.0, 2500.0], [8, 12])
    analyzer = TermStructureAnalyzer()
    basis = analyzer.compute_basis(curve, continuous_close=2440.0)
    assert basis == pytest.approx(2440.0 - 2450.0, rel=1e-6)
    assert basis < 0, "Continuous below front futures → negative basis"

    # Positive basis case (continuous above front)
    basis_positive = analyzer.compute_basis(curve, continuous_close=2460.0)
    assert basis_positive == pytest.approx(2460.0 - 2450.0, rel=1e-6)
    assert basis_positive > 0


def test_compute_basis_nan_when_no_continuous_price() -> None:
    """compute_basis returns NaN when continuous_close is NaN or curve is empty."""
    curve = _make_curve([2450.0, 2500.0], [8, 12])
    analyzer = TermStructureAnalyzer()

    assert math.isnan(analyzer.compute_basis(curve, continuous_close=float("nan")))

    empty = FuturesCurve(asset="gold", observation_date=date(2026, 7, 1), points=[])
    assert math.isnan(analyzer.compute_basis(empty, continuous_close=2440.0))


# ---------------------------------------------------------------------------
# analyze() integration tests (3 tests)
# ---------------------------------------------------------------------------


def test_analyze_returns_snapshot_with_correct_fields() -> None:
    """analyze() returns TermStructureSnapshot with all fields correctly set."""
    curve = _make_curve([2450.0, 2500.0, 2550.0], [8, 9, 12])
    analyzer = TermStructureAnalyzer()
    snapshot = analyzer.analyze(curve, continuous_close=2445.0)

    assert isinstance(snapshot, TermStructureSnapshot)
    assert snapshot.asset == "gold"
    assert snapshot.observation_date == date(2026, 7, 1)
    assert snapshot.front_price == pytest.approx(2450.0)
    assert snapshot.back_price == pytest.approx(2550.0)
    assert snapshot.n_contracts == 3
    assert snapshot.regime == TermStructureRegime.CONTANGO
    assert not math.isnan(snapshot.annualized_slope_pct)
    assert not math.isnan(snapshot.roll_yield_annualized)
    assert snapshot.basis == pytest.approx(2445.0 - 2450.0)
    assert not math.isnan(snapshot.basis_pct)
    assert snapshot.curve is curve


def test_analyze_series_returns_one_snapshot_per_curve() -> None:
    """analyze_series() returns one TermStructureSnapshot per input curve."""
    curves = [
        _make_curve([2450.0, 2500.0], [8, 12], observation_date=date(2026, 6, 1)),
        _make_curve([2460.0, 2510.0], [8, 12], observation_date=date(2026, 7, 1)),
        _make_curve([2440.0, 2495.0], [8, 12], observation_date=date(2026, 8, 1)),
    ]
    analyzer = TermStructureAnalyzer()
    snapshots = analyzer.analyze_series(
        curves,
        continuous_closes=[2445.0, 2458.0, 2438.0],
    )

    assert len(snapshots) == 3
    assert all(isinstance(s, TermStructureSnapshot) for s in snapshots)
    # Preserves input order
    assert snapshots[0].observation_date == date(2026, 6, 1)
    assert snapshots[1].observation_date == date(2026, 7, 1)
    assert snapshots[2].observation_date == date(2026, 8, 1)
    # Basis is populated because continuous_closes was provided
    assert not math.isnan(snapshots[0].basis)


def test_analyze_empty_curve_returns_flat_regime_and_nan_metrics() -> None:
    """analyze() handles empty curve — FLAT regime, NaN for all computed metrics."""
    empty = FuturesCurve(asset="gold", observation_date=date(2026, 7, 1), points=[])
    analyzer = TermStructureAnalyzer()
    snapshot = analyzer.analyze(empty, continuous_close=2440.0)

    assert snapshot.regime == TermStructureRegime.FLAT
    assert snapshot.n_contracts == 0
    assert math.isnan(snapshot.front_price)
    assert math.isnan(snapshot.back_price)
    assert math.isnan(snapshot.raw_slope)
    assert math.isnan(snapshot.annualized_slope_pct)
    assert math.isnan(snapshot.roll_yield_annualized)
    assert math.isnan(
        snapshot.basis
    )  # empty curve → NaN even if continuous_close provided
