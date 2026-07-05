"""TermStructureAnalyzer: computes term structure analytics from FuturesCurve objects.

Takes FuturesCurve snapshots from Module 9 (FuturesCurveBuilder) and computes
the four analytical outputs that characterize commodity term structure:
    1. Contango/backwardation slope (annualized, normalized to front price)
    2. Roll yield (annualized return from rolling the front-to-second contract)
    3. Basis (continuous close - front contract price)
    4. Regime classification (CONTANGO / BACKWARDATION / FLAT)

All results are assembled into TermStructureSnapshot objects.

Architecture: Layer 5 — Commodity Intelligence (term structure analytics).
Consumes: FuturesCurve (Module 9). Produces: TermStructureSnapshot.
The analyzer is stateless — no data is stored between calls.

The continuous_close parameter in analyze() and compute_basis() is the only
point where the continuous series (Phase 1) and contract series (Phase 2)
interact. The analyzer receives the price as a parameter — it never calls
DataLoader directly. This preserves ADR-001's separation of the two pipelines.

See Architecture Section 5 (Layer 5 Responsibilities).
See ADR-001 (continuous vs. contract data strategy).
"""

from __future__ import annotations

import logging
import math

from src.core.types import (
    FuturesCurve,
    TermStructureRegime,
    TermStructureSnapshot,
)


class TermStructureAnalyzer:
    """Computes term structure analytics from FuturesCurve objects.

    All methods accept FuturesCurve (produced by Module 9 FuturesCurveBuilder).
    The analyzer is stateless — each call is independent. No data is stored
    between calls.

    Configuration:
        regime_threshold: Annualized slope (as fraction of front price) above
            which the term structure is classified as CONTANGO or BACKWARDATION.
            Default 0.005 (0.5%/year). Commodity markets in mild contango
            or backwardation may be near this threshold — adjust per asset
            class if needed.

    Usage:
        from src.core.config import Config
        from src.commodity.curve import FuturesCurveBuilder
        from src.commodity.term_structure import TermStructureAnalyzer

        config = Config.load('config/')
        builder = FuturesCurveBuilder(config)
        analyzer = TermStructureAnalyzer()

        curve = builder.build('gold')
        snapshot = analyzer.analyze(curve, continuous_close=4172.50)
        print(f'Regime: {snapshot.regime.value}')
        print(f'Annualized slope: {snapshot.annualized_slope_pct:.2%}')
        print(f'Roll yield: {snapshot.roll_yield_annualized:.2%}')
        print(f'Basis: {snapshot.basis:.2f}')
    """

    DEFAULT_REGIME_THRESHOLD: float = 0.005
    """Default annualized slope threshold for regime classification.
    0.5% per year: curves with |slope_pct| <= 0.005 are classified as FLAT."""

    def __init__(
        self,
        regime_threshold: float = DEFAULT_REGIME_THRESHOLD,
    ) -> None:
        """Initialise TermStructureAnalyzer.

        Args:
            regime_threshold: Annualized slope fraction above which the term
                structure is classified as CONTANGO or BACKWARDATION.
                Default 0.005 (0.5%/year). Adjust for assets with noisier
                term structure data (e.g. Natural Gas).
        """
        self._regime_threshold = regime_threshold
        self._logger = logging.getLogger(__name__)

    def analyze(
        self,
        curve: FuturesCurve,
        continuous_close: float = float("nan"),
    ) -> TermStructureSnapshot:
        """Compute all term structure analytics for a single FuturesCurve.

        The primary entry point for Module 13 (Dashboard Page 6) and
        Phase 3 signal conditioning.

        Args:
            curve: FuturesCurve from FuturesCurveBuilder.build().
            continuous_close: Closing price from the continuous front-month
                series (DataLoader.load(asset)["close"].iloc[-1]).
                Used to compute basis and basis_pct. Pass float('nan') or
                omit if basis is not needed.

        Returns:
            TermStructureSnapshot with all analytics fields populated.
            Fields requiring >= 2 curve points return NaN if insufficient data.
            Basis fields return NaN if continuous_close is NaN.
        """
        regime = self.classify_regime(curve)
        slope_pct = self.contango_slope_annualized(curve)
        roll = self.roll_yield_annualized(curve)
        basis, basis_pct = self._compute_basis_pair(curve, continuous_close)

        self._logger.info(
            "TermStructureAnalyzer: %s at %s — regime=%s n=%d slope_pct=%.4f roll=%.4f",
            curve.asset,
            curve.observation_date,
            regime.value,
            curve.n_points,
            0.0 if math.isnan(slope_pct) else slope_pct,
            0.0 if math.isnan(roll) else roll,
        )

        return TermStructureSnapshot(
            asset=curve.asset,
            observation_date=curve.observation_date,
            regime=regime,
            front_price=curve.front_price,
            back_price=curve.back_price,
            n_contracts=curve.n_points,
            raw_slope=curve.slope,
            annualized_slope_pct=slope_pct,
            roll_yield_annualized=roll,
            basis=basis,
            basis_pct=basis_pct,
            curve=curve,
        )

    def analyze_series(
        self,
        curves: list[FuturesCurve],
        continuous_closes: list[float] | None = None,
    ) -> list[TermStructureSnapshot]:
        """Compute analytics for a list of FuturesCurve objects.

        Used for historical term structure analysis — produces a time series
        of TermStructureSnapshot objects that can be plotted on Dashboard Page 6
        or used as a conditioning variable in Phase 3 signal research.

        Args:
            curves: List of FuturesCurve objects from
                FuturesCurveBuilder.build_historical_curves().
            continuous_closes: Optional aligned list of continuous close prices,
                one per curve. If provided, must be the same length as curves.
                If None, basis and basis_pct are NaN for all snapshots.

        Returns:
            List of TermStructureSnapshot objects, one per input curve.
            Preserves input order (does not sort).

        Raises:
            ValueError: If continuous_closes is provided but has different
                length than curves.
        """
        if continuous_closes is not None and len(continuous_closes) != len(curves):
            raise ValueError(
                f"continuous_closes length ({len(continuous_closes)}) must match "
                f"curves length ({len(curves)})"
            )

        results: list[TermStructureSnapshot] = []
        for i, curve in enumerate(curves):
            cc = continuous_closes[i] if continuous_closes is not None else float("nan")
            results.append(self.analyze(curve, continuous_close=cc))
        return results

    def classify_regime(self, curve: FuturesCurve) -> TermStructureRegime:
        """Classify the term structure regime.

        Uses annualized_slope_pct against the configured regime_threshold.
        Returns FLAT when fewer than 2 contracts are available, or when the
        annualized slope cannot be computed (NaN).

        Args:
            curve: FuturesCurve to classify.

        Returns:
            TermStructureRegime.CONTANGO if slope_pct > threshold.
            TermStructureRegime.BACKWARDATION if slope_pct < -threshold.
            TermStructureRegime.FLAT otherwise (including insufficient data).
        """
        slope_pct = self.contango_slope_annualized(curve)
        if math.isnan(slope_pct):
            return TermStructureRegime.FLAT
        if slope_pct > self._regime_threshold:
            return TermStructureRegime.CONTANGO
        if slope_pct < -self._regime_threshold:
            return TermStructureRegime.BACKWARDATION
        return TermStructureRegime.FLAT

    def contango_slope_annualized(self, curve: FuturesCurve) -> float:
        """Annualized contango/backwardation slope as fraction of front price.

        Normalizes the raw USD/day slope to a percentage of the front price,
        annualized. This makes term structure comparable across commodities
        with very different price levels (e.g. Gold at $4,000/oz vs
        Natural Gas at $2/MMBtu).

        Formula: ((back_price / front_price) - 1) / years_to_back
        Where years_to_back = back_days_to_delivery / 365

        Returns positive for contango, negative for backwardation.

        Args:
            curve: FuturesCurve with at least 2 points.

        Returns:
            Annualized slope as decimal fraction. e.g. 0.025 = +2.5%/year.
            NaN if: fewer than 2 points, front_price <= 0, back days <= 0,
            or zero day spread between front and back.
        """
        if len(curve.points) < 2:
            return float("nan")

        front = curve.points[0]
        back = curve.points[-1]

        if front.close <= 0:
            return float("nan")
        if back.days_to_delivery <= 0:
            return float("nan")
        if back.days_to_delivery == front.days_to_delivery:
            return float("nan")

        years_to_back = back.days_to_delivery / 365.0
        return (back.close / front.close - 1.0) / years_to_back

    def roll_yield_annualized(self, curve: FuturesCurve) -> float:
        """Annualized roll return for a long futures position.

        Computed as the annualized return from rolling the front contract
        to the second contract at expiry.

        Sign convention (industry standard):
            Positive = backwardation (rolling earns a profit for longs).
            Negative = contango (rolling incurs a cost for longs).

        This is the roll return component of the Gorton-Rouwenhorst (2006)
        commodity futures decomposition:
            Total return = Spot return + Roll return + Collateral return

        Formula: (front_price - second_price) / second_price * (365 / days_between)

        Args:
            curve: FuturesCurve with at least 2 points.

        Returns:
            Annualized roll yield as decimal fraction.
            NaN if: fewer than 2 contracts, second_price <= 0,
            or days_between deliveries is zero or negative.
        """
        if len(curve.points) < 2:
            return float("nan")

        front = curve.points[0]
        second = curve.points[1]

        if second.close <= 0:
            return float("nan")

        days_between = second.days_to_delivery - front.days_to_delivery
        if days_between <= 0:
            return float("nan")

        return (front.close - second.close) / second.close * (365.0 / days_between)

    def compute_basis(
        self,
        curve: FuturesCurve,
        continuous_close: float,
    ) -> float:
        """Compute the basis: continuous_close - front_contract_price.

        The basis measures the premium or discount of the continuous
        (spot-proxy) price relative to the nearest futures delivery.

        Positive basis: continuous trades above front futures (backwardation-like).
        Negative basis: continuous trades below front futures (contango-like).

        Note on pseudo-basis: this platform uses the continuous futures series
        as a proxy for physical spot price, per ADR-001. The continuous series
        embeds roll methodology artifacts from Yahoo Finance's stitching process.
        This basis is therefore a pseudo-basis, not a true physical market basis.
        Documented as an accepted Phase 2 limitation.

        Args:
            curve: FuturesCurve with at least 1 point.
            continuous_close: Most recent closing price from the continuous
                front-month series. Source: DataLoader.load(asset)["close"].iloc[-1].

        Returns:
            basis = continuous_close - front_contract_price.
            NaN if continuous_close is NaN or curve is empty.
        """
        if math.isnan(continuous_close) or curve.is_empty:
            return float("nan")
        return continuous_close - curve.front_price

    def _compute_basis_pair(
        self,
        curve: FuturesCurve,
        continuous_close: float,
    ) -> tuple[float, float]:
        """Return (basis, basis_pct) for internal use by analyze().

        Returns:
            (basis, basis_pct) where basis_pct = basis / continuous_close.
            Both NaN if continuous_close is NaN, zero, or curve is empty.
        """
        basis = self.compute_basis(curve, continuous_close)
        if math.isnan(basis):
            return float("nan"), float("nan")
        if math.isnan(continuous_close) or continuous_close == 0.0:
            return float("nan"), float("nan")
        return basis, basis / continuous_close
