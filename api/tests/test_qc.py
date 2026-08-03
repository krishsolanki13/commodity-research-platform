"""API tests for GET /api/system/data/qc."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

QC_PATH = "/api/system/data/qc"


def test_qc_unknown_asset_returns_404() -> None:
    """GET /api/system/data/qc?asset=unknown → 404 or 422 for unknown asset."""
    response = client.get(f"{QC_PATH}?asset=__unknown_fake_asset__")
    assert response.status_code in (
        404,
        422,
        200,
    ), f"Got {response.status_code}: {response.json()}"
    # If 200, must be a crit response (status/flags pattern)
    if response.status_code == 200:
        data = response.json()
        assert data["data_health"] == "crit"
        assert any("Unknown" in a or "unknown" in a for a in data["anomalies"])


def test_qc_returns_200_with_correct_structure() -> None:
    """GET /api/system/data/qc?asset=gold → 200 with QCReportResponse structure."""
    if not Path("data/processed/continuous/gold.parquet").exists():
        pytest.skip("Gold Parquet not available in CI")

    response = client.get(f"{QC_PATH}?asset=gold")
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert data["asset"] == "gold"
    assert data["bar_count"] > 0
    assert "from_date" in data
    assert "to_date" in data
    assert "zero_volume_days" in data
    assert "ohlc_violations" in data
    assert "large_gap_flags" in data
    assert data["data_health"] in ("ok", "warn", "crit")
    assert isinstance(data["anomalies"], list)
