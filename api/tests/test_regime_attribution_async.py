"""API tests for async regime attribution endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_regime_attribution_compute_unknown_run_returns_202() -> None:
    """POST /api/regime-attribution/compute with nonexistent run → 202 immediately.
    The job launches async; error surfaces in status poll, not in the 202 response."""
    response = client.post(
        "/api/regime-attribution/compute",
        json={"run_id": "nonexistent_run_id_12345", "asset": "gold", "n_contracts": 4},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"


def test_regime_attribution_status_unknown_job_returns_404() -> None:
    """GET /api/regime-attribution/{unknown}/status → 404."""
    response = client.get("/api/regime-attribution/nonexistent_job_id_xyz/status")
    assert response.status_code == 404
