# Commodity Systematic Research Platform
## Architecture Reference Document

**Version:** 3.0
**Status:** Active — Phase 1 Complete, Phase 2 Complete, Phase 3 Complete. Next: F-track (React + FastAPI).
**Audience:** Developers, quantitative researchers, architecture reviewers
**Last Updated:** Phase 3 completion (M01–M19, 267 tests, phase-3-complete tag)

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

**Phase 1 — Research MVP (COMPLETE — M01–M07, 107 tests):**
- Continuous futures data ingestion from Yahoo Finance (CSV/Parquet)
- Data validation and normalization pipeline with configurable OHLC strictness
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
- Institutional dark theme (navy #0e1628) with monospace typography

**Phase 2 — Commodity Intelligence (COMPLETE — M08–M13, 186 tests):**
- Contract-level futures data ingestion via Yahoo Finance individual contract tickers (e.g., GCZ24.CMX)
- Futures curve construction: `FuturesCurveBuilder` producing `FuturesCurve` snapshots
- Term structure analytics: `TermStructureAnalyzer` producing `TermStructureSnapshot`
- Contango/backwardation slope (annualized, normalized to front price)
- Roll yield calculation (annualized, sign convention: positive = backwardation)
- Basis calculation (continuous close − front contract price; pseudo-basis per ADR-001)
- Term structure regime detection: `TermStructureRegime` (CONTANGO / BACKWARDATION / FLAT)
- Volatility-scaled position sizing: `VolatilityScaledSizer` with `configure()` protocol
- MLflow experiment tracking: local filesystem backend, one experiment per asset
- Dashboard Page 6: Futures Curve (forward curve visualization, regime KPIs, history charts)

**Phase 3 — Portfolio Analytics and Infrastructure (COMPLETE — M14–M19, 267 tests):**
- Multi-asset runner: `MultiAssetRunner` producing portfolio equity curve across all 6 assets
- Portfolio performance: `PortfolioPerformanceEngine` — Sharpe, drawdown, attribution, `absolute_pnl_by_asset`
- Risk analytics: `RiskEngine` — historical VaR (95/99%), Expected Shortfall, notional exposure, diversification benefit
- Cross-asset correlation: `CorrelationEngine` — pairwise matrix, rolling 63/126-day, realized strategy vol
- ClickHouse integration: `ClickHouseStore` behind `DataStore` ABC, 24,862 rows migrated, config-switchable
- Portfolio persistence: `save_portfolio_summary()` writes `portfolio_summary.json` per run
- Dashboard Page 7: Cross-Asset Analytics (7 sections: KPIs, equity curve, attribution, risk, heatmap, rolling, vol)

**F-Track — React + FastAPI Frontend (Planned):**
- FastAPI serialization shell (F0): HTTP boundary over all `src/` analytics
- React + TypeScript SPA (F1–F8): IC Gate doctrine, immutability-derived caching, type-generation chain
- Commodity Intelligence UI (F9–F11): curve scrubber, regime timelines, basis/roll-yield charts
- Portfolio UI (F12–F15): multi-asset portfolio view, risk dashboards, correlation heatmap

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

3. Contract-level data (individual expiry contracts, e.g., GCZ24, CLF25) is obtained from Yahoo Finance using asset-specific exchange suffix tickers (e.g., GCZ24.CMX for COMEX contracts, CLF25.NYM for NYMEX contracts). Contract data is maintained as a separate dataset used exclusively for term structure analysis. It is never used in signal generation or backtesting.

4. `OHLCVValidator` uses `strict_ohlc=False` for all Yahoo Finance data (both continuous and contract-level). Yahoo Finance settlement prices are volume-weighted averages of the closing range and can legally fall outside the intraday High/Low. The 2020-04-20 WTI negative price event (−$37.63) is genuine historical data, not a data error. `strict_ohlc=True` is reserved for Phase 3 institutional vendor data where OHLC consistency is guaranteed.

5. Open Interest field is optional; Yahoo Finance does not provide reliable OI data for commodity futures.

6. All data quality issues — OHLC consistency violations, trading gaps, anomalous prices, zero-volume sessions — are detected and logged as warnings during ingestion. Structural violations (duplicate dates) raise `DataValidationError`.

### 3.2 Backtesting Assumptions

1. Signals are generated using Close[t].
2. Trades are executed at Open[t+1].
3. Bar frequency is daily.
4. The backtester is vectorized. It does not simulate an event-driven order queue, partial fills, margin calls, or forced liquidations.
5. Short selling is permitted on all assets, reflecting the symmetric long/short capability of futures markets.
6. Roll handling is not modeled. The continuous series is treated as a single uninterrupted price stream.
7. Position sizers implement the `configure(ohlcv)` protocol. `VectorizedBacktester.run()` calls `sizer.configure(ohlcv)` before the simulation loop. Static sizers (FixedNotionalSizer) inherit a no-op default. Dynamic sizers (VolatilityScaledSizer) override to pre-compute data-driven state.

### 3.3 Infrastructure Constraints

1. Single developer. Architecture prioritizes clarity and correctness over engineering throughput.
2. All data is stored on the local filesystem. No cloud storage in Phase 1 or 2.
3. No paid data subscriptions in Phase 1 or 2. Free data sources only (Yahoo Finance).
4. No hardcoded credentials, API keys, or filesystem paths. Secrets via `.env`. Paths via `config.yaml`.
5. Python ecosystem only. No JVM, C++, or non-Python dependencies in Phase 1 or 2.
6. MLflow 3.x requires `MLFLOW_ALLOW_FILE_STORE=true` for local filesystem tracking. This is set programmatically in `_try_log_to_mlflow()` and exported by the launcher scripts.

---

## 4. Architecture Overview

The platform is organized into nine logical layers. Dependencies flow strictly downward. No layer imports from or depends on a layer above it. The dashboard (Layer 8) is the only layer permitted to compose outputs from multiple layers simultaneously.

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0 — DATA INFRASTRUCTURE                                  │
│  ContinuousDataSource + ContractDataSource                       │
│  Ingestion → Validation (strict_ohlc=False) → Normalization      │
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
│  VectorizedBacktester + CostModel                               │
│  PositionSizer (Fixed | VolatilityScaled) + RunManager + MLflow  │
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
│  INTELLIGENCE (Complete)   │     │  (Phase 3)                   │
│  ContractDataLoader         │     │  VaR → ES → Exposure         │
│  FuturesCurveBuilder        │     └──────────────────────────────┘
│  TermStructureAnalyzer      │     ┌──────────────────────────────┐
│  FuturesCurve + Snapshot    │     │  LAYER 7 — CROSS-ASSET       │
└────────────────────────────┘     │  ANALYTICS (Phase 3)         │
                                   │  Correlations → Regime → Vol │
                                   └──────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 8 — DASHBOARD (Streamlit — Phase 1/2/3 complete)         │
│  Presentation layer only. Consumes Layer 0–7 via clean APIs.    │
│  No data manipulation in dashboard code.                        │
│  7 pages: Market Overview, Research Workbench, Strategy Builder, │
│  Backtest Results, Performance Analysis, Futures Curve,          │
│  Cross-Asset Analytics                                          │
│                                                                 │
│  F-TRACK (Planned): FastAPI (F0) + React/TypeScript SPA (F1–F15)│
│  Replaces Streamlit. IC Gate enforced in UI. Typed contracts     │
│  from types.py → Pydantic → OpenAPI → TypeScript.              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Layer Responsibilities

### Layer 0 — Data Infrastructure

**Purpose:** Single source of truth for all data access. The only layer that reads from the filesystem, external APIs, or external data sources.

**Phase 1 responsibilities (implemented):**
- `ContinuousDataSource` abstraction → `LocalCSVSource` implementation
- OHLCV validation: gap detection, anomaly flagging, consistency checks (strict_ohlc=False for Yahoo Finance data)
- Field normalization: standard column names, float64 dtypes, UTC DatetimeIndex
- `ParquetStore`: read/write normalized continuous series at `data/processed/continuous/{asset}.parquet`
- `DataLoader`: orchestrates Source → Validator → Normalizer → Store pipeline

**Phase 2 responsibilities (implemented):**
- `FuturesContractSource`: reads individual contract CSVs from `data/raw/contracts/{asset}/{ticker}.csv`
- `parse_contract_ticker()`: converts canonical ticker string (e.g., GCZ24) to `ContractMetadata`
- `ContractParquetStore`: read/write contract OHLCV + sidecar metadata JSON at `data/processed/contracts/{asset}/{ticker}.parquet`
- `ContractDataLoader`: orchestrates contract pipeline; provides `load_contract()`, `load_curve()`, `list_contracts()`
- `scripts/acquire_contract_data.py`: downloads individual contracts from Yahoo Finance using exchange-suffix tickers (e.g., GCZ24.CMX); saves as canonical tickers (GCZ24.csv)

**Key design decisions:**
- Exchange suffix (`.CMX` for COMEX, `.NYM` for NYMEX/ICE) is a yfinance API concern only. Storage and `ContractMetadata.ticker` always use the canonical ticker without suffix.
- `OHLCVNormalizer.normalize()` clears `result.attrs = {}` before returning to prevent pyarrow UserWarning during Parquet serialization. `DataLoader.load()` re-populates `asset`, `source`, `continuous` attrs on both fast and slow paths.

**Does NOT do:** Indicator computation, signal generation, or any analytical transformation.

**Output contracts:** `NormalizedOHLCV` DataFrame; `ContractMetadata` dataclass.

---

### Layer 1 — Feature Engineering

**Purpose:** Transform normalized price data into a feature space suitable for signal research.

**Responsibilities:**
- `Indicator` abstract base class defining the `compute(df: DataFrame) -> Series` interface
- Indicator registry: dictionary mapping indicator names to Indicator implementations
- Implementations: SMA, EMA, RSI, RVGI, Momentum
- Parameter-aware column naming convention: `ema_50`, `rsi_14`, `rvgi_10`
- `FeaturePipeline`: applies a list of Indicator specs to a NormalizedOHLCV DataFrame, returns FeatureFrame
- `FeatureSpec` dataclass: records indicator name, parameters, column name, asset, computation timestamp
- `FeatureFrame` class: wraps DataFrame, tracks which columns are OHLCV vs. computed features

**Does NOT do:** Signal generation, threshold decisions, or position logic.

**Output contract:** `FeatureFrame` + `List[FeatureSpec]`.

---

### Layer 2 — Signal Research

**Purpose:** Generate and evaluate signals from feature data. This is the primary research layer.

**Responsibilities:**
- `SignalGenerator` abstract base class
- `RawSignal` generation: continuous float signal values (z-scored, normalized, or unbounded depending on signal type)
- Signal evaluation: IC (Pearson correlation of signal[t] vs. forward_return[t+1]), ICIR, signal decay at horizons {1, 2, 5, 10, 20 bars}, turnover
- `PositionSignal` construction: discretize RawSignal into {+1, 0, -1} via thresholding or ranking rules
- Signal implementations: EMA Crossover, Momentum, RSI Reversion, Donchian Breakout

**Critical rule:** IC evaluation precedes backtesting. IC is a precondition for deciding whether a backtest is warranted, not a post-hoc diagnostic.

**Output contract:** `RawSignal` (pd.Series, float64) + `PositionSignal` (pd.Series, int or float, {-1, 0, +1}).

---

### Layer 3 — Backtesting Engine

**Purpose:** Simulate strategy execution over historical data under realistic cost assumptions.

**Responsibilities:**
- `VectorizedBacktester`: consumes PositionSignal + OHLCV, applies Close[t] → Open[t+1] execution rule. Accepts optional `sizer: PositionSizer | None = None` parameter for sizer dependency injection.
- `CostModel`: commission per trade (flat fee) + proportional slippage (ticks × tick_value)
- `PositionSizer` ABC: `configure(ohlcv)` no-op hook + abstract `compute_size(signal, asset, equity)`
  - `FixedNotionalSizer(notional_usd=...)`: Phase 1 default; returns fixed USD notional regardless of asset volatility
  - `VolatilityScaledSizer(target_annual_vol, lookback_days, vol_cap, ...)`: Phase 2; sizes positions to target a fixed annualized volatility contribution; `configure(ohlcv)` pre-computes realized vol
- `TradeLog`: detects position changes, constructs TradeRecord objects, computes trade-level PnL
- `EquityCurve`: cumulative PnL series indexed by date
- `RunManager`: assigns run ID (YYYYMMDD_HHMMSS_{strategy}_{asset}), persists BacktestResult artifacts to `data/runs/{run_id}/`, logs to MLflow via `_try_log_to_mlflow()` in `save_metrics()`

**configure() protocol:** `VectorizedBacktester.run()` calls `self._sizer.configure(ohlcv)` before the simulation begins. `FixedNotionalSizer` inherits the no-op. `VolatilityScaledSizer` overrides to pre-compute realized volatility from the OHLCV close series.

**Does NOT do:** Performance metric computation, signal generation, or any indicator calculation.

**Output contract:** `BacktestResult`.

---

### Layer 4 — Performance and Attribution

**Purpose:** Compute performance metrics and assemble structured reports from BacktestResult.

**Responsibilities:**
- Scalar metrics: Total Return, CAGR, Sharpe Ratio, Sortino Ratio, Calmar Ratio, Max Drawdown, Average Drawdown, Win Rate, Profit Factor, Average Trade Duration, Turnover, Average Win/Loss, Largest Win/Loss
- Rolling metrics: Rolling Sharpe (63-day, 126-day), Rolling Volatility, Rolling Drawdown
- Trade-level statistics: Consecutive Wins/Losses
- Signal performance metrics: IC, ICIR, decay (surfaced from BacktestResult.signal_evaluation)
- `PerformanceReport` assembly

**Does NOT do:** Chart rendering, dashboard display logic, or backtest simulation.

**Output contract:** `PerformanceReport`.

---

### Layer 5 — Commodity Intelligence (Implemented — Phase 2)

**Purpose:** Futures term structure analysis using contract-level (individual expiry) data.

**Responsibilities:**
- `ContractDataLoader` (Layer 0 extension): provides contract data to this layer
- `FuturesCurveBuilder`: constructs `FuturesCurve` snapshots from contract OHLCV data
  - `build(asset, observation_date, n_contracts)` → `FuturesCurve`
  - `build_historical_curves(asset, dates, n_contracts)` → `list[FuturesCurve]`
  - `available_assets()` → `list[str]` (assets with processed Parquet contract data)
- `TermStructureAnalyzer`: computes analytics from `FuturesCurve` objects
  - `analyze(curve, continuous_close)` → `TermStructureSnapshot`
  - `analyze_series(curves, continuous_closes)` → `list[TermStructureSnapshot]`
  - `contango_slope_annualized(curve)`: (back/front − 1) / years_to_back
  - `roll_yield_annualized(curve)`: (front − second) / second × (365 / days_between)
  - `compute_basis(curve, continuous_close)`: continuous_close − front_contract_price

**Layer 5 / Layer 0 connection for basis:** `TermStructureAnalyzer.compute_basis()` receives `continuous_close` as a parameter (not by calling `DataLoader` internally). The dashboard is the orchestration point that loads both pipelines and passes the continuous close to the analyzer. This is the only point in the platform where the two data pipelines interact.

**Uses exclusively:** Contract-level data (e.g., GCZ24, CLF25). The continuous series is provided externally as a parameter for basis computation only; it is never mixed with contract data in the analytical pipeline.

---

### Layer 6 — Risk Analytics (Implemented — Phase 3)

**Purpose:** Portfolio-level risk measurement on a notional-aware basis.

**Responsibilities (implemented):**
- `RiskEngine.compute(multi_result, lookback_days=252)` → `RiskReport`
- Historical VaR at 95% and 99% confidence (historical simulation, no parametric assumption)
- Expected Shortfall (CVaR) at 95% and 99%
- Average gross and net notional exposure per asset (averaged over active trading days)
- Portfolio diversification benefit: sum(asset_var_99) / portfolio_var_99
- VaR expressed as positive USD loss magnitudes; NaN for < 20 observations

**Known gap (evaluation finding):** VaR is backward-looking (realized strategy P&L). Forward-looking VaR (current positions × return scenarios) is not implemented. Kupiec backtesting (VaR calibration verification) is not implemented. No margin model.

---

### Layer 7 — Cross-Asset Analytics (Implemented — Phase 3)

**Purpose:** Multi-asset statistical analysis.

**Responsibilities (implemented):**
- `CorrelationEngine.compute(multi_result)` → `CorrelationReport`
- Pairwise Pearson correlation matrix of strategy daily returns (not price returns)
- Rolling correlations at 63-day and 126-day windows (upper-triangle storage only, TD-M17-A)
- Realized strategy volatility per asset (annualized std of strategy P&L returns)

**Note on strategy vol vs price vol:** `realized_vol_by_asset` values are strategy P&L vols (2–8%/yr for EMA 50/200), not commodity price vols (15–60%/yr). Labels must say "Strategy Realized Vol" not "Asset Volatility."

**Known gap (evaluation finding):** Layer 7 architecture text originally promised "volatility regime analysis" and "regime-conditional performance attribution." These were not implemented in M17 and have no owning module in the roadmap. The architecture promise has been removed from this version to match the actual implementation. Regime-conditional attribution is a planned future extension.

---

### Layer 8 — Dashboard

**Purpose:** Interactive presentation layer. Orchestrates user interaction and displays layer outputs.

**Rules:**
- No data manipulation, computation, or business logic in dashboard code
- All data consumed through layer interfaces (function calls to Layers 0–7)
- Dashboard pages import from `src/` modules only; they do not access `data/` directly
- Streamlit session state manages page-level user inputs
- Dark institutional theme (#0e1628 navy) applied via `inject_global_css()` from `_theme.py`
- `render_kpi_row()` for KPI displays (replaces `st.metric()` on pages 3, 4, 5, 6)
- `section_header()` for labeled section dividers

---

## 6. Data Flow

### Phase 1 — Signal Research Pipeline

```
External Source (Yahoo Finance / CSV)
         │
         ▼
Layer 0: DataLoader: LocalCSVSource → OHLCVValidator(strict_ohlc=False)
         → OHLCVNormalizer → ParquetStore
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
         │  ↑ sizer.configure(ohlcv) called before simulation
         │
         ├─ [Parquet write: data/runs/{run_id}/]
         │
         ▼
Layer 4: PerformanceEngine.compute(backtest_result) → PerformanceReport
         │  ↳ RunManager.save_metrics() → [JSON write + MLflow log]
         │
         ▼
Layer 8: Dashboard pages render PerformanceReport charts and tables
```

### Phase 3 — Portfolio Analytics Pipeline

```
MultiAssetRunner.run(assets, strategy_name, parameters, sizer)
         │
         ▼  [per asset: DataLoader → FeaturePipeline → SignalGenerator →
             SignalEvaluator → PositionSignalConstructor → VectorizedBacktester]
         │
MultiAssetBacktestResult (portfolio_equity_curve + per-asset BacktestResults)
         │
         ├──▶ PortfolioPerformanceEngine.compute() → PortfolioPerformanceReport
         │       [portfolio Sharpe, drawdown, attribution, absolute_pnl_by_asset]
         │
         ├──▶ RiskEngine.compute() → RiskReport
         │       [VaR 95/99, ES 95/99, notional exposure, diversification benefit]
         │
         ├──▶ CorrelationEngine.compute() → CorrelationReport
         │       [correlation matrix, rolling correlations, strategy realized vol]
         │
         ├──▶ save_portfolio_summary() → data/runs/{run_id}/portfolio_summary.json
         │
         └──▶ Layer 8: Dashboard Page 7 renders all three reports
```

### Phase 2 — Term Structure Pipeline

```
Yahoo Finance individual contract tickers (e.g., GCZ24.CMX)
         │
         ▼
scripts/acquire_contract_data.py → data/raw/contracts/{asset}/{ticker}.csv
         │
         ▼
Layer 0: ContractDataLoader: FuturesContractSource → OHLCVValidator(strict_ohlc=False)
         → OHLCVNormalizer → ContractParquetStore
         │
         ▼ [Parquet write: data/processed/contracts/{asset}/{ticker}.parquet]
         │
         ▼ [Parquet read via load_curve()]
Layer 5: FuturesCurveBuilder.build(asset, observation_date) → FuturesCurve
         │
         ▼
Layer 5: TermStructureAnalyzer.analyze(curve, continuous_close) → TermStructureSnapshot
         │
         ▼
Layer 8: Dashboard Page 6 renders term structure charts and KPI row
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
Metadata (stored as DataFrame attrs — not preserved by Parquet):
  asset           str       # e.g., "gold"  — re-populated by DataLoader.load()
  source          str       # e.g., "parquet"
  continuous      bool      # True for continuous series
Invariants:
  No duplicate index entries
  OHLC consistency violations logged as WARNING (strict_ohlc=False for Yahoo Finance)
```

### FeatureSpec

```
Type: dataclass
Fields:
  indicator_name  str             # e.g., "ema"
  parameters      Dict[str, Any]  # e.g., {"period": 50}
  column_name     str             # e.g., "ema_50"
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
Column naming convention: {indicator_name}_{primary_parameter}
```

### RawSignal / PositionSignal

```
RawSignal:
  Type: pandas.Series, float64
  Constraint: No look-ahead. Values at index t use only Close[t] and earlier.

PositionSignal:
  Type: pandas.Series, int8 or float64
  Values: +1 (long), 0 (flat), -1 (short)
  Constraint: Same no-look-ahead constraint as RawSignal.
```

### ContractMetadata

```
Type: dataclass
Fields:
  ticker           str    # Canonical ticker, e.g. 'GCZ24' (no exchange suffix)
  asset            str    # Platform identifier, e.g. 'gold'
  contract_root    str    # CME root symbol, e.g. 'GC'
  contract_month   int    # Delivery month 1-12
  contract_year    int    # Delivery year (4-digit)
  expiry_date      date | None   # None in Phase 2 (no roll calendar)
  first_notice_date date | None  # None in Phase 2
  n_bars           int    # Bars downloaded (0 if not yet downloaded)
Properties:
  month_code → str   # CME month code (F=Jan, G=Feb, ... Z=Dec)
```

### CurvePoint

```
Type: dataclass
Fields:
  metadata         ContractMetadata
  close            float   # Settlement price at or nearest to observation_date
  volume           float   # May be NaN
  observation_date date    # Anchor date for curve construction
  data_date        date    # Actual date of price used (may be before observation_date)
  days_to_delivery int     # Approx days from observation_date to delivery month start
                           # Negative for expired contracts still in dataset
```

### FuturesCurve

```
Type: dataclass
Fields:
  asset            str
  observation_date date
  points           list[CurvePoint]   # Sorted nearest delivery first
Properties:
  n_points, is_empty, front_price, back_price, prices, tickers
  is_contango: back_price > front_price (False if < 2 points)
  is_backwardation: front_price > back_price (False if < 2 points)
  slope: (back_price - front_price) / (back_dtd - front_dtd)  [USD/day; NaN if < 2 points]
  spread(front_idx, back_idx): price difference between two points
```

### TermStructureRegime

```
Type: str, Enum
Values:
  CONTANGO      = "contango"       # annualized_slope_pct > threshold (default 0.5%/yr)
  BACKWARDATION = "backwardation"  # annualized_slope_pct < -threshold
  FLAT          = "flat"           # |annualized_slope_pct| <= threshold or < 2 contracts
Inherits str for JSON serialization and direct string comparison.
```

### TermStructureSnapshot

```
Type: dataclass
Fields:
  asset                  str
  observation_date       date
  regime                 TermStructureRegime
  front_price            float    # NaN if curve empty
  back_price             float    # NaN if curve empty
  n_contracts            int
  raw_slope              float    # USD/day; NaN if < 2 contracts
  annualized_slope_pct   float    # (back/front - 1) / years_to_back; NaN if < 2
  roll_yield_annualized  float    # (front - second) / second * (365/days_between)
                                  # Positive in backwardation (tailwind for longs)
                                  # NaN if < 2 contracts
  basis                  float    # continuous_close - front_price; NaN if not provided
  basis_pct              float    # basis / continuous_close; NaN if not provided
  curve                  FuturesCurve   # source curve reference
```

### MultiAssetBacktestResult

```
Type: dataclass
Fields:
  strategy_name      str
  signal_name        str
  parameters         dict[str, Any]
  assets             list[str]          # successfully backtested assets
  skipped_assets     list[str]          # assets that failed pipeline execution
  run_id             str                # YYYYMMDD_HHMMSS_portfolio_{strategy}
  executed_at        datetime.datetime  # UTC
  asset_results      dict[str, BacktestResult]  # per-asset results
  portfolio_equity_curve  pd.Series    # sum of per-asset equity curves (inner-join)
  portfolio_pnl_series    pd.Series    # sum of per-asset PnL (zero-filled)
Properties:
  n_assets, assets_with_trades, total_trades
Capital model: each asset runs with same initial capital independently.
  Portfolio equity starts at n_assets × initial_capital_per_asset.
Alignment: inner-join (intersection of all asset date ranges).
```

### PortfolioPerformanceReport

```
Type: dataclass
Fields:
  strategy_name, run_id, assets, skipped_assets
  initial_capital_per_asset   float   # USD
  initial_capital_total       float   # n_assets × initial_capital_per_asset
  portfolio_date_range        tuple[datetime.date, datetime.date]  # inner-join range
  portfolio_metrics           dict[str, float]   # total_return, cagr, sharpe, sortino,
                                                 # calmar, max_drawdown, portfolio_vol,
                                                 # n_trading_days
  asset_contributions         dict[str, float]   # fractional P&L contribution
  absolute_pnl_by_asset       dict[str, float]   # USD P&L per asset (always stable)
  per_asset_reports           dict[str, PerformanceReport]
Note: use absolute_pnl_by_asset (not asset_contributions) when |total_pnl/capital| < 1%
```

### RiskReport

```
Type: dataclass
Fields:
  portfolio_var_95/99      float   # positive USD loss magnitude (historical simulation)
  portfolio_var_95/99_pct  float   # as fraction of initial_capital_total
  portfolio_es_95/99       float   # Expected Shortfall (always >= VaR at same confidence)
  asset_var_95/99          dict[str, float]  # per-asset VaR
  avg_gross_notional_by_asset  dict[str, float]  # mean |position| over active days
  avg_net_notional_by_asset    dict[str, float]  # mean signed position over active days
  total_avg_gross_notional     float
  total_avg_net_notional       float
  portfolio_diversification_benefit  (property) sum(asset_var_99) / portfolio_var_99
VaR methodology: historical simulation on pnl_series over lookback_days (default 252).
  Returns NaN if < 20 observations.
```

### CorrelationReport

```
Type: dataclass
Fields:
  correlation_matrix         dict[str, dict[str, float]]  # full symmetric Pearson matrix
  rolling_correlations_63    dict[str, dict[str, pd.Series]]  # upper-triangle ONLY (a<b)
  rolling_correlations_126   dict[str, dict[str, pd.Series]]  # upper-triangle ONLY (a<b)
  realized_vol_by_asset      dict[str, float]   # strategy return vol (NOT price vol)
  portfolio_realized_vol     float
  avg_pairwise_correlation   float
  most_correlated_pair       tuple[str, str, float]  # alphabetically ordered
  least_correlated_pair      tuple[str, str, float]  # alphabetically ordered
Upper-triangle rolling lookup (TD-M17-A):
  rolling_correlations_63[a][b] only exists when a < b alphabetically.
  Always look up as: a, b = min(x,y), max(x,y)
Return normalization: pnl_series / initial_capital_per_asset (not equity_curve.pct_change())
```

### BacktestResult / PerformanceReport

```
BacktestResult:
  run_id, asset, trades: List[TradeRecord], equity_curve, positions, pnl_series,
  metadata: BacktestMetadata, signal_evaluation: Optional[SignalEvaluation]

PerformanceReport:
  run_id, initial_capital_usd,
  scalar_metrics: Dict[str, float]  # ~16 keys including initial_capital
  rolling_metrics: Dict[str, pd.Series]
  trade_statistics: Dict[str, Any]
  signal_metrics: Dict[str, float]   # from signal_evaluation if present
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

Data coverage: 4,100–4,150 bars per asset (2010–2026, varying by asset).

### 8.2 Contract-Level Futures (Phase 2 — Implemented)

Individual expiry contracts are obtained from Yahoo Finance using exchange-suffix API tickers.

**Ticker convention:**
- Canonical ticker (storage): `{root}{month_code}{2-digit-year}` — e.g., `GCZ24`
- yfinance API ticker: `{canonical}.{exchange_suffix}` — e.g., `GCZ24.CMX`
- Exchange suffix: `.CMX` for COMEX assets (Gold, Silver, Copper), `.NYM` for NYMEX/ICE assets (WTI, Brent, Natural Gas)
- Month codes: F(Jan) G(Feb) H(Mar) J(Apr) K(May) M(Jun) N(Jul) Q(Aug) U(Sep) V(Oct) X(Nov) Z(Dec)

Note: Brent (BZ) is ICE-listed but Yahoo Finance exposes the NYMEX-cleared version using `.NYM`. This is the correct suffix for yfinance API calls.

**Coverage:** Typically 2–3 years per contract from yfinance. Expired contracts older than this are generally unavailable. Brent contracts have historically thinner coverage than WTI or Gold.

**Asset configuration** (in `assets.yaml`):

| Asset | Root | Exchange Suffix |
|-------|------|-----------------|
| Gold | GC | CMX |
| Silver | SI | CMX |
| Copper | HG | CMX |
| WTI Crude | CL | NYM |
| Brent Crude | BZ | NYM |
| Natural Gas | NG | NYM |

---

## 9. Storage Strategy

### 9.0 Repository Structure (Current — Post Phase 2)

```
commodity_research/
│
├── config/
│   ├── config.yaml                    # System config: paths, logging, costs, sizing, mlflow
│   ├── assets.yaml                    # Per-asset metadata: multipliers, ticks, tickers,
│   │                                  #   contract_root, exchange_suffix
│   └── strategies.yaml                # Strategy parameter defaults
│
├── data/                              # All data files — never committed to git
│   ├── raw/
│   │   ├── continuous/                # Downloaded source CSVs (immutable)
│   │   └── contracts/                 # Individual contract CSVs by asset (Phase 2, immutable)
│   │       └── {asset}/
│   │           └── {ticker}.csv       # e.g., gold/GCZ24.csv
│   ├── processed/
│   │   ├── continuous/                # Canonical Parquet — one file per asset
│   │   └── contracts/                 # One Parquet + sidecar .meta.json per contract ticker
│   │       └── {asset}/
│   │           ├── {ticker}.parquet
│   │           └── {ticker}.meta.json
│   ├── runs/                          # Backtest run artifacts
│   │   └── {run_id}/
│   │       ├── params.json
│   │       ├── trades.parquet
│   │       ├── equity_curve.parquet
│   │       ├── pnl_series.parquet
│   │       ├── positions.parquet
│   │       └── metrics.json
│   └── mlruns/                        # MLflow experiment tracking (Phase 2)
│       └── {experiment_id}/           # commodity_research_{asset} experiments
│
├── src/
│   ├── core/
│   │   ├── types.py                   # All shared types (Phase 1 + Phase 2 additions)
│   │   ├── registry.py                # ABCs including PositionSizer with configure()
│   │   ├── config.py                  # Config loader with mlflow_tracking_uri,
│   │   │                              #   mlflow_experiment_prefix properties
│   │   └── logging_config.py
│   │
│   ├── data/
│   │   ├── sources/
│   │   │   ├── base.py                # ContinuousDataSource ABC
│   │   │   ├── csv.py                 # LocalCSVSource (strict_ohlc=False)
│   │   │   └── futures_contract.py    # FuturesContractSource + parse_contract_ticker()
│   │   ├── validator.py               # OHLCVValidator (strict_ohlc: bool = True)
│   │   ├── normalizer.py              # OHLCVNormalizer (clears attrs before return)
│   │   ├── store.py                   # ParquetStore
│   │   ├── loader.py                  # DataLoader (re-populates attrs after both paths)
│   │   ├── contract_store.py          # ContractStore ABC + ContractParquetStore
│   │   └── contract_loader.py         # ContractDataLoader
│   │
│   ├── research/                      # Layer 1 (unchanged)
│   ├── signal/                        # Layer 2 (unchanged)
│   │
│   ├── backtesting/
│   │   ├── engine.py                  # VectorizedBacktester (sizer param + configure call)
│   │   ├── costs.py
│   │   ├── sizing.py                  # FixedNotionalSizer + VolatilityScaledSizer
│   │   ├── trade_log.py
│   │   └── run_manager.py             # RunManager + _try_log_to_mlflow() + _sanitize_mlflow_key()
│   │
│   ├── performance/                   # Layer 4 (unchanged)
│   │
│   └── commodity/                     # Layer 5 (Phase 2 — new)
│       ├── __init__.py
│       ├── curve.py                   # FuturesCurveBuilder
│       └── term_structure.py          # TermStructureAnalyzer
│
├── dashboard/
│   ├── app.py
│   ├── components/
│   │   ├── _theme.py                  # Dark theme, inject_global_css, render_kpi_row,
│   │   │                              #   section_header, apply_base_layout, palette constants
│   │   ├── price_chart.py
│   │   ├── equity_curve_chart.py
│   │   ├── metrics_table.py
│   │   ├── signal_chart.py
│   │   └── curve_chart.py             # render_forward_curve_chart,
│   │                                  #   render_term_structure_history_chart (Phase 2)
│   └── pages/
│       ├── 1_market_overview.py
│       ├── 2_research_workbench.py
│       ├── 3_strategy_builder.py
│       ├── 4_backtest_results.py
│       ├── 5_performance_analysis.py
│       └── 6_futures_curve.py         # Phase 2
│
├── scripts/
│   ├── acquire_data.py                # Downloads continuous series CSVs
│   └── acquire_contract_data.py       # Downloads individual contract CSVs (Phase 2)
│
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_types.py
│   ├── test_data_validation.py        # OHLCVValidator with strict_ohlc tests
│   ├── test_data_loader.py
│   ├── test_indicators.py
│   ├── test_pipeline.py
│   ├── test_signal_evaluation.py
│   ├── test_signals.py
│   ├── test_backtester.py
│   ├── test_performance.py
│   ├── test_contract_data.py          # Phase 2 — ContractDataLoader etc.
│   ├── test_futures_curve.py          # Phase 2 — FuturesCurveBuilder
│   ├── test_term_structure.py         # Phase 2 — TermStructureAnalyzer
│   ├── test_volatility_sizer.py       # Phase 2 — VolatilityScaledSizer
│   └── test_mlflow_integration.py     # Phase 2 — MLflow logging
│
├── docs/
│   ├── adr/ADRs.md
│   └── implementation_notes/          # Per-module notes (M01–M13)
│
├── launch_dashboard.ps1               # Windows launcher (.venv + MLFLOW_ALLOW_FILE_STORE)
├── launch_dashboard.sh                # Mac/Linux launcher
└── .streamlit/config.toml             # Dark theme: backgroundColor=#0e1628
```

### 9.1 Storage Rules

- Raw files are immutable once written.
- Processed Parquet files are regenerated from raw on demand (idempotent normalization).
- Run artifacts are immutable once written. Reruns create new run IDs.
- File paths are never hardcoded. All paths resolved via `config.yaml` + `src/core/config.py`.
- MLflow run artifacts (parameters, metrics) duplicate a subset of the file-based artifacts. MLflow is the searchable interface; file-based storage is the authoritative source.

### 9.2 ClickHouse (Implemented — Phase 3)

ClickHouse is now available as an opt-in analytical backend. `ClickHouseStore` implements the `DataStore` ABC and is config-switchable.

```yaml
# config.yaml — switch between backends:
storage:
  backend: "parquet"     # default, unchanged behavior
  # backend: "clickhouse"   # opt-in; requires Docker container running
  clickhouse:
    host: "localhost"
    port: 8123
    database: "commodity_research"
    table_ohlcv: "ohlcv_continuous"
    connect_timeout: 10
    send_receive_timeout: 30
```

**Docker:**
```bash
docker compose up -d     # starts clickhouse/clickhouse-server:24.3-alpine
# HTTP: localhost:8123   # Native: localhost:9000
```

**Migration:**
```bash
python scripts/setup_clickhouse_schema.py
python scripts/migrate_to_clickhouse.py   # migrates all 6 assets (24,862 rows total)
```

**Current state:** 24,862 rows across 6 assets. Parquet vs ClickHouse numerical equivalence confirmed at rtol=1e-6. `storage.backend = "parquet"` remains the default — ClickHouse is opt-in. Upper layers are unchanged regardless of backend.

**Honest sizing note:** 24,862 rows does not require ClickHouse. DuckDB is the right-sized alternative for this data volume. ClickHouse is retained as a migration-seam demonstration and production-infrastructure resemblance exercise, consistent with the project's stated objective of defensible architecture. See ADR-004.

---

## 10. Signal Research Workflow

The signal research workflow follows standard institutional practice. Signal quality must be assessed before committing to a full backtest.

```
1. Load asset data
   └─ DataLoader.load(asset="gold") → NormalizedOHLCV

2. Build feature frame
   └─ FeaturePipeline.compute(ohlcv, specs=[...]) → FeatureFrame

3. Generate raw signal
   └─ SignalGenerator.generate(feature_frame) → RawSignal

4. Evaluate signal quality  ← THIS STEP PRECEDES BACKTESTING
   └─ SignalEvaluator.evaluate(raw_signal, ohlcv)
      ├─ IC    = corr(signal[t], log_return[t+1])
      ├─ ICIR  = mean(IC_rolling) / std(IC_rolling)
      └─ Decay = IC at horizons {1, 2, 5, 10, 20}

5. Construct position signal
   └─ PositionSignalConstructor.build(raw_signal, threshold=0.0) → PositionSignal

6. Run backtest
   └─ VectorizedBacktester.run(position_signal, ohlcv) → BacktestResult
      ↑ configure(ohlcv) called on sizer before simulation

7. Compute performance
   └─ PerformanceEngine.compute(backtest_result) → PerformanceReport

8. Store run
   └─ RunManager.save(backtest_result) + RunManager.save_metrics(run_id, report)
      ↳ Writes file artifacts AND logs to MLflow (best-effort)
```

### IC Interpretation Guidelines

| IC Value | Interpretation |
|----------|---------------|
| \|IC\| < 0.02 | Signal likely noise. Backtest not warranted. |
| 0.02 ≤ \|IC\| < 0.05 | Weak signal. Investigate further before backtesting. |
| \|IC\| ≥ 0.05 | Meaningful predictive content. Proceed to backtest. |
| ICIR ≥ 0.5 | Signal consistent across time. |

**Direction matters:** Negative IC (e.g., −0.35) indicates an inverse signal — predictive but in the opposite direction. Five-way classification: positive meaningful / inverse meaningful / weak positive / weak inverse / noise.

---

## 11. Backtesting Assumptions

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Signal generation time | Close[t] | Realistic end-of-day signal computation |
| Trade execution time | Open[t+1] | Eliminates look-ahead bias |
| Bar frequency | Daily | Appropriate for systematic commodity research |
| Engine type | Vectorized | Sufficient for signal research and strategy screening |
| Initial capital | $1,000,000 (default) | Starting capital account value |
| Short selling | Permitted | Futures markets support symmetric long/short |
| Direction reversal | Two trades | +1 → -1 closes long, opens short; two transaction costs |
| Open position at period end | Force-closed at Close[T] | Flagged in TradeRecord.force_closed |
| Roll handling | Not modeled | Continuous series treated as single price stream |
| Margin | Not modeled | Research platform; not execution simulator |
| Sizer configure | Called before simulation | VectorizedBacktester.run() calls sizer.configure(ohlcv) |

---

## 12. Position Sizing Model

### Phase 1 — Fixed Notional (Implemented)

```
position_size_notional = config.sizing.fixed_notional_usd  # default: $100,000
```

**Limitation:** Equal notional ≠ equal risk. Natural Gas (~60%/yr vol) with $100K notional carries 4× the risk of Gold (~15%/yr vol). Documented as accepted Phase 1 simplification.

### Phase 2 — Volatility-Scaled Sizing (Implemented)

```
realized_vol   = std(daily_returns[-lookback_days:]) * sqrt(252)   # annualized
                 capped at vol_cap (default 50%/yr)
target_notional = (target_annual_vol * current_equity) / realized_vol
position_size  = target_notional * |signal|
```

`VolatilityScaledSizer` parameters: `target_annual_vol` (default 0.01 = 1%/yr), `lookback_days` (default 63), `vol_cap` (default 0.50), `min_notional`, `max_notional`.

**Economic property:** Verified — Gold (~23%/yr vol) at $1M equity with 1%/yr target produces ~$42,567 notional vs. $100,000 fixed. Natural Gas (~60%/yr vol) produces ~$16,667. Equal vol contributions confirmed to within 5% tolerance.

**Known limitations (deferred to Phase 3):**
- TD-B: Static equity — `current_equity` is passed as initial capital throughout the simulation rather than rolling MTM equity. Fix in Phase 3 engine.
- TD-C: End-of-sample vol estimate — `configure()` is called once with the full OHLCV before simulation. The vol estimate uses the final lookback period, creating mild look-ahead bias for early bars. Fix in Phase 3 via rolling vol Series with bar_date parameter.

### Phase 3 — Risk Budgeting (Planned)

Portfolio-level risk budgeting allocates capital across strategies and assets based on risk targets and correlation structure.

---

## 13. Dashboard Architecture

The dashboard is implemented in Streamlit. It is a pure presentation layer.

**Visual theme:** Institutional dark navy (#0e1628 background, #162033 sidebar), teal-green/red P&L encoding, monospace throughout. Defined in `dashboard/components/_theme.py` and `.streamlit/config.toml`. Applied via `inject_global_css()` called at the top of every page file.

**Rules:**
- No data manipulation, computation, or business logic in dashboard code
- All data consumed through layer interfaces (function calls to Layers 0–7)
- Dashboard pages import from `src/` only; they do not access `data/` directly
- `render_kpi_row()` for structured KPI displays (HTML table — no st.metric fingerprint)
- `section_header()` for labeled section dividers
- `@st.cache_data` / `@st.cache_resource` for expensive computations
- No `use_container_width` parameter (deprecated 2025-12-31)
- No emoji in any dashboard file

### Page Map

| Page | Content | Layers Consumed | Phase | Status |
|------|---------|-----------------|-------|--------|
| 1. Market Overview | Commodity universe, latest prices, returns, volume | Layer 0 | 1 | Complete |
| 2. Research Workbench | Price charts, indicators, IC analysis, signal visualization | Layers 0, 1, 2 | 1 | Complete |
| 3. Strategy Builder | Strategy selection, parameters, backtest trigger | Layers 0, 1, 2, 3 | 1 | Complete |
| 4. Backtest Results | Trade log, equity curve, daily PnL | Layer 3 | 1 | Complete |
| 5. Performance Analysis | Risk-adjusted metrics, rolling Sharpe, IC attribution | Layers 3, 4 | 1 | Complete |
| 6. Futures Curve | Forward curve, term structure regime, roll yield, basis, history | Layers 0, 5 | 2 | Complete |
| 7. Cross-Asset Analytics | Portfolio KPIs, equity curve, attribution, VaR, correlation heatmap, rolling corr, strategy vol | Layers 4, 6, 7 | 3 | Complete |

**F-Track (Planned):** Page 7 (and all prior pages) will be replaced by the React + FastAPI workstation (F0–F15). The Streamlit dashboard remains functional as the Phase 3 reference implementation. The React frontend adds IC Gate enforcement in UI, URL-shareable state, Run Comparison, and the full commodity-intelligence screen.

### Component Organization

```
dashboard/components/
  _theme.py               — Palette constants, apply_base_layout(), inject_global_css(),
                            section_header(), render_kpi_row()
  price_chart.py          — OHLCV candlestick chart with indicator overlays
  equity_curve_chart.py   — Cumulative PnL + drawdown, rolling metrics
  metrics_table.py        — Performance metrics DataFrame display
  signal_chart.py         — Signal strength chart, IC decay bar chart
  curve_chart.py          — render_forward_curve_chart(),
                            render_term_structure_history_chart()
  correlation_heatmap.py  — render_correlation_heatmap() (6×6 annotated heatmap),
                            render_rolling_correlation_chart() (Phase 3)
```

Component rules: Pure functions returning Plotly figures. No `st.*` calls. No `src/` imports at module level (TYPE_CHECKING guard for type annotations only). Components do not import from other components.

---

## 14. Configuration Reference

### config.yaml (Current — Post Phase 3)

```yaml
paths:
  raw_data: "data/raw/continuous/"
  processed_data: "data/processed/continuous/"
  runs: "data/runs/"
  contracts_raw: "data/raw/contracts/"
  contracts_processed: "data/processed/contracts/"
  logs: "logs/"

logging:
  level: "INFO"
  format: "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
  file: "logs/platform.log"

costs:
  default_commission_usd: 5.00
  default_slippage_ticks: 1

sizing:
  method: "fixed_notional"       # fixed_notional | volatility_scaled
  fixed_notional_usd: 100000
  target_annual_vol: 0.15        # Used by VolatilityScaledSizer (15% annualized)

data:
  default_start_date: "2010-01-01"
  default_end_date: null

mlflow:
  tracking_uri: "file:./data/mlruns"
  experiment_prefix: "commodity_research"
```

### assets.yaml (Current — Post Phase 2)

```yaml
gold:
  ticker_continuous: "GC=F"
  contract_root: "GC"
  exchange_suffix: "CMX"
  exchange: "COMEX"
  currency: "USD"
  unit: "troy_oz"
  contract_multiplier: 100
  tick_size: 0.10
  tick_value: 10.00

silver:
  ticker_continuous: "SI=F"
  contract_root: "SI"
  exchange_suffix: "CMX"
  exchange: "COMEX"
  currency: "USD"
  unit: "troy_oz"
  contract_multiplier: 5000
  tick_size: 0.005
  tick_value: 25.00

copper:
  ticker_continuous: "HG=F"
  contract_root: "HG"
  exchange_suffix: "CMX"
  exchange: "COMEX"
  currency: "USD"
  unit: "lb"
  contract_multiplier: 25000
  tick_size: 0.0005
  tick_value: 12.50

wti:
  ticker_continuous: "CL=F"
  contract_root: "CL"
  exchange_suffix: "NYM"
  exchange: "NYMEX"
  currency: "USD"
  unit: "barrel"
  contract_multiplier: 1000
  tick_size: 0.01
  tick_value: 10.00

brent:
  ticker_continuous: "BZ=F"
  contract_root: "BZ"
  exchange_suffix: "NYM"
  exchange: "ICE"
  currency: "USD"
  unit: "barrel"
  contract_multiplier: 1000
  tick_size: 0.01
  tick_value: 10.00

natural_gas:
  ticker_continuous: "NG=F"
  contract_root: "NG"
  exchange_suffix: "NYM"
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

### Phase 1 — Research MVP (COMPLETE)

**Tag:** `phase-1-complete` (after M07) / `pre-phase-2-complete` (after sprint)
**Tests:** 107 passing
**Modules:** M01–M07 + Pre-Phase 2 Sprint

**Delivered:**
- End-to-end single-asset research pipeline for all 6 commodities
- All 4 signal generators operational (EMA Crossover, Momentum, RSI Reversion, Donchian)
- Vectorized backtester with file-based run tracking
- PerformanceReport with 16 scalar metrics + rolling metrics
- Dashboard pages 1–5 with dark institutional theme
- Real continuous futures data: 4,100–4,150 bars per asset (2010–2026)

### Phase 2 — Commodity Intelligence (COMPLETE)

**Tag:** `phase-2-complete` (after M13)
**Tests:** 186 passing (no regressions from Phase 1)
**Modules:** M08–M13

**Delivered:**
- Contract-level data ingestion (Yahoo Finance individual contracts, exchange suffix routing)
- `FuturesCurve` term structure snapshots with contango/backwardation properties
- `TermStructureSnapshot` with annualized slope, roll yield, basis, regime classification
- `VolatilityScaledSizer` with `configure()` protocol — equal vol contributions verified
- MLflow local experiment tracking (commodity_research_{asset} experiments)
- Dashboard Page 6: forward curve chart, dual-subplot history, 5-KPI row

### Phase 3 — Portfolio Analytics and Infrastructure (COMPLETE)

**Tag:** `phase-3-complete` (after M19)
**Tests:** 267 passing (188 after Phase 2 + 79 in Phase 3)
**Modules:** M14–M19

**Delivered:**
- M14: `MultiAssetRunner` — runs VectorizedBacktester across all 6 assets, aggregates into portfolio equity curve (inner-join alignment, $6M portfolio start for 6 × $1M assets)
- M15: `PortfolioPerformanceEngine` — portfolio Sharpe, drawdown, CAGR, attribution; `absolute_pnl_by_asset` (always-stable per-asset attribution); `save_portfolio_summary()` for portfolio persistence
- M16: `RiskEngine` — historical VaR (95/99%), Expected Shortfall, avg gross/net notional, diversification benefit (2.23× confirmed on real data)
- M17: `CorrelationEngine` — pairwise Pearson correlation matrix of strategy returns, rolling correlations (63/126-day), realized strategy vol; confirmed Gold-Silver corr 0.65, WTI-Brent 0.62 (strategy returns)
- M18: `ClickHouseStore` implementing `DataStore` ABC; ClickHouse 24.3 via Docker; 24,862 rows migrated; config-switchable (`storage.backend = "parquet"` default)
- M19: Dashboard Page 7 (Cross-Asset Analytics); `correlation_heatmap.py` component; portfolio persistence per run

**F-Track — React + FastAPI Frontend (Next):**
- F0: FastAPI serialization shell (HTTP boundary over all `src/` functions)
- F1–F8: React/TypeScript SPA — IC Gate doctrine, immutability-derived caching, type-generation chain (`types.py → Pydantic → OpenAPI → TypeScript`)
- F9–F11: Commodity Intelligence UI
- F12–F15: Portfolio UI, scale pass

---

## 16. Known Limitations

1. **Yahoo Finance roll gaps.** Continuous series are not back-adjusted. Price-level indicators spanning roll dates include artificial discontinuities. Mitigated by preferring log-return-based signals. F-track mitigation: in-house back-adjusted series from contract-level data (ADR-001 migration step 3).

2. **Vectorized backtester.** Does not simulate order routing, partial fills, margin calls, or forced liquidations. Suitable for signal research; insufficient for execution simulation.

3. **No real-time data.** Platform is entirely historical.

4. **No roll calendar.** The platform does not know when roll events occurred in the Yahoo Finance continuous series. `days_to_delivery` in `CurvePoint` uses delivery month start as proxy. Future: `config/roll_calendar.yaml` with CME roll dates.

5. **Basis is pseudo-basis.** `TermStructureAnalyzer.compute_basis()` uses the continuous front-month series as a spot proxy. Labeled "Continuous-Contract Basis" in the dashboard.

6. **Static equity in position sizing (TD-B).** `VolatilityScaledSizer` receives initial capital, not rolling MTM equity. Future fix: rolling equity passed to engine's internal sizing call.

7. **End-of-sample volatility estimate (TD-C).** `VolatilityScaledSizer.configure()` uses the final lookback window. Early bars technically sized with look-ahead vol. Future fix: rolling vol Series indexed by bar_date.

8. **Brent thin contract coverage.** Brent (BZ) typically shows 2–3 curve points in yfinance instead of 6. Dashboard Page 6 handles this gracefully.

9. **No statistical validation.** All results are full-sample in-sample. No walk-forward testing, no out-of-sample split, no inference (no Sharpe standard errors, no p-values), no multiple-testing correction. This is the defining research limitation of the platform in its current state. The `src/validation/` module is the highest-priority future extension.

10. **MLflow 3.x filesystem restriction.** `MLFLOW_ALLOW_FILE_STORE=true` required. Set programmatically and in launcher scripts. Future: HTTP tracking server eliminates this requirement.

11. **Strategy vol vs price vol.** `CorrelationEngine.realized_vol_by_asset` values (2–8%/yr for EMA 50/200) are strategy P&L vols, not commodity price vols (15–60%/yr). Labeled "Strategy Realized Vol" throughout the dashboard to prevent confusion.

12. **VaR is backward-looking.** `RiskEngine` computes VaR from realized strategy P&L history (not current positions × return scenarios). No Kupiec backtesting for VaR calibration. No margin model.

13. **No data manifests or run provenance.** `BacktestMetadata` does not record git SHA, package versions, or data hashes. This means runs are code-reproducible but not fully environment-reproducible. Future: add provenance to `BacktestMetadata`.

14. **Carry signal not implemented.** Roll yield (computed by `TermStructureAnalyzer`) never feeds a `CarrySignal` into the signal research layer. ADR-001 does not prohibit this — a carry signal derived from contract data and traded on the continuous series is architecturally compatible. This is the highest-value missing research module.

15. **Pipeline duplication (TD-M14-A).** `_build_pipeline_components()` in `MultiAssetRunner` duplicates the strategy→pipeline mapping from `3_strategy_builder.py`. Future: extract to `src/backtesting/pipeline_builder.py`.

---

## 17. Future Evolution Path

### Research Workflow Evolution

```
Phase 1: Per-asset signal research → single-asset backtest → performance report [DONE]
Phase 2: Term structure analytics + volatility sizing → regime display [DONE]
Phase 3: Portfolio construction → risk analytics → correlation → ClickHouse [DONE]
Next (Essential):   src/validation/ → walk-forward + inference + PSR/DSR
Next (High-value):  CarrySignal → commodity-native factor
Next (High-value):  In-house back-adjusted series (ADR-001 migration step 3)
Later:  Seasonality, CFTC COT, cross-sectional IC, SweepRunner, CapitalAllocator
```

### Infrastructure Evolution

```
Data:     CSV ingestion (done) → Parquet local lake (done) → ClickHouse OLAP store (done M18)
Storage:  Local filesystem (done) → ClickHouse available (done M18) → object storage (future)
Compute:  Pandas vectorized (done) → Polars/Dask for large data (future)
Tracking: File-based (done) → MLflow local (done M12) → MLflow remote server (future F-track)
Frontend: Streamlit (done M07, M13, M19) → FastAPI + React (F-track F0–F15)
Pipeline: Manual execution (done) → SweepRunner (future) → Prefect/Airflow (future)
```

### Backtesting Evolution

```
Phase 1: Vectorized engine (done — signal research)
Future:  Event-driven engine (realistic execution simulation)
Future:  Golden-master + property tests on the engine (needed before Phase 3+ refactors)
```

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
| ADR-008 | Dashboard Architecture | Superseded by FRONTEND_TDR-001 |
| ADR-009 | Run Tracking Strategy | Accepted |
| ADR-010 | Multi-Asset Research Scope and Phasing | Accepted |
