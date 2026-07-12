"""Largest-Triangle-Three-Buckets (LTTB) downsampler for OHLCV chart payloads.

This is a display transform — it lives in api/, not src/. It has no research
significance; it exists solely to keep chart payloads under ~3,000 points.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def lttb_ohlcv(df: pd.DataFrame, threshold: int = 3_000) -> pd.DataFrame:
    """Downsample an OHLCV DataFrame to at most `threshold` rows using LTTB.

    Uses the close column as the representative value for triangle area
    computation. Always preserves the first and last rows.

    Reference: Steinarsson, S. (2013). Downsampling Time Series for Visual
    Representation. MSc thesis, University of Iceland.

    Args:
        df: DataFrame with DatetimeIndex and at minimum a "close" column.
        threshold: Maximum number of rows in the output.

    Returns:
        DataFrame with exactly `threshold` rows (or the original if n <= threshold).
    """
    n = len(df)
    if n <= threshold:
        return df

    close = df["close"].to_numpy(dtype=float)

    # Bucket size for the (threshold-2) interior selections
    every = (n - 2) / (threshold - 2)

    selected: list[int] = [0]
    a = 0  # index of the last selected point

    for i in range(threshold - 2):
        # Next-bucket range: used to compute the average "C" point
        nxt_start = int((i + 1) * every) + 1
        nxt_end = min(int((i + 2) * every) + 1, n)

        if nxt_end > nxt_start:
            # Average x is the midpoint of the bucket's index range
            avg_x = (nxt_start + nxt_end - 1) / 2.0
            avg_y = float(close[nxt_start:nxt_end].mean())
        else:
            avg_x = float(n - 1)
            avg_y = float(close[n - 1])

        # Current bucket range
        cur_start = int(i * every) + 1
        cur_end = min(int((i + 1) * every) + 1, n - 1)

        if cur_start >= cur_end:
            # Degenerate bucket — take the only available index
            best = min(cur_start, n - 2)
            selected.append(best)
            a = best
            continue

        # Vectorized triangle area computation for all candidates in bucket
        j = np.arange(cur_start, cur_end, dtype=float)
        areas = (
            np.abs(
                (float(a) - avg_x) * (close[cur_start:cur_end] - close[a])
                - (float(a) - j) * (avg_y - close[a])
            )
            * 0.5
        )

        best = cur_start + int(np.argmax(areas))
        selected.append(best)
        a = best

    selected.append(n - 1)
    return df.iloc[selected].copy()
