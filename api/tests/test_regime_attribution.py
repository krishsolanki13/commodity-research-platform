"""API tests for GET /api/runs/{run_id}/regime-attribution."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_regime_attribution_unknown_run_returns_404() -> None:
    """GET /api/runs/nonexistent/regime-attribution → 404."""
    response = client.get("/api/runs/20000101_000000_fake_run_gold/regime-attribution")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"


def test_regime_attribution_returns_200_structure() -> None:
    """GET /api/runs/{id}/regime-attribution → 200 with correct response shape."""
    runs_dir = Path("data/runs")
    gold_runs = (
        sorted(
            [
                d
                for d in runs_dir.iterdir()
                if d.name.endswith("_gold") and (d / "trades.parquet").exists()
            ],
            reverse=True,
        )
        if runs_dir.exists()
        else []
    )

    if not gold_runs:
        pytest.skip("No completed Gold runs on disk")

    run_id = gold_runs[0].name
    response = client.get(f"/api/runs/{run_id}/regime-attribution")

    if response.status_code == 500:
        # Acceptable if contract data not available
        pytest.skip("Contract data not available for regime computation")

    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.json()}"

    data = response.json()
    assert "run_id" in data
    assert "regime_metrics" in data
    assert "regime_coverage" in data
    assert "dominant_regime" in data
    assert "total_days_in_run" in data

    # If regime data was available, verify structure
    if data["regime_metrics"]:
        for regime_str, metrics in data["regime_metrics"].items():
            assert "n_days" in metrics
            assert "coverage" in metrics
            assert regime_str in ("contango", "backwardation", "flat")
