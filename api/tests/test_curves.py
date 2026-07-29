"""API tests for commodity intelligence routes — /api/curves/*.

Tests: available list, snapshot structure, NaN serialization,
404 on unknown asset, history structure and field consistency.

Prior baseline: 309 (267 backend + 42 API).
Target: 309 + 6 = 315.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _available_assets() -> list[str]:
    response = client.get("/api/curves/available")
    if response.status_code != 200:
        pytest.skip("Curves available endpoint not reachable")
    return response.json().get("assets", [])


def test_curves_available_returns_200_with_assets_list() -> None:
    """GET /api/curves/available → 200 with list under 'assets'."""
    response = client.get("/api/curves/available")
    assert response.status_code == 200
    data = response.json()
    assert "assets" in data
    assert isinstance(data["assets"], list)


def test_curves_available_contains_at_least_one_platform_asset() -> None:
    """At least one of the 6 platform assets has processed contract data."""
    assets = _available_assets()
    if not assets:
        pytest.skip(
            "No contract data available in CI — data/processed/contracts/ not present"
        )
    platform = {"gold", "silver", "copper", "wti", "brent", "natural_gas"}
    assert (
        len(set(assets) & platform) >= 1
    ), f"Expected at least one platform asset in /api/curves/available, got: {assets}"


def test_curves_snapshot_returns_200_and_required_fields() -> None:
    """GET /api/curves/{asset}/snapshot → 200 with required response fields."""
    assets = _available_assets()
    if not assets:
        pytest.skip("No contract data available")
    asset = assets[0]
    response = client.get(f"/api/curves/{asset}/snapshot?n_contracts=4")
    assert response.status_code == 200
    data = response.json()
    assert data["asset"] == asset
    assert "observation_date" in data
    assert data["regime"] in ("contango", "backwardation", "flat")
    assert isinstance(data["points"], list)
    assert isinstance(data["n_contracts"], int)


def test_curves_snapshot_nan_fields_serialize_as_null() -> None:
    """NaN float fields must appear as JSON null, never 'NaN' (JSON spec)."""
    assets = _available_assets()
    if not assets:
        pytest.skip("No contract data available")
    # n_contracts=1 forces slope/yield NaN (requires >= 2 contracts)
    response = client.get(f"/api/curves/{assets[0]}/snapshot?n_contracts=1")
    assert response.status_code == 200
    assert (
        "NaN" not in response.text
    ), "Literal 'NaN' in response — check @field_serializer on FuturesCurveResponse"
    data = response.json()
    slope = data.get("annualized_slope_pct")
    assert slope is None or isinstance(slope, float)


def test_curves_snapshot_unknown_asset_returns_404() -> None:
    """GET /api/curves/notanasset/snapshot → 404."""
    response = client.get("/api/curves/notanasset/snapshot")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_curves_history_returns_snapshots_with_correct_structure() -> None:
    """GET /api/curves/{asset}/history → 200, n_snapshots == len(snapshots)."""
    assets = _available_assets()
    asset_to_test = next((a for a in ["gold", "silver", "wti"] if a in assets), None)
    if asset_to_test is None:
        pytest.skip("None of gold/silver/wti have contract data")
    response = client.get(
        f"/api/curves/{asset_to_test}/history"
        "?from_date=2025-01-01&to_date=2026-07-01&n_contracts=4"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["asset"] == asset_to_test
    assert isinstance(data["snapshots"], list)
    assert data["n_snapshots"] == len(data["snapshots"])
    required = {
        "observation_date",
        "regime",
        "n_contracts",
        "annualized_slope_pct",
        "roll_yield_annualized",
        "front_price",
    }
    for snap in data["snapshots"]:
        assert not (required - set(snap.keys()))
        assert snap["regime"] in ("contango", "backwardation", "flat")
        assert "NaN" not in json.dumps(
            snap
        ), f"NaN in snapshot {snap['observation_date']} — must be null"


def test_curves_snapshot_historical_observation_date() -> None:
    """GET /api/curves/{asset}/snapshot?observation_date= returns
    a snapshot for a specific historical date, not today.
    """
    assets = _available_assets()
    asset_to_test = next((a for a in ["gold", "silver", "wti"] if a in assets), None)
    if asset_to_test is None:
        pytest.skip("None of gold/silver/wti have contract data")

    # Request a historical date known to be within the contract data window
    response = client.get(
        f"/api/curves/{asset_to_test}/snapshot"
        "?n_contracts=4&observation_date=2025-06-01"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["asset"] == asset_to_test
    # observation_date in response must be on or before the requested date
    # (builder returns nearest available date <= observation_date)
    assert (
        data["observation_date"] <= "2025-06-01"
    ), f"Expected observation_date <= 2025-06-01, got {data['observation_date']}"
    assert data["regime"] in ("contango", "backwardation", "flat")
    assert "NaN" not in response.text
