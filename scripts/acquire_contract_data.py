"""Contract data acquisition: download individual futures contracts from Yahoo Finance.

Saves raw OHLCV CSVs to data/raw/contracts/{asset}/{canonical_ticker}.csv.
These files are gitignored and must be acquired before Module 9 curve construction.

Ticker convention:
    Canonical ticker (storage): GCZ24  — root + month_code + 2-digit-year
    yfinance API ticker:        GCZ24.CMX — canonical + exchange suffix
    The exchange suffix (.CMX for COMEX, .NYM for NYMEX) is an API concern only.
    Storage paths and ContractMetadata always use the canonical ticker.

Usage (from project root with .venv active):
    python scripts/acquire_contract_data.py
    python scripts/acquire_contract_data.py --assets gold wti --lookback_years 2
    python scripts/acquire_contract_data.py --assets gold --no-overwrite

See ADR-001 for the contract vs. continuous data architecture decision.
See Architecture Section 8.1 for ticker convention documentation.
"""

from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))  # noqa: E402

import yfinance as yf  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# CME month codes — standard across all futures exchanges
MONTH_CODES: dict[int, str] = {
    1: "F",
    2: "G",
    3: "H",
    4: "J",
    5: "K",
    6: "M",
    7: "N",
    8: "Q",
    9: "U",
    10: "V",
    11: "X",
    12: "Z",
}

# Asset configuration: CME root symbol and Yahoo Finance exchange suffix
# exchange_suffix: CMX = COMEX (metals), NYM = NYMEX (energy)
# Note: Brent (BZ) is ICE-listed but Yahoo Finance exposes the NYMEX-cleared
# version using .NYM — this is the correct suffix for yfinance API calls.
ASSET_CONFIGS: dict[str, dict[str, str]] = {
    "gold": {"root": "GC", "suffix": "CMX"},
    "silver": {"root": "SI", "suffix": "CMX"},
    "copper": {"root": "HG", "suffix": "CMX"},
    "wti": {"root": "CL", "suffix": "NYM"},
    "brent": {"root": "BZ", "suffix": "NYM"},
    "natural_gas": {"root": "NG", "suffix": "NYM"},
}

RAW_CONTRACTS_DIR = project_root / "data" / "raw" / "contracts"


def build_ticker(root: str, month: int, year: int) -> str:
    """Build the canonical contract ticker (no exchange suffix).

    This is the storage identifier used for CSV filenames, Parquet paths,
    and ContractMetadata.ticker. e.g. GCZ24.

    Args:
        root: CME root symbol (e.g. 'GC').
        month: Delivery month integer 1-12.
        year: Delivery year 4-digit integer.

    Returns:
        Canonical ticker string (e.g. 'GCZ24').
    """
    return f"{root}{MONTH_CODES[month]}{str(year)[-2:]}"


def build_yfinance_ticker(root: str, suffix: str, month: int, year: int) -> str:
    """Build the full yfinance API ticker including exchange suffix.

    This is passed to yf.Ticker() only during data acquisition.
    Never used for storage paths or ContractMetadata.ticker.
    e.g. GCZ24.CMX for Gold December 2024 on COMEX.

    Args:
        root: CME root symbol (e.g. 'GC').
        suffix: Exchange suffix (e.g. 'CMX' for COMEX, 'NYM' for NYMEX).
        month: Delivery month integer 1-12.
        year: Delivery year 4-digit integer.

    Returns:
        Full yfinance ticker string (e.g. 'GCZ24.CMX').
    """
    return f"{root}{MONTH_CODES[month]}{str(year)[-2:]}.{suffix}"


def generate_contract_tickers(
    root: str,
    lookback_years: int = 3,
) -> list[tuple[str, int, int]]:
    """Generate canonical contract tickers for the lookback window.

    Generates tickers for every calendar month from (today - lookback_years)
    to (today + 18 months forward). Not all tickers will have yfinance data —
    expired contracts are silently skipped during acquisition.

    Args:
        root: CME root symbol (e.g. 'GC').
        lookback_years: Years of history to cover. Default 3.

    Returns:
        List of (canonical_ticker, month, year) tuples sorted chronologically.
        e.g. [('GCZ22', 12, 2022), ('GCF23', 1, 2023), ...]
    """
    today = datetime.date.today()
    start = today.replace(year=today.year - lookback_years, day=1)

    # Forward window: 18 months ahead
    forward_months = 18
    end_year = today.year + (today.month + forward_months - 1) // 12
    end_month = (today.month + forward_months - 1) % 12 + 1

    tickers: list[tuple[str, int, int]] = []
    current = start
    while (current.year, current.month) <= (end_year, end_month):
        canonical = build_ticker(root, current.month, current.year)
        tickers.append((canonical, current.month, current.year))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return tickers


def acquire_asset_contracts(
    asset: str,
    lookback_years: int = 3,
    overwrite: bool = True,
    min_bars: int = 5,
) -> dict[str, str]:
    """Download all contracts for a single asset.

    Args:
        asset: Platform asset identifier (e.g. 'gold').
        lookback_years: Years of contract history to cover.
        overwrite: If False, skip tickers that already have a CSV file.
        min_bars: Minimum bars required to save a contract. Fewer = discarded.

    Returns:
        Dict mapping canonical_ticker -> status string.
    """
    root = ASSET_CONFIGS[asset]["root"]
    suffix = ASSET_CONFIGS[asset]["suffix"]

    asset_dir = RAW_CONTRACTS_DIR / asset
    asset_dir.mkdir(parents=True, exist_ok=True)

    tickers = generate_contract_tickers(root, lookback_years)
    results: dict[str, str] = {}

    logger.info(
        "Acquiring %d contract tickers for %s (root: %s, suffix: .%s, lookback: %d yr)",
        len(tickers),
        asset,
        root,
        suffix,
        lookback_years,
    )

    for canonical_ticker, month, year in tickers:
        yf_ticker = build_yfinance_ticker(root, suffix, month, year)
        csv_path = asset_dir / f"{canonical_ticker}.csv"

        if not overwrite and csv_path.exists():
            results[canonical_ticker] = "skipped (exists)"
            continue

        try:
            ticker_obj = yf.Ticker(yf_ticker)
            df = ticker_obj.history(period="max")

            if df.empty or len(df) < min_bars:
                results[canonical_ticker] = f"no data ({len(df)} bars)"
                continue

            # Drop futures-irrelevant columns returned by history()
            df = df.drop(
                columns=[c for c in df.columns if c in ("Dividends", "Stock Splits")],
                errors="ignore",
            )

            # Strip timezone before writing CSV — OHLCVNormalizer expects
            # timezone-naive date strings consistent with yf.download() output
            if hasattr(df.index, "tz") and df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df.index.name = "Date"

            df.to_csv(csv_path)
            results[canonical_ticker] = f"OK ({len(df)} bars)"
            logger.debug("  %s (yf: %s): %d bars", canonical_ticker, yf_ticker, len(df))

        except Exception as exc:  # noqa: BLE001
            results[canonical_ticker] = f"FAILED — {exc}"
            logger.warning(
                "  %s (yf: %s): failed — %s", canonical_ticker, yf_ticker, exc
            )

    ok = sum(1 for s in results.values() if s.startswith("OK"))
    logger.info(
        "%s: %d/%d contracts downloaded (%d skipped, %d no data)",
        asset,
        ok,
        len(tickers),
        sum(1 for s in results.values() if s.startswith("skipped")),
        sum(1 for s in results.values() if "no data" in s),
    )

    return results


def acquire_all(
    assets: list[str] | None = None,
    lookback_years: int = 3,
    overwrite: bool = True,
) -> None:
    """Download contract data for all configured assets.

    Args:
        assets: List of asset identifiers to acquire. Defaults to all 6.
        lookback_years: Years of contract history to cover per asset.
        overwrite: If False, skip assets/contracts that already have CSV files.
    """
    if assets is None:
        assets = list(ASSET_CONFIGS.keys())

    all_results: dict[str, dict[str, str]] = {}

    for asset in assets:
        if asset not in ASSET_CONFIGS:
            logger.warning(
                "Unknown asset '%s' — skipping. Valid: %s",
                asset,
                list(ASSET_CONFIGS.keys()),
            )
            continue
        all_results[asset] = acquire_asset_contracts(
            asset, lookback_years=lookback_years, overwrite=overwrite
        )

    print("\n" + "=" * 70)
    print("Contract Data Acquisition Summary")
    print("=" * 70)
    for asset, results in all_results.items():
        ok = sum(1 for s in results.values() if s.startswith("OK"))
        total = len(results)
        print(f"  {asset:<14}  {ok:>3}/{total} contracts downloaded")
    print("=" * 70)
    print(f"\nData written to: {RAW_CONTRACTS_DIR}")
    print("Next: run ContractDataLoader.load_curve() in the dashboard.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download individual futures contract data from Yahoo Finance."
    )
    parser.add_argument(
        "--assets",
        nargs="+",
        choices=list(ASSET_CONFIGS.keys()),
        default=None,
        help="Assets to download. Default: all 6.",
    )
    parser.add_argument(
        "--lookback_years",
        type=int,
        default=3,
        help="Years of contract history. Default: 3.",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Skip contracts that already have CSV files.",
    )
    args = parser.parse_args()

    acquire_all(
        assets=args.assets,
        lookback_years=args.lookback_years,
        overwrite=not args.no_overwrite,
    )
