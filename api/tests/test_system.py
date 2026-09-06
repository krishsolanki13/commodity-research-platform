from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient


def _make_ohlcv(n: int = 100) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    rng = np.random.default_rng(1)
    return pd.DataFrame(
        {
            "open": rng.uniform(900, 1100, n),
            "high": rng.uniform(1050, 1150, n),
            "low": rng.uniform(850, 950, n),
            "close": rng.uniform(900, 1100, n),
            "volume": rng.uniform(1e5, 1e7, n),
        },
        index=idx,
    )


def test_data_status_has_all_assets(client: TestClient) -> None:
    with patch("src.data.loader.DataLoader") as mock_loader:
        instance = mock_loader.return_value
        instance.load.return_value = _make_ohlcv()
        response = client.get("/api/system/data-status")
    assert response.status_code == 200
    names = [a["name"] for a in response.json()["assets"]]
    assert set(names) == {"gold", "silver", "copper", "wti", "brent", "natural_gas"}


def test_ingest_calls_data_loader(client: TestClient) -> None:
    with patch("src.data.loader.DataLoader") as mock_loader:
        instance = mock_loader.return_value
        instance.load.return_value = _make_ohlcv()
        response = client.post("/api/system/ingest", json={"asset": "gold"})
    assert response.status_code == 202
    assert "gold" in response.json()["assets_ingested"]
    instance.load.assert_called_once_with("gold")


def test_config_excludes_secrets(client: TestClient) -> None:
    response = client.get("/api/system/config")
    assert response.status_code == 200
    import json

    flat = json.dumps(response.json()).lower()
    for term in ["password", "api_key", "secret"]:
        assert f'"{term}"' not in flat, f"Found sensitive key: {term}"


def test_curve_coverage_unknown_asset_404(client: TestClient) -> None:
    response = client.get("/api/system/curve-coverage/not_an_asset")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ASSET_NOT_FOUND"


def test_curve_coverage_returns_cached_date(client: TestClient) -> None:
    from datetime import date  # noqa: PLC0415

    with patch(
        "api.curve_coverage.get_curve_coverage_start",
        return_value=date(2024, 9, 27),
    ):
        response = client.get("/api/system/curve-coverage/gold")
    assert response.status_code == 200
    data = response.json()
    assert data["asset"] == "gold"
    assert data["curve_coverage_start"] == "2024-09-27"
    assert "Carry" in data["message"]
