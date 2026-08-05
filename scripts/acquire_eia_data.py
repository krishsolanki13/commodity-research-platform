#!/usr/bin/env python
"""Download and process EIA petroleum inventory data.

Downloads weekly crude oil inventory data from the EIA API v2 for WTI
and Brent-proxy series. Computes inventory surprise vs 5-year seasonal
average and saves to data/processed/eia/{asset}.parquet.

API key persistence — create config/local.yaml (gitignored) once:
    eia:
      api_key: your_key_here

Then just run:
    python scripts/acquire_eia_data.py

Alternatively set the environment variable for the current session:
    $env:EIA_API_KEY = "your_key_here"     (PowerShell)
    export EIA_API_KEY=your_key_here       (Unix/macOS)

Get a free API key at: https://www.eia.gov/opendata/

SSL note: uses an unverified SSL context to work around Windows
corporate certificate chain issues with HTTPS endpoints.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

if TYPE_CHECKING:
    import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

PROCESSED_DIR = Path("data/processed/eia")

EIA_SERIES_MAP = {
    "wti": "WCRSTUS1",
    "brent": "WCSSTUS1",
}

EIA_BASE_URL = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"


def _ssl_context() -> ssl.SSLContext:
    """Return an unverified SSL context.

    Required on Windows where the Python SSL store may not include the
    issuer certificates for api.eia.gov. Acceptable for a research
    platform consuming public government data.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def get_api_key() -> str | None:
    """Get EIA API key from config/local.yaml or environment variable.

    Priority:
      1. config/local.yaml  (eia.api_key)  — recommended for persistence
      2. EIA_API_KEY environment variable  — for CI / one-off use
    """
    # Check config/local.yaml first (gitignored, persistent)
    local_config = Path("config/local.yaml")
    if local_config.exists():
        try:
            import yaml  # noqa: PLC0415

            cfg = yaml.safe_load(local_config.read_text(encoding="utf-8"))
            if isinstance(cfg, dict):
                key = cfg.get("eia", {}).get("api_key") or cfg.get("eia_api_key")
                if key:
                    logger.info("EIA API key loaded from config/local.yaml")
                    return str(key)
        except Exception:  # noqa: BLE001
            pass

    # Fall back to environment variable
    key = os.environ.get("EIA_API_KEY")
    if key:
        logger.info("EIA API key loaded from EIA_API_KEY environment variable")
        return key

    return None


def fetch_eia_series(series_id: str, api_key: str) -> pd.DataFrame:
    """Fetch weekly inventory data for a single EIA series."""
    import pandas as pd  # noqa: PLC0415

    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[]": "value",
        "facets[series][]": series_id,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": "5000",
        "offset": "0",
    }

    url = EIA_BASE_URL + "?" + urlencode(params)
    logger.info("Fetching EIA series %s ...", series_id)

    try:
        with urlopen(url, context=_ssl_context(), timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        logger.error("Failed to fetch EIA series %s: %s", series_id, exc)
        return pd.DataFrame()

    records = data.get("response", {}).get("data", [])
    if not records:
        logger.warning("No data returned for series %s", series_id)
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["period"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.tz_localize("UTC")
    df["inventory"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.sort_values("date").drop_duplicates("date")
    df = df.set_index("date")[["inventory"]]

    logger.info(
        "Series %s: %d records (%s to %s)",
        series_id,
        len(df),
        df.index[0].date(),
        df.index[-1].date(),
    )
    return df


def compute_surprise(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inventory change, 5-year seasonal average, and surprise z-score."""
    df = df.copy()

    df["inventory_change"] = df["inventory"].diff()
    df["week_of_year"] = df.index.isocalendar().week.astype(int)

    seasonal_means = df.groupby("week_of_year")["inventory_change"].transform(
        lambda x: x.expanding(min_periods=3).mean().shift(1)
    )

    df["seasonal_avg"] = seasonal_means
    df["surprise"] = df["inventory_change"] - df["seasonal_avg"]

    surprise_mean = df["surprise"].rolling(window=52, min_periods=10).mean()
    surprise_std = df["surprise"].rolling(window=52, min_periods=10).std(ddof=1)
    df["surprise_zscore"] = (df["surprise"] - surprise_mean) / surprise_std.replace(
        0, float("nan")
    )
    df["surprise_zscore"] = df["surprise_zscore"].fillna(0.0)

    return df[["inventory", "inventory_change", "surprise", "surprise_zscore"]]


def main() -> int:
    api_key = get_api_key()
    if not api_key:
        logger.error(
            "EIA API key not found.\n"
            "Recommended: add to config/local.yaml (created once, gitignored):\n"
            "  eia:\n"
            "    api_key: your_key_here\n"
            "Alternative: set EIA_API_KEY environment variable for this session.\n"
            "Get a free key at: https://www.eia.gov/opendata/"
        )
        return 1

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for asset, series_id in EIA_SERIES_MAP.items():
        logger.info("Processing EIA data for '%s' (series: %s)", asset, series_id)
        df = fetch_eia_series(series_id, api_key)
        if df.empty:
            logger.warning("Skipping '%s' — no data returned", asset)
            continue

        df = compute_surprise(df)
        out_path = PROCESSED_DIR / f"{asset}.parquet"
        df.to_parquet(out_path, engine="pyarrow")
        logger.info("Saved %s: %d records", out_path, len(df))

    logger.info("EIA data acquisition complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
