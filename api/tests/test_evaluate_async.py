"""API tests for async signal evaluation (TD-EVAL-ASYNC)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.models import DecayEntry, SignalEvaluateResponse, SignalEvaluationData
from api.routers import signals as signals_router


def _canned_evaluate_response() -> SignalEvaluateResponse:
    return SignalEvaluateResponse(
        asset="gold",
        strategy="carry",
        params={"threshold": 0.0, "n_contracts": 4},
        evaluation=SignalEvaluationData(
            ic=0.04,
            icir=0.8,
            turnover=0.1,
            decay=[DecayEntry(horizon=h, ic=0.03) for h in (1, 2, 5, 10, 20)],
            evaluation_window=1250,
            computed_at="2026-09-06T00:00:00.000Z",
            ic_band="weak_positive",
        ),
    )


def test_evaluate_async_rejects_sync_only_strategy(client: TestClient) -> None:
    response = client.post(
        "/api/signals/evaluate-async",
        json={
            "asset": "gold",
            "strategy": "ema_crossover",
            "params": {"fast_period": 50, "slow_period": 200},
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "SYNC_ONLY_STRATEGY"


def test_evaluate_sync_rejects_carry(client: TestClient) -> None:
    response = client.post(
        "/api/signals/evaluate",
        json={
            "asset": "gold",
            "strategy": "carry",
            "params": {"threshold": 0.0, "n_contracts": 4},
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ASYNC_REQUIRED_STRATEGY"


def test_evaluate_async_unknown_job_status_404(client: TestClient) -> None:
    response = client.get("/api/signals/evaluate-async/nonexistent_job_xyz/status")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "JOB_NOT_FOUND"


def test_evaluate_async_unknown_job_result_404(client: TestClient) -> None:
    response = client.get("/api/signals/evaluate-async/nonexistent_job_xyz/result")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "JOB_NOT_FOUND"


def test_evaluate_async_result_not_complete_409(client: TestClient) -> None:
    signals_router._evaluate_tasks["queued_job_test"] = {
        "status": "queued",
        "result": None,
        "error": None,
    }
    try:
        response = client.get("/api/signals/evaluate-async/queued_job_test/result")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "JOB_NOT_COMPLETE"
    finally:
        signals_router._evaluate_tasks.pop("queued_job_test", None)


def test_evaluate_async_carry_completes_with_result(client: TestClient) -> None:
    canned = _canned_evaluate_response()
    with patch(
        "api.routers.signals._evaluate_signal_sync",
        return_value=canned,
    ):
        response = client.post(
            "/api/signals/evaluate-async",
            json={
                "asset": "gold",
                "strategy": "carry",
                "params": {"threshold": 0.0, "n_contracts": 4},
                "from_date": "2021-08-28",
                "to_date": "2026-08-28",
            },
        )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    job_id = data["job_id"]
    assert "eval_carry_gold" in job_id

    status = client.get(f"/api/signals/evaluate-async/{job_id}/status")
    assert status.status_code == 200
    assert status.json()["status"] == "complete"

    result = client.get(f"/api/signals/evaluate-async/{job_id}/result")
    assert result.status_code == 200
    body = result.json()
    assert body["strategy"] == "carry"
    assert body["evaluation"]["evaluation_window"] == 1250
    assert body["evaluation"]["ic"] == 0.04
