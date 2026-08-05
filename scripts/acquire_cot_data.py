#!/usr/bin/env python
"""Download and process CFTC COT disaggregated futures data.

Downloads annual ZIP files from CFTC, parses net speculative positioning
for each platform asset, computes rolling percentile rank, and saves to
data/processed/cot/{asset}.parquet.

Usage:
    python scripts/acquire_cot_data.py
    python scripts/acquire_cot_data.py --years 2020 2021 2022 2023 2024 2025

The script downloads only years not already cached in data/raw/cot/.
Re-run at any time to refresh; will skip already-downloaded years.

SSL note: uses an unverified SSL context to work around Windows
corporate certificate chain issues with government HTTPS endpoints.
User-Agent note: CFTC server returns 403 without a browser User-Agent.
"""

from __future__ import annotations

import argparse
import logging
import ssl
import sys
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

RAW_DIR = Path("data/raw/cot")
PROCESSED_DIR = Path("data/processed/cot")
CFTC_URL = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"

CFTC_MARKET_TO_ASSET: dict[str, str] = {
    "GOLD - COMMODITY EXCHANGE INC.": "gold",
    "SILVER - COMMODITY EXCHANGE INC.": "silver",
    "COPPER- #1 - COMMODITY EXCHANGE INC.": "copper",
    "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE": "wti",
    "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE": "natural_gas",
}


def _ssl_context() -> ssl.SSLContext:
    """Return an unverified SSL context for Windows certificate chain issues."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def download_year(year: int) -> Path | None:
    """Download COT ZIP for a given year. Returns local path or None on failure."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"fut_disagg_{year}.zip"
    if out_path.exists():
        logger.info("Year %d: already downloaded at %s", year, out_path)
        return out_path

    url = CFTC_URL.format(year=year)
    logger.info("Downloading COT %d from %s ...", year, url)
    try:
        # CFTC server returns 403 without a browser User-Agent header
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, context=_ssl_context(), timeout=60) as response:
            data = response.read()
        out_path.write_bytes(data)
        logger.info("Year %d: downloaded (%d bytes)", year, len(data))
        return out_path
    except URLError as exc:
        logger.error("Year %d: download failed — %s", year, exc)
        return None


def parse_zip(zip_path: Path) -> pd.DataFrame:
    """Parse a CFTC COT ZIP file into a raw DataFrame."""
    import pandas as pd  # noqa: PLC0415

    with zipfile.ZipFile(zip_path) as zf:
        csv_files = [
            n for n in zf.namelist() if n.endswith(".csv") or n.endswith(".txt")
        ]
        if not csv_files:
            logger.warning("No data file in %s", zip_path)
            return pd.DataFrame()
        with zf.open(csv_files[0]) as f:
            df = pd.read_csv(f, low_memory=False)
        df.columns = [c.lower().strip() for c in df.columns]
        return df


def process_and_save(all_years_df: pd.DataFrame) -> None:
    """Process combined multi-year COT DataFrame and save per-asset Parquets."""
    import pandas as pd  # noqa: PLC0415

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Two date column formats exist across years:
    #   2010-2012: report_date_as_mm_dd_yyyy
    #   2013+:     report_date_as_yyyy-mm-dd
    # Combine both into a single 'date' column before processing.
    all_years_df = all_years_df.copy()
    col_mmddyyyy = next((c for c in all_years_df.columns if "mm_dd_yyyy" in c), None)
    col_yyyymmdd = next((c for c in all_years_df.columns if "yyyy-mm-dd" in c), None)

    all_years_df["date"] = pd.NaT
    if col_mmddyyyy:
        all_years_df["date"] = all_years_df["date"].fillna(
            pd.to_datetime(all_years_df[col_mmddyyyy], errors="coerce")
        )
    if col_yyyymmdd:
        all_years_df["date"] = all_years_df["date"].fillna(
            pd.to_datetime(all_years_df[col_yyyymmdd], errors="coerce")
        )

    market_col = next(
        (c for c in all_years_df.columns if "market" in c and "exchange" in c), None
    )
    long_col = next(
        (
            c
            for c in all_years_df.columns
            if "m_money" in c and "long" in c and "spread" not in c
        ),
        None,
    )
    short_col = next(
        (
            c
            for c in all_years_df.columns
            if "m_money" in c and "short" in c and "spread" not in c
        ),
        None,
    )

    if not all([market_col, long_col, short_col]):
        logger.error(
            "Could not identify required columns. Found: %s",
            list(all_years_df.columns[:20]),
        )
        return

    known_markets = set(CFTC_MARKET_TO_ASSET.keys())
    df = all_years_df[all_years_df[market_col].isin(known_markets)].copy()

    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.tz_localize("UTC")

    df["long_specs"] = pd.to_numeric(df[long_col], errors="coerce").fillna(0)
    df["short_specs"] = pd.to_numeric(df[short_col], errors="coerce").fillna(0)
    df["net_speculative"] = df["long_specs"] - df["short_specs"]
    df["asset"] = df[market_col].map(CFTC_MARKET_TO_ASSET)

    for asset, asset_df in df.groupby("asset"):
        asset_df = asset_df.sort_values("date").drop_duplicates("date")
        asset_df = asset_df.set_index("date")[
            ["net_speculative", "long_specs", "short_specs"]
        ]

        asset_df["percentile_rank"] = (
            asset_df["net_speculative"]
            .rolling(window=52, min_periods=10)
            .apply(
                lambda x: float(
                    (x.iloc[:-1] < x.iloc[-1]).sum() / max(len(x) - 1, 1) * 100
                ),
                raw=False,
            )
        )

        out_path = PROCESSED_DIR / f"{asset}.parquet"
        asset_df.to_parquet(out_path, engine="pyarrow")
        logger.info(
            "Saved %s: %d weekly records (%s to %s)",
            out_path,
            len(asset_df),
            asset_df.index[0].date(),
            asset_df.index[-1].date(),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Download CFTC COT data")
    current_year = __import__("datetime").date.today().year
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=list(range(2010, current_year + 1)),
        help="Years to download (default: 2010 to current year)",
    )
    args = parser.parse_args()

    import pandas as pd  # noqa: PLC0415

    all_dfs = []
    for year in args.years:
        zip_path = download_year(year)
        if zip_path is None:
            continue
        df = parse_zip(zip_path)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        logger.error("No data downloaded. Check internet connection and SSL.")
        return 1

    combined = pd.concat(all_dfs, ignore_index=True)
    logger.info("Combined: %d rows across %d years", len(combined), len(all_dfs))
    process_and_save(combined)
    logger.info("COT data acquisition complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
