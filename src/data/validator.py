"""OHLCV data validator for Layer 0 data infrastructure.

Validates raw OHLCV DataFrames before normalization. Raises DataValidationError
for structural violations. Logs warnings for gaps and anomalies.
See Architecture Section 5 (Layer 0 Responsibilities).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import pandas as pd


class DataValidationError(Exception):
    """Raised when OHLCV data fails structural consistency validation.

    Structural violations that cause this exception:
        - high < low for any row
        - close > high for any row
        - close < low for any row
        - open <= 0 or close <= 0 for any row
        - duplicate date entries

    Non-structural anomalies (logged as WARNING, do not raise):
        - Missing trading day gaps
        - Zero volume rows
        - Daily returns exceeding 50% (possible roll gap)

    See Architecture Section 5 for the distinction between errors and warnings.
    """


@dataclass
class ValidationResult:
    """Complete validation outcome for an OHLCV DataFrame.

    Returned by OHLCVValidator.validate() when no structural errors exist.
    If structural errors exist, DataValidationError is raised instead.
    """

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    asset: str
    row_count: int
    date_range: tuple[date, date]


class OHLCVValidator:
    """Validates raw OHLCV DataFrames before normalization.

     Parameters:
        asset: Asset identifier for error and log messages.
        strict_ohlc: If True (default), OHLC consistency violations raise
            DataValidationError. If False, violations are logged as WARNING
            and data proceeds through the pipeline.

            Set strict_ohlc=False for Yahoo Finance continuous series which
            exhibit settlement price mixing artifacts per ADR-001: exchange
            settlement prices are volume-weighted averages of the closing range
            and can legally fall outside the intraday High/Low. Also handles
            the 2020-04-20 WTI negative price event (-$37.63) which is genuine
            historically significant market data, not a data error.

            Set strict_ohlc=True for Phase 2 contract-level data from premium
            vendors where OHLC consistency is guaranteed by the data provider.

    Raises DataValidationError if structural consistency violations are found.
    Logs WARNING for gaps and anomalies that do not block processing.
    Column names are normalised to lowercase internally — both 'Close' and
    'close' are accepted. See Architecture Section 5.
    """

    REQUIRED_COLUMNS: list[str] = ["open", "high", "low", "close"]
    EXTREME_RETURN_THRESHOLD: float = 0.50

    def __init__(self, asset: str, strict_ohlc: bool = True) -> None:
        """Initialise OHLCVValidator.

        Args:
            asset: Asset identifier used in log and error messages.
            strict_ohlc: If True, OHLC violations raise DataValidationError.
                If False, violations are warnings only. Default True.
        """
        self._asset = asset
        self._strict_ohlc = strict_ohlc
        self._logger = logging.getLogger(__name__)

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """Run all validation checks against the raw DataFrame.

        Normalises column names to lowercase before all checks.
        Structural violations raise DataValidationError with all violations
        joined in the message. Anomalies are logged and collected.

        Args:
            df: Raw OHLCV DataFrame from LocalCSVSource.fetch().

        Returns:
            ValidationResult with is_valid=True and any warnings collected.

        Raises:
            DataValidationError: If structural OHLC violations or duplicate
                date entries are found.
        """
        normalised = df.copy()
        normalised.columns = [c.lower().strip() for c in normalised.columns]

        errors: list[str] = []
        warnings: list[str] = []

        ohlc_issues = self._check_ohlc_consistency(normalised)
        dup_issues = self._check_duplicates(normalised)

        if self._strict_ohlc:
            # Strict mode: OHLC violations are hard errors.
            # Use for Phase 2 contract-level data from premium vendors.
            errors.extend(ohlc_issues)
        else:
            # Lenient mode: OHLC violations are warnings only.
            # Appropriate for Yahoo Finance continuous series which exhibit
            # settlement price mixing artifacts. See ADR-001.
            if ohlc_issues:
                self._logger.warning(
                    "OHLCVValidator [%s]: %d OHLC consistency violations detected "
                    "(strict_ohlc=False — treating as warnings per ADR-001). "
                    "Likely causes: settlement price mixing artifact or known market events "
                    "(e.g. WTI negative price 2020-04-20). First 3 violations: %s",
                    self._asset,
                    len(ohlc_issues),
                    ohlc_issues[:3],
                )
            warnings.extend(ohlc_issues)

        errors.extend(dup_issues)
        warnings.extend(self._check_gaps(normalised))
        warnings.extend(self._check_anomalies(normalised))

        for warning in warnings:
            self._logger.warning(warning)

        if errors:
            raise DataValidationError(
                f"OHLCV validation failed for '{self._asset}':\n" + "\n".join(errors)
            )

        date_range = self._extract_date_range(normalised)

        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            asset=self._asset,
            row_count=len(df),
            date_range=date_range,
        )

    def _check_ohlc_consistency(self, df: pd.DataFrame) -> list[str]:
        """Check OHLC relationships and price positivity using vectorized operations.

        Args:
            df: DataFrame with lowercase column names.

        Returns:
            List of error strings, one per violation.
        """
        errors: list[str] = []

        missing = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            errors.append(f"Missing required columns for {self._asset}: {missing}")
            return errors

        date_col = self._find_date_column(df)

        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")
        close = pd.to_numeric(df["close"], errors="coerce")
        open_ = pd.to_numeric(df["open"], errors="coerce")

        labels: pd.Series
        if date_col is not None:
            labels = df[date_col].astype(str)
        else:
            labels = pd.Series(range(len(df)), index=df.index).astype(str)

        def _collect(mask: pd.Series, msg_fn: Callable[..., str]) -> None:
            for label, *vals in zip(
                labels[mask],
                *[s[mask] for s in [high, low, close, open_]],
                strict=False,
            ):
                errors.append(msg_fn(label, *vals))

        # high < low
        mask = high < low
        for lbl, h, low_val in zip(labels[mask], high[mask], low[mask], strict=False):
            errors.append(
                f"Row {lbl}: high ({h:.4f}) < low ({low_val:.4f}) for {self._asset}"
            )

        # close > high
        mask = close > high
        for lbl, c, h in zip(labels[mask], close[mask], high[mask], strict=False):
            errors.append(
                f"Row {lbl}: close ({c:.4f}) > high ({h:.4f}) for {self._asset}"
            )

        # close < low
        mask = close < low
        for lbl, c, low_val in zip(labels[mask], close[mask], low[mask], strict=False):
            errors.append(
                f"Row {lbl}: close ({c:.4f}) < low ({low_val:.4f}) for {self._asset}"
            )

        # open <= 0
        mask = open_ <= 0
        for lbl, o in zip(labels[mask], open_[mask], strict=False):
            errors.append(f"Row {lbl}: open ({o:.4f}) <= 0 for {self._asset}")

        # close <= 0
        mask = close <= 0
        for lbl, c in zip(labels[mask], close[mask], strict=False):
            errors.append(f"Row {lbl}: close ({c:.4f}) <= 0 for {self._asset}")

        return errors

    def _check_duplicates(self, df: pd.DataFrame) -> list[str]:
        """Check for duplicate date entries.

        Args:
            df: DataFrame with lowercase column names.

        Returns:
            List of error strings for duplicate dates.
        """
        date_col = self._find_date_column(df)
        if date_col is None:
            return []

        duplicated_mask = df.duplicated(subset=[date_col], keep=False)
        duplicated_values = df.loc[duplicated_mask, date_col].unique()
        return [
            f"Duplicate date entry: {val} for {self._asset}"
            for val in duplicated_values
        ]

    def _check_gaps(self, df: pd.DataFrame) -> list[str]:
        """Check for missing business days.

        Generates expected business days between the first and last date
        in the DataFrame and identifies any missing days.

        Args:
            df: DataFrame with lowercase column names.

        Returns:
            List of warning strings, one per missing business day.
        """
        date_col = self._find_date_column(df)
        if date_col is None:
            return []

        try:
            dates = pd.to_datetime(df[date_col]).dt.date
            if len(dates) < 2:
                return []
            expected = set(pd.bdate_range(start=dates.min(), end=dates.max()).date)
            actual = set(dates)
            missing = sorted(expected - actual)
            return [f"Gap detected: {d} missing for {self._asset}" for d in missing]
        except Exception:  # noqa: BLE001
            return []

    def _check_anomalies(self, df: pd.DataFrame) -> list[str]:
        """Check for anomalous values: zero volume and extreme daily returns.

        Args:
            df: DataFrame with lowercase column names.

        Returns:
            List of warning strings for anomalous rows.
        """
        warnings: list[str] = []
        date_col = self._find_date_column(df)

        if "volume" in df.columns:
            vol = pd.to_numeric(df["volume"], errors="coerce")
            zero_mask = vol == 0
            labels = (
                df[date_col].astype(str)
                if date_col
                else pd.Series(range(len(df)), index=df.index).astype(str)
            )
            for lbl in labels[zero_mask]:
                warnings.append(f"Row {lbl}: volume is zero for {self._asset}")

        if "close" in df.columns and len(df) > 1:
            close = pd.to_numeric(df["close"], errors="coerce")
            returns = close.pct_change().abs()
            extreme_mask = returns > self.EXTREME_RETURN_THRESHOLD
            labels = (
                df[date_col].astype(str)
                if date_col
                else pd.Series(range(len(df)), index=df.index).astype(str)
            )
            for lbl, ret in zip(
                labels[extreme_mask], returns[extreme_mask], strict=False
            ):
                warnings.append(
                    f"Row {lbl}: daily return {ret * 100:.1f}% exceeds "
                    f"50% threshold for {self._asset} (possible roll gap)"
                )

        return warnings

    def _find_date_column(self, df: pd.DataFrame) -> str | None:
        """Return the first date-like column name (lowercase), or None."""
        for col in df.columns:
            if col in ("date", "datetime", "timestamp"):
                return str(col)
        return None

    def _extract_date_range(self, df: pd.DataFrame) -> tuple[date, date]:
        """Extract (first_date, last_date) tuple from the DataFrame."""
        date_col = self._find_date_column(df)
        if date_col is None:
            today = date.today()
            return (today, today)
        dates = pd.to_datetime(df[date_col]).dt.date
        return (dates.min(), dates.max())
