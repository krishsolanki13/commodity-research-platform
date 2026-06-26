"""Shared type definitions and dataclasses for the Commodity Systematic
Research Platform.

This module is the single source of truth for all inter-layer contracts.
No layer defines shared types outside this file.
See Architecture Section 7 (Layer Contracts) for the full specification.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
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

# FeatureFrame is defined in src/research/feature_frame.py (Module 3).
# It is a Python class wrapping a pandas DataFrame, per ADR-006.
# After Module 3 is complete, add this import here:
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
