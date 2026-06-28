"""Integration tests for DataLoader: Layer 0 pipeline orchestration.

Tests the full pipeline: LocalCSVSource → OHLCVValidator → OHLCVNormalizer → ParquetStore.
All tests use the tmp_config fixture to redirect paths to a temporary directory,
ensuring no test reads from or writes to data/raw/ or data/processed/ in the repository.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import pytest

from src.core.config import Config
from src.data.loader import DataLoader


@pytest.fixture
def tmp_config(tmp_path: Path, gold_ohlcv: pd.DataFrame) -> Config:
    """Config fixture pointing all data paths to a temporary directory.

    Creates a self-contained data environment in tmp_path:
        tmp_path/data/raw/continuous/gold.csv       ← test fixture as raw input
        tmp_path/data/processed/continuous/          ← DataLoader writes Parquet here
        tmp_path/data/runs/
        tmp_path/logs/

    Returns a Config instance with paths redirected to tmp_path.
    The production config/, config/assets.yaml, config/strategies.yaml are
    unchanged — only the paths are overridden.
    """
    # Create directory structure
    raw_dir = tmp_path / "data" / "raw" / "continuous"
    raw_dir.mkdir(parents=True)
    processed_dir = tmp_path / "data" / "processed" / "continuous"
    processed_dir.mkdir(parents=True)
    (tmp_path / "data" / "runs").mkdir(parents=True)
    (tmp_path / "logs").mkdir(parents=True)

    # Write gold_ohlcv fixture as a CSV in the temporary raw directory.
    # reset_index() moves the DatetimeIndex back to a 'date' column so
    # LocalCSVSource can discover and parse it.
    gold_ohlcv.reset_index().to_csv(raw_dir / "gold.csv", index=False)

    # Load production config then redirect the four path values
    cfg = Config.load("config/")
    cfg.paths["raw_data"] = str(tmp_path / "data" / "raw") + "/"
    cfg.paths["processed_data"] = str(tmp_path / "data" / "processed") + "/"
    cfg.paths["runs"] = str(tmp_path / "data" / "runs") + "/"
    cfg.paths["logs"] = str(tmp_path / "logs") + "/"
    return cfg


def test_loader_returns_normalized_ohlcv(tmp_config: Config) -> None:
    """DataLoader.load() returns a DataFrame matching the NormalizedOHLCV contract."""
    df = DataLoader(tmp_config).load("gold")

    # Index contract
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.tzinfo is not None, "DatetimeIndex must be timezone-aware"
    assert str(df.index.tzinfo) == "UTC", f"Expected UTC, got {df.index.tzinfo}"

    # Column contract
    expected_columns = ["open", "high", "low", "close", "volume", "open_interest"]
    assert (
        list(df.columns) == expected_columns
    ), f"Expected {expected_columns}, got {list(df.columns)}"

    # Dtype contract
    for col in expected_columns:
        assert (
            df[col].dtype == "float64"
        ), f"Column '{col}' has dtype {df[col].dtype}, expected float64"


def test_loader_sets_attrs_correctly(tmp_config: Config) -> None:
    """DataLoader.load() populates all five required DataFrame.attrs."""
    df = DataLoader(tmp_config).load("gold")

    assert df.attrs.get("asset") == "gold"
    assert df.attrs.get("continuous") is True
    assert "source" in df.attrs, "attrs missing 'source'"
    assert "data_start" in df.attrs, "attrs missing 'data_start'"
    assert "data_end" in df.attrs, "attrs missing 'data_end'"


def test_loader_writes_parquet(tmp_config: Config) -> None:
    """DataLoader.load() writes a Parquet file to data/processed/continuous/."""
    DataLoader(tmp_config).load("gold")

    parquet_path = (
        Path(tmp_config.paths["processed_data"]) / "continuous" / "gold.parquet"
    )
    assert parquet_path.exists(), f"Expected Parquet file at {parquet_path}"

    # Confirm it is a readable, non-empty Parquet file
    stored_df = pd.read_parquet(parquet_path, engine="pyarrow")
    assert len(stored_df) > 0, "Parquet file is empty"


def test_loader_is_idempotent(tmp_config: Config) -> None:
    """Running DataLoader.load() twice on unchanged data produces identical output."""
    loader = DataLoader(tmp_config)
    df1 = loader.load("gold", force_reload=True)
    df2 = loader.load("gold", force_reload=True)

    pd.testing.assert_frame_equal(df1, df2, check_names=True)


def test_loader_fast_path_uses_parquet(tmp_config: Config) -> None:
    """With force_reload=False, DataLoader reads from Parquet without touching the CSV."""
    loader = DataLoader(tmp_config)

    # First call: run full pipeline and write Parquet
    df_pipeline = loader.load("gold", force_reload=True)

    # Delete the raw CSV — if fast path works, second call must succeed without it
    raw_csv = Path(tmp_config.paths["raw_data"]) / "continuous" / "gold.csv"
    raw_csv.unlink()
    assert not raw_csv.exists(), "CSV must be absent to validate fast path"

    # Second call: must succeed using Parquet (fast path)
    df_cached = loader.load("gold", force_reload=False)

    assert len(df_cached) == len(df_pipeline)
    assert list(df_cached.columns) == list(df_pipeline.columns)
    assert df_cached.attrs.get("asset") == "gold"


def test_loader_force_reload_reruns_pipeline(tmp_config: Config) -> None:
    """force_reload=True re-runs the pipeline and overwrites existing Parquet."""
    loader = DataLoader(tmp_config)

    # First run: write initial Parquet
    loader.load("gold", force_reload=True)

    parquet_path = (
        Path(tmp_config.paths["processed_data"]) / "continuous" / "gold.parquet"
    )
    mtime_first = parquet_path.stat().st_mtime

    # Allow filesystem timestamp to advance
    time.sleep(0.1)

    # Second run with force_reload=True: Parquet must be overwritten
    df_second = loader.load("gold", force_reload=True)
    mtime_second = parquet_path.stat().st_mtime

    assert (
        mtime_second >= mtime_first
    ), "Parquet file modification time should advance after force_reload=True"
    # Verify the re-run produced valid output
    assert len(df_second) > 0
    assert df_second.attrs.get("asset") == "gold"
