"""API tests for sweep endpoints.

3 tests:
  1. POST /api/sweeps returns 202 with sweep_id and n_combinations (always runs)
  2. GET /api/sweeps/{id}/status returns 404 for unknown sweep (always runs)
  3. GET /api/sweeps returns 200 with list structure (always runs)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.mark.slow
@pytest.mark.timeout(0)
def test_sweep_launch_returns_202_with_sweep_id() -> None:
    """POST /api/sweeps → 202 with sweep_id and correct n_combinations."""
    response = client.post(
        "/api/sweeps",
        json={
            "asset": "gold",
            "strategy_name": "ema_crossover",
            "param_grid": {
                "fast_period": [10, 20],
                "slow_period": [100, 200],
            },
        },
    )
    assert (
        response.status_code == 202
    ), f"Expected 202, got {response.status_code}: {response.json()}"
    data = response.json()
    assert "sweep_id" in data
    assert data["status"] == "queued"
    assert data["n_combinations"] == 4  # 2 × 2


def test_sweep_status_unknown_returns_404() -> None:
    """GET /api/sweeps/nonexistent/status → 404."""
    response = client.get("/api/sweeps/20000101_000000_sweep_fake_strategy_gold/status")
    assert response.status_code == 404


def test_sweep_list_returns_200_with_list_structure() -> None:
    """GET /api/sweeps → 200 with 'sweeps' list and 'total' count."""
    response = client.get("/api/sweeps")
    assert response.status_code == 200
    data = response.json()
    assert "sweeps" in data
    assert "total" in data
    assert isinstance(data["sweeps"], list)
    assert data["total"] == len(data["sweeps"])
