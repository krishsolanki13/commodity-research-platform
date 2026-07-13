from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient


def _make_ohlcv(n: int = 500) -> pd.DataFrame:
    """Synthetic NormalizedOHLCV DataFrame with UTC DatetimeIndex."""
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    rng = np.random.default_rng(0)
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


def test_get_assets_returns_six_assets(client: TestClient) -> None:
    with patch("api.routers.assets._load_ohlcv", return_value=_make_ohlcv()):
        response = client.get("/api/assets")
    assert response.status_code == 200
    assert len(response.json()["assets"]) == 6


def test_get_assets_total_runs_present(client: TestClient) -> None:
    with (
        patch("api.routers.assets._load_ohlcv", return_value=_make_ohlcv()),
        patch("api.routers.assets._load_asset_metadata", return_value=[]),
    ):
        response = client.get("/api/assets")
    assert response.status_code == 200
    assert "total_runs" in response.json()


def test_get_ohlcv_shape(client: TestClient) -> None:
    mock_df = _make_ohlcv(500)
    with patch("api.routers.assets._load_ohlcv", return_value=mock_df):
        response = client.get("/api/assets/gold/ohlcv")
    assert response.status_code == 200
    data = response.json()
    assert data["bars"] == 500
    assert data["downsampled"] is False
    assert len(data["data"]["index"]) == 500


def test_get_ohlcv_downsample_triggers(client: TestClient) -> None:
    mock_df = _make_ohlcv(4000)
    with patch("api.routers.assets._load_ohlcv", return_value=mock_df):
        response = client.get("/api/assets/gold/ohlcv?downsample=view")
    assert response.status_code == 200
    data = response.json()
    assert data["downsampled"] is True
    assert data["bars"] <= 3000
    assert data["bars_original"] == 4000


def test_get_ohlcv_unknown_asset_404(client: TestClient) -> None:
    response = client.get("/api/assets/unobtainium/ohlcv")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASSET_NOT_FOUND"


def test_get_ohlcv_index_is_epoch_ms(client: TestClient) -> None:
    mock_df = _make_ohlcv(5)
    with patch("api.routers.assets._load_ohlcv", return_value=mock_df):
        response = client.get("/api/assets/gold/ohlcv")
    assert response.status_code == 200
    first_index = response.json()["data"]["index"][0]
    assert first_index > 1_000_000_000_000
