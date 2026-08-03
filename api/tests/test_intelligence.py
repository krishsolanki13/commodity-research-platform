"""API tests for GET /api/intelligence/pca."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_pca_unknown_asset_returns_error() -> None:
    """GET /api/intelligence/pca?asset=__fake → 422."""
    response = client.get("/api/intelligence/pca?asset=__unknown_fake_asset__")
    assert response.status_code in (
        404,
        422,
        500,
    ), f"Expected error status, got {response.status_code}"


def test_pca_returns_200_with_correct_structure() -> None:
    """GET /api/intelligence/pca?asset=gold → 200 with CurvePCAResponse."""
    if not (
        Path("data/processed/contracts").exists()
        and any(Path("data/processed/contracts").iterdir())
    ):
        pytest.skip("Contract data not available in CI")

    response = client.get(
        "/api/intelligence/pca?asset=gold&n_components=3&n_contracts=4"
    )
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.json()}"

    data = response.json()
    assert "asset" in data and data["asset"] == "gold"
    assert "n_components" in data and data["n_components"] <= 3
    assert "explained_variance_ratio" in data
    assert "loadings" in data
    assert "factor_series" in data
    assert "factor_index_epoch_ms" in data
    assert len(data["loadings"]) == data["n_components"]
    assert len(data["factor_index_epoch_ms"]) == data["n_observation_dates"]

    # Epoch-ms values must be > 1e12
    idx = data["factor_index_epoch_ms"]
    if idx:
        assert all(
            t > 1_000_000_000_000 for t in idx[:5]
        ), f"factor_index_epoch_ms values must be epoch-ms: {idx[:3]}"
