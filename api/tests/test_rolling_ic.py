"""API tests for GET /api/signals/rolling-ic.

3 tests: invalid params → 422, valid request → 200 with ColumnarSeries structure,
NaN serializes as null (no literal 'NaN' in response).
Data-dependent tests skip in CI if no Gold Parquet.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_PATH = Path("data/processed/continuous/gold.parquet")


def test_rolling_ic_invalid_params_returns_422(client) -> None:
    """GET /api/signals/rolling-ic with invalid params JSON → 422."""
    response = client.get(
        "/api/signals/rolling-ic"
        "?asset=gold&strategy=ema_crossover&params=not_valid_json"
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.slow
@pytest.mark.timeout(0)
def test_rolling_ic_returns_200_with_columnar_structure(client) -> None:
    """GET /api/signals/rolling-ic → 200 with index and columns.rolling_ic."""
    if not DATA_PATH.exists():
        pytest.skip("Gold Parquet not available in CI")

    params = json.dumps({"fast_period": 50, "slow_period": 200})
    response = client.get(
        f"/api/signals/rolling-ic"
        f"?asset=gold&strategy=ema_crossover&params={params}&window=63"
    )
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.json()}"

    data = response.json()
    assert "data" in data, "Response must have 'data' field"
    assert "index" in data["data"], "data must have 'index' (epoch-ms list)"
    assert "columns" in data["data"], "data must have 'columns' dict"
    assert (
        "rolling_ic" in data["data"]["columns"]
    ), "columns must contain 'rolling_ic' key"

    index = data["data"]["index"]
    assert len(index) > 0, "index must be non-empty"
    assert all(
        t > 1_000_000_000_000 for t in index if t is not None
    ), "All index values must be epoch-ms (> 1e12)"


@pytest.mark.slow
@pytest.mark.timeout(0)
def test_rolling_ic_no_nan_literal_in_response(client) -> None:
    """NaN values must serialize as JSON null, not literal 'NaN'."""
    if not DATA_PATH.exists():
        pytest.skip("Gold Parquet not available in CI")

    params = json.dumps({"fast_period": 50, "slow_period": 200})
    response = client.get(
        f"/api/signals/rolling-ic"
        f"?asset=gold&strategy=ema_crossover&params={params}&window=63"
    )
    assert response.status_code == 200

    assert (
        "NaN" not in response.text
    ), "Literal 'NaN' in response — NaN must serialize as JSON null."

    rolling_ic_values = response.json()["data"]["columns"]["rolling_ic"]
    first_62 = rolling_ic_values[:62]
    assert all(v is None for v in first_62), (
        f"First 62 values must be null (window=63). "
        f"Non-null at indices: {[i for i, v in enumerate(first_62) if v is not None]}"
    )
