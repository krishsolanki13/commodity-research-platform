"""Data acquisition script: download continuous futures data from Yahoo Finance.

Saves raw OHLCV CSVs to data/raw/continuous/{asset}.csv.
These files are gitignored and must be acquired by each developer
before running the dashboard.

Usage (from project root, with .venv active):
    python scripts/acquire_data.py

Data is NOT back-adjusted (auto_adjust=False). This is deliberate:
- The platform uses raw continuous series for signal research (ADR-001)
- Roll gaps are expected and documented as accepted data limitations
- Back-adjustment would alter price levels and affect level-dependent indicators

The OHLCVNormalizer already handles Yahoo Finance's title-case column names
and drops Adj Close per the platform's raw-close convention.

See ADR-001 for the continuous vs. contract-level data architecture decision.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as a script
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yfinance as yf  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Asset → Yahoo Finance continuous ticker mapping
# Source: ADR-001 and Architecture Section 8.1
ASSETS: dict[str, dict] = {
    "gold": {"ticker": "GC=F", "exchange": "COMEX", "unit": "USD/troy oz"},
    "silver": {"ticker": "SI=F", "exchange": "COMEX", "unit": "USD/troy oz"},
    "copper": {"ticker": "HG=F", "exchange": "COMEX", "unit": "USD/lb"},
    "wti": {"ticker": "CL=F", "exchange": "NYMEX", "unit": "USD/barrel"},
    "brent": {"ticker": "BZ=F", "exchange": "ICE", "unit": "USD/barrel"},
    "natural_gas": {"ticker": "NG=F", "exchange": "NYMEX", "unit": "USD/MMBtu"},
}

DEFAULT_START = "2010-01-01"
RAW_DATA_DIR = project_root / "data" / "raw" / "continuous"


def acquire_all(
    start: str = DEFAULT_START,
    assets: dict[str, dict] | None = None,
    overwrite: bool = True,
) -> None:
    """Download continuous futures data for all configured assets.

    Args:
        start: Start date for download in YYYY-MM-DD format.
        assets: Asset configuration dict. Defaults to all 6 Phase 1 assets.
        overwrite: If True, overwrite existing CSV files. If False, skip
            assets that already have a CSV file.
    """
    if assets is None:
        assets = ASSETS

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, str] = {}

    for asset_name, meta in assets.items():
        ticker = meta["ticker"]
        output_path = RAW_DATA_DIR / f"{asset_name}.csv"

        if not overwrite and output_path.exists():
            logger.info(
                "Skipping %s (%s) — file already exists at %s",
                asset_name,
                ticker,
                output_path,
            )
            results[asset_name] = "skipped (exists)"
            continue

        logger.info(
            "Downloading %s (%s · %s · %s) from %s...",
            asset_name,
            ticker,
            meta["exchange"],
            meta["unit"],
            start,
        )

        try:
            df = yf.download(
                ticker,
                start=start,
                auto_adjust=False,  # Keep raw Close; do not back-adjust (ADR-001)
                progress=False,
            )

            if df.empty:
                logger.warning(
                    "No data returned for %s (%s). Ticker may be unavailable.",
                    asset_name,
                    ticker,
                )
                results[asset_name] = "FAILED — no data returned"
                continue

            # yfinance returns MultiIndex columns for single-ticker downloads
            # when auto_adjust=False; flatten if necessary
            if hasattr(df.columns, "levels"):
                df.columns = df.columns.droplevel(1)

            df.to_csv(output_path)
            logger.info(
                "  %s: %d bars (%s to %s) → %s",
                asset_name,
                len(df),
                df.index.min().strftime("%Y-%m-%d"),
                df.index.max().strftime("%Y-%m-%d"),
                output_path,
            )
            results[asset_name] = f"OK ({len(df)} bars)"

        except Exception as exc:  # noqa: BLE001
            logger.error("  %s (%s): FAILED — %s", asset_name, ticker, exc)
            results[asset_name] = f"FAILED — {exc}"

    # Summary
    print("\n" + "=" * 60)
    print("Data Acquisition Summary")
    print("=" * 60)
    for asset_name, status in results.items():
        print(f"  {asset_name:<14}  {status}")
    print("=" * 60)

    successful = sum(1 for s in results.values() if s.startswith("OK"))
    print(f"\n{successful}/{len(assets)} assets acquired successfully.")

    if successful > 0:
        print(f"\nData written to: {RAW_DATA_DIR}")
        print("Run the dashboard with:")
        print("  Windows:  .\\launch_dashboard.ps1")
        print("  Mac/Linux: ./launch_dashboard.sh")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Acquire continuous futures data from Yahoo Finance."
    )
    parser.add_argument(
        "--start",
        default=DEFAULT_START,
        help=f"Start date (YYYY-MM-DD). Default: {DEFAULT_START}",
    )
    parser.add_argument(
        "--assets",
        nargs="+",
        choices=list(ASSETS.keys()),
        default=None,
        help="Specific assets to download. Default: all 6.",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Skip assets that already have a CSV file.",
    )
    args = parser.parse_args()

    selected = {k: ASSETS[k] for k in args.assets} if args.assets else None

    acquire_all(
        start=args.start,
        assets=selected,
        overwrite=not args.no_overwrite,
    )
