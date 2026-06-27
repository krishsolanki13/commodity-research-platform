"""Shared pytest fixtures for the Commodity Systematic Research Platform.

Provides a Config instance and a synthetic Gold OHLCV DataFrame for use
across all test modules from Module 2 onward.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.core.config import Config


@pytest.fixture(scope="session")
def config() -> Config:
    """Session-scoped Config instance loaded from config/.

    Reads config.yaml, assets.yaml, and strategies.yaml from the
    repository config/ directory. All tests requiring configuration
    access should use this fixture rather than calling Config.load()
    directly.
    """
    return Config.load("config/")


@pytest.fixture
def gold_ohlcv() -> pd.DataFrame:
    """Function-scoped synthetic Gold OHLCV DataFrame (252 bars).

    Reads from tests/fixtures/gold_sample.csv. The date column is parsed
    as a UTC DatetimeIndex. No dtype normalisation is applied — that is
    the responsibility of the Normalizer in Module 2.

    Returns:
        DataFrame with DatetimeIndex (UTC) and columns:
        open, high, low, close, volume (252 rows, seed=42).
    """
    df = pd.read_csv(
        "tests/fixtures/gold_sample.csv",
        parse_dates=["date"],
    )
    df = df.set_index("date")
    df.index = pd.DatetimeIndex(df.index).tz_localize("UTC")
    return df
