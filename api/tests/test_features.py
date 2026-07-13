from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient


def _make_ohlcv(n: int = 300) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    rng = np.random.default_rng(42)
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


def _make_feature_frame(ohlcv: pd.DataFrame) -> MagicMock:
    """Fake FeatureFrame with ema_50 and ema_200 columns."""
    df = ohlcv.copy()
    df["ema_50"] = df["close"].ewm(span=50).mean()
    df["ema_200"] = df["close"].ewm(span=200).mean()
    ff = MagicMock()
    ff.data = df
    ff.feature_specs = [
        MagicMock(
            indicator_name="ema",
            parameters={"period": 50},
            column_name="ema_50",
            asset="gold",
            computed_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        ),
        MagicMock(
            indicator_name="ema",
            parameters={"period": 200},
            column_name="ema_200",
            asset="gold",
            computed_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        ),
    ]
    return ff


def test_get_indicators_returns_five(client: TestClient) -> None:
    response = client.get("/api/indicators")
    assert response.status_code == 200
    names = [i["name"] for i in response.json()["indicators"]]
    assert set(names) == {"sma", "ema", "rsi", "rvgi", "momentum"}


def test_get_indicators_each_has_params_schema(client: TestClient) -> None:
    response = client.get("/api/indicators")
    for ind in response.json()["indicators"]:
        assert len(ind["params_schema"]) >= 1
        assert "name" in ind["params_schema"][0]
        assert "default" in ind["params_schema"][0]


def test_compute_features_happy_path(client: TestClient) -> None:
    ohlcv = _make_ohlcv()
    ff = _make_feature_frame(ohlcv)
    with (
        patch("src.data.loader.DataLoader") as mock_loader,
        patch("src.research.pipeline.FeaturePipeline") as mock_pipeline,
    ):
        mock_loader.return_value.load.return_value = ohlcv
        mock_pipeline.return_value.compute.return_value = ff
        response = client.post(
            "/api/features/compute",
            json={
                "asset": "gold",
                "specs": [
                    {"name": "ema", "params": {"period": 50}},
                    {"name": "ema", "params": {"period": 200}},
                ],
            },
        )
    assert response.status_code == 200
    cols = response.json()["columns"]["columns"]
    assert any("ema" in k for k in cols)


def test_compute_features_unknown_indicator_400(client: TestClient) -> None:
    ohlcv = _make_ohlcv()
    with patch("src.data.loader.DataLoader") as mock_loader:
        mock_loader.return_value.load.return_value = ohlcv
        response = client.post(
            "/api/features/compute",
            json={
                "asset": "gold",
                "specs": [{"name": "nonexistent_indicator", "params": {}}],
            },
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNKNOWN_INDICATOR"


def test_compute_features_calls_only_pipeline(client: TestClient) -> None:
    """Handler must call FeaturePipeline.compute — not signal or backtest modules."""
    ohlcv = _make_ohlcv()
    ff = _make_feature_frame(ohlcv)
    with (
        patch("src.data.loader.DataLoader") as mock_loader,
        patch("src.research.pipeline.FeaturePipeline") as mock_pipeline,
    ):
        mock_loader.return_value.load.return_value = ohlcv
        mock_pipeline.return_value.compute.return_value = ff
        client.post(
            "/api/features/compute",
            json={
                "asset": "gold",
                "specs": [{"name": "ema", "params": {"period": 50}}],
            },
        )
        assert mock_pipeline.return_value.compute.call_count == 1
