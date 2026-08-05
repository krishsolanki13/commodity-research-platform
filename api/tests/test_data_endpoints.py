"""API tests for COT and EIA data endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

SKIP_NO_COT = pytest.mark.skipif(
    not Path("data/processed/cot/gold.parquet").exists(),
    reason="COT data not acquired",
)

SKIP_NO_EIA = pytest.mark.skipif(
    not Path("data/processed/eia/wti.parquet").exists(),
    reason="EIA data not acquired",
)


@SKIP_NO_COT
def test_cot_endpoint_returns_200_for_gold() -> None:
    """GET /api/system/data/cot?asset=gold returns available COT records."""
    response = client.get("/api/system/data/cot?asset=gold")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert len(data["records"]) > 0


def test_cot_endpoint_brent_returns_unavailable() -> None:
    """Brent has no CFTC COT data — available=False."""
    response = client.get("/api/system/data/cot?asset=brent")
    assert response.status_code == 200
    assert response.json()["available"] is False


@SKIP_NO_EIA
def test_eia_endpoint_returns_200_for_wti() -> None:
    """GET /api/system/data/eia?asset=wti returns available EIA records."""
    response = client.get("/api/system/data/eia?asset=wti")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert len(data["records"]) > 0


def test_eia_endpoint_gold_returns_unavailable() -> None:
    """Gold is not a crude oil asset — available=False."""
    response = client.get("/api/system/data/eia?asset=gold")
    assert response.status_code == 200
    assert response.json()["available"] is False
