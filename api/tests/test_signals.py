from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api.routers.signals import classify_ic_band


def _make_ohlcv(n: int = 300) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    rng = np.random.default_rng(7)
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


def _make_signal(n: int = 300) -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    return pd.Series(np.random.default_rng(9).uniform(-1, 1, n), index=idx)


def _make_evaluation(ic: float) -> MagicMock:
    ev = MagicMock()
    ev.ic = ic
    ev.icir = ic * 2.0
    ev.turnover = 0.05
    ev.ic_decay = {1: ic, 2: ic * 0.9, 5: ic * 0.7, 10: ic * 0.5, 20: ic * 0.3}
    return ev


def test_get_strategies_returns_four(client: TestClient) -> None:
    response = client.get("/api/strategies")
    assert response.status_code == 200
    names = [s["name"] for s in response.json()["strategies"]]
    assert set(names) == {
        "ema_crossover",
        "momentum",
        "rsi_reversion",
        "donchian_breakout",
        "carry",
    }


def test_generate_signal_happy_path(client: TestClient) -> None:
    ohlcv = _make_ohlcv()
    raw = _make_signal()
    with patch(
        "api.routers.signals._run_signal_pipeline",
        return_value=(ohlcv, raw, raw.apply(lambda x: 1 if x > 0 else -1)),
    ):
        response = client.post(
            "/api/signals/generate",
            json={
                "asset": "gold",
                "strategy": "ema_crossover",
                "params": {"fast_period": 50, "slow_period": 200},
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "raw_signal" in data
    assert "position_signal" in data
    assert "raw" in data["raw_signal"]["columns"]
    assert "position" in data["position_signal"]["columns"]


def test_generate_signal_unknown_strategy_400(client: TestClient) -> None:
    response = client.post(
        "/api/signals/generate",
        json={
            "asset": "gold",
            "strategy": "magic_oscillator",
            "params": {},
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNKNOWN_STRATEGY"


def test_evaluate_signal_happy_path(client: TestClient) -> None:
    ohlcv = _make_ohlcv()
    raw = _make_signal()
    ev = _make_evaluation(ic=0.06)
    with (
        patch(
            "api.routers.signals._run_signal_pipeline",
            return_value=(ohlcv, raw, raw),
        ),
        patch("src.signal.evaluation.SignalEvaluator") as mock_eval,
    ):
        mock_eval.return_value.evaluate.return_value = ev
        response = client.post(
            "/api/signals/evaluate",
            json={
                "asset": "gold",
                "strategy": "ema_crossover",
                "params": {"fast_period": 50, "slow_period": 200},
            },
        )
    assert response.status_code == 200
    assert "evaluation" in response.json()
    assert "ic_band" in response.json()["evaluation"]


def test_ic_band_noise() -> None:
    assert classify_ic_band(0.01) == "noise"
    assert classify_ic_band(-0.01) == "noise"
    assert classify_ic_band(None) == "noise"


def test_ic_band_strong() -> None:
    assert classify_ic_band(0.06) == "strong"
    assert classify_ic_band(0.10) == "strong"


def test_ic_band_inverse_meaningful() -> None:
    assert classify_ic_band(-0.06) == "inverse_meaningful"
    assert classify_ic_band(-0.08) == "inverse_meaningful"
