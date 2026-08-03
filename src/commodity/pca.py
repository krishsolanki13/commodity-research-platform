"""Forward curve Principal Component Analysis for commodity term structure.

Decomposes the multi-maturity forward curve into orthogonal factors (Level,
Slope, Curvature) using PCA. Each factor is a time series explaining a
fraction of the total variance in curve movements.

Standard in institutional commodity research. References:
  Cortazar, G. & Schwartz, E. (1994). The valuation of commodity contingent
  claims. Journal of Derivatives, 1(4), 27-39.

  Clewlow, L. & Strickland, C. (2000). Energy Derivatives. Lacima Group.

Algorithm:
  1. Build historical curves via FuturesCurveBuilder.
  2. Extract front-to-Nth contract price at each date.
  3. Normalize by front-month price (eliminates level of prices,
     keeps the SHAPE of the curve for shape-factor PCA).
  4. Demean each column (maturity) across time.
  5. Apply PCA (sklearn if available, numpy SVD otherwise).
  6. Return loadings, explained variance, and PC time series.
"""

from __future__ import annotations

import datetime
import logging
import math
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.core.config import Config
    from src.core.types import CurvePCAResult

logger = logging.getLogger(__name__)


class CurvePCAEngine:
    """Computes PCA on a commodity's historical forward curve.

    Uses price normalization (each contract price / front-month price) to
    focus PCA on curve SHAPE rather than price level. This produces the
    standard Level/Slope/Curvature interpretation.

    Args:
        config: Platform Config for loading contract data.
    """

    def __init__(self, config: Config) -> None:
        self._config = config

    def compute(
        self,
        asset: str,
        n_components: int = 3,
        n_contracts: int = 4,
        from_date: datetime.date | None = None,
        to_date: datetime.date | None = None,
    ) -> CurvePCAResult:
        """Run forward curve PCA for the specified asset and date range.

        Args:
            asset: Asset identifier (e.g. 'gold').
            n_components: Number of principal components to retain (default 3).
            n_contracts: Number of forward curve contracts to include.
            from_date: Start date (inclusive). Default: earliest available.
            to_date: End date (inclusive). Default: latest available.

        Returns:
            CurvePCAResult with loadings, explained variance, and PC series.

        Raises:
            ValueError: If asset has no contract data or insufficient observations.
        """
        from src.commodity.curve import FuturesCurveBuilder  # noqa: PLC0415
        from src.core.types import CurvePCAResult  # noqa: PLC0415
        from src.data.loader import DataLoader  # noqa: PLC0415

        logger.info(
            "CurvePCAEngine: computing for %s — n_components=%d, n_contracts=%d",
            asset,
            n_components,
            n_contracts,
        )

        builder = FuturesCurveBuilder(self._config)

        # Check contract data availability
        available = builder.available_assets()
        if asset not in available:
            raise ValueError(
                f"No contract data for '{asset}'. Available: {sorted(available)}"
            )

        # Use continuous OHLCV date range as the trading calendar
        loader = DataLoader(self._config)
        ohlcv = loader.load(asset)

        # Filter date range
        all_dates = [d.date() for d in ohlcv.index]
        if from_date:
            all_dates = [d for d in all_dates if d >= from_date]
        if to_date:
            all_dates = [d for d in all_dates if d <= to_date]

        if not all_dates:
            raise ValueError(
                f"No trading dates for '{asset}' in range [{from_date}, {to_date}]."
            )

        logger.info(
            "CurvePCAEngine: building curves for %d dates (%s to %s)",
            len(all_dates),
            all_dates[0],
            all_dates[-1],
        )

        # Build historical curves
        curves = builder.build_historical_curves(
            asset=asset,
            dates=all_dates,
            n_contracts=n_contracts,
        )

        # ── Step 1: Extract price matrix ─────────────────────────────────
        price_matrix, valid_dates = self._extract_price_matrix(
            curves=curves,
            dates=all_dates,
            n_contracts=n_contracts,
        )

        if price_matrix is None or len(price_matrix) < n_components + 5:
            raise ValueError(
                f"Insufficient valid curve observations for PCA on '{asset}'. "
                f"Got {0 if price_matrix is None else len(price_matrix)} valid dates, "
                f"need at least {n_components + 5}."
            )

        logger.info(
            "CurvePCAEngine: price matrix shape %s (%d valid dates of %d total)",
            price_matrix.shape,
            len(valid_dates),
            len(all_dates),
        )

        # ── Step 2: Normalize by front-month price ────────────────────────
        # normalized[t, i] = price[t, i] / price[t, 0]
        # After normalization, front-month column is identically 1.0.
        # PCA on this matrix captures curve SHAPE factors (slope, curvature)
        # relative to the front-month reference price.
        front_prices = price_matrix[:, 0:1]  # keep 2D for broadcasting
        normalized = price_matrix / front_prices

        # ── Step 3: Demean each column ────────────────────────────────────
        col_means = normalized.mean(axis=0)
        demeaned = normalized - col_means

        # ── Step 4: PCA ───────────────────────────────────────────────────
        n_components_actual = min(n_components, n_contracts, len(valid_dates) - 1)
        loadings, explained_var_ratio, factor_scores = self._run_pca(
            demeaned, n_components=n_components_actual
        )

        # ── Step 5: Build result ──────────────────────────────────────────
        pc_labels = [f"PC{i + 1}" for i in range(n_components_actual)]
        cumulative = [
            float(sum(explained_var_ratio[: i + 1]))
            for i in range(len(explained_var_ratio))
        ]

        # Loadings: dict of PC label → list of loadings per maturity
        loadings_dict = {
            pc_labels[i]: [float(v) for v in loadings[i]]
            for i in range(n_components_actual)
        }

        # Factor series: dict of PC label → list of factor values
        factor_series_dict: dict[str, list[float | None]] = {
            pc_labels[i]: [float(v) for v in factor_scores[:, i]]
            for i in range(n_components_actual)
        }
        # Epoch-ms timestamps for valid dates
        epoch_ms = [
            int(pd.Timestamp(d, tz="UTC").as_unit("ns").value // 1_000_000)
            for d in valid_dates
        ]

        logger.info(
            "CurvePCAEngine: complete. PC1=%.1f%%, PC2=%.1f%%, cumulative_%dPC=%.1f%%",
            explained_var_ratio[0] * 100 if len(explained_var_ratio) > 0 else 0,
            explained_var_ratio[1] * 100 if len(explained_var_ratio) > 1 else 0,
            n_components_actual,
            cumulative[-1] * 100 if cumulative else 0,
        )

        return CurvePCAResult(
            asset=asset,
            n_components=n_components_actual,
            n_contracts=n_contracts,
            n_observation_dates=len(valid_dates),
            computation_date=datetime.date.today(),
            explained_variance_ratio=[float(v) for v in explained_var_ratio],
            cumulative_variance_ratio=cumulative,
            loadings=loadings_dict,
            factor_series=factor_series_dict,
            factor_index_epoch_ms=epoch_ms,
            pc_labels=pc_labels,
        )

    def _extract_price_matrix(
        self,
        curves: list,
        dates: list[datetime.date],
        n_contracts: int,
    ) -> tuple[np.ndarray | None, list[datetime.date]]:
        """Extract price matrix from FuturesCurve list.

        Builds a (n_dates × n_contracts) matrix from FuturesCurve objects.
        Rows with missing or non-positive prices are dropped.

        Returns:
            (price_matrix, valid_dates) — both aligned.
            Returns (None, []) if no valid rows found.
        """
        rows = []
        valid_dates = []

        for curve, date in zip(curves, dates, strict=False):
            prices = self._get_contract_prices(curve, n_contracts)
            if prices is None or len(prices) < n_contracts:
                continue
            if any(math.isnan(p) or p <= 0 for p in prices):
                continue
            rows.append(prices)
            valid_dates.append(date)

        if not rows:
            return None, []

        return np.array(rows, dtype=float), valid_dates

    def _get_contract_prices(
        self,
        curve: object,
        n_contracts: int,
    ) -> list[float] | None:
        """Extract ordered contract prices from a FuturesCurve object.

        FuturesCurve (src/core/types.py) has:
          .prices  — property returning list[float] ordered front-to-back
          .points  — list[CurvePoint], each with .close: float

        Returns None if the curve has insufficient contracts.
        """
        # Pattern A: .prices property (FuturesCurve canonical property)
        if hasattr(curve, "prices"):
            prices = list(curve.prices)
            return prices[:n_contracts] if len(prices) >= n_contracts else None

        # Pattern B: .points list of CurvePoint objects (each with .close)
        if hasattr(curve, "points"):
            points = list(curve.points)
            if len(points) < n_contracts:
                return None
            return [
                float(getattr(p, "close", float("nan"))) for p in points[:n_contracts]
            ]

        logger.warning(
            "CurvePCAEngine: unknown FuturesCurve structure — attributes: %s",
            [a for a in dir(curve) if not a.startswith("_")],
        )
        return None

    def _run_pca(
        self,
        matrix: np.ndarray,
        n_components: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Run PCA and return (loadings, explained_variance_ratio, scores).

        Uses sklearn if available, numpy SVD otherwise.
        Both approaches produce equivalent results.

        Returns:
            loadings: shape (n_components, n_features) — eigenvectors
            explained_variance_ratio: shape (n_components,) — fraction of variance
            scores: shape (n_observations, n_components) — factor time series
        """
        try:
            from sklearn.decomposition import PCA as _PCA  # noqa: PLC0415

            pca = _PCA(n_components=n_components)
            scores = pca.fit_transform(matrix)
            return pca.components_, pca.explained_variance_ratio_, scores

        except ImportError:
            pass

        # numpy SVD fallback — S_full computed before truncation (Constraint 8)
        _, s_full, _ = np.linalg.svd(matrix, full_matrices=False)
        total_var = float(np.sum(s_full**2))

        u, s, vt = np.linalg.svd(matrix, full_matrices=False)
        u = u[:, :n_components]
        s_trunc = s[:n_components]
        vt = vt[:n_components, :]

        scores = u * s_trunc[np.newaxis, :]
        explained = s_trunc**2 / total_var if total_var > 0 else np.zeros(n_components)

        return vt, explained, scores
