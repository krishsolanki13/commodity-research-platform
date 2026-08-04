"""WTI-Brent spread signal — cointegration-based mean reversion in crude oil.

The WTI-Brent spread (WTI price minus Brent price) is cointegrated over the
long run: transportation costs, quality differentials, and regional supply
dynamics create a mean-reverting relationship. When the spread widens
(WTI cheap relative to Brent), mean reversion implies WTI will rise or
Brent will fall. When the spread narrows, the reverse.

This signal computes the z-score of the spread over a rolling lookback
window and returns it as a single-asset signal on WTI:
  z > +threshold → short WTI (spread too wide, WTI expensive relative to Brent)
  z < -threshold → long WTI  (spread too narrow, WTI cheap relative to Brent)

LIMITATION: This is a single-asset approximation. The true spread trade
is long WTI / short Brent (or vice versa) in equal notional. The Brent
leg is not tracked in the backtest P&L. The single-asset P&L on WTI
approximates the spread P&L because WTI and Brent are ~90% correlated —
but the Sharpe ratio will differ from a true spread strategy.

Cointegration test: Engle-Granger ADF on the spread level. If the spread
is not cointegrated (ADF p > 0.10), the signal returns all-zero with a
warning — running a mean-reversion strategy on a non-stationary spread
is not statistically supported.

References:
    Engle, R. & Granger, C. (1987). Co-integration and error correction.
    Econometrica, 55(2), 251-276.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.core.config import Config
    from src.research.feature_frame import FeatureFrame

logger = logging.getLogger(__name__)

# Asset identifier for Brent crude continuous series.
# Default: "brent" — update if Task 0b reveals a different identifier
# (e.g., "crude_brent", "bz", "co").
_BRENT_ASSET = "brent"


class WTIBrentSpreadSignal:
    """WTI-Brent spread mean-reversion signal.

    Generates a z-score signal on WTI based on the rolling z-score of the
    WTI-Brent price spread. Requires WTI as the primary asset — raises
    ValueError if called on any other asset.

    Args:
        config: Platform Config for loading Brent OHLCV data.
        lookback: Rolling window for spread mean and std (default 63 days).
        threshold: Z-score threshold for signal entry (default 1.0).
            Note: PositionSignalConstructor.build() applies the final
            threshold on the returned RawSignal (z-score series).

    Parameters in config/strategies.yaml:
        lookback: 63    (rolling window in trading days)
        threshold: 1.0  (z-score entry threshold — passed to build())
    """

    def __init__(
        self,
        config: Config,
        lookback: int = 63,
        threshold: float = 1.0,
    ) -> None:
        self._config = config
        self._lookback = lookback
        self._threshold = threshold

    @property
    def name(self) -> str:
        """Strategy identifier used in run_id, MLflow, and catalog."""
        return "wti_brent_spread"

    def generate(self, feature_frame: FeatureFrame) -> pd.Series:
        """Generate WTI-Brent spread z-score signal.

        Args:
            feature_frame: FeatureFrame for WTI (from FeaturePipeline([])).
                Used for date range (feature_frame.data.index) and asset
                validation (feature_frame.asset).

        Returns:
            pd.Series of z-score values (continuous, not discretized).
            series.name = self.name per RawSignal (pd.Series type alias) convention.
            Returns all-zero series if:
              - Brent data unavailable
              - Spread is not cointegrated (ADF p > 0.10)

        Raises:
            ValueError: If feature_frame.asset is not "wti".
        """
        from src.data.loader import DataLoader  # noqa: PLC0415

        # DEV-EM7-3: feature_frame.data.index and .asset
        asset = feature_frame.asset
        dates_index = feature_frame.data.index

        if asset != "wti":
            raise ValueError(
                f"WTIBrentSpreadSignal requires asset='wti', got '{asset}'. "
                "This signal computes the WTI-Brent spread z-score on WTI."
            )

        flat_signal = pd.Series(0.0, index=dates_index, name=self.name)

        # Load WTI and Brent continuous OHLCV
        try:
            loader = DataLoader(self._config)
            wti_ohlcv = loader.load("wti")
            brent_ohlcv = loader.load(_BRENT_ASSET)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "WTIBrentSpreadSignal: failed to load OHLCV data (%s) — "
                "returning flat signal.",
                exc,
            )
            return flat_signal

        # Align WTI and Brent on the feature_frame date range
        wti_close = wti_ohlcv["close"].reindex(dates_index)
        brent_close = brent_ohlcv["close"].reindex(dates_index)

        # Forward-fill to handle minor date mismatches (different exchange calendars)
        wti_close = wti_close.ffill()
        brent_close = brent_close.ffill()

        # Require sufficient aligned data
        valid = wti_close.notna() & brent_close.notna()
        if valid.sum() < self._lookback + 10:
            logger.warning(
                "WTIBrentSpreadSignal: insufficient aligned data "
                "(%d valid dates, need > %d) — returning flat signal.",
                valid.sum(),
                self._lookback + 10,
            )
            return flat_signal

        # ── Cointegration test (Engle-Granger, numpy-only) ───────────────
        spread_valid = wti_close[valid] - brent_close[valid]
        is_cointegrated, adf_stat, adf_pval = self._adf_test(spread_valid)

        logger.info(
            "WTIBrentSpreadSignal: ADF test — stat=%.4f, p=%.4f, cointegrated=%s",
            adf_stat,
            adf_pval,
            is_cointegrated,
        )

        if not is_cointegrated:
            logger.warning(
                "WTIBrentSpreadSignal: spread is NOT cointegrated "
                "(ADF p=%.4f > 0.10) — returning flat signal. "
                "Mean-reversion strategy not statistically supported.",
                adf_pval,
            )
            return flat_signal

        # ── Rolling z-score ───────────────────────────────────────────────
        spread_full = wti_close - brent_close

        rolling_mean = spread_full.rolling(
            window=self._lookback,
            min_periods=max(10, self._lookback // 4),
        ).mean()
        rolling_std = spread_full.rolling(
            window=self._lookback,
            min_periods=max(10, self._lookback // 4),
        ).std(ddof=1)

        # Z-score: (spread - mean) / std; guard against zero std (flat spread window)
        z_score = (spread_full - rolling_mean) / rolling_std.replace(0, float("nan"))

        # Fill NaN (initial window, constant spread) with 0
        z_score = z_score.fillna(0.0)

        # Sign convention (confirmed — EM12 Risk Register §10):
        #   spread = WTI - Brent
        #   z_score > 0: spread above mean → WTI expensive → SHORT WTI → signal NEGATIVE
        #   z_score < 0: spread below mean → WTI cheap    → LONG  WTI → signal POSITIVE
        #   Therefore: signal = -z_score  (negation is correct)
        # PositionSignalConstructor applies self._threshold to discretize to {+1, 0, -1}.
        signal = -z_score

        signal.name = self.name

        n_long = int((signal > self._threshold).sum())
        n_short = int((signal < -self._threshold).sum())
        logger.info(
            "WTIBrentSpreadSignal: bars above +threshold=%d, below -threshold=%d",
            n_long,
            n_short,
        )

        return signal

    @staticmethod
    def _adf_test(
        series: pd.Series,
        max_lags: int = 5,
    ) -> tuple[bool, float, float]:
        """Augmented Dickey-Fuller test for stationarity (numpy-only implementation).

        H0: series has a unit root (non-stationary).
        Reject H0 at p < 0.10 → series is stationary → cointegrated.

        Regression: Δy_t = α + β·y_{t-1} + Σγ_i·Δy_{t-i} + ε_t
        t-statistic on β is the ADF statistic.
        P-value approximated via MacKinnon (1994) response surface.

        Returns:
            (is_cointegrated, adf_statistic, p_value)
        """
        y = series.dropna().values.astype(float)
        n = len(y)

        if n < 20:
            return False, 0.0, 1.0

        dy = np.diff(y)
        n_diff = len(dy)

        n_lags = min(max_lags, n_diff // 5)
        n_obs = n_diff - n_lags

        if n_obs < 10:
            return False, 0.0, 1.0

        dy_dep = dy[n_lags:]

        x_cols = [y[n_lags:-1]]  # y_{t-1} (lagged level)
        for lag in range(1, n_lags + 1):
            x_cols.append(dy[n_lags - lag : n_diff - lag])  # lagged differences
        x_cols.append(np.ones(n_obs))  # intercept

        x_mat = np.column_stack(x_cols)

        try:
            xtx_inv = np.linalg.inv(x_mat.T @ x_mat)
        except np.linalg.LinAlgError:
            return False, 0.0, 1.0

        beta = xtx_inv @ (x_mat.T @ dy_dep)
        residuals = dy_dep - x_mat @ beta
        sigma2 = float(np.sum(residuals**2) / (n_obs - x_mat.shape[1]))

        se_beta = math.sqrt(sigma2 * float(xtx_inv[0, 0]))
        if se_beta <= 0:
            return False, 0.0, 1.0

        adf_stat = float(beta[0] / se_beta)
        pval = _adf_pvalue_approx(adf_stat)

        return pval < 0.10, adf_stat, pval


def _adf_pvalue_approx(adf_stat: float) -> float:
    """Approximate ADF p-value via MacKinnon (1994) critical value interpolation.

    Piecewise linear interpolation between tabulated critical values for
    ADF with constant (intercept only). Research-quality approximation —
    sufficient for binary cointegration screening at p < 0.10.
    """
    # (ADF statistic, approximate p-value) pairs from MacKinnon (1994)
    table = [
        (-4.38, 0.001),
        (-3.96, 0.005),
        (-3.56, 0.01),
        (-3.22, 0.025),
        (-2.86, 0.05),
        (-2.57, 0.10),
        (-2.23, 0.20),
        (-1.94, 0.30),
        (-1.62, 0.40),
        (-1.28, 0.50),
    ]

    if adf_stat <= table[0][0]:
        return 0.001
    if adf_stat >= table[-1][0]:
        return 0.99

    for i in range(len(table) - 1):
        x0, p0 = table[i]
        x1, p1 = table[i + 1]
        if x0 <= adf_stat <= x1:
            t = (adf_stat - x0) / (x1 - x0)
            return float(p0 + t * (p1 - p0))

    return 0.99
