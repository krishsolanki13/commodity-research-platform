from __future__ import annotations

import math
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field, field_serializer

# ── Shared primitives ─────────────────────────────────────────────────────────


class ColumnarSeries(BaseModel):
    """Time series in columnar format.

    index: epoch milliseconds UTC.
    columns: column_name → list of float | None (None encodes NaN).
    This is the wire format for ALL time series (OHLCV, equity, signals, etc.).
    3–5× smaller than row-of-objects format.
    """

    index: list[int] = Field(description="Epoch milliseconds UTC")
    columns: dict[str, list[float | None]] = Field(
        description="Column values. None encodes NaN (JSON null)."
    )


class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: str | None = None
    field_errors: dict[str, str] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class DeleteResponse(BaseModel):
    deleted: bool
    run_id: str


# ── Assets ────────────────────────────────────────────────────────────────────


class AssetMetadata(BaseModel):
    """assets.yaml contract for one asset."""

    name: str
    display_name: str
    ticker_continuous: str
    contract_root: str
    exchange_suffix: str
    exchange: str
    currency: str
    unit: str
    contract_multiplier: int
    tick_size: float
    tick_value: float


class AssetSummaryResponse(BaseModel):
    name: str
    last_price: float | None
    last_date: str | None  # ISO date
    return_1d: float | None  # fraction, not percent
    return_1w: float | None
    return_1m: float | None
    realized_vol_63d: float | None  # annualized fraction
    avg_volume_20d: float | None
    bar_count: int
    data_health: Literal["ok", "warn", "crit", "missing"]
    flagged_anomalies: int


class UniverseResponse(BaseModel):
    assets: list[AssetMetadata]
    summaries: dict[str, AssetSummaryResponse]  # keyed by asset name
    total_runs: int
    last_ingestion: str | None  # ISO datetime UTC


class OhlcvResponse(BaseModel):
    asset: str
    from_date: str
    to_date: str
    bars: int  # actual bars returned (after downsampling if applied)
    bars_original: int  # bars before downsampling
    downsampled: bool
    data: ColumnarSeries  # columns: open, high, low, close, volume


# ── Features ──────────────────────────────────────────────────────────────────


class ParamSpec(BaseModel):
    name: str
    kind: Literal["int", "float", "bool", "str"]
    default: Any
    min: float | None = None
    max: float | None = None
    description: str
    unit: str | None = None  # e.g. "bars", "%", "USD"


class IndicatorMeta(BaseModel):
    name: str  # e.g. "ema"
    display_name: str  # e.g. "Exponential Moving Average"
    category: Literal["trend", "momentum", "oscillator", "volatility", "volume"]
    params_schema: list[ParamSpec]
    column_name_template: str  # e.g. "ema_{period}"


class IndicatorCatalogResponse(BaseModel):
    indicators: list[IndicatorMeta]


class FeatureSpecRequest(BaseModel):
    name: str  # indicator name, e.g. "ema"
    params: dict[str, Any]  # e.g. {"period": 50}


class FeatureComputeRequest(BaseModel):
    asset: str
    from_date: str | None = None
    to_date: str | None = None
    specs: list[FeatureSpecRequest]


class FeatureSpecResponse(BaseModel):
    indicator_name: str
    params: dict[str, Any]
    column_name: str  # e.g. "ema_50"
    asset: str
    computed_at: str  # ISO datetime UTC


class FeatureComputeResponse(BaseModel):
    asset: str
    from_date: str
    to_date: str
    bars: int
    specs: list[FeatureSpecResponse]
    columns: ColumnarSeries  # columns keyed by column_name (e.g. "ema_50", "ema_200")


# ── Signals ───────────────────────────────────────────────────────────────────


class StrategyMeta(BaseModel):
    name: str  # e.g. "ema_crossover"
    display_name: str  # e.g. "EMA Crossover"
    description: str
    params_schema: list[ParamSpec]
    default_params: dict[str, Any]  # from strategies.yaml


class StrategyCatalogResponse(BaseModel):
    strategies: list[StrategyMeta]


class SignalGenerateRequest(BaseModel):
    asset: str
    strategy: str
    params: dict[str, Any]
    from_date: str | None = None
    to_date: str | None = None


class SignalGenerateResponse(BaseModel):
    asset: str
    strategy: str
    params: dict[str, Any]
    bars: int
    raw_signal: ColumnarSeries  # columns: {"raw": [...]}
    position_signal: (
        ColumnarSeries  # columns: {"position": [...]}  values in {-1, 0, 1}
    )


class DecayEntry(BaseModel):
    horizon: int  # bars forward: 1, 2, 5, 10, 20
    ic: float | None  # None if insufficient data


class SignalEvaluationData(BaseModel):
    """IC Gate data. ic_band follows ADR-007 five-way classification:
    |IC| >= 0.05 and IC > 0  → "strong"
    |IC| >= 0.05 and IC < 0  → "inverse_meaningful"
    0.02 <= IC < 0.05        → "weak_positive"
    -0.05 < IC <= -0.02      → "weak_inverse"
    |IC| < 0.02              → "noise"
    """

    ic: float | None
    icir: float | None
    turnover: float | None
    decay: list[DecayEntry]  # 5 entries at horizons 1, 2, 5, 10, 20
    evaluation_window: int  # bars used for IC calculation
    computed_at: str  # ISO datetime UTC
    ic_band: Literal[
        "strong", "weak_positive", "weak_inverse", "inverse_meaningful", "noise"
    ]


class SignalEvaluateRequest(BaseModel):
    asset: str
    strategy: str
    params: dict[str, Any]
    from_date: str | None = None
    to_date: str | None = None


class SignalEvaluateResponse(BaseModel):
    asset: str
    strategy: str
    params: dict[str, Any]
    evaluation: SignalEvaluationData


# ── Backtests + task lifecycle ─────────────────────────────────────────────────


class BacktestLaunchRequest(BaseModel):
    asset: str
    strategy: str
    params: dict[str, Any]
    from_date: str | None = None
    to_date: str | None = None
    initial_capital: float = 1_000_000.0
    commission_per_trade: float = 5.0
    slippage_ticks: int = 1
    sizing_method: Literal["fixed_notional", "volatility_scaled"] = "fixed_notional"
    notional_usd: float = 100_000.0
    target_annual_vol: float | None = None
    signal_threshold: float = 0.0
    signal_evaluation: SignalEvaluationData | None = None
    # None = IC gate override. The API accepts this without error — gate
    # enforcement is client-side doctrine only (ADR-007).


class TaskLaunchResponse(BaseModel):
    run_id: str
    status: Literal["queued"] = "queued"


class TaskStatusResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running", "complete", "failed"]
    error: str | None = None
    executed_at: str | None = None  # ISO datetime UTC; set on complete or failed


# ── Runs ──────────────────────────────────────────────────────────────────────


class ProvenanceInfo(BaseModel):
    git_sha: str  # 8-char SHA, e.g. "dcde2a36"
    dirty_flag: bool
    package_versions: dict[str, str]  # e.g. {"pandas": "2.3.3", "numpy": "2.5.0"}


class RunListItem(BaseModel):
    run_id: str
    asset: str
    strategy: str
    status: Literal["complete", "failed", "running", "queued"]
    from_date: str
    to_date: str
    sharpe: float | None
    max_drawdown: float | None
    total_return: float | None
    cagr: float | None
    win_rate: float | None
    n_trades: int | None
    ic: float | None
    ic_band: str | None
    executed_at: str


class RunListResponse(BaseModel):
    runs: list[RunListItem]
    total: int
    page: int
    page_size: int


class RunDetailResponse(BaseModel):
    run_id: str
    asset: str
    strategy: str
    status: Literal["complete", "failed"]
    from_date: str
    to_date: str
    params: dict[str, Any]  # complete params.json content
    metrics: dict[str, float | None]  # all 16 scalar metrics from metrics.json
    provenance: ProvenanceInfo
    signal_evaluation: SignalEvaluationData | None  # None = override was used


class SeriesResponse(BaseModel):
    run_id: str
    name: Literal["equity_curve", "pnl", "positions"]
    data: ColumnarSeries  # single "value" column


class TradeRecord(BaseModel):
    direction: Literal["long", "short"]
    entry_date: str  # ISO date
    exit_date: str  # ISO date
    entry_price: float
    exit_price: float
    duration_bars: int
    gross_pnl: float
    cost: float
    net_pnl: float
    return_pct: float
    force_closed: bool


class TradeStats(BaseModel):
    n_trades: int
    avg_duration_bars: float | None
    avg_win: float | None
    avg_loss: float | None
    largest_win: float | None
    largest_loss: float | None


class TradesPageResponse(BaseModel):
    run_id: str
    trades: list[TradeRecord]
    page: int
    page_size: int
    total: int
    stats: TradeStats


class CompareRunSummary(BaseModel):
    run_id: str
    asset: str
    strategy: str
    params: dict[str, Any]
    metrics: dict[str, float | None]
    from_date: str
    to_date: str


class AlignedRunSeries(BaseModel):
    run_id: str
    equity_normalized: ColumnarSeries  # % of initial capital
    rolling_sharpe_63: ColumnarSeries  # aligned to intersection window


class CompareRequest(BaseModel):
    ids: list[str] = Field(min_length=2, max_length=8)


class CompareResponse(BaseModel):
    runs: list[CompareRunSummary]
    aligned_series: list[AlignedRunSeries]
    intersection_from: str | None  # None if no common dates
    intersection_to: str | None
    intersection_bars: int | None
    mixed_assets: bool  # True if comparing across different assets


# ── Portfolio ─────────────────────────────────────────────────────────────────


class PortfolioLaunchRequest(BaseModel):
    strategy: str
    params: dict[str, Any]
    assets: list[str] | None = None  # None = all 6 assets
    from_date: str | None = None
    to_date: str | None = None
    initial_capital_per_asset: float = 1_000_000.0
    commission_per_trade: float = 5.0
    slippage_ticks: int = 1
    sizing_method: Literal["fixed_notional", "volatility_scaled"] = "fixed_notional"
    notional_usd: float = 100_000.0
    signal_threshold: float = 0.0


class PortfolioAssetHeadline(BaseModel):
    asset: str
    sharpe: float | None
    max_drawdown: float | None
    total_return: float | None
    cagr: float | None
    n_trades: int | None
    absolute_pnl: float | None  # USD P&L (from absolute_pnl_by_asset)


class PortfolioSummaryResponse(BaseModel):
    run_id: str
    strategy: str
    assets: list[str]
    skipped_assets: list[str]
    portfolio_date_range_from: str
    portfolio_date_range_to: str
    portfolio_date_range_bars: int
    initial_capital_per_asset: float
    initial_capital_total: float
    portfolio_metrics: dict[str, float | None]
    # Keys: total_return, cagr, sharpe, sortino, calmar, max_drawdown,
    #       portfolio_vol, n_trading_days
    absolute_pnl_by_asset: dict[str, float]  # always-stable USD attribution
    asset_contributions: dict[str, float] | None  # None when |total_pnl/capital| < 1%
    per_asset_headlines: list[PortfolioAssetHeadline]


class RiskReportResponse(BaseModel):
    run_id: str
    portfolio_var_95: float | None  # positive USD loss magnitude; None if < 20 obs
    portfolio_var_99: float | None
    portfolio_var_95_pct: float | None
    portfolio_var_99_pct: float | None
    portfolio_es_95: float | None  # Expected Shortfall; always >= VaR at same level
    portfolio_es_99: float | None
    asset_var_95: dict[str, float | None]
    asset_var_99: dict[str, float | None]
    avg_gross_notional_by_asset: dict[str, float]
    avg_net_notional_by_asset: dict[str, float]
    total_avg_gross_notional: float
    total_avg_net_notional: float
    portfolio_diversification_benefit: float | None
    # sum(asset_var_99) / portfolio_var_99; None if portfolio_var_99 is None
    lookback_days: int
    methodology: str = "historical_simulation"
    # Note: VaR is backward-looking (realized P&L history, not current positions × scenarios)

    # EM4 — Kupiec VaR backtesting
    n_backtesting_days: int = 0
    exceptions_95: int = 0
    exceptions_99: int = 0
    exception_rate_95: float | None = None
    exception_rate_99: float | None = None
    kupiec_lr_99: float | None = None
    kupiec_pvalue_99: float | None = None

    # EM4 — Contribution to strategy volatility
    asset_contribution_to_vol: dict[str, float] = Field(default_factory=dict)
    asset_contribution_to_vol_pct: dict[str, float] = Field(default_factory=dict)


class RollingCorrSeries(BaseModel):
    """Rolling correlation between one asset pair."""

    asset_a: str
    asset_b: str
    data: ColumnarSeries  # single "value" column, values in [-1, 1]


class CorrelationReportResponse(BaseModel):
    run_id: str
    # Pairwise Pearson correlation of STRATEGY daily returns (not price returns)
    correlation_matrix: dict[str, dict[str, float]]
    # API symmetrizes TD-M17-A before returning: both [a][b] and [b][a] present
    rolling_correlations_63: dict[str, dict[str, RollingCorrSeries]]
    rolling_correlations_126: dict[str, dict[str, RollingCorrSeries]]
    realized_vol_by_asset: dict[str, float]
    # STRATEGY P&L VOLATILITY (2–8%/yr for EMA 50/200), NOT commodity price vol
    # (15–60%/yr). Must NOT be relabeled as "asset_volatility".
    portfolio_realized_vol: float
    avg_pairwise_correlation: float
    most_correlated_pair: tuple[str, str, float]
    least_correlated_pair: tuple[str, str, float]
    framing_note: str = (
        "Correlations are between strategy daily returns (PnL / initial_capital), "
        "not commodity price returns. Strategies with frequent flat periods show lower "
        "static correlation than underlying prices. Use rolling charts to see structural relationships."
    )


class PortfolioEquityResponse(BaseModel):
    run_id: str
    portfolio_equity: (
        ColumnarSeries  # columns: {"value": [...]}; starts at initial_capital_total
    )
    portfolio_pnl: ColumnarSeries  # daily PnL series


class PortfolioRunListItem(BaseModel):
    """Summary of a single portfolio run for the run list endpoint.

    Read from portfolio_summary.json on disk. Provides enough data
    for the frontend portfolioHistory store and run selector UI.
    """

    run_id: str
    strategy_name: str
    assets: list[str]
    skipped_assets: list[str] = []
    total_return: float | None = None
    sharpe: float | None = None
    max_drawdown: float | None = None
    portfolio_vol: float | None = None
    initial_capital_total: float | None = None
    portfolio_date_range: list[str] = []


class PortfolioRunListResponse(BaseModel):
    """Response for GET /api/portfolio/runs."""

    runs: list[PortfolioRunListItem]
    total: int


class PortfolioAssetsResponse(BaseModel):
    run_id: str
    assets: list[str]
    asset_metrics: dict[str, dict[str, float | None]]
    asset_run_ids: dict[str, str | None] = {}


# ── System ────────────────────────────────────────────────────────────────────


class DataFlag(BaseModel):
    date: str
    violation_type: str
    detail: str


class AssetDataStatus(BaseModel):
    name: str
    bar_count: int
    from_date: str | None
    to_date: str | None
    last_ingested: str | None  # ISO datetime UTC
    flagged_anomalies: int
    data_health: Literal["ok", "warn", "crit", "missing"]
    flags: list[DataFlag]


class DataStatusResponse(BaseModel):
    assets: list[AssetDataStatus]
    total_flags: int


class IngestRequest(BaseModel):
    asset: str | None = None  # None = ingest all 6 assets


class IngestResponse(BaseModel):
    status: Literal["ok", "partial", "failed"]
    assets_ingested: list[str]
    assets_failed: list[str]
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    backend_tests: int


class ConfigResponse(BaseModel):
    config: dict[str, Any]  # config.yaml content, sanitized
    assets: dict[str, Any]  # assets.yaml content
    strategies: dict[str, Any]  # strategies.yaml content


def _nan_to_none(v: float | None) -> float | None:
    """Shared NaN→None serializer. JSON does not support NaN."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


class CurvePointResponse(BaseModel):
    ticker: str
    close: float
    days_to_delivery: int
    data_date: str


class FuturesCurveResponse(BaseModel):
    asset: str
    observation_date: str
    regime: str
    front_price: float | None
    back_price: float | None
    n_contracts: int
    annualized_slope_pct: float | None
    roll_yield_annualized: float | None
    basis: float | None
    basis_pct: float | None
    points: list[CurvePointResponse]

    @field_serializer(
        "annualized_slope_pct",
        "roll_yield_annualized",
        "basis",
        "basis_pct",
        "front_price",
        "back_price",
    )
    def _nan_float(self, v: float | None) -> float | None:
        return _nan_to_none(v)


class CurveAvailableResponse(BaseModel):
    assets: list[str]


class TermStructureSnapshotSummary(BaseModel):
    observation_date: str
    regime: str
    annualized_slope_pct: float | None
    roll_yield_annualized: float | None
    basis: float | None
    front_price: float | None
    n_contracts: int

    @field_serializer(
        "annualized_slope_pct", "roll_yield_annualized", "basis", "front_price"
    )
    def _nan_float(self, v: float | None) -> float | None:
        return _nan_to_none(v)


class CurveHistoryResponse(BaseModel):
    asset: str
    from_date: str
    to_date: str
    n_snapshots: int
    snapshots: list[TermStructureSnapshotSummary]


# ── Serialization utilities ────────────────────────────────────────────────────


def series_to_columnar(series: pd.Series, col_name: str = "value") -> ColumnarSeries:
    """Convert a pandas Series with DatetimeIndex to ColumnarSeries (epoch ms).

    NaN values become None (serialized as JSON null).
    """
    index_ms = (series.index.as_unit("ns").view("int64") // 1_000_000).tolist()
    values: list[float | None] = [
        None if pd.isna(v) else float(v) for v in series.values
    ]
    return ColumnarSeries(index=index_ms, columns={col_name: values})


def df_to_columnar(df: pd.DataFrame) -> ColumnarSeries:
    """Convert a pandas DataFrame with DatetimeIndex to ColumnarSeries (epoch ms).

    NaN values become None (serialized as JSON null).
    """
    index_ms = (df.index.as_unit("ns").view("int64") // 1_000_000).tolist()
    columns: dict[str, list[float | None]] = {
        col: [None if pd.isna(v) else float(v) for v in df[col].values]
        for col in df.columns
    }
    return ColumnarSeries(index=index_ms, columns=columns)
