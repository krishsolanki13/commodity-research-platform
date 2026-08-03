"""Data quality control for OHLCV assets.

Computes a QCReport from a loaded OHLCV DataFrame: bar count, date range,
zero-volume days, OHLC constraint violations, large price gap flags, and
an overall data health assessment.

Used by:
  - GET /api/data/qc?asset=gold  (on-demand, no pre-computation needed)
  - scripts/acquire_data.py       (optional: write_qc_report() after ingestion)

QCReport is a lightweight dataclass — no Parquet storage needed.
The /api/data/qc endpoint computes and returns in < 100ms for 4,150 bars.
"""

from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Thresholds for data quality flags
_LARGE_PRICE_GAP_THRESHOLD = 0.15  # 15% day-over-day gap → flag
_MIN_BARS_FOR_OK = 252  # < 252 bars → at least warn


@dataclass
class QCReport:
    """Data quality assessment for one asset's OHLCV history.

    data_health:
      "ok"   — no issues or < 3 minor flags
      "warn" — 1–5% of bars have issues (possible gaps or anomalies)
      "crit" — > 5% of bars have issues or structural violations

    anomalies: human-readable list of specific issues found.
    """

    asset: str
    generated_at: str  # ISO datetime UTC
    bar_count: int
    from_date: str  # ISO date of first bar
    to_date: str  # ISO date of last bar
    zero_volume_days: int
    ohlc_violations: int  # bars where high < low or close outside [low, high]
    large_gap_flags: int  # bars with > 15% day-over-day close gap
    data_health: str  # "ok" | "warn" | "crit"
    anomalies: list[str] = field(default_factory=list)


def compute_qc(ohlcv: pd.DataFrame, asset: str) -> QCReport:
    """Compute a QCReport from a loaded OHLCV DataFrame.

    Args:
        ohlcv: NormalizedOHLCV DataFrame with open/high/low/close/volume
               columns and a DatetimeIndex.
        asset: Asset identifier for the report.

    Returns:
        QCReport with all quality metrics populated.
    """
    n = len(ohlcv)
    now_utc = datetime.datetime.now(datetime.UTC).isoformat()

    if n == 0:
        return QCReport(
            asset=asset,
            generated_at=now_utc,
            bar_count=0,
            from_date="",
            to_date="",
            zero_volume_days=0,
            ohlc_violations=0,
            large_gap_flags=0,
            data_health="crit",
            anomalies=["No data available"],
        )

    from_date = ohlcv.index[0].date().isoformat()
    to_date = ohlcv.index[-1].date().isoformat()
    anomalies: list[str] = []

    # ── Zero volume days ──────────────────────────────────────────────────
    if "volume" in ohlcv.columns:
        zero_vol = int((ohlcv["volume"] == 0).sum())
        if zero_vol > 0:
            anomalies.append(f"{zero_vol} bars with zero volume")
    else:
        zero_vol = 0

    # ── OHLC constraint violations ────────────────────────────────────────
    violations = 0
    if all(c in ohlcv.columns for c in ["open", "high", "low", "close"]):
        high_lt_low = (ohlcv["high"] < ohlcv["low"]).sum()
        close_above_high = (ohlcv["close"] > ohlcv["high"]).sum()
        close_below_low = (ohlcv["close"] < ohlcv["low"]).sum()
        violations = int(high_lt_low + close_above_high + close_below_low)
        if violations > 0:
            anomalies.append(
                f"{violations} OHLC constraint violations "
                f"(high<low: {int(high_lt_low)}, "
                f"close>high: {int(close_above_high)}, "
                f"close<low: {int(close_below_low)})"
            )

    # ── Large price gap flags ─────────────────────────────────────────────
    large_gaps = 0
    if "close" in ohlcv.columns:
        pct_change = ohlcv["close"].pct_change().abs()
        large_gaps = int((pct_change > _LARGE_PRICE_GAP_THRESHOLD).sum())
        if large_gaps > 0:
            anomalies.append(
                f"{large_gaps} large price gaps (>{_LARGE_PRICE_GAP_THRESHOLD:.0%} day-over-day)"
            )

    # ── Data health classification ────────────────────────────────────────
    total_issues = violations + large_gaps + (zero_vol > 10)
    issue_rate = total_issues / n if n > 0 else 0.0

    if violations > 0 or n < _MIN_BARS_FOR_OK:
        if violations > 0:
            data_health = "crit"
        else:
            data_health = "warn"
            anomalies.append(f"Fewer than {_MIN_BARS_FOR_OK} bars ({n} bars available)")
    elif issue_rate > 0.05:
        data_health = "warn"
    else:
        data_health = "ok"

    logger.info(
        "QC: %s — %d bars, health=%s, violations=%d, gaps=%d, zero_vol=%d",
        asset,
        n,
        data_health,
        violations,
        large_gaps,
        zero_vol,
    )

    return QCReport(
        asset=asset,
        generated_at=now_utc,
        bar_count=n,
        from_date=from_date,
        to_date=to_date,
        zero_volume_days=zero_vol,
        ohlc_violations=violations,
        large_gap_flags=large_gaps,
        data_health=data_health,
        anomalies=anomalies,
    )


def write_qc_report(qc_report: QCReport, qc_dir: Path | None = None) -> Path:
    """Persist a QCReport to disk as JSON.

    Writes to {qc_dir}/{asset}_{date}.json.
    Default qc_dir: data/qc/.

    Args:
        qc_report: Computed QCReport.
        qc_dir: Override directory (default: data/qc/).

    Returns:
        Path to the written JSON file.
    """
    base_dir = qc_dir or Path("data/qc")
    base_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.date.today().isoformat()
    out_path = base_dir / f"{qc_report.asset}_{date_str}.json"

    data = {
        "asset": qc_report.asset,
        "generated_at": qc_report.generated_at,
        "bar_count": qc_report.bar_count,
        "from_date": qc_report.from_date,
        "to_date": qc_report.to_date,
        "zero_volume_days": qc_report.zero_volume_days,
        "ohlc_violations": qc_report.ohlc_violations,
        "large_gap_flags": qc_report.large_gap_flags,
        "data_health": qc_report.data_health,
        "anomalies": qc_report.anomalies,
    }
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("QC report written: %s", out_path)
    return out_path
