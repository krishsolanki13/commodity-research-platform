"""Shared type definitions and dataclasses for the Commodity Systematic
Research Platform.

This module is the single source of truth for all inter-layer contracts.
No layer defines shared types outside this file.
See Architecture Section 7 (Layer Contracts) for the full specification.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# NormalizedOHLCV
# ---------------------------------------------------------------------------

# NormalizedOHLCV is a pandas DataFrame with a defined schema.
# Represented as a type alias to avoid pandas subclassing issues.
#
# Schema (Architecture Section 7):
#   Index:   DatetimeIndex (UTC, daily frequency)
#   Columns: open (float64), high (float64), low (float64), close (float64),
#            volume (float64), open_interest (float64, nullable)
#   Attrs:   asset (str), source (str), continuous (bool),
#            data_start (date), data_end (date)
#   Invariants:
#     high >= low for all rows
#     high >= close for all rows
#     low <= close for all rows
#     open > 0, close > 0 for all rows
#     No duplicate index entries
NormalizedOHLCV = pd.DataFrame


# ---------------------------------------------------------------------------
# FeatureFrame — forward reference (Module 3)
# ---------------------------------------------------------------------------

# FeatureFrame: defined in src/research/feature_frame.py (implemented in Module 3).
# Per ADR-006: FeatureFrame is a Python class with .data, .feature_specs, .asset properties.
# IMPORTANT: do NOT import FeatureFrame here. Circular import exists:
#   feature_frame.py imports FeatureSpec from this module (types.py).
#   Importing FeatureFrame here would create a circular dependency.
# Upper layers import FeatureFrame directly:
#   from src.research.feature_frame import FeatureFrame


# ---------------------------------------------------------------------------
# RawSignal
# ---------------------------------------------------------------------------

# RawSignal is a pandas Series with the following contract:
#   Index:      DatetimeIndex matching the FeatureFrame
#   Values:     float64 (continuous; z-scored or normalised per signal type)
#   Name:       str, signal identifier (e.g., "ema_crossover_50_200")
#   Constraint: No look-ahead. Value at index t uses only information from
#               t and earlier. See ADR-002.
RawSignal = pd.Series


# ---------------------------------------------------------------------------
# PositionSignal
# ---------------------------------------------------------------------------

# PositionSignal is a pandas Series with the following contract:
#   Index:      DatetimeIndex matching the FeatureFrame
#   Values:     int8 or float64, restricted to {+1, 0, -1}
#               +1 = long, 0 = flat, -1 = short
#   Name:       str, position signal identifier
#   Constraint: Same no-look-ahead constraint as RawSignal. See ADR-002.
PositionSignal = pd.Series


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FeatureSpec:
    """Metadata record for a single computed indicator column.

    A list of FeatureSpec objects accompanies every FeatureFrame and is
    serialised with every backtest run artifact to ensure reproducibility.
    See ADR-006 for the FeatureFrame and FeatureSpec design.
    """

    indicator_name: str
    parameters: dict[str, Any]
    column_name: str
    asset: str
    computed_at: datetime.datetime


@dataclass
class SignalEvaluation:
    """Carries IC, ICIR, and decay results from Layer 2 to PerformanceReport.

    Computed by SignalEvaluator before backtesting. IC analysis is a
    precondition for deciding whether a backtest is warranted. See ADR-007.
    """

    signal_name: str
    asset: str
    ic: float
    icir: float
    ic_decay: dict[int, float]
    turnover: float
    ic_rolling_window: int
    evaluation_start: datetime.date
    evaluation_end: datetime.date


@dataclass
class TradeRecord:
    """Single trade record produced by the backtesting engine.

    Represents a continuous period during which the PositionSignal holds
    the same non-zero direction. See Architecture Section 11 for trade
    boundary detection rules and the force_closed field note below.

    Note: force_closed is the last field because it has a default value.
    Python dataclasses require all default fields to follow non-default
    fields. Do not reorder.
    """

    run_id: str
    asset: str
    direction: int
    entry_date: datetime.date
    exit_date: datetime.date
    entry_price: float
    exit_price: float
    size_notional: float
    size_contracts: float
    gross_pnl: float
    transaction_cost: float
    net_pnl: float
    duration_bars: int
    return_pct: float
    force_closed: bool = False


@dataclass
class BacktestMetadata:
    """Complete parameter snapshot for a single backtest run.

    Serialised to params.json in data/runs/{run_id}/ by RunManager.
    Enables full reproduction of any run from stored artifacts.
    See ADR-009 for the run tracking strategy.
    """

    run_id: str
    asset: str
    strategy_name: str
    signal_name: str
    parameters: dict[str, Any]
    data_source: str
    data_start: datetime.date
    data_end: datetime.date
    initial_capital_usd: float
    cost_model_params: dict[str, Any]
    sizing_model_params: dict[str, Any]
    executed_at: datetime.datetime
    git_commit_hash: str


@dataclass
class BacktestResult:
    """Complete output of a single backtest run.

    Produced by VectorizedBacktester and consumed by PerformanceEngine.
    signal_evaluation is attached by the orchestration layer after Layer 2
    evaluation; it is None if evaluation was skipped.
    See ADR-003 and ADR-007.
    """

    run_id: str
    asset: str
    trades: list[TradeRecord]
    equity_curve: pd.Series
    positions: pd.Series
    pnl_series: pd.Series
    metadata: BacktestMetadata
    signal_evaluation: SignalEvaluation | None = None


@dataclass
class PerformanceReport:
    """Structured performance report assembled by PerformanceEngine.

    Produced from BacktestResult by Layer 4. Consumed by the dashboard
    presentation layer (Layer 8). See Architecture Section 7 for expected
    dict keys.

    scalar_metrics keys:
        total_return, cagr, sharpe, sortino, calmar, max_drawdown,
        avg_drawdown, win_rate, profit_factor, avg_trade_duration_bars,
        turnover, avg_win, avg_loss, largest_win, largest_loss,
        initial_capital

    rolling_metrics keys:
        rolling_sharpe_63, rolling_sharpe_126, rolling_vol_63,
        rolling_drawdown

    signal_metrics keys (populated from signal_evaluation if present):
        ic, icir, signal_decay_1, signal_decay_2, signal_decay_5,
        signal_decay_10, signal_decay_20
    """

    run_id: str
    initial_capital_usd: float
    scalar_metrics: dict[str, float]
    rolling_metrics: dict[str, pd.Series]
    trade_statistics: dict[str, Any]
    signal_metrics: dict[str, float]


@dataclass
class ContractMetadata:
    """Identifies a single futures delivery contract.

    Produced by FuturesContractSource and ContractDataLoader.
    Consumed by Module 9 FuturesCurveLayer and Module 10 TermStructureAnalytics.
    """

    ticker: str
    """Full canonical ticker string. e.g. 'GCZ24' for Gold December 2024.
    This is the storage identifier — no exchange suffix."""

    asset: str
    """Platform asset identifier. e.g. 'gold'."""

    contract_root: str
    """CME root symbol. e.g. 'GC' for Gold."""

    contract_month: int
    """Delivery month as integer 1-12."""

    contract_year: int
    """Delivery year as 4-digit integer."""

    expiry_date: date | None = None
    """Last trading date for this contract. None if not yet known."""

    first_notice_date: date | None = None
    """First notice date (physical delivery assets). None for cash-settled."""

    n_bars: int = 0
    """Number of trading bars downloaded for this contract. 0 if not yet downloaded."""

    @property
    def month_code(self) -> str:
        """CME month code for this contract's delivery month."""
        _MONTH_CODES = {  # noqa: N806
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
        return _MONTH_CODES[self.contract_month]

    def __str__(self) -> str:
        return f"{self.ticker} ({self.asset} {self.contract_year}-{self.contract_month:02d})"


@dataclass
class CurvePoint:
    """A single point on the futures term structure.

    Represents one delivery contract's price contribution to the forward
    curve at a specific observation date.

    Produced by FuturesCurveBuilder._build_curve_point().
    Consumed as part of FuturesCurve by Module 10 (TermStructureAnalytics).
    """

    metadata: ContractMetadata
    """Contract identification — ticker, asset, delivery month/year."""

    close: float
    """Settlement price at or nearest to the observation_date."""

    volume: float
    """Trading volume at the data_date. May be NaN if not available."""

    observation_date: date
    """The anchor date for which this curve was constructed."""

    data_date: date
    """Actual date of the price used. May be before observation_date if
    no data exists on exactly the observation_date (e.g. market holiday)."""

    days_to_delivery: int
    """Approximate days from observation_date to start of delivery month.
    Computed as (date(year, month, 1) - observation_date).days.
    Negative values indicate an expired contract still in the dataset."""


@dataclass
class FuturesCurve:
    """A term structure snapshot — the full forward price curve at one date.

    Produced by FuturesCurveBuilder.build(). Points are sorted by
    delivery date, nearest first. Consumed by Module 10 (TermStructureAnalytics).
    """

    asset: str
    observation_date: date
    points: list[CurvePoint]

    @property
    def n_points(self) -> int:
        return len(self.points)

    @property
    def is_empty(self) -> bool:
        return len(self.points) == 0

    @property
    def front_price(self) -> float:
        return self.points[0].close if self.points else float("nan")

    @property
    def back_price(self) -> float:
        return self.points[-1].close if self.points else float("nan")

    @property
    def prices(self) -> list[float]:
        return [p.close for p in self.points]

    @property
    def tickers(self) -> list[str]:
        return [p.metadata.ticker for p in self.points]

    @property
    def is_contango(self) -> bool:
        """True if back_price > front_price. False for < 2 points."""
        if len(self.points) < 2:
            return False
        return self.points[-1].close > self.points[0].close

    @property
    def is_backwardation(self) -> bool:
        """True if front_price > back_price. False for < 2 points."""
        if len(self.points) < 2:
            return False
        return self.points[-1].close < self.points[0].close

    @property
    def slope(self) -> float:
        """Price per day slope. Positive = contango. NaN if < 2 points."""
        if len(self.points) < 2:
            return float("nan")
        front = self.points[0]
        back = self.points[-1]
        day_spread = back.days_to_delivery - front.days_to_delivery
        if day_spread == 0:
            return float("nan")
        return (back.close - front.close) / day_spread

    def spread(self, front_idx: int = 0, back_idx: int = -1) -> float:
        """Price spread: points[back_idx].close - points[front_idx].close."""
        try:
            return self.points[back_idx].close - self.points[front_idx].close
        except IndexError:
            return float("nan")


class TermStructureRegime(str, Enum):  # noqa: UP042
    """Classification of the futures term structure at a point in time.

    Produced by TermStructureAnalyzer.classify_regime().
    Stored in TermStructureSnapshot.regime.

    Inherits from str for JSON serialization compatibility — values can be
    written to metrics.json and compared with plain string literals.

    CONTANGO:      Annualized slope > +threshold. Deferred delivery priced
                   higher than near-term. Typical in commodity markets with
                   high storage costs relative to convenience yield.
    BACKWARDATION: Annualized slope < -threshold. Near-term delivery priced
                   higher than deferred. Occurs during supply squeezes or
                   periods of elevated physical demand.
    FLAT:          |Annualized slope| <= threshold. Negligible term structure
                   slope, or fewer than 2 contracts available.
    """

    CONTANGO = "contango"
    BACKWARDATION = "backwardation"
    FLAT = "flat"

    def __str__(self) -> str:
        return self.value


@dataclass
class TermStructureSnapshot:
    """Analytics computed for a single FuturesCurve at one observation date.

    Produced by TermStructureAnalyzer.analyze(). Contains all computed
    term structure metrics alongside the source FuturesCurve.

    Consumed by Module 13 (Dashboard Page 6) for visualization.
    In Phase 3, regime may be used as a conditioning variable for
    signal research and cross-asset analytics.

    Basis note: basis and basis_pct use the continuous front-month price
    (DataLoader output) as a proxy for spot. This is a pseudo-basis since
    the continuous series embeds roll artifacts per ADR-001. Documented as
    an accepted Phase 2 limitation.
    """

    asset: str
    """Platform asset identifier. e.g. 'gold'."""

    observation_date: date
    """Date at which this snapshot was computed."""

    regime: TermStructureRegime
    """Discrete regime classification: CONTANGO, BACKWARDATION, or FLAT."""

    front_price: float
    """Nearest delivery contract price. NaN if curve is empty."""

    back_price: float
    """Farthest delivery contract price in the snapshot. NaN if curve empty."""

    n_contracts: int
    """Number of contracts in the source curve."""

    raw_slope: float
    """Raw slope from FuturesCurve.slope — USD per day. Positive = contango.
    NaN if fewer than 2 contracts."""

    annualized_slope_pct: float
    """Annualized contango/backwardation rate as decimal fraction of front price.
    e.g. 0.025 = +2.5%/year contango. Negative in backwardation.
    Normalizes slope across assets with different price levels.
    NaN if fewer than 2 contracts or front_price is zero."""

    roll_yield_annualized: float
    """Annualized roll return for a long futures position (front-to-second roll).
    Positive in backwardation (tailwind for longs).
    Negative in contango (headwind for longs).
    Formula: (front - second) / second * (365 / days_between).
    NaN if fewer than 2 contracts."""

    basis: float
    """continuous_close - front_contract_price.
    Positive: continuous (spot proxy) above front futures.
    Negative: continuous below front futures.
    NaN if continuous_close was not provided or curve is empty."""

    basis_pct: float
    """basis / continuous_close. Expressed as decimal fraction.
    NaN if continuous_close was not provided, is zero, or curve is empty."""

    curve: FuturesCurve
    """Source FuturesCurve from which this snapshot was computed.
    Provides access to the underlying price data for consumers."""
