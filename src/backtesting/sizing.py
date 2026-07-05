"""FixedNotionalSizer: Phase 1 position sizing per ADR-005.

Each signal receives a fixed USD notional exposure regardless of asset
volatility. Phase 2 will add VolatilityScaledSizer implementing the
same PositionSizer interface. See ADR-005.
"""

from __future__ import annotations

import logging
import math

import pandas as pd

from src.core.registry import PositionSizer


class FixedNotionalSizer(PositionSizer):
    """Phase 1 position sizing: fixed USD notional per signal.

    Position size does not vary with signal strength, asset, or current
    equity. This is a documented Phase 1 simplification — results
    represent relative signal performance, not realistic risk-adjusted
    dollar PnL. See ADR-005.
    """

    def __init__(self, notional_usd: float) -> None:
        """Initialise FixedNotionalSizer.

        Args:
            notional_usd: Fixed USD notional exposure per signal.
                Default 100000.0 per config.yaml sizing.fixed_notional_usd.
        """
        self._notional_usd = notional_usd
        self._logger = logging.getLogger(__name__)

    def compute_size(self, signal: float, asset: str, equity: float) -> float:
        """Return the fixed notional size, ignoring signal/asset/equity.

        Args:
            signal: Unused in Phase 1. Accepted for interface compliance
                with Phase 2 VolatilityScaledSizer.
            asset: Unused in Phase 1. Accepted for interface compliance.
            equity: Unused in Phase 1. Accepted for interface compliance.

        Returns:
            Fixed USD notional size. See ADR-005.
        """
        return self._notional_usd


class VolatilityScaledSizer(PositionSizer):
    """Sizes positions to target a fixed annualized volatility contribution.

    Addresses the limitation of FixedNotionalSizer (ADR-005): fixed notional
    does not equalize risk across assets with different volatility profiles.
    Natural Gas (~60%/yr vol) with $100K notional has 4x the risk of Gold
    (~15%/yr vol) with the same notional.

    VolatilityScaledSizer targets the same annualized volatility contribution
    from each asset, regardless of its price level or current volatility regime.

    Formula:
        realized_vol = std(daily_returns[-lookback:]) * sqrt(252)
        target_notional = (target_annual_vol * current_equity) / realized_vol
        position_size = target_notional * |signal|

    configure() must be called with the OHLCV DataFrame before size() is called.
    VectorizedBacktester.run() handles this automatically after the Phase 2
    extension adds self._sizer.configure(ohlcv) before the simulation loop.

    size() returns 0.0 if configure() has not been called, if realized vol is NaN
    (insufficient data for the lookback window), or if realized vol is zero.

    See ADR-005 for the sizing architecture decision.
    See Architecture Section 12 (PositionSizer Interface).
    """

    def __init__(
        self,
        target_annual_vol: float = 0.01,
        lookback_days: int = 63,
        vol_cap: float = 0.50,
        min_notional: float = 0.0,
        max_notional: float | None = None,
    ) -> None:
        """Initialise VolatilityScaledSizer.

        Args:
            target_annual_vol: Target annualized volatility contribution per
                asset as a fraction of account equity. Default 0.01 (1%/yr).
                e.g. 0.01 with $1M equity targets $10,000/yr volatility per asset.
                Use the same value across all assets to achieve equal risk weighting.
            lookback_days: Rolling window in trading days for realized volatility
                estimate. Default 63 (~3 months). Shorter windows are more
                responsive to volatility regime changes but noisier.
            vol_cap: Maximum realized volatility allowed before capping. Default
                0.50 (50%/yr). Prevents excessively small positions during unusually
                calm volatility regimes. Also prevents extreme leverage if the
                lookback period happened to be unusually low-vol.
            min_notional: Minimum position size in USD. Default 0.0 (no floor).
                Applied after volatility scaling.
            max_notional: Maximum position size in USD. Default None (no ceiling).
                Applied after volatility scaling. Useful to prevent single-asset
                concentration in low-volatility regimes.
        """
        self._target_annual_vol = target_annual_vol
        self._lookback_days = lookback_days
        self._vol_cap = vol_cap
        self._min_notional = min_notional
        self._max_notional = max_notional
        self._realized_vol: float = float("nan")  # populated by configure()
        self._logger = logging.getLogger(__name__)

    def configure(self, ohlcv: pd.DataFrame) -> None:
        """Pre-compute realized volatility from OHLCV data.

        Called by VectorizedBacktester.run() before the simulation loop.
        Must be called before size() — size() returns 0.0 if not configured.

        Overwrites any previously computed realized_vol. Safe to call multiple
        times (e.g. on force_reload scenarios), though not expected in normal use.

        Args:
            ohlcv: NormalizedOHLCV DataFrame from DataLoader.load().
                Uses the 'close' column to compute daily close-to-close returns.
        """
        self._realized_vol = self.compute_realized_vol(ohlcv)
        self._logger.info(
            "VolatilityScaledSizer: configured — realized_vol=%.4f "
            "(lookback=%d days, cap=%.2f, target_vol=%.4f)",
            self._realized_vol if not math.isnan(self._realized_vol) else -1.0,
            self._lookback_days,
            self._vol_cap,
            self._target_annual_vol,
        )

    def compute_realized_vol(self, ohlcv: pd.DataFrame) -> float:
        """Compute annualized realized volatility from close price series.

        Uses the most recent lookback_days of daily close-to-close returns.
        Applies vol_cap: if raw realized vol exceeds the cap, the cap is used
        instead. This prevents excessively small positions in calm regimes.

        Args:
            ohlcv: NormalizedOHLCV DataFrame. Must contain 'close' column.

        Returns:
            Annualized realized volatility as decimal fraction (e.g. 0.15 = 15%/yr).
            NaN if: 'close' column absent, or fewer than lookback_days + 1 rows.
            Capped at vol_cap if raw annual vol exceeds it.
        """
        if "close" not in ohlcv.columns:
            self._logger.warning(
                "VolatilityScaledSizer: 'close' column absent in OHLCV. "
                "size() will return 0.0 until configure() succeeds."
            )
            return float("nan")

        daily_returns = ohlcv["close"].pct_change().dropna()

        if len(daily_returns) < self._lookback_days:
            self._logger.warning(
                "VolatilityScaledSizer: insufficient data — %d bars available, "
                "%d required for lookback. size() will return 0.0.",
                len(daily_returns),
                self._lookback_days,
            )
            return float("nan")

        recent_returns = daily_returns.iloc[-self._lookback_days :]
        daily_std = float(recent_returns.std())

        if daily_std <= 0.0:
            return float("nan")

        annual_vol = daily_std * math.sqrt(252)

        if annual_vol > self._vol_cap:
            self._logger.debug(
                "VolatilityScaledSizer: raw vol %.4f exceeds cap %.4f — applying cap",
                annual_vol,
                self._vol_cap,
            )
            annual_vol = self._vol_cap

        return annual_vol

    def size(self, signal: float, current_equity: float) -> float:
        """Return position size in USD notional scaled to target volatility.

        Returns 0.0 if signal is flat, configure() has not been called,
        or realized_vol is NaN or non-positive.

        The returned size is unsigned. The direction (long/short) is applied by
        VectorizedBacktester based on the signal sign. This matches the
        FixedNotionalSizer contract.

        Args:
            signal: Position signal. -1 = full short, 0 = flat, +1 = full long.
                |signal| scales the notional proportionally (Phase 3 compatibility).
                For Phase 1 where signal is always {-1, 0, +1}, |signal| is 0 or 1.
            current_equity: Current portfolio equity in USD.

        Returns:
            Unsigned position size in USD notional. Always >= 0.
            0.0 if signal == 0, configure() not called, or realized_vol invalid.
        """
        if signal == 0.0:
            return 0.0

        if math.isnan(self._realized_vol) or self._realized_vol <= 0.0:
            return 0.0

        target_notional = (
            self._target_annual_vol * current_equity
        ) / self._realized_vol
        target_notional *= abs(signal)

        if self._min_notional > 0.0:
            target_notional = max(target_notional, self._min_notional)
        if self._max_notional is not None:
            target_notional = min(target_notional, self._max_notional)

        return float(target_notional)

    def compute_size(self, signal: float, asset: str, equity: float) -> float:
        """PositionSizer interface — delegates to size()."""
        return self.size(signal, equity)

    @property
    def realized_vol(self) -> float:
        """The most recently computed realized volatility. NaN if not configured."""
        return self._realized_vol

    @property
    def target_annual_vol(self) -> float:
        """The target annualized volatility contribution per asset."""
        return self._target_annual_vol

    @property
    def lookback_days(self) -> int:
        """Rolling window in trading days for realized vol computation."""
        return self._lookback_days

    @property
    def is_configured(self) -> bool:
        """True if configure() has been called and produced a valid vol estimate."""
        return not math.isnan(self._realized_vol) and self._realized_vol > 0.0
