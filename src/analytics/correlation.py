"""CorrelationEngine: cross-asset correlation and volatility analytics.

Computes pairwise Pearson correlation matrices, rolling correlations at
63-day and 126-day windows, and per-asset realized volatility from
MultiAssetBacktestResult.

Returns are computed as pnl_series / initial_capital_per_asset.
This is consistent with Module 16 VaR return computation and correctly
marks flat trading days as zero-return days.

Architecture: Layer 7 (Cross-Asset Analytics) — Phase 3.
Stateless: each compute() call is independent.

See Architecture Section 5 (Layer 7) and ADR-010.
"""

from __future__ import annotations

import logging
import math
from datetime import date
from itertools import combinations

import pandas as pd

from src.core.types import CorrelationReport, MultiAssetBacktestResult


class CorrelationEngine:
    """Computes cross-asset correlation analytics from MultiAssetBacktestResult.

    Stateless — each compute() call is fully independent. No instance state
    is set beyond self._logger.

    Usage:
        engine = CorrelationEngine()
        report = engine.compute(multi_result)
        print(f"Gold-Silver correlation: {report.get_correlation('gold', 'silver'):.4f}")
        print(f"Most correlated pair: {report.most_correlated_pair}")
        print(f"Avg pairwise correlation: {report.avg_pairwise_correlation:.4f}")
    """

    def __init__(self) -> None:
        """Initialise CorrelationEngine (stateless)."""
        self._logger = logging.getLogger(__name__)

    def compute(
        self,
        multi_result: MultiAssetBacktestResult,
        rolling_windows: tuple[int, int] = (63, 126),
    ) -> CorrelationReport:
        """Compute cross-asset correlation analytics.

        Args:
            multi_result: MultiAssetBacktestResult from MultiAssetRunner.run().
                Requires: asset_results with pnl_series, portfolio_pnl_series.
            rolling_windows: Two rolling window sizes in trading days.
                Default (63, 126) = approximately 3 months and 6 months.

        Returns:
            CorrelationReport with static matrix, rolling correlations,
            realized vols, and derived analytics.

        Raises:
            ValueError: If asset_results is empty.
            ValueError: If rolling_windows does not have exactly 2 elements.
        """
        if not multi_result.asset_results:
            raise ValueError(
                "CorrelationEngine.compute(): no asset results in MultiAssetBacktestResult."
            )
        if len(rolling_windows) != 2:
            raise ValueError(
                f"CorrelationEngine.compute(): rolling_windows must have exactly 2 elements, "
                f"got {len(rolling_windows)}."
            )

        # Step 1: Build aligned returns DataFrame
        initial_capital_per_asset = float(
            next(iter(multi_result.asset_results.values())).metadata.initial_capital_usd
        )
        initial_capital_total = initial_capital_per_asset * len(multi_result.assets)

        returns_df = self._build_returns_dataframe(
            multi_result.asset_results,
            initial_capital_per_asset,
        )

        # Step 2: Static correlation matrix
        correlation_matrix = self._compute_correlation_matrix(returns_df)

        # Step 3: Rolling correlations
        w1, w2 = rolling_windows
        rolling_63 = self._compute_rolling_correlations(returns_df, window=w1)
        rolling_126 = self._compute_rolling_correlations(returns_df, window=w2)

        # Step 4: Realized volatility per asset
        realized_vol_by_asset = self._compute_realized_vols(returns_df)

        # Step 5: Portfolio realized vol
        portfolio_returns = multi_result.portfolio_pnl_series / initial_capital_total
        portfolio_realized_vol = self._annualize_vol(portfolio_returns)

        # Step 6: Derived analytics
        avg_pairwise = self._compute_avg_pairwise_correlation(correlation_matrix)
        most_corr = self._find_extremal_pair(correlation_matrix, highest=True)
        least_corr = self._find_extremal_pair(correlation_matrix, highest=False)

        self._logger.info(
            "CorrelationEngine: %s — %d assets, avg_pairwise_corr=%.4f, "
            "most_corr=%s↔%s(%.4f), least_corr=%s↔%s(%.4f)",
            multi_result.run_id,
            len(multi_result.assets),
            avg_pairwise,
            most_corr[0],
            most_corr[1],
            most_corr[2],
            least_corr[0],
            least_corr[1],
            least_corr[2],
        )

        return CorrelationReport(
            strategy_name=multi_result.strategy_name,
            run_id=multi_result.run_id,
            assets=multi_result.assets,
            computation_date=date.today(),
            correlation_matrix=correlation_matrix,
            rolling_correlations_63=rolling_63,
            rolling_correlations_126=rolling_126,
            realized_vol_by_asset=realized_vol_by_asset,
            portfolio_realized_vol=portfolio_realized_vol,
            avg_pairwise_correlation=avg_pairwise,
            most_correlated_pair=most_corr,
            least_correlated_pair=least_corr,
        )

    def _build_returns_dataframe(
        self,
        asset_results: dict,
        initial_capital_per_asset: float,
    ) -> pd.DataFrame:
        """Build an aligned DataFrame of daily return series per asset.

        Returns are pnl_series / initial_capital_per_asset. Alignment uses
        inner join (intersection of all date indices). Missing dates filled
        with 0.0 (flat trading day = zero return).

        Args:
            asset_results: Dict of asset → BacktestResult.
            initial_capital_per_asset: Denominator for return normalization.

        Returns:
            DataFrame with one column per asset, rows = common trading dates,
            values = daily return fractions.
        """
        if initial_capital_per_asset <= 0:
            raise ValueError(
                "_build_returns_dataframe: initial_capital_per_asset must be > 0"
            )

        returns_dict: dict[str, pd.Series] = {}
        for asset, bt_result in asset_results.items():
            daily_returns = bt_result.pnl_series / initial_capital_per_asset
            returns_dict[asset] = daily_returns

        df = pd.DataFrame(returns_dict)

        # Inner join: only dates where ALL assets have data
        df = df.dropna(how="any")

        if df.empty:
            self._logger.warning(
                "CorrelationEngine: empty returns DataFrame after inner-join — "
                "no common date range across all assets"
            )

        return df

    def _compute_correlation_matrix(
        self,
        returns_df: pd.DataFrame,
    ) -> dict[str, dict[str, float]]:
        """Compute full pairwise Pearson correlation matrix.

        Returns nested dict: matrix[asset_a][asset_b] → float.
        Diagonal entries = 1.0. Symmetric.

        Args:
            returns_df: Aligned daily returns DataFrame.

        Returns:
            Nested dict of float correlations. NaN for any pair with
            insufficient data.
        """
        assets = list(returns_df.columns)
        matrix: dict[str, dict[str, float]] = {a: {} for a in assets}

        if returns_df.empty or len(returns_df) < 2:
            for a in assets:
                for b in assets:
                    matrix[a][b] = 1.0 if a == b else float("nan")
            return matrix

        corr_df = returns_df.corr(method="pearson")

        for a in assets:
            for b in assets:
                try:
                    val = float(corr_df.loc[a, b])
                    matrix[a][b] = val if not math.isnan(val) else float("nan")
                except (KeyError, ValueError):
                    matrix[a][b] = float("nan")

        return matrix

    def _compute_rolling_correlations(
        self,
        returns_df: pd.DataFrame,
        window: int,
    ) -> dict[str, dict[str, pd.Series]]:
        """Compute rolling pairwise correlations at a given window size.

        Args:
            returns_df: Aligned daily returns DataFrame.
            window: Rolling window in trading days (e.g. 63 or 126).

        Returns:
            Nested dict: rolling[asset_a][asset_b] → pd.Series of daily
            rolling correlations. Upper triangle only (asset_a < asset_b
            alphabetically) — diagonal and lower triangle omitted to reduce
            memory. Module 19 can use symmetry to reconstruct the full matrix.

            Returns empty nested dicts if returns_df is empty.
        """
        assets = sorted(returns_df.columns.tolist())
        rolling: dict[str, dict[str, pd.Series]] = {a: {} for a in assets}

        if returns_df.empty or len(returns_df) < window:
            return rolling

        for asset_a, asset_b in combinations(assets, 2):
            if asset_a not in returns_df.columns or asset_b not in returns_df.columns:
                continue
            pair_corr = (
                returns_df[asset_a]
                .rolling(window=window, min_periods=window)
                .corr(returns_df[asset_b])
            )
            rolling[asset_a][asset_b] = pair_corr

        return rolling

    def _compute_realized_vols(
        self,
        returns_df: pd.DataFrame,
    ) -> dict[str, float]:
        """Compute annualized realized volatility per asset.

        std(daily_returns) * sqrt(252). Uses full date range of returns_df.
        Returns NaN if fewer than 20 observations.

        Args:
            returns_df: Aligned daily returns DataFrame.

        Returns:
            Dict of asset → annualized realized vol (decimal fraction).
        """
        vols: dict[str, float] = {}
        for asset in returns_df.columns:
            vols[asset] = self._annualize_vol(returns_df[asset])
        return vols

    def _annualize_vol(self, returns: pd.Series) -> float:
        """Annualize the volatility of a daily return series.

        Args:
            returns: Daily return series (fractions, not percentages).

        Returns:
            Annualized vol = std(returns) * sqrt(252).
            NaN if fewer than 20 valid observations.
        """
        clean = returns.dropna()
        if len(clean) < 20:
            return float("nan")
        return float(clean.std()) * math.sqrt(252)

    def _compute_avg_pairwise_correlation(
        self,
        correlation_matrix: dict[str, dict[str, float]],
    ) -> float:
        """Mean of all unique off-diagonal correlation matrix entries.

        Args:
            correlation_matrix: Nested dict from _compute_correlation_matrix().

        Returns:
            Mean off-diagonal Pearson correlation. NaN if fewer than 2 assets
            or all off-diagonal values are NaN.
        """
        assets = list(correlation_matrix.keys())
        if len(assets) < 2:
            return float("nan")

        off_diagonal_values: list[float] = []
        for a, b in combinations(assets, 2):
            val = correlation_matrix.get(a, {}).get(b, float("nan"))
            if not math.isnan(val):
                off_diagonal_values.append(val)

        if not off_diagonal_values:
            return float("nan")

        return float(sum(off_diagonal_values) / len(off_diagonal_values))

    def _find_extremal_pair(
        self,
        correlation_matrix: dict[str, dict[str, float]],
        highest: bool,
    ) -> tuple[str, str, float]:
        """Find the most or least correlated asset pair.

        Args:
            correlation_matrix: Nested dict from _compute_correlation_matrix().
            highest: If True, find highest absolute correlation.
                     If False, find lowest absolute correlation.

        Returns:
            (asset_a, asset_b, correlation_value) with asset_a < asset_b.
            Returns ("", "", NaN) if fewer than 2 assets or no valid pairs.
        """
        assets = sorted(correlation_matrix.keys())
        if len(assets) < 2:
            return ("", "", float("nan"))

        best_pair: tuple[str, str, float] = ("", "", float("nan"))
        best_abs: float = -1.0 if highest else float("inf")

        for a, b in combinations(assets, 2):
            val = correlation_matrix.get(a, {}).get(b, float("nan"))
            if math.isnan(val):
                continue
            abs_val = abs(val)
            if highest and abs_val > best_abs or not highest and abs_val < best_abs:
                best_abs = abs_val
                best_pair = (a, b, val)

        return best_pair
