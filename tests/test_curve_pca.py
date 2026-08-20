"""Backend tests for CurvePCAEngine.

3 tests:
  - 1 pure unit (always runs — mathematical invariant)
  - 2 data-dependent (skip if no contract data)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

CONTRACT_PATH = Path("data/processed/contracts")
HAS_CONTRACT_DATA = CONTRACT_PATH.exists() and any(CONTRACT_PATH.iterdir())
SKIP_NO_CONTRACT = pytest.mark.skipif(
    not HAS_CONTRACT_DATA,
    reason="Contract Parquet files not available in CI",
)


def test_curve_pca_engine_run_pca_explained_variance_sums_correctly() -> None:
    """_run_pca() explained_variance_ratio values sum to <= 1.0.

    Tests the PCA computation in isolation using synthetic data.
    Verifies that explained variance is a valid probability distribution.
    """
    from src.commodity.pca import CurvePCAEngine

    config = MagicMock()
    engine = CurvePCAEngine(config=config)

    # Synthetic curve price matrix: 100 dates × 4 contracts
    rng = np.random.default_rng(42)
    matrix = rng.normal(0, 1, size=(100, 4))

    loadings, evr, scores = engine._run_pca(matrix, n_components=3)

    assert len(evr) == 3, f"Expected 3 EVR values, got {len(evr)}"
    assert all(0.0 <= v <= 1.0 for v in evr), f"EVR values must be in [0, 1]: {evr}"
    assert sum(evr) <= 1.0 + 1e-9, f"EVR values must sum to <= 1.0: sum={sum(evr):.6f}"
    assert loadings.shape == (3, 4), f"Loadings shape: {loadings.shape}"
    assert scores.shape == (100, 3), f"Scores shape: {scores.shape}"


@SKIP_NO_CONTRACT
@pytest.mark.slow
@pytest.mark.timeout(0)
def test_curve_pca_gold_produces_valid_result() -> None:
    """CurvePCAEngine.compute() on Gold produces a valid CurvePCAResult."""
    from src.commodity.pca import CurvePCAEngine
    from src.core.config import Config
    from src.core.types import CurvePCAResult

    config = Config.load()
    engine = CurvePCAEngine(config=config)
    result = engine.compute(asset="gold", n_components=3, n_contracts=4)

    assert isinstance(result, CurvePCAResult)
    assert result.asset == "gold"
    assert result.n_components <= 3
    assert result.n_observation_dates > 0
    assert len(result.explained_variance_ratio) == result.n_components
    assert len(result.loadings) == result.n_components
    assert len(result.factor_index_epoch_ms) == result.n_observation_dates


@SKIP_NO_CONTRACT
@pytest.mark.slow
@pytest.mark.timeout(0)
def test_curve_pca_explained_variance_invariants() -> None:
    """Explained variance invariants: monotone, sums correctly, PC1 is largest."""
    from src.commodity.pca import CurvePCAEngine
    from src.core.config import Config

    config = Config.load()
    engine = CurvePCAEngine(config=config)
    result = engine.compute(asset="gold", n_components=3, n_contracts=4)

    evr = result.explained_variance_ratio
    if len(evr) < 2:
        pytest.skip("Too few components for monotonicity check")

    # PC1 explains the most variance
    assert evr[0] == max(
        evr
    ), f"PC1 ({evr[0]:.4f}) must explain >= variance of any other PC: {evr}"

    # Cumulative variance is non-decreasing
    cumvar = result.cumulative_variance_ratio
    for i in range(1, len(cumvar)):
        assert (
            cumvar[i] >= cumvar[i - 1] - 1e-9
        ), f"Cumulative variance must be non-decreasing: {cumvar}"

    # Total explained variance is in [0, 1]
    assert (
        0.0 <= cumvar[-1] <= 1.0 + 1e-9
    ), f"Total explained variance {cumvar[-1]:.4f} out of [0, 1]"

    # Factor series lengths match observation count
    for pc_label, series in result.factor_series.items():
        assert len(series) == result.n_observation_dates, (
            f"{pc_label} factor series length {len(series)} != "
            f"n_observation_dates {result.n_observation_dates}"
        )
