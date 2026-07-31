"""Shared type definitions and dataclasses for the Commodity Systematic
Research Platform.

This module is the single source of truth for all inter-layer contracts.
No layer defines shared types outside this file.
See Architecture Section 7 (Layer Contracts) for the full specification.
"""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
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
    git_sha: str = "unknown"
    """Short git commit SHA at time of backtest run (first 8 chars).
    'unknown' if not running in a git repository."""

    dirty_flag: bool = False
    """True if working tree had uncommitted changes at run time."""

    package_versions: dict[str, str] = field(default_factory=dict)
    """Key package versions at run time: pandas, numpy, yfinance, etc."""


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


@dataclass
class MultiAssetBacktestResult:
    """Result of running VectorizedBacktester across multiple assets.

    Each asset is run independently with the same strategy, parameters, and
    position sizer. Results are aggregated into a portfolio equity curve and
    portfolio PnL series.

    Produced by MultiAssetRunner.run().
    Consumed by Module 15 (PortfolioPerformanceEngine).

    Capital model: each asset receives the same initial capital independently
    (config default: $1,000,000). The portfolio equity curve is the sum of
    per-asset equity curves. No active capital allocation is applied.

    See ADR-010 (Multi-Asset Research Scope and Phasing).
    """

    strategy_name: str
    signal_name: str
    parameters: dict[str, Any]
    assets: list[str]
    skipped_assets: list[str]
    run_id: str
    executed_at: datetime.datetime
    asset_results: dict[str, BacktestResult]
    portfolio_equity_curve: pd.Series
    portfolio_pnl_series: pd.Series

    @property
    def n_assets(self) -> int:
        """Number of successfully backtested assets."""
        return len(self.assets)

    @property
    def assets_with_trades(self) -> list[str]:
        """Subset of assets that executed at least one trade."""
        return [a for a, r in self.asset_results.items() if len(r.trades) > 0]

    @property
    def total_trades(self) -> int:
        """Sum of all trades across all assets."""
        return sum(len(r.trades) for r in self.asset_results.values())


@dataclass
class PortfolioPerformanceReport:
    """Portfolio-level performance analytics from MultiAssetBacktestResult.

    Produced by PortfolioPerformanceEngine.compute(multi_result).
    Consumed by Module 19 (Dashboard Page 7).

    Contains portfolio-level scalars, per-asset attribution fractions,
    and individual PerformanceReport for each successful asset.

    Note: portfolio_date_range explicitly surfaces the inner-join alignment
    from MultiAssetRunner._aggregate_portfolio(). The portfolio equity curve
    only spans dates where ALL assets have data — this field makes that
    visible to the researcher.

    See ADR-010 (Multi-Asset Research Scope and Phasing).
    """

    strategy_name: str
    run_id: str
    assets: list[str]
    skipped_assets: list[str]
    initial_capital_per_asset: float
    initial_capital_total: float
    portfolio_date_range: tuple[datetime.date, datetime.date]
    portfolio_metrics: dict[str, float]
    asset_contributions: dict[str, float]
    absolute_pnl_by_asset: dict[str, float]
    """Per-asset total P&L in absolute USD over the portfolio date range.
    Always meaningful regardless of total portfolio P&L magnitude.
    Use this when |total_portfolio_pnl / initial_capital_total| < 1% —
    asset_contributions becomes numerically unstable near-zero denominators.
    Sign convention: positive = profit, negative = loss.
    Computed over the inner-join date range (same as portfolio_pnl_series index)."""
    per_asset_reports: dict[str, PerformanceReport]

    asset_run_ids: dict[str, str | None] = field(default_factory=dict)
    """Maps asset identifier → individual BacktestResult.run_id.
    Populated by PortfolioPerformanceEngine.compute() from
    multi_result.asset_results. Used by the frontend to link portfolio
    asset rows to individual /runs/{id} detail pages.
    Empty dict for portfolio runs created before this fix was shipped."""

    @property
    def n_assets(self) -> int:
        """Number of successfully backtested assets."""
        return len(self.assets)

    @property
    def portfolio_sharpe(self) -> float:
        """Portfolio Sharpe ratio. NaN if insufficient data."""
        return self.portfolio_metrics.get("sharpe", float("nan"))

    @property
    def portfolio_max_drawdown(self) -> float:
        """Portfolio max drawdown (negative fraction)."""
        return self.portfolio_metrics.get("max_drawdown", float("nan"))

    @property
    def portfolio_total_return(self) -> float:
        """Portfolio total return as decimal fraction."""
        return self.portfolio_metrics.get("total_return", float("nan"))

    @property
    def portfolio_cagr(self) -> float:
        """Portfolio annualized compound return."""
        return self.portfolio_metrics.get("cagr", float("nan"))


@dataclass
class RiskReport:
    """Portfolio risk analytics from MultiAssetBacktestResult.

    Produced by RiskEngine.compute(multi_result).
    Consumed by Module 19 (Dashboard Page 7).

    All VaR and ES values are expressed as positive USD loss magnitudes.
    A portfolio_var_99 of 5000.0 means: with 99% confidence, the daily
    portfolio loss will not exceed $5,000.

    Methodology: historical simulation over the lookback_days window.
    No distributional assumption — correct for fat-tailed commodity returns.

    VaR and ES are computed on the inner-join PnL series from
    MultiAssetBacktestResult (the common date range across all assets).

    See Architecture Section 5 (Layer 6) and ADR-003.
    """

    strategy_name: str
    """Strategy identifier matching strategies.yaml."""

    run_id: str
    """Portfolio run ID from MultiAssetBacktestResult.run_id."""

    assets: list[str]
    """Successfully backtested assets included in this risk report."""

    computation_date: datetime.date
    """Date this report was computed (typically today)."""

    lookback_days: int
    """Number of trading days used for VaR/ES historical simulation."""

    initial_capital_total: float
    """Total portfolio initial capital (sum across all assets, USD)."""

    # ── Portfolio-level Value at Risk ─────────────────────────────────────

    portfolio_var_95: float
    """Historical VaR at 95% confidence (positive USD loss magnitude).
    Interpretation: on 95% of days, portfolio loss will not exceed this amount.
    Computed from portfolio_pnl_series over lookback_days."""

    portfolio_var_99: float
    """Historical VaR at 99% confidence (positive USD loss magnitude).
    Always >= portfolio_var_95. NaN if insufficient lookback data."""

    portfolio_var_95_pct: float
    """portfolio_var_95 / initial_capital_total. Fraction of total capital."""

    portfolio_var_99_pct: float
    """portfolio_var_99 / initial_capital_total. Fraction of total capital."""

    # ── Portfolio-level Expected Shortfall ───────────────────────────────

    portfolio_es_95: float
    """Expected Shortfall (CVaR) at 95% confidence (positive USD).
    Mean of portfolio daily losses exceeding portfolio_var_95.
    Always >= portfolio_var_95. Coherent risk measure."""

    portfolio_es_99: float
    """Expected Shortfall (CVaR) at 99% confidence (positive USD).
    Mean of portfolio daily losses exceeding portfolio_var_99.
    Always >= portfolio_var_99 and >= portfolio_es_95."""

    # ── Per-asset Value at Risk ───────────────────────────────────────────

    asset_var_95: dict[str, float]
    """Per-asset historical VaR at 95% confidence (positive USD).
    Computed from each asset's individual pnl_series over lookback_days.
    Does not account for cross-asset diversification effects."""

    asset_var_99: dict[str, float]
    """Per-asset historical VaR at 99% confidence (positive USD)."""

    # ── Notional Exposure ─────────────────────────────────────────────────

    avg_gross_notional_by_asset: dict[str, float]
    """Mean |position| in USD over active trading days (positions != 0).
    Represents typical active exposure per asset. Zero if never in a trade."""

    avg_net_notional_by_asset: dict[str, float]
    """Mean signed position in USD over active trading days.
    Positive = net long bias. Negative = net short bias."""

    total_avg_gross_notional: float
    """Sum of avg_gross_notional_by_asset across all assets."""

    total_avg_net_notional: float
    """Sum of avg_net_notional_by_asset across all assets (signed)."""

    # ── Kupiec VaR Backtesting (EM4) ─────────────────────────────────────────

    n_backtesting_days: int = 0
    """Number of trading days used in Kupiec backtesting.
    Equal to len(portfolio_pnl_series.dropna().iloc[-lookback_days:]).
    0 if backtesting could not be computed."""

    exceptions_95: int = 0
    """Days where portfolio loss exceeded VaR95 (count).
    Expected at 5% confidence: ~5% of n_backtesting_days."""

    exceptions_99: int = 0
    """Days where portfolio loss exceeded VaR99 (count).
    Expected at 1% confidence: ~1% of n_backtesting_days."""

    exception_rate_95: float = 0.0
    """Observed exception rate at 95% confidence: exceptions_95 / n_backtesting_days.
    Should be approximately 0.05 for a well-calibrated VaR95."""

    exception_rate_99: float = 0.0
    """Observed exception rate at 99% confidence: exceptions_99 / n_backtesting_days.
    Should be approximately 0.01 for a well-calibrated VaR99."""

    kupiec_lr_99: float = 0.0
    """Kupiec (1995) likelihood ratio statistic at 99% confidence.
    Approximately chi-squared(1) under H0 that VaR is correctly calibrated.
    NaN if exception rate is 0 or 1 (boundary — LR undefined)."""

    kupiec_pvalue_99: float = 1.0
    """P-value for Kupiec test at 99% confidence.
    Low p-value (<0.05) rejects null that VaR99 is correctly calibrated.
    p-value = 1 - chi2_cdf(kupiec_lr_99, df=1).
    NaN if LR is undefined."""

    # ── Contribution to Risk (EM4) ───────────────────────────────────────────

    asset_contribution_to_vol: dict[str, float] = field(default_factory=dict)
    """Per-asset contribution to portfolio annualized strategy volatility.
    CTR_i = w_i x (Sw)_i / sqrt(w^T S w)
    where w = notional weights from avg_gross_notional_by_asset,
    S = covariance matrix from CorrelationReport.
    Values are in vol units (annualized). Sum ~ portfolio_vol.
    Empty dict if CorrelationReport not provided to RiskEngine.compute()."""

    asset_contribution_to_vol_pct: dict[str, float] = field(default_factory=dict)
    """Per-asset contribution as fraction of total portfolio strategy vol.
    CTR_pct_i = CTR_i / portfolio_vol. Values sum to approximately 1.0.
    Empty dict if CorrelationReport not provided to RiskEngine.compute()."""

    @property
    def portfolio_diversification_benefit(self) -> float:
        """Ratio of sum of per-asset VaR99 to portfolio VaR99.

        Values > 1.0 indicate diversification is reducing portfolio risk
        below what a naive sum of individual risks would suggest.
        NaN if portfolio_var_99 is zero or NaN.
        """
        if math.isnan(self.portfolio_var_99) or self.portfolio_var_99 == 0.0:
            return float("nan")
        sum_asset_var = sum(v for v in self.asset_var_99.values() if not math.isnan(v))
        return sum_asset_var / self.portfolio_var_99


@dataclass
class CorrelationReport:
    """Cross-asset correlation and volatility analytics.

    Produced by CorrelationEngine.compute(multi_result).
    Consumed by Module 19 (Dashboard Page 7) for correlation heatmap,
    rolling correlation charts, and per-asset realized volatility display.

    All correlations are Pearson correlations of daily return series
    (pnl_series / initial_capital_per_asset) over the specified window.

    Rolling correlations use the inner-join date range from
    MultiAssetBacktestResult (same as portfolio equity curve).

    See Architecture Section 5 (Layer 7).
    """

    strategy_name: str
    """Strategy identifier matching strategies.yaml."""

    run_id: str
    """Portfolio run ID from MultiAssetBacktestResult.run_id."""

    assets: list[str]
    """Assets included in this correlation report."""

    computation_date: datetime.date
    """Date this report was computed."""

    # ── Static correlation matrix ─────────────────────────────────────────

    correlation_matrix: dict[str, dict[str, float]]
    """Full pairwise Pearson correlation matrix of daily returns.

    Nested dict: correlation_matrix[asset_a][asset_b] → float.
    Diagonal entries are always 1.0.
    Symmetric: correlation_matrix[a][b] == correlation_matrix[b][a].
    Computed over the full available return history (inner-join range).
    NaN for any pair where one asset has insufficient data."""

    # ── Rolling correlations ──────────────────────────────────────────────

    rolling_correlations_63: dict[str, dict[str, pd.Series]]
    """Rolling 63-day (≈3-month) Pearson correlations.

    rolling_correlations_63[asset_a][asset_b] → pd.Series of daily
    rolling correlation values. Same date index as portfolio equity curve.
    NaN at start until 63 observations are available."""

    rolling_correlations_126: dict[str, dict[str, pd.Series]]
    """Rolling 126-day (≈6-month) Pearson correlations.

    rolling_correlations_126[asset_a][asset_b] → pd.Series. NaN at
    start until 126 observations are available."""

    # ── Per-asset realized volatility ─────────────────────────────────────

    realized_vol_by_asset: dict[str, float]
    """Annualized realized volatility per asset.

    Computed as std(daily_returns) * sqrt(252) over the full
    inner-join date range. This is the realized vol over the
    strategy's trading period, not a lookback-window estimate.
    NaN if fewer than 20 return observations available."""

    portfolio_realized_vol: float
    """Annualized realized volatility of the portfolio daily returns
    (from portfolio_pnl_series / initial_capital_total). Comparable to
    PortfolioPerformanceReport.portfolio_metrics['portfolio_vol'] —
    should match within floating-point tolerance."""

    # ── Derived analytics ──────────────────────────────────────────────────

    avg_pairwise_correlation: float
    """Mean of all off-diagonal correlation matrix entries.

    Positive: assets tend to move together (low diversification benefit).
    Near zero: low average pairwise correlation (high diversification).
    Negative: assets tend to move in opposite directions (rare for commodities).
    NaN if fewer than 2 assets."""

    most_correlated_pair: tuple[str, str, float]
    """The asset pair with the highest absolute static correlation.
    (asset_a, asset_b, correlation_value). asset_a < asset_b alphabetically."""

    least_correlated_pair: tuple[str, str, float]
    """The asset pair with the lowest absolute static correlation.
    (asset_a, asset_b, correlation_value). asset_a < asset_b alphabetically."""

    @property
    def n_assets(self) -> int:
        """Number of assets in the correlation matrix."""
        return len(self.assets)

    @property
    def n_pairs(self) -> int:
        """Number of unique off-diagonal pairs: n*(n-1)/2."""
        n = len(self.assets)
        return n * (n - 1) // 2

    def get_correlation(self, asset_a: str, asset_b: str) -> float:
        """Return the static correlation between two assets.

        Args:
            asset_a: First asset identifier.
            asset_b: Second asset identifier.

        Returns:
            Pearson correlation. 1.0 if asset_a == asset_b.
            NaN if either asset is not in the matrix.
        """
        if asset_a == asset_b:
            return 1.0
        try:
            return self.correlation_matrix[asset_a][asset_b]
        except KeyError:
            return float("nan")


@dataclass
class TrainTestSplit:
    """Date boundaries and bar counts for one walk-forward fold.

    Used by WalkForwardValidator to define train/test windows.
    embargo_bars bars between train_end and test_start prevent leakage
    from autocorrelated consecutive returns.
    """

    fold_idx: int
    train_start: datetime.date
    train_end: datetime.date
    test_start: datetime.date
    test_end: datetime.date
    n_train_bars: int
    n_test_bars: int
    embargo_bars: int


@dataclass
class WalkForwardFold:
    """Out-of-sample results for one walk-forward fold.

    Contains performance metrics for both the train window (in-sample)
    and the test window (out-of-sample). overfitting_ratio is the ratio
    of test Sharpe to train Sharpe — values near 1.0 suggest no overfit.
    """

    split: TrainTestSplit
    train_sharpe: float
    test_sharpe: float
    train_return: float
    test_return: float
    train_max_dd: float
    test_max_dd: float
    train_n_trades: int
    test_n_trades: int
    overfitting_ratio: float  # test_sharpe / train_sharpe; NaN if train_sharpe == 0


@dataclass
class ValidationReport:
    """Complete statistical validation report for a strategy/asset combination.

    Aggregates walk-forward fold results and statistical inference metrics.
    The Deflated Sharpe Ratio (DSR) is the headline result: it is the
    Probabilistic Sharpe Ratio adjusted for the number of trials that were
    run to find this strategy configuration (read from MLflow).

    References:
        Bailey, D.H. & López de Prado, M. (2012). The Sharpe Ratio
        Efficient Frontier. Journal of Risk, 15(2), 3-44.
    """

    validation_run_id: str
    asset: str
    strategy_name: str
    parameters: dict[str, object]
    n_splits: int
    embargo_bars: int
    computation_date: datetime.date

    # Walk-forward fold results
    folds: list[WalkForwardFold]
    insample_sharpe: float  # Sharpe on full training data (pre-split)
    outsample_sharpe: float  # Mean Sharpe across test folds
    insample_return: float  # Cumulative return on full training data
    outsample_return: float  # Mean return across test folds
    overfitting_ratio: float  # Mean of fold.overfitting_ratio values

    # Statistical inference (Bailey & López de Prado 2012)
    sharpe_se: float  # Standard error of observed in-sample Sharpe
    psr: float  # PSR vs SR₀ = 0: P[true SR > 0]
    n_trials: int  # Number of trials from MLflow (for DSR)
    sr_benchmark: float  # E[max SR | n_trials] — DSR benchmark
    dsr: float  # DSR = PSR[sr_benchmark]: P[true SR > E[max SR]]

    # Summary
    is_significant: bool  # DSR > 0.95 (adjustable threshold)
    dsr_threshold: float  # Threshold used (default 0.95)


@dataclass
class RegimeMetrics:
    """Performance metrics for a strategy conditioned on a single regime.

    All float fields are NaN when the regime has insufficient data
    (< 20 trading days). regime string matches TermStructureRegime str()
    value: 'contango' | 'backwardation' | 'flat'.
    """

    regime: str
    n_days: int = 0
    coverage: float = 0.0
    sharpe: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    n_trades: int = 0
    win_rate: float = 0.0


@dataclass
class RegimeAttributionReport:
    """Regime-conditional performance attribution for a single backtest run.

    regime_metrics: dict keyed by TermStructureRegime str() value
                    ('contango', 'backwardation', 'flat').
    regime_coverage: fraction of days per regime (values sum to ~1.0).
    dominant_regime: regime key with highest coverage.
    """

    run_id: str
    asset: str
    strategy_name: str
    n_contracts: int
    computation_date: datetime.date
    regime_metrics: dict[str, RegimeMetrics] = field(default_factory=dict)
    regime_coverage: dict[str, float] = field(default_factory=dict)
    dominant_regime: str = ""
    total_days_with_regime: int = 0
    total_days_in_run: int = 0


@dataclass
class SweepRunSummary:
    """Result of a single backtest within a parameter sweep.

    Each entry represents one (asset, strategy, parameters) combination
    that was run as part of a sweep. status='failed' entries have NaN
    metrics and a non-None error string.

    run_id follows the standard format: YYYYMMDD_HHMMSS_{strategy}_{asset}.
    sweep_id tags this run to its parent sweep for MLflow grouping.
    """

    sweep_id: str
    run_id: str
    parameters: dict[str, object]
    sharpe: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    n_trades: int = 0
    status: str = "complete"
    error: str | None = None


@dataclass
class SweepResult:
    """Complete result of a parameter sweep.

    Contains all SweepRunSummary entries from the sweep, ordered by
    the sequence in which they were executed (not sorted). Sorting is
    applied at the API layer.

    param_grid stores the original grid (not expanded combinations).
    n_combinations = product of len(v) for v in param_grid.values().
    """

    sweep_id: str
    asset: str
    strategy_name: str
    param_grid: dict[str, list]
    n_combinations: int
    n_complete: int
    n_failed: int
    computation_date: datetime.date
    runs: list[SweepRunSummary] = field(default_factory=list)
