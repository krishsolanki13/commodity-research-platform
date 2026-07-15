from __future__ import annotations

import pandas as pd

from api.models import ColumnarSeries, df_to_columnar


def test_columnar_series_nan_serializes_as_null() -> None:
    """None values in ColumnarSeries must serialize as JSON null, not NaN."""
    series = ColumnarSeries(index=[1_000], columns={"v": [None]})
    json_str = series.model_dump_json()
    assert "null" in json_str
    assert "NaN" not in json_str


def test_df_to_columnar_epoch_ms():
    """Verify index is epoch MILLISECONDS — not seconds, not nanoseconds.

    Any real date in 2010-2026 produces epoch-ms > 1_000_000_000_000.
    Epoch-seconds for the same dates are < 1_000_000_000_000.
    Epoch-nanoseconds for the same dates are > 1_000_000_000_000_000.
    The two bounds below pin the value to the millisecond range exactly.
    """
    df = pd.DataFrame(
        {"close": [1900.5]},
        index=pd.DatetimeIndex(["2026-01-01"], tz="UTC"),
    )
    result = df_to_columnar(df)

    assert result.index[0] > 1_000_000_000_000, (
        f"Expected epoch-ms (> 1e12), got {result.index[0]} — "
        f"check df_to_columnar divisor: must be 1_000_000 (not 1_000_000_000)"
    )
    assert (
        result.index[0] < 2_000_000_000_000
    ), f"Value {result.index[0]} looks like nanoseconds, not milliseconds"
    assert result.columns["close"] == [1900.5]
