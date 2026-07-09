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

from src.core.types import MultiAssetBacktestResult, RiskReport


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

        self._logger.info(
            "RiskEngine: %s — VaR99=%.0f (%.2f%% of capital), "
            "ES99=%.0f, gross_notional=%.0f",
            multi_result.run_id,
            portfolio_var_99,
            portfolio_var_99_pct * 100
            if not math.isnan(portfolio_var_99_pct)
            else float("nan"),
            portfolio_es_99,
            total_avg_gross,
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
