# Commodity Systematic Research Platform
## Architecture Reference Document

**Version:** 1.0
**Status:** Active
**Audience:** Developers, quantitative researchers, architecture reviewers

---

## Table of Contents

1. [Project Goals](#1-project-goals)
2. [Scope](#2-scope)
3. [Assumptions and Constraints](#3-assumptions-and-constraints)
4. [Architecture Overview](#4-architecture-overview)
5. [Layer Responsibilities](#5-layer-responsibilities)
6. [Data Flow](#6-data-flow)
7. [Layer Contracts](#7-layer-contracts)
8. [Data Sources](#8-data-sources)
9. [Storage Strategy](#9-storage-strategy)
10. [Signal Research Workflow](#10-signal-research-workflow)
11. [Backtesting Assumptions](#11-backtesting-assumptions)
12. [Position Sizing Model](#12-position-sizing-model)
13. [Dashboard Architecture](#13-dashboard-architecture)
14. [Configuration Reference](#14-configuration-reference)
15. [Phase Roadmap](#15-phase-roadmap)
16. [Known Limitations](#16-known-limitations)
17. [Future Evolution Path](#17-future-evolution-path)
18. [ADR Index](#18-adr-index)

---

## 1. Project Goals

The Commodity Systematic Research Platform is a modular quantitative research and strategy development environment designed to simulate the workflow of an institutional systematic trading team focused on commodity futures markets.

The platform provides a unified environment for:

- Historical commodity futures data ingestion, validation, and storage
- Feature engineering and technical indicator computation
- Signal generation, quality evaluation, and research
- Systematic strategy development and backtesting under realistic execution assumptions
- Performance measurement, attribution, and risk analysis
- Commodity-specific market structure analysis (term structure, contango, backwardation, roll yield, basis)
- Cross-asset correlation and regime analysis

**Intended users:** Quantitative researchers, systematic strategy developers, and commodity market analysts.

**Purpose:** Research and education. The platform is not designed for live trading or production execution.

**Design philosophy:** The platform prioritizes defensible architecture, clear separation of concerns, institutional workflow alignment, and extensibility over rapid implementation. Every design decision should be justifiable to a quantitative researcher, systematic trader, or trading technology engineer.

---

## 2. Scope

### 2.1 In Scope

**Phase 1 — Research MVP:**
- Continuous futures data ingestion from Yahoo Finance (CSV/Parquet)
- Data validation and normalization pipeline
- Feature engineering pipeline (SMA, EMA, RSI, RVGI, Momentum)
- FeatureFrame and FeatureSpec management
- Signal generation layer with RawSignal and PositionSignal separation
- Signal evaluation metrics: IC, ICIR, signal decay, turnover
- Vectorized single-asset backtesting engine
- Transaction cost and slippage modeling
- Fixed notional position sizing ($100,000 per signal)
- Performance metrics: Total Return, CAGR, Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, Profit Factor, Turnover, Rolling Sharpe
- File-based run tracking and experiment management
- Streamlit dashboard: Market Overview, Research Workbench, Strategy Builder, Backtest Results, Performance Analysis

**Phase 2 — Commodity Intelligence:**
- Contract-level futures data ingestion (individual expiry contracts)
- Futures curve construction and visualization
- Term structure analytics: contango, backwardation, basis, roll yield
- Term structure regime detection (contango / backwardation / flat)
- Volatility-scaled position sizing
- MLflow experiment tracking integration
- Dashboard extension: Commodity Intelligence page

**Phase 3 — Portfolio Analytics and Infrastructure:**
- Multi-strategy portfolio aggregation and performance
- Risk analytics: VaR, Expected Shortfall, gross/net exposure
- Cross-asset correlation analysis and rolling correlations
- ClickHouse integration for analytical query performance
- Dashboard extension: Cross-Asset Analytics page

### 2.2 Out of Scope

- Live trading, order routing, or execution simulation beyond vectorized backtesting
- Real-time or intraday data feeds
- Options, structured products, or derivatives beyond vanilla futures
- Multi-user access, authentication, or authorization
- Cloud deployment or containerized infrastructure
- Tick-level or high-frequency data analysis
- Equity, fixed income, or FX instruments

---

## 3. Assumptions and Constraints

### 3.1 Data Assumptions

1. Continuous futures series (GC=F, CL=F, SI=F, HG=F, NG=F, BZ=F) are obtained from Yahoo Finance and represent front-month contracts stitched without documented back-adjustment methodology. These series are treated as opaque vendor-provided continuous price streams. See ADR-001.

2. Yahoo Finance continuous series are NOT back-adjusted. Price discontinuities occur at roll dates. All return-based calculations must use log returns or percentage changes rather than raw price differences. Long-period price-level indicators (EMA-200, SMA-200) will include roll gaps and this is accepted as a known limitation of free data sources. See the Known Limitations section.

3. Contract-level data (individual expiry contracts, e.g., CLN26, CLQ26) is maintained as a separate dataset used exclusively for term structure analysis. It is never used in signal generation or backtesting.

4. Open Interest field is optional; many free data sources do not provide reliable OI data.

5. All data quality issues — OHLC consistency violations, trading gaps, anomalous prices, zero-volume sessions — must be detected and flagged during ingestion before data reaches upper layers.

### 3.2 Backtesting Assumptions

1. Signals are generated using Close[t].
2. Trades are executed at Open[t+1].
3. Bar frequency is daily.
4. The backtester is vectorized. It does not simulate an event-driven order queue, partial fills, margin calls, or forced liquidations.
5. Short selling is permitted on all assets, reflecting the symmetric long/short capability of futures markets.
6. Roll handling is not modeled. The continuous series is treated as a single uninterrupted price stream.

### 3.3 Infrastructure Constraints

1. Single developer. Architecture prioritizes clarity and correctness over engineering throughput.
2. All data is stored on the local filesystem. No cloud storage in Phase 1 or 2.
3. No paid data subscriptions in Phase 1. Free data sources only.
4. No hardcoded credentials, API keys, or filesystem paths. Secrets via `.env`. Paths via `config.yaml`.
5. Python ecosystem only. No JVM, C++, or non-Python dependencies in Phase 1 or 2.

---

## 4. Architecture Overview

The platform is organized into nine logical layers. Dependencies flow strictly downward. No layer imports from or depends on a layer above it. The dashboard (Layer 8) is the only layer permitted to compose outputs from multiple layers simultaneously.

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0 — DATA INFRASTRUCTURE                                  │
│  DataSource abstraction → Ingestion → Validation → Normalization│
│  Storage: raw/ (CSV) → processed/ (Parquet)                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │  NormalizedOHLCV DataFrame
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 1 — FEATURE ENGINEERING                                  │
│  Indicator registry → FeaturePipeline → FeatureFrame + FeatureSpec│
└──────────────────────────────┬──────────────────────────────────┘
                               │  FeatureFrame
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 2 — SIGNAL RESEARCH                                      │
│  RawSignal → IC / ICIR / Decay / Turnover → PositionSignal      │
└──────────────────────────────┬──────────────────────────────────┘
                               │  PositionSignal + RawSignal
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 3 — BACKTESTING ENGINE                                   │
│  VectorizedBacktester + CostModel + PositionSizer + RunManager  │
└──────────────────────────────┬──────────────────────────────────┘
                               │  BacktestResult
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 4 — PERFORMANCE AND ATTRIBUTION                          │
│  Scalar metrics → Rolling metrics → PerformanceReport           │
└──────────────────────────────┬──────────────────────────────────┘
                               │  PerformanceReport
             ┌─────────────────┴──────────────────┐
             │                                     │
┌────────────▼───────────────┐     ┌───────────────▼──────────────┐
│  LAYER 5 — COMMODITY       │     │  LAYER 6 — RISK ANALYTICS    │
│  INTELLIGENCE (Phase 2)    │     │  (Phase 3)                   │
│  Futures curve → Term      │     │  VaR → ES → Exposure         │
│  structure → Regime        │     └──────────────────────────────┘
└────────────────────────────┘     ┌──────────────────────────────┐
                                   │  LAYER 7 — CROSS-ASSET       │
                                   │  ANALYTICS (Phase 3)         │
                                   │  Correlations → Regime → Vol │
                                   └──────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 8 — DASHBOARD (Streamlit)                                │
│  Presentation layer only. Consumes Layer 0–7 via clean APIs.    │
│  No data manipulation in dashboard code.                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Layer Responsibilities

### Layer 0 — Data Infrastructure

**Purpose:** Single source of truth for all data access. The only layer that reads from the filesystem, external APIs, or external data sources.

**Responsibilities:**
- DataSource abstraction: `ContinuousDataSource`, `ContractDataSource` (see ADR-001)
- Raw data ingestion (Yahoo Finance CSV download, manual CSV upload)
- OHLCV validation: type enforcement, OHLC consistency (`high >= low`, `close` within `[low, high]`), gap detection, anomaly flagging
- Field normalization: standard column names (`open`, `high`, `low`, `close`, `volume`, `open_interest`), float64 dtypes, UTC DatetimeIndex
- Parquet serialization: writing normalized data to `data/processed/`
- DataStore interface: read/write Parquet, manage file paths via config

**Does NOT do:** Indicator computation, signal generation, or any analytical transformation.

**Output contract:** `NormalizedOHLCV` — see Layer Contracts section.

---

### Layer 1 — Feature Engineering

**Purpose:** Transform normalized price data into a feature space suitable for signal research.

**Responsibilities:**
- `Indicator` abstract base class defining the `compute(df: DataFrame) -> Series` interface
- Indicator registry: dictionary mapping indicator names to Indicator implementations
- Implementations: SMA, EMA, RSI, RVGI, Momentum (Phase 1); ATR, Volatility (Phase 2)
- Parameter-aware column naming convention: `ema_50`, `rsi_14`, `rvgi_10`
- `FeaturePipeline`: applies a list of Indicator specs to a NormalizedOHLCV DataFrame, returns FeatureFrame
- `FeatureSpec` dataclass: records indicator name, parameters, column name, asset, computation timestamp
- `FeatureFrame` class: wraps DataFrame, tracks which columns are OHLCV vs. computed features

**Does NOT do:** Signal generation, threshold decisions, or position logic.

**Output contract:** `FeatureFrame` + `List[FeatureSpec]` — see Layer Contracts section.

---

### Layer 2 — Signal Research

**Purpose:** Generate and evaluate signals from feature data. This is the primary research layer.

**Responsibilities:**
- `SignalGenerator` abstract base class
- `RawSignal` generation: continuous float signal values (z-scored, normalized, or unbounded depending on signal type)
- Signal evaluation module: IC (Pearson correlation of signal[t] vs. forward_return[t+1]), ICIR, signal decay curve across forward horizons (1, 2, 5, 10, 20 bars), turnover
- `PositionSignal` construction: discretize RawSignal into {+1, 0, -1} via thresholding or ranking rules
- Signal implementations: EMA Crossover Trend (Phase 1), Momentum Trend (Phase 1), Mean Reversion (Phase 1), Donchian Breakout (Phase 1)

**Critical rule:** Signal evaluation (IC, ICIR, decay) must be computed before backtesting. IC analysis is not a backtest; it is a precondition for deciding whether a backtest is warranted.

**Output contract:** `RawSignal` (pd.Series, float64) + `PositionSignal` (pd.Series, int or float, {-1, 0, +1}) — see Layer Contracts section.

---

### Layer 3 — Backtesting Engine

**Purpose:** Simulate strategy execution over historical data under realistic cost assumptions.

**Responsibilities:**
- `VectorizedBacktester`: consumes PositionSignal + OHLCV, applies Close[t] → Open[t+1] execution rule
- `CostModel`: commission per trade (flat fee) + proportional slippage (ticks × tick_value)
- `PositionSizer`: converts PositionSignal to position size in notional or contracts (Phase 1: fixed notional; Phase 2: volatility-scaled)
- `TradeLog`: detects position changes, constructs TradeRecord objects, computes trade-level PnL
- `EquityCurve`: cumulative PnL series indexed by date
- `RunManager`: assigns run ID, persists BacktestResult artifacts to `data/runs/{run_id}/`
- `BacktestResult` assembly

**Architectural constraint:** The backtester is isolated behind an interface so that an event-driven engine may be added in a future phase without modifying strategy or signal logic. See ADR-003.

**Does NOT do:** Performance metric computation, signal generation, or any indicator calculation.

**Output contract:** `BacktestResult` — see Layer Contracts section.

---

### Layer 4 — Performance and Attribution

**Purpose:** Compute performance metrics and assemble structured reports from BacktestResult.

**Responsibilities:**
- Scalar metrics: Total Return, CAGR, Sharpe Ratio, Sortino Ratio, Calmar Ratio, Max Drawdown, Average Drawdown, Drawdown Duration, Win Rate, Profit Factor, Average Trade Duration, Turnover
- Rolling metrics: Rolling Sharpe (63-day, 126-day), Rolling Volatility, Rolling Drawdown
- Trade-level statistics: Average Win, Average Loss, Largest Win, Largest Loss, Consecutive Wins/Losses
- Signal performance metrics: IC (also computed in Layer 2; surfaced here in context of backtest)
- `PerformanceReport` assembly

**Does NOT do:** Chart rendering, dashboard display logic, or backtest simulation.

**Output contract:** `PerformanceReport` — see Layer Contracts section.

---

### Layer 5 — Commodity Intelligence (Phase 2)

**Purpose:** Futures term structure analysis using contract-level (individual expiry) data.

**Responsibilities:**
- Contract-level data ingestion via `ContractDataSource`
- Futures curve construction: snapshot of contract prices across expiry dates for a given observation date
- Contango/backwardation detection and slope quantification
- Roll yield calculation: return from rolling a futures position
- Basis calculation: difference between spot (continuous front-month) and nearest futures contract
- Term structure regime flag: contango / backwardation / flat based on curve slope

**Uses exclusively:** Contract-level data (e.g., CLN26, CLQ26). Never uses continuous series.

---

### Layer 6 — Risk Analytics (Phase 3)

**Purpose:** Portfolio-level risk measurement on a notional-aware basis.

**Responsibilities:**
- Historical VaR at configurable confidence levels (95%, 99%)
- Expected Shortfall (CVaR)
- Gross and net notional exposure by asset and commodity sector
- Contract multiplier integration (from assets.yaml) for accurate dollar exposure

---

### Layer 7 — Cross-Asset Analytics (Phase 3)

**Purpose:** Multi-asset statistical analysis.

**Responsibilities:**
- Pairwise correlation matrix across commodity returns
- Rolling correlations (63-day, 126-day windows)
- Volatility regime analysis
- Regime-conditional performance attribution

---

### Layer 8 — Dashboard

**Purpose:** Interactive presentation layer. Orchestrates user interaction and displays layer outputs.

**Rules:**
- No data manipulation, computation, or business logic in dashboard code
- All data consumed through layer interfaces (function calls to Layers 0–7)
- Dashboard pages import from `src/` modules only; they do not access `data/` directly
- Streamlit session state manages page-level user inputs

---

## 6. Data Flow

```
External Source (Yahoo Finance / CSV)
         │
         ▼
Layer 0: DataSource.fetch() → Validator.validate() → Normalizer.normalize()
         │
         ▼ [Parquet write: data/processed/continuous/{asset}.parquet]
         │
         ▼ [Parquet read]
Layer 1: FeaturePipeline.compute(ohlcv) → FeatureFrame + List[FeatureSpec]
         │
         ▼
Layer 2: SignalGenerator.generate(feature_frame) → RawSignal
         │
         ▼
Layer 2: SignalEvaluator.evaluate(raw_signal, ohlcv) → IC, ICIR, Decay
         │
         ▼
Layer 2: PositionSignalConstructor.build(raw_signal) → PositionSignal
         │
         ▼
Layer 3: VectorizedBacktester.run(position_signal, ohlcv) → BacktestResult
         │                 │
         │                 ▼ [Parquet write: data/runs/{run_id}/]
         ▼
Layer 4: PerformanceEngine.compute(backtest_result) → PerformanceReport
         │
         ▼
Layer 8: Dashboard pages read PerformanceReport and render charts/tables
```

---

## 7. Layer Contracts

All shared types are defined in `src/core/types.py`. These are the authoritative contracts between layers.

### NormalizedOHLCV

```
Type: pandas.DataFrame
Index: pandas.DatetimeIndex (UTC, daily frequency)
Columns:
  open            float64   # session open price
  high            float64   # session high price
  low             float64   # session low price
  close           float64   # session close price
  volume          float64   # traded volume
  open_interest   float64   # open interest (nullable, may be NaN)
Metadata (stored as DataFrame attrs):
  asset           str       # e.g., "gold"
  source          str       # e.g., "yahoo_finance"
  continuous      bool      # True for continuous series, False for individual contracts
  data_start      date
  data_end        date
Invariants:
  high >= low for all rows
  high >= close for all rows
  low <= close for all rows
  open > 0, close > 0 for all rows
  No duplicate index entries
```

### FeatureSpec

```
Type: dataclass
Fields:
  indicator_name  str             # e.g., "ema"
  parameters      Dict[str, Any]  # e.g., {"period": 50}
  column_name     str             # e.g., "ema_50" (computed from name + params)
  asset           str
  computed_at     datetime
```

### FeatureFrame

```
Type: Python class wrapping a pandas.DataFrame
  feature_frame.data          → the underlying DataFrame
  feature_frame.feature_specs → List[FeatureSpec] for all computed columns
  feature_frame.asset         → str, the asset identifier
Index: same DatetimeIndex as NormalizedOHLCV
Columns (on feature_frame.data): all NormalizedOHLCV columns plus indicator columns
  ema_50          float64   # example: EMA with period=50
  ema_200         float64
  sma_20          float64
  rsi_14          float64
  rvgi_10         float64
  momentum_20     float64
Column naming convention: {indicator_name}_{primary_parameter}
```

### RawSignal

```
Type: pandas.Series
Index: DatetimeIndex matching FeatureFrame
Values: float64 (continuous; z-scored or normalized depending on signal type)
Name: str  # signal identifier, e.g., "ema_crossover_50_200"
Constraint: No look-ahead. Values at index t may only use information from t and earlier.
```

### PositionSignal

```
Type: pandas.Series
Index: DatetimeIndex matching FeatureFrame
Values: int8 or float64
  +1  = long
   0  = flat
  -1  = short
Name: str  # position signal identifier
Constraint: Same no-look-ahead constraint as RawSignal.
```

### SignalEvaluation

```
Type: dataclass
Purpose: Carries IC/ICIR/decay results from Layer 2 to PerformanceReport via BacktestResult.
Fields:
  signal_name       str
  asset             str
  ic                float               # Pearson correlation: signal[t] vs log_return[t+1]
  icir              float               # mean(rolling_IC) / std(rolling_IC)
  ic_decay          Dict[int, float]    # {horizon_bars: IC_at_horizon}, horizons: {1,2,5,10,20}
  turnover          float               # mean(|PositionSignal[t] - PositionSignal[t-1]|)
  ic_rolling_window int                 # window used for rolling IC (default: 63)
  evaluation_start  date
  evaluation_end    date
```

### TradeRecord

```
Type: dataclass
Fields:
  run_id              str
  asset               str
  direction           int         # +1 long, -1 short
  entry_date          date
  exit_date           date
  entry_price         float
  exit_price          float
  size_notional       float       # USD notional at entry
  size_contracts      float       # number of contracts (if applicable)
  gross_pnl           float       # PnL before costs
  transaction_cost    float       # commission + slippage in USD
  net_pnl             float       # gross_pnl - transaction_cost
  duration_bars       int         # number of bars held
  return_pct          float       # net_pnl / size_notional
  force_closed        bool        # True if position was closed at backtest end (not by signal)
```

### BacktestResult

```
Type: dataclass
Fields:
  run_id              str
  asset               str
  trades              List[TradeRecord]
  equity_curve        pd.Series    # DatetimeIndex, float64, capital account value
                                   #   starts at initial_capital_usd, grows/falls with net PnL
                                   #   equity_curve[0] = initial_capital_usd
  positions           pd.Series    # DatetimeIndex, float64, position size in notional
  pnl_series          pd.Series    # DatetimeIndex, float64, daily net PnL
  metadata            BacktestMetadata
  signal_evaluation   Optional[SignalEvaluation]  # set by orchestration layer after Layer 2;
                                                  # None if evaluation was skipped
```

### BacktestMetadata

```
Type: dataclass
Fields:
  run_id              str
  asset               str
  strategy_name       str
  signal_name         str
  parameters          Dict[str, Any]
  data_source         str
  data_start          date
  data_end            date
  initial_capital_usd float           # starting capital account value (default: 1_000_000)
  cost_model_params   Dict[str, Any]
  sizing_model_params Dict[str, Any]
  executed_at         datetime
  git_commit_hash     str             # git rev-parse HEAD at time of run
```

### PerformanceReport

```
Type: dataclass
Fields:
  run_id              str
  initial_capital_usd float           # copied from BacktestMetadata; context for interpreting metrics
  scalar_metrics      Dict[str, float]
    Keys: total_return, cagr, sharpe, sortino, calmar, max_drawdown,
          avg_drawdown, win_rate, profit_factor, avg_trade_duration_bars,
          turnover, avg_win, avg_loss, largest_win, largest_loss
    Note: total_return = (equity_curve[-1] - initial_capital_usd) / initial_capital_usd
          daily_return[t] = pnl_series[t] / equity_curve[t-1]  (return on capital)
          sharpe = mean(daily_return) / std(daily_return) * sqrt(252)
  rolling_metrics     Dict[str, pd.Series]
    Keys: rolling_sharpe_63, rolling_sharpe_126, rolling_vol_63, rolling_drawdown
  trade_statistics    Dict[str, Any]
  signal_metrics      Dict[str, float]
    Source: populated from backtest_result.signal_evaluation if present; empty dict if None.
    Keys: ic, icir, signal_decay_1, signal_decay_2, signal_decay_5, signal_decay_10, signal_decay_20
```

---

## 8. Data Sources

### 8.1 Continuous Futures (Phase 1 and 2)

| Asset | Yahoo Ticker | Exchange | Price Unit | Contract Multiplier | Tick Size | Tick Value |
|-------|-------------|----------|------------|-------------------|-----------|-----------|
| Gold | GC=F | COMEX | USD/troy oz | 100 oz | $0.10 | $10.00 |
| Silver | SI=F | COMEX | USD/troy oz | 5,000 oz | $0.005 | $25.00 |
| Copper | HG=F | COMEX | USD/lb | 25,000 lb | $0.0005 | $12.50 |
| WTI Crude | CL=F | NYMEX | USD/barrel | 1,000 bbl | $0.01 | $10.00 |
| Brent Crude | BZ=F | ICE | USD/barrel | 1,000 bbl | $0.01 | $10.00 |
| Natural Gas | NG=F | NYMEX | USD/MMBtu | 10,000 MMBtu | $0.001 | $10.00 |

**Data limitation:** Yahoo Finance continuous series use an undocumented roll methodology and are not back-adjusted. Price level discontinuities will exist at roll dates. This affects price-level indicators computed across roll boundaries. Mitigations: (1) prefer log-return-based signals where possible; (2) document this as a known limitation in run metadata; (3) perform roll-adjusted ingestion in Phase 2 using contract-level data.

### 8.2 Contract-Level Futures (Phase 2)

Individual expiry contracts (e.g., CLN26, CLQ26, CLU26) will be used for term structure and curve analysis only. Source to be confirmed before Phase 2 begins. Candidates: Barchart.com manual CSV export, Nasdaq Data Link (CHRIS dataset), broker-provided data.

---

## 9. Storage Strategy

### 9.0 Repository Structure

The full repository layout is listed below. This is the authoritative reference for Module 1 (Repository Initialization).

```
commodity_research/
│
├── config/
│   ├── config.yaml                    # System config: paths, logging, costs, sizing
│   ├── assets.yaml                    # Per-asset metadata: multipliers, ticks, tickers
│   └── strategies.yaml                # Strategy parameter defaults
│
├── data/                              # All data files — never committed to git
│   ├── raw/
│   │   ├── continuous/                # Downloaded source CSVs (immutable)
│   │   └── contracts/                 # Individual contract CSVs (Phase 2, immutable)
│   ├── processed/
│   │   ├── continuous/                # Canonical Parquet — one file per asset
│   │   └── contracts/                 # One file per contract ticker (Phase 2)
│   └── runs/                          # Backtest run artifacts
│       └── {run_id}/
│
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── types.py                   # All shared type definitions and dataclasses
│   │   ├── registry.py                # Abstract base classes: DataSource, Indicator, SignalGenerator, BacktestEngine, PositionSizer
│   │   ├── config.py                  # Config loader (reads config.yaml, assets.yaml, strategies.yaml)
│   │   └── logging_config.py          # Logging setup
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── sources/
│   │   │   ├── base.py                # ContinuousDataSource (abstract subclass of DataSource for continuous series)
│   │   │   └── csv.py                 # LocalCSVSource (Phase 1), YahooFinanceSource (optional Phase 1)
│   │   ├── validator.py               # OHLCV consistency and gap detection
│   │   ├── normalizer.py              # dtype enforcement, column renaming, index normalization
│   │   ├── store.py                   # ParquetStore: read/write processed Parquet
│   │   └── loader.py                  # DataLoader: orchestrates Source → Validator → Normalizer → Store
│   │
│   ├── research/
│   │   ├── __init__.py
│   │   ├── base.py                    # Indicator ABC
│   │   ├── feature_frame.py           # FeatureFrame class and FeatureSpec dataclass
│   │   ├── moving_averages.py         # SMA, EMA
│   │   ├── oscillators.py             # RSI, RVGI
│   │   ├── momentum.py                # Momentum
│   │   └── pipeline.py                # FeaturePipeline
│   │
│   ├── signal/
│   │   ├── __init__.py
│   │   ├── base.py                    # SignalGenerator ABC
│   │   ├── evaluation.py              # SignalEvaluator: IC, ICIR, decay, turnover
│   │   ├── trend.py                   # EMACrossoverSignal, MomentumSignal
│   │   ├── reversion.py               # RSIReversionSignal
│   │   ├── breakout.py                # DonchianBreakoutSignal
│   │   └── position.py                # PositionSignalConstructor
│   │
│   ├── backtesting/
│   │   ├── __init__.py
│   │   ├── engine.py                  # VectorizedBacktester
│   │   ├── costs.py                   # CostModel
│   │   ├── sizing.py                  # FixedNotionalSizer (Phase 1), VolatilityScaledSizer (Phase 2)
│   │   ├── trade_log.py               # TradeLog, trade boundary detection
│   │   └── run_manager.py             # RunManager: run ID assignment and artifact persistence
│   │
│   ├── performance/
│   │   ├── __init__.py
│   │   ├── metrics.py                 # All scalar metric calculations
│   │   ├── rolling.py                 # Rolling Sharpe, rolling volatility, rolling drawdown
│   │   └── report.py                  # PerformanceEngine.compute() → PerformanceReport
│   │
│   ├── commodity/                     # Phase 2
│   │   ├── __init__.py
│   │   ├── curve.py                   # FuturesCurveBuilder
│   │   ├── term_structure.py          # Contango/backwardation slope, regime flag
│   │   └── roll_yield.py              # Roll yield, basis calculations
│   │
│   └── risk/                          # Phase 3
│       ├── __init__.py
│       ├── var.py                     # VaR, Expected Shortfall
│       ├── exposure.py                # Gross/net notional exposure
│       └── correlation.py             # Cross-asset correlations
│
├── dashboard/
│   ├── app.py                         # Streamlit entry point and page router
│   ├── components/
│   │   ├── price_chart.py
│   │   ├── equity_curve_chart.py
│   │   ├── metrics_table.py
│   │   ├── signal_chart.py
│   │   ├── futures_curve_chart.py     # Phase 2
│   │   └── correlation_heatmap.py     # Phase 3
│   └── pages/
│       ├── 1_market_overview.py
│       ├── 2_research_workbench.py
│       ├── 3_strategy_builder.py
│       ├── 4_backtest_results.py
│       ├── 5_performance_analysis.py
│       ├── 6_commodity_intelligence.py  # Phase 2
│       └── 7_cross_asset_analytics.py   # Phase 3
│
├── tests/
│   ├── conftest.py                    # Shared fixtures and synthetic test data
│   ├── fixtures/
│   │   └── gold_sample.csv            # 252-row synthetic OHLCV for deterministic tests
│   ├── test_config.py
│   ├── test_types.py
│   ├── test_data_validation.py
│   ├── test_data_loader.py
│   ├── test_indicators.py
│   ├── test_pipeline.py
│   ├── test_signal_evaluation.py
│   ├── test_signals.py
│   ├── test_backtester.py
│   └── test_performance.py
│
├── docs/
│   ├── adr/
│   │   └── ADRs.md                    # All Architecture Decision Records
│   └── implementation_notes/          # Post-module implementation summaries
│
├── notebooks/
│   └── research_sandbox.ipynb         # Exploratory research only; not production code
│
├── logs/                              # Runtime logs (gitignored)
├── .env.example                       # Secret template (no real values)
├── .gitignore                         # Excludes: data/, logs/, .env, __pycache__, *.pyc
├── pyproject.toml                     # Project metadata and dependencies
├── ARCHITECTURE.md                    # This document
└── IMPLEMENTATION_ROADMAP.md          # Module development sequence
```

**Key rules:**
- `data/` is never committed to git. Add to `.gitignore`.
- `logs/` is never committed to git. Add to `.gitignore`.
- `src/core/types.py` is the single source of truth for all shared types. No layer defines types outside this file.
- `src/core/registry.py` is the single source of truth for all abstract base classes.
- No module outside `src/data/` may read from the `data/` directory directly.

### 9.1 Data Directory Layout

```
data/
├── raw/
│   ├── continuous/           # Downloaded source CSVs — never modified post-download
│   │   └── {asset}_{date}.csv
│   └── contracts/            # Individual contract CSVs
│       └── {ticker}_{date}.csv
├── processed/
│   ├── continuous/           # Canonical Parquet — one file per asset
│   │   └── {asset}.parquet
│   └── contracts/            # One file per contract ticker
│       └── {ticker}.parquet
└── runs/
    └── {run_id}/             # run_id format: YYYYMMDD_HHMMSS_{strategy}_{asset}
        ├── params.json        # Complete parameter snapshot
        ├── trades.parquet
        ├── equity_curve.parquet
        ├── pnl_series.parquet
        ├── positions.parquet
        └── metrics.json
```

### 9.2 Rules

- Raw files are immutable once written.
- Processed Parquet files are regenerated from raw on demand (idempotent normalization).
- Run artifacts are immutable once written. Reruns create new run IDs.
- File paths are never hardcoded. All paths resolved via `config.yaml` + `src/core/config.py`.

### 9.3 Phase 3 Migration

Phase 3 will introduce ClickHouse as an analytical query layer over processed data. The `DataStore` abstraction in Layer 0 is designed to support an alternative `ClickHouseStore` implementation alongside the existing `ParquetStore` without modifying upper layers. See ADR-004.

---

## 10. Signal Research Workflow

The signal research workflow follows standard institutional practice for systematic signal evaluation. Signal quality must be assessed before committing to a full backtest.

### Workflow Steps

```
1. Load asset data
   └─ DataLoader.load(asset="gold") → NormalizedOHLCV

2. Build feature frame
   └─ FeaturePipeline.compute(ohlcv, specs=[...]) → FeatureFrame

3. Generate raw signal
   └─ SignalGenerator.generate(feature_frame) → RawSignal

4. Evaluate signal quality  ← THIS STEP PRECEDES BACKTESTING
   └─ signal_evaluation = SignalEvaluator.evaluate(raw_signal, ohlcv)
      ├─ IC    = corr(signal[t], log_return[t+1])
      ├─ ICIR  = mean(IC_rolling) / std(IC_rolling)
      └─ Decay = IC at horizons {1, 2, 5, 10, 20}

5. Construct position signal
   └─ PositionSignalConstructor.build(raw_signal, threshold=0.0) → PositionSignal

6. Run backtest
   └─ VectorizedBacktester.run(position_signal, ohlcv) → BacktestResult
      backtest_result.signal_evaluation = signal_evaluation  # attach evaluation result

7. Compute performance
   └─ PerformanceEngine.compute(backtest_result) → PerformanceReport
      (PerformanceEngine reads backtest_result.signal_evaluation for signal_metrics)

8. Store run
   └─ RunManager.save(backtest_result)          → writes params.json and time-series Parquet
      RunManager.save_metrics(run_id, report)   → writes metrics.json to same run directory
```

### IC Interpretation Guidelines

These thresholds are approximate benchmarks from institutional systematic research practice:

| IC Value | Interpretation |
|----------|---------------|
| \|IC\| < 0.02 | Signal likely noise. Backtest not warranted. |
| 0.02 ≤ \|IC\| < 0.05 | Weak signal. Investigate further before backtesting. |
| \|IC\| ≥ 0.05 | Meaningful predictive content. Proceed to backtest. |
| ICIR ≥ 0.5 | Signal is consistent across time, not merely high in limited periods. |

**Note:** Commodity futures markets tend to exhibit lower IC values than equity markets due to stronger mean reversion at short horizons and more pronounced macro regime dependence. Calibrate thresholds accordingly.

---

## 11. Backtesting Assumptions

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Signal generation time | Close[t] | Reflects realistic end-of-day signal computation |
| Trade execution time | Open[t+1] | Eliminates look-ahead bias; matches realistic execution |
| Bar frequency | Daily | Appropriate for systematic commodity research |
| Engine type | Vectorized | Sufficient for signal research and strategy screening |
| Initial capital | $1,000,000 (default, configurable) | Starting capital account value; equity_curve[0] = initial_capital_usd |
| Short selling | Permitted | Futures markets support symmetric long/short |
| Direction reversal | Treated as two trades | A +1 → -1 change closes the long and opens a short; two transaction costs applied |
| Open position at period end | Force-closed at Close[T] | Any position open at the last bar is closed at the final close price and recorded as a trade |
| Roll handling | Not modeled | Continuous series treated as single price stream |
| Margin | Not modeled (Phase 1) | Research platform; not execution simulator |
| Partial fills | Not modeled | Beyond scope of vectorized engine |
| Commission model | Per-trade flat fee | Configurable in config.yaml |
| Slippage model | Fixed ticks per side | Configurable in config.yaml |
| PnL currency | USD | Contract multipliers applied from assets.yaml |

---

## 12. Position Sizing Model

### Phase 1 — Fixed Notional

Each signal receives a fixed USD notional exposure regardless of asset volatility.

```
position_size_notional = config.sizing.fixed_notional_usd  # default: $100,000
```

**Limitation:** A $100,000 position in Natural Gas carries substantially different risk than $100,000 in Gold due to different volatility characteristics. This is accepted as a Phase 1 simplification appropriate for signal research normalization. Results should not be interpreted as realistic dollar PnL.

### Phase 2 — Volatility-Scaled Sizing

Position size is scaled to target a fixed annualized volatility per position.

```
target_vol     = config.sizing.target_annual_vol   # e.g., 0.15 (15% annualized)
realized_vol   = rolling_std(log_returns, window=63) * sqrt(252)
current_equity = equity_curve.iloc[-1]             # current capital account value
position_size_notional = (target_vol / realized_vol) * current_equity
```

`current_equity` is the most recent value of the capital account (initial_capital_usd + cumulative net PnL to date). This ensures that position sizes scale with both volatility and current account value, which is standard practice at institutional commodity systematic desks.

### Phase 3 — Risk Budgeting and Portfolio Allocation

Portfolio-level risk budgeting allocates capital across strategies and assets based on risk targets and correlation structure. Implementation in Phase 3.

---

## 13. Dashboard Architecture

The dashboard is implemented in Streamlit. It is a pure presentation layer.

**Rules:**
- Dashboard pages may not perform data computation. All analytics are computed in `src/` modules.
- Dashboard pages import from `src/` only. They do not access `data/` directories directly.
- All data exchange between pages uses Streamlit session state or cached function results.
- Dashboard code does not contain strategy logic, indicator math, or performance calculations.

### Page Map

| Page | Content | Layers Consumed | Phase |
|------|---------|-----------------|-------|
| 1. Market Overview | Commodity universe, latest prices, returns, volume summary | Layer 0 | 1 |
| 2. Research Workbench | Price charts, indicators, IC analysis, signal visualization | Layers 0, 1, 2 | 1 |
| 3. Strategy Builder | Strategy selection, parameters, asset selection, backtest trigger | Layers 0, 1, 2, 3 | 1 |
| 4. Backtest Results | Trade log, equity curve, daily PnL | Layer 3 | 1 |
| 5. Performance Analysis | Metrics table, rolling Sharpe, drawdown chart, turnover | Layers 3, 4 | 1 |
| 6. Commodity Intelligence | Futures curves, contango/backwardation, basis, roll yield | Layer 5 | 2 |
| 7. Cross-Asset Analytics | Correlation matrix, rolling correlations, vol comparison | Layers 4, 7 | 3 |

### Streamlit Component Organization

Reusable chart components live in `dashboard/components/`:
- `price_chart.py` — OHLCV candlestick chart with overlay indicators
- `equity_curve_chart.py` — cumulative PnL chart with drawdown overlay
- `metrics_table.py` — structured performance metrics display
- `signal_chart.py` — signal strength visualization with IC overlay
- `futures_curve_chart.py` — term structure visualization (Phase 2)
- `correlation_heatmap.py` — correlation matrix display (Phase 3)

---

## 14. Configuration Reference

### config.yaml

```yaml
paths:
  raw_data: "data/raw/"
  processed_data: "data/processed/"
  runs: "data/runs/"
  logs: "logs/"

logging:
  level: "INFO"
  format: "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
  file: "logs/platform.log"

costs:
  default_commission_usd: 5.00
  default_slippage_ticks: 1

sizing:
  method: "fixed_notional"       # Phase 1: fixed_notional | Phase 2: volatility_scaled
  fixed_notional_usd: 100000
  target_annual_vol: 0.15         # Phase 2 only

data:
  default_start_date: "2010-01-01"
  default_end_date: null           # null = today
```

### assets.yaml

```yaml
gold:
  ticker_continuous: "GC=F"
  exchange: "COMEX"
  currency: "USD"
  unit: "troy_oz"
  contract_multiplier: 100
  tick_size: 0.10
  tick_value: 10.00

silver:
  ticker_continuous: "SI=F"
  exchange: "COMEX"
  currency: "USD"
  unit: "troy_oz"
  contract_multiplier: 5000
  tick_size: 0.005
  tick_value: 25.00

copper:
  ticker_continuous: "HG=F"
  exchange: "COMEX"
  currency: "USD"
  unit: "lb"
  contract_multiplier: 25000
  tick_size: 0.0005
  tick_value: 12.50

wti:
  ticker_continuous: "CL=F"
  exchange: "NYMEX"
  currency: "USD"
  unit: "barrel"
  contract_multiplier: 1000
  tick_size: 0.01
  tick_value: 10.00

brent:
  ticker_continuous: "BZ=F"
  exchange: "ICE"
  currency: "USD"
  unit: "barrel"
  contract_multiplier: 1000
  tick_size: 0.01
  tick_value: 10.00

natural_gas:
  ticker_continuous: "NG=F"
  exchange: "NYMEX"
  currency: "USD"
  unit: "MMBtu"
  contract_multiplier: 10000
  tick_size: 0.001
  tick_value: 10.00
```

### strategies.yaml

```yaml
ema_crossover:
  fast_period: 50
  slow_period: 200
  signal_threshold: 0.0

momentum:
  lookback_period: 20
  z_score_window: 63
  signal_threshold: 0.5

donchian_breakout:
  channel_period: 20

rsi_reversion:
  period: 14
  oversold_threshold: 30
  overbought_threshold: 70
```

---

## 15. Phase Roadmap

### Phase 1 — Research MVP (Current)

**Goal:** End-to-end single-asset research pipeline operational for at least one commodity and one strategy, with all core layers functional.

**Layers:** 0, 1, 2, 3, 4, 8 (pages 1–5)

**Success criteria:**
- Can ingest and normalize data for all 6 commodities
- Can compute all Phase 1 indicators on any loaded asset
- Can generate, evaluate (IC/ICIR), and backtest at least one signal
- BacktestResult stored as Parquet run artifacts
- PerformanceReport computes all Phase 1 metrics
- Dashboard pages 1–5 functional

### Phase 2 — Commodity Intelligence and Realistic Sizing

**Goal:** Term structure analytics operational; position sizing reflects volatility; experiment tracking formalized.

**Layers:** 5 (new), updates to 0, 2, 3, 8

**Additions:**
- Contract-level data ingestion pipeline
- Futures curve construction and term structure analytics
- Contango/backwardation/basis/roll yield metrics
- Regime flag from term structure slope
- Volatility-scaled position sizing
- MLflow integration for run tracking (replaces file-only approach)
- Dashboard page 6

### Phase 3 — Portfolio Analytics and Infrastructure

**Goal:** Multi-asset portfolio analysis; risk analytics; ClickHouse storage.

**Layers:** 6, 7 (new), updates to 3, 4, 8

**Additions:**
- Multi-asset backtest aggregation (portfolio equity curve, portfolio-level metrics)
- Risk analytics: VaR, Expected Shortfall, gross/net exposure
- Cross-asset correlation analysis
- ClickHouse integration (analytical queries over time-series data)
- Dashboard page 7

---

## 16. Known Limitations

1. **Yahoo Finance roll gaps.** Continuous series are not back-adjusted. Price-level indicators spanning roll dates will include artificial discontinuities. Mitigated by preferring log-return-based signals. Documented in all run metadata.

2. **Vectorized backtester.** Does not simulate order routing, partial fills, margin calls, or forced liquidations. Suitable for signal research; insufficient for execution simulation.

3. **No real-time data.** Platform is entirely historical.

4. **Fixed notional sizing (Phase 1).** Equal notional across assets does not equal equal risk. Natural Gas is significantly more volatile than Gold per dollar of notional.

5. **Independent per-asset backtesting (Phase 1).** Results from different assets are not combined into a portfolio equity curve. Portfolio-level metrics are not computed until Phase 3.

6. **No roll calendar.** The platform does not know when roll events occurred in the Yahoo Finance continuous series, making it impossible to strip out roll-date returns or flag roll periods in the signal series.

7. **Open Interest.** OI data from Yahoo Finance is often sparse or unavailable. OI-based signals are not implemented in Phase 1.

---

## 17. Future Evolution Path

### Research Workflow Evolution

```
Phase 1: Per-asset signal research → single-asset backtest → performance report
Phase 2: Term structure signals + volatility sizing → multi-period comparison
Phase 3: Portfolio construction → risk budgeting → portfolio-level attribution
Later:   Factor decomposition → regime-conditional alpha research
```

### Infrastructure Evolution

```
Data:     CSV ingestion → Parquet local lake → ClickHouse OLAP store
Storage:  Local filesystem → S3/GCS + Parquet → ClickHouse + object storage
Compute:  Pandas vectorized → Polars/Dask for large data → cluster compute
Tracking: File-based → MLflow local → MLflow remote server → Neptune
Pipeline: Manual execution → Streamlit triggers → Prefect/Airflow scheduled pipelines
```

### Backtesting Evolution

```
Phase 1: Vectorized engine (signal research)
Phase 3: Event-driven engine (realistic execution simulation, needed for HFT research)
Later:   Dedicated backtesting framework integration (e.g., vectorbt, Nautilus)
```

The vectorized → event-driven transition does not require modifying Layer 2 or Layer 4. The `BacktestResult` contract is engine-agnostic by design.

---

## 18. ADR Index

All Architecture Decision Records are maintained in `docs/adr/ADRs.md`.

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | Continuous vs. Contract-Level Futures Data | Accepted |
| ADR-002 | Signal Timing Convention (Close[t] → Open[t+1]) | Accepted |
| ADR-003 | Vectorized Backtesting Engine | Accepted |
| ADR-004 | Storage Strategy: Parquet + ClickHouse Migration Path | Accepted |
| ADR-005 | Position Sizing Methodology | Accepted |
| ADR-006 | FeatureFrame and FeatureSpec Design | Accepted |
| ADR-007 | Signal Research Layer: RawSignal, PositionSignal, IC Evaluation | Accepted |
| ADR-008 | Dashboard Architecture | Accepted |
| ADR-009 | Run Tracking Strategy | Accepted |
| ADR-010 | Multi-Asset Research Scope and Phasing | Accepted |
