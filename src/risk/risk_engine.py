"""RiskEngine: portfolio and per-asset risk analytics.

Computes historical Value at Risk (VaR), Expected Shortfall (CVaR),
and notional exposure from MultiAssetBacktestResult.

Methodology: historical simulation. No parametric (normal) distribution
assumption — correct for fat-tailed commodity futures return distributions.

Architecture: Layer 6 (Risk Analytics) — Phase 3.
Stateless: each compute() call is independent.

See Architecture Section 5 (Layer 6) and ADR-003.
"""

from __future__ import annotations

import logging
import math
from datetime import date

import pandas as pd

from src.core.types import CorrelationReport, MultiAssetBacktestResult, RiskReport


class RiskEngine:
    """Computes risk metrics from MultiAssetBacktestResult.

    Stateless — each compute() call is independent. Holds no per-call
    state. The lookback_days parameter is passed per call to allow
    researchers to explore different risk windows interactively.

    Usage:
        engine = RiskEngine()
        risk = engine.compute(multi_result)
        print(f"Portfolio VaR 99%: ${risk.portfolio_var_99:,.0f}")
        print(f"Portfolio ES  99%: ${risk.portfolio_es_99:,.0f}")
        print(f"VaR as % of capital: {risk.portfolio_var_99_pct:.4%}")
        print(f"Diversification benefit: {risk.portfolio_diversification_benefit:.2f}x")
    """

    def __init__(self) -> None:
        """Initialise RiskEngine (stateless — no configuration held)."""
        self._logger = logging.getLogger(__name__)

    def compute(
        self,
        multi_result: MultiAssetBacktestResult,
        lookback_days: int = 252,
        corr_report: CorrelationReport | None = None,
    ) -> RiskReport:
        """Compute portfolio and per-asset risk metrics.

        All VaR and ES values use the most recent lookback_days trading days
        of the PnL series (historical simulation window).

        Args:
            multi_result: MultiAssetBacktestResult from MultiAssetRunner.run().
                Requires: asset_results, portfolio_pnl_series.
            lookback_days: Rolling window for historical simulation.
                Default 252 (~1 trading year). Must be >= 20.

        Returns:
            RiskReport with portfolio VaR/ES, per-asset VaR, and notional
            exposure. Individual metrics may be NaN if insufficient data.

        Raises:
            ValueError: If asset_results is empty.
            ValueError: If lookback_days < 20.
        """
        if not multi_result.asset_results:
            raise ValueError(
                "RiskEngine.compute(): no asset results in MultiAssetBacktestResult."
            )
        if lookback_days < 20:
            raise ValueError(
                f"RiskEngine.compute(): lookback_days={lookback_days} must be >= 20."
            )

        # Initial capital from first asset's BacktestResult metadata
        first_result = next(iter(multi_result.asset_results.values()))
        initial_capital_per_asset = float(first_result.metadata.initial_capital_usd)
        initial_capital_total = initial_capital_per_asset * len(multi_result.assets)

        # ── Portfolio-level VaR and ES ────────────────────────────────────
        port_pnl = multi_result.portfolio_pnl_series

        portfolio_var_95 = self._compute_var(port_pnl, 0.95, lookback_days)
        portfolio_var_99 = self._compute_var(port_pnl, 0.99, lookback_days)
        portfolio_es_95 = self._compute_es(port_pnl, 0.95, lookback_days)
        portfolio_es_99 = self._compute_es(port_pnl, 0.99, lookback_days)

        portfolio_var_95_pct = (
            portfolio_var_95 / initial_capital_total
            if initial_capital_total > 0 and not math.isnan(portfolio_var_95)
            else float("nan")
        )
        portfolio_var_99_pct = (
            portfolio_var_99 / initial_capital_total
            if initial_capital_total > 0 and not math.isnan(portfolio_var_99)
            else float("nan")
        )

        # ── Per-asset VaR ─────────────────────────────────────────────────
        asset_var_95: dict[str, float] = {}
        asset_var_99: dict[str, float] = {}

        for asset, bt_result in multi_result.asset_results.items():
            asset_var_95[asset] = self._compute_var(
                bt_result.pnl_series, 0.95, lookback_days
            )
            asset_var_99[asset] = self._compute_var(
                bt_result.pnl_series, 0.99, lookback_days
            )

        # ── Notional exposure ─────────────────────────────────────────────
        avg_gross: dict[str, float] = {}
        avg_net: dict[str, float] = {}

        for asset, bt_result in multi_result.asset_results.items():
            gross, net = self._compute_notional_exposure(bt_result.positions)
            avg_gross[asset] = gross
            avg_net[asset] = net

        total_avg_gross = sum(v for v in avg_gross.values() if not math.isnan(v))
        total_avg_net = sum(v for v in avg_net.values() if not math.isnan(v))

        # ── EM4: Kupiec VaR Backtesting ───────────────────────────────────────
        kupiec_fields = self._compute_kupiec(
            port_pnl=port_pnl,
            var_95=portfolio_var_95,
            var_99=portfolio_var_99,
            lookback_days=lookback_days,
        )

        # ── EM4: Contribution to Strategy Volatility ──────────────────────────
        contribution_fields = self._compute_contribution_to_risk(
            assets=multi_result.assets,
            avg_gross_notional_by_asset=avg_gross,
            total_avg_gross_notional=total_avg_gross,
            corr_report=corr_report,
        )

        self._logger.info(
            "RiskEngine: %s — VaR99=%.0f (%.2f%% of capital), "
            "ES99=%.0f, gross_notional=%.0f"
            ", exceptions_99=%d (%.1f%%), contribution_pct=%s",
            multi_result.run_id,
            portfolio_var_99,
            portfolio_var_99_pct * 100
            if not math.isnan(portfolio_var_99_pct)
            else float("nan"),
            portfolio_es_99,
            total_avg_gross,
            kupiec_fields["exceptions_99"],
            float(kupiec_fields["exception_rate_99"]) * 100
            if not math.isnan(float(kupiec_fields["exception_rate_99"]))
            else float("nan"),
            {k: f"{v:.2%}" for k, v in contribution_fields["contribution_pct"].items()},
        )

        return RiskReport(
            strategy_name=multi_result.strategy_name,
            run_id=multi_result.run_id,
            assets=multi_result.assets,
            computation_date=date.today(),
            lookback_days=lookback_days,
            initial_capital_total=initial_capital_total,
            portfolio_var_95=portfolio_var_95,
            portfolio_var_99=portfolio_var_99,
            portfolio_var_95_pct=portfolio_var_95_pct,
            portfolio_var_99_pct=portfolio_var_99_pct,
            portfolio_es_95=portfolio_es_95,
            portfolio_es_99=portfolio_es_99,
            asset_var_95=asset_var_95,
            asset_var_99=asset_var_99,
            avg_gross_notional_by_asset=avg_gross,
            avg_net_notional_by_asset=avg_net,
            total_avg_gross_notional=total_avg_gross,
            total_avg_net_notional=total_avg_net,
            # EM4 — Kupiec VaR backtesting
            n_backtesting_days=int(kupiec_fields["n_days"]),
            exceptions_95=int(kupiec_fields["exceptions_95"]),
            exceptions_99=int(kupiec_fields["exceptions_99"]),
            exception_rate_95=float(kupiec_fields["exception_rate_95"]),
            exception_rate_99=float(kupiec_fields["exception_rate_99"]),
            kupiec_lr_99=float(kupiec_fields["kupiec_lr_99"]),
            kupiec_pvalue_99=float(kupiec_fields["kupiec_pvalue_99"]),
            # EM4 — Contribution to strategy volatility
            asset_contribution_to_vol=contribution_fields["contribution_to_vol"],
            asset_contribution_to_vol_pct=contribution_fields["contribution_pct"],
        )

    def _compute_var(
        self,
        pnl_series: pd.Series,
        confidence: float,
        lookback_days: int,
    ) -> float:
        """Compute historical VaR at the given confidence level.

        VaR is expressed as a positive USD loss magnitude.

        Method:
            1. Take the most recent lookback_days values of pnl_series
            2. The VaR at confidence c = |quantile(1 - c)| of the PnL dist
               e.g. at 99%: the 1st percentile worst PnL, made positive

        Args:
            pnl_series: Daily P&L series in USD.
            confidence: Confidence level (0.95 or 0.99 typically).
            lookback_days: Historical simulation window length.

        Returns:
            VaR as positive USD loss. NaN if fewer than 20 valid observations.
        """
        clean = pnl_series.dropna()
        if len(clean) < 20:
            return float("nan")

        recent = clean.iloc[-lookback_days:]
        if len(recent) < 20:
            return float("nan")

        quantile_value = float(recent.quantile(1.0 - confidence))
        return abs(quantile_value)

    def _compute_es(
        self,
        pnl_series: pd.Series,
        confidence: float,
        lookback_days: int,
    ) -> float:
        """Compute Expected Shortfall (CVaR) at the given confidence level.

        ES is the mean of losses beyond the VaR threshold.
        Always >= VaR at the same confidence level.
        ES is a coherent risk measure; VaR is not.

        Args:
            pnl_series: Daily P&L series in USD.
            confidence: Confidence level (0.95 or 0.99 typically).
            lookback_days: Historical simulation window length.

        Returns:
            ES as positive USD loss. NaN if no observations beyond VaR threshold
            or fewer than 20 valid observations.
        """
        clean = pnl_series.dropna()
        if len(clean) < 20:
            return float("nan")

        recent = clean.iloc[-lookback_days:]
        if len(recent) < 20:
            return float("nan")

        var_threshold = float(recent.quantile(1.0 - confidence))
        tail_losses = recent[recent <= var_threshold]

        if len(tail_losses) == 0:
            # No observations beyond VaR — return VaR as fallback
            return abs(var_threshold)

        return abs(float(tail_losses.mean()))

    def _compute_notional_exposure(
        self,
        positions: pd.Series,
    ) -> tuple[float, float]:
        """Compute average gross and net notional exposure.

        Exposure is averaged over active trading days only (positions != 0),
        representing the typical exposure when the strategy is in a trade.
        Returns (0.0, 0.0) if the strategy never entered a position.

        Args:
            positions: USD notional position series from BacktestResult.
                Positive = long, negative = short, zero = flat.

        Returns:
            (avg_gross_notional, avg_net_notional) over active days.
            Both are USD amounts. Gross is non-negative. Net may be signed.
        """
        if positions is None or len(positions) == 0:
            return 0.0, 0.0

        active = positions[positions != 0]

        if len(active) == 0:
            return 0.0, 0.0

        avg_gross = float(active.abs().mean())
        avg_net = float(active.mean())

        return avg_gross, avg_net

    # ── EM4: Kupiec VaR Backtesting ───────────────────────────────────────────

    def _compute_kupiec(
        self,
        port_pnl: pd.Series,
        var_95: float,
        var_99: float,
        lookback_days: int,
    ) -> dict[str, int | float]:
        """Compute Kupiec (1995) VaR backtesting statistics.

        Counts exception days (actual loss > VaR) and tests whether the
        exception rate matches the stated confidence level via a likelihood
        ratio test. LR ~ chi-squared(1) under H0 (correct calibration).

        Args:
            port_pnl: Portfolio daily P&L series (signed — losses are negative).
            var_95: Portfolio VaR at 95% confidence (positive magnitude).
            var_99: Portfolio VaR at 99% confidence (positive magnitude).
            lookback_days: Rolling window for backtesting.

        Returns:
            Dict with keys: n_days, exceptions_95, exceptions_99,
            exception_rate_95, exception_rate_99, kupiec_lr_99, kupiec_pvalue_99.
        """
        clean = port_pnl.dropna()
        recent = clean.iloc[-lookback_days:]
        N = len(recent)  # noqa: N806

        nan_result: dict[str, int | float] = {
            "n_days": N,
            "exceptions_95": 0,
            "exceptions_99": 0,
            "exception_rate_95": float("nan"),
            "exception_rate_99": float("nan"),
            "kupiec_lr_99": float("nan"),
            "kupiec_pvalue_99": float("nan"),
        }

        if N < 30 or math.isnan(var_99):
            return nan_result

        # Exceptions: days where pnl < -var (pnl is signed; var is positive magnitude)
        x_95 = int((recent < -var_95).sum())
        x_99 = int((recent < -var_99).sum())

        er_95 = x_95 / N
        er_99 = x_99 / N

        lr_99, pv_99 = self._kupiec_lr(x_99, N, confidence=0.99)

        return {
            "n_days": N,
            "exceptions_95": x_95,
            "exceptions_99": x_99,
            "exception_rate_95": er_95,
            "exception_rate_99": er_99,
            "kupiec_lr_99": lr_99,
            "kupiec_pvalue_99": pv_99,
        }

    def _kupiec_lr(
        self,
        x: int,
        N: int,  # noqa: N803
        confidence: float,
    ) -> tuple[float, float]:
        """Compute Kupiec likelihood ratio and p-value.

        H0: exception rate = 1 - confidence (correctly calibrated VaR).
        LR = -2 x log[ L(H0) / L(H1) ] where L is the binomial likelihood.
        LR ~ chi-squared(1) under H0.

        Returns:
            (lr_statistic, pvalue). Both NaN at boundary cases (x=0 or x=N).
        """
        p_0 = 1.0 - confidence  # expected exception rate under H0
        p_hat = x / N  # observed exception rate

        if p_hat == 0.0 or p_hat == 1.0 or x == 0:
            return float("nan"), float("nan")

        try:
            lr = -2.0 * (
                x * math.log(p_0 / p_hat)
                + (N - x) * math.log((1.0 - p_0) / (1.0 - p_hat))
            )
        except (ValueError, ZeroDivisionError):
            return float("nan"), float("nan")

        pvalue = self._chi2_1_sf(lr)
        return float(lr), float(pvalue)

    def _chi2_1_sf(self, x: float) -> float:
        """Survival function (1 - CDF) of chi-squared(1) distribution at x.

        scipy 1.18.0 is available — uses scipy.stats.chi2.sf as primary.
        Falls back to erfc(sqrt(x/2)), which is exact for df=1.
        """
        if math.isnan(x) or x < 0:
            return float("nan")
        try:
            import scipy.stats  # noqa: PLC0415

            return float(scipy.stats.chi2.sf(x, df=1))
        except ImportError:
            return float(math.erfc(math.sqrt(x / 2.0)))

    # ── EM4: Contribution to Strategy Volatility ──────────────────────────────

    def _compute_contribution_to_risk(
        self,
        assets: list[str],
        avg_gross_notional_by_asset: dict[str, float],
        total_avg_gross_notional: float,
        corr_report: CorrelationReport | None,
        risk_report_partial: None = None,
    ) -> dict[str, dict[str, float]]:
        """Compute per-asset contribution to portfolio strategy volatility.

        Uses notional weights and the correlation-based covariance matrix
        to decompose portfolio vol into per-asset marginal contributions.

        CTR_i = w_i x (Sw)_i / sqrt(w^T S w)
        where S_ij = corr_ij x vol_i x vol_j

        Vol values are strategy P&L vols from CorrelationReport
        (2-8%/yr for EMA 50/200), not commodity price vols (15-60%/yr).
        The decomposition is internally consistent.

        Returns:
            Dict with keys:
              'contribution_to_vol': dict[str, float] -- CTR_i in vol units
              'contribution_pct': dict[str, float] -- CTR_i / port_vol (sums ~1.0)
            Both empty dicts if corr_report is None or computation fails.
        """
        empty: dict[str, dict[str, float]] = {
            "contribution_to_vol": {},
            "contribution_pct": {},
        }

        if corr_report is None:
            return empty

        if total_avg_gross_notional <= 0 or len(assets) < 2:
            return empty

        try:
            import numpy as np  # noqa: PLC0415

            # Notional weights (sum to 1.0 across assets)
            weights = np.array(
                [
                    avg_gross_notional_by_asset.get(a, 0.0) / total_avg_gross_notional
                    for a in assets
                ]
            )

            # Strategy P&L vols from CorrelationReport
            vols = np.array(
                [corr_report.realized_vol_by_asset.get(a, float("nan")) for a in assets]
            )
            # NaN vols -> 0 (asset treated as uncorrelated, zero contribution)
            vols = np.where(np.isnan(vols), 0.0, vols)

            # Covariance matrix: S_ij = corr_ij x vol_i x vol_j
            n = len(assets)
            cov = np.zeros((n, n))
            for i, a in enumerate(assets):
                for j, b in enumerate(assets):
                    corr = corr_report.get_correlation(a, b)
                    if math.isnan(corr):
                        corr = 0.0
                    cov[i, j] = corr * vols[i] * vols[j]

            sigma_w = cov @ weights  # (Sw) vector
            port_var = float(weights @ sigma_w)  # w^T S w

            if port_var <= 0:
                return empty

            port_vol = math.sqrt(port_var)

            # CTR_i = w_i x (Sw)_i / port_vol  ->  sum(CTR_i) = port_vol
            # CTR_pct_i = CTR_i / port_vol      ->  sum(CTR_pct_i) = 1.0
            ctr = weights * sigma_w / port_vol
            ctr_pct = ctr / port_vol

            return {
                "contribution_to_vol": {a: float(ctr[i]) for i, a in enumerate(assets)},
                "contribution_pct": {
                    a: float(ctr_pct[i]) for i, a in enumerate(assets)
                },
            }

        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "RiskEngine: contribution-to-risk computation failed: %s", exc
            )
            return empty
