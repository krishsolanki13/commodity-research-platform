from __future__ import annotations

import pandas as pd

from api.models import ColumnarSeries, df_to_columnar


def test_columnar_series_nan_serializes_as_null() -> None:
    """None values in ColumnarSeries must serialize as JSON null, not NaN."""
    series = ColumnarSeries(index=[1_000], columns={"v": [None]})
    json_str = series.model_dump_json()
    assert "null" in json_str
    assert "NaN" not in json_str


def test_df_to_columnar_epoch_ms() -> None:
    """df_to_columnar must emit epoch-millisecond integers, not nanoseconds."""
    idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    df = pd.DataFrame({"close": [100.0, 101.0, 102.0, 103.0, 104.0]}, index=idx)
    result = df_to_columnar(df)
    # 2024-01-01 UTC in epoch ms ≈ 1_704_067_200_000 — well above 1 trillion
    assert result.index[0] > 1_000_000_000_000
    assert len(result.index) == 5
    assert "close" in result.columns
    assert len(result.columns["close"]) == 5
