# Commodity Systematic Research Platform
## Architecture Reference Document

**Version:** 4.0
**Status:** Active — Phase 1–3 Complete. Enhancement Modules EM1–EM14 Complete. F-Track + FEP Complete. E2E Suite Complete.
**Audience:** Developers, quantitative researchers, architecture reviewers
**Last Updated:** EM14 + FEP + E2E completion (M01–M19 + EM1–EM14, 429 backend tests, 406 frontend vitest, 114 E2E)

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
13. [Dashboard and API Architecture](#13-dashboard-and-api-architecture)
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
- Alternative data ingestion (CFTC COT positioning, EIA petroleum inventory)
- Feature engineering and technical indicator computation
- Signal generation, quality evaluation, and rolling IC analysis
- Walk-forward statistical validation with Probabilistic Sharpe Ratio and Deflated Sharpe Ratio
- Systematic strategy development and backtesting under realistic execution assumptions
- Parameter sweep infrastructure for performance surface characterisation
- Performance measurement, attribution, and risk analysis
- Commodity-specific market structure analysis (term structure, contango, backwardation, roll yield, basis, PCA)
- Cross-asset correlation, regime-conditional attribution, and alternative data signal integration
- React/TypeScript research workbench with IC Gate enforcement in the UI

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
- Signal generation layer with RawSignal and PositionSignal separation
- Signal evaluation metrics: IC, ICIR, signal decay, turnover
- Vectorized single-asset backtesting engine
- Transaction cost and slippage modeling
- Fixed notional position sizing ($100,000 per signal)
- Performance metrics: 16 scalar + rolling metrics
- File-based run tracking and MLflow experiment management
- Streamlit dashboard: Market Overview, Research Workbench, Strategy Builder, Backtest Results, Performance Analysis

**Phase 2 — Commodity Intelligence (COMPLETE — M08–M13, 186 tests):**
- Contract-level futures data ingestion via Yahoo Finance individual contracts
- `FuturesCurveBuilder` producing `FuturesCurve` snapshots
- `TermStructureAnalyzer` producing `TermStructureSnapshot`
- Contango/backwardation slope, roll yield, basis, regime classification
- `VolatilityScaledSizer` with `configure()` protocol
- MLflow experiment tracking: local filesystem backend, one experiment per asset
- Dashboard Page 6: Futures Curve

**Phase 3 — Portfolio Analytics and Infrastructure (COMPLETE — M14–M19, 267 tests):**
- `MultiAssetRunner` — portfolio equity curve across all 6 assets
- `PortfolioPerformanceEngine` — Sharpe, drawdown, attribution, `absolute_pnl_by_asset`
- `RiskEngine` — historical VaR (95/99%), Expected Shortfall, notional exposure, diversification benefit
- `CorrelationEngine` — pairwise matrix, rolling 63/126-day, realized strategy vol
- `ClickHouseStore` behind `DataStore` ABC, 24,862 rows migrated, config-switchable
- `save_portfolio_summary()` with portfolio persistence per run
- Dashboard Page 7: Cross-Asset Analytics

**Enhancement Modules EM1–EM14 (COMPLETE — 429 tests):**

| Module | Key Deliverable |
|---|---|
| EM1 | Foundation: golden master tests, CI, `pipeline_builder.py` extracted, TD-M14-A closed |
| EM2 | Engine correctness: rolling MTM equity (TD-B resolved), point-in-time vol scaling (TD-C resolved) |
| EM3 | Portfolio persistence: 7 disk artifacts per run, disk-based fallback |
| EM4 | Risk analytics depth: Kupiec VaR backtesting, contribution-to-risk decomposition |
| EM5 | Statistical validation: `WalkForwardValidator`, PSR, Deflated Sharpe Ratio (scipy-free) |
| EM6 | Rolling IC endpoint: `GET /api/signals/rolling-ic` |
| EM7 | Carry signal: roll yield z-score from FuturesCurve data |
| EM8 | Regime attribution: `RegimeAttributionEngine`, conditional Sharpe/return/drawdown per regime |
| EM9 | `SweepRunner`: parameter grid expansion, async API, MLflow tagging |
| EM10 | Testing infrastructure: Hypothesis property tests, QC reports, `reproduce_run.py` |
| EM11 | Curve PCA: Level/Slope/Curvature factor decomposition |
| EM12 | WTI-Brent spread signal: Engle-Granger cointegration, numpy-only ADF |
| EM13 | Alternative data: CFTC COT positioning + EIA petroleum inventory signals |
| EM14 | Async improvements: portfolio persisting status, async regime attribution, sweep progress |

**F-Track — React + FastAPI Frontend (COMPLETE — 406 vitest, 114 E2E):**
- FastAPI serialization shell: 30+ endpoints, consistent async job pattern (POST → poll → result)
- React/TypeScript SPA with IC Gate enforcement, TanStack Query, Zustand, ECharts
- 13 screens across all platform capabilities
- Walk-forward validation tab, regime attribution panel (per-asset + Portfolio Combined), rolling IC chart
- COT and EIA data sections in Data Manager
- SQLite run index (`data/runs/index.db`) for sub-second `GET /api/runs` regardless of run count
- Comprehensive Playwright E2E suite: 114 passed / 3 skipped / 0 failed

### 2.2 Out of Scope

- Live trading, order routing, or execution simulation beyond vectorized backtesting
- Real-time or intraday data feeds
- Options, structured products, or derivatives beyond vanilla futures
- Multi-user access, authentication, or authorization (under consideration for future hosted deployment)
- Tick-level or high-frequency data analysis
- Equity, fixed income, or FX instruments

---

## 3. Assumptions and Constraints

### 3.1 Data Assumptions

1. Continuous futures series (GC=F, CL=F, SI=F, HG=F, NG=F, BZ=F) are obtained from Yahoo Finance and represent front-month contracts stitched without documented back-adjustment methodology. These series are treated as opaque vendor-provided continuous price streams. See ADR-001.

2. Yahoo Finance continuous series are NOT back-adjusted. Price discontinuities occur at roll dates. All return-based calculations must use log returns or percentage changes rather than raw price differences. Long-period price-level indicators (EMA-200, SMA-200) will include roll gaps and this is accepted as a known limitation.

3. Contract-level data (individual expiry contracts, e.g., GCZ24, CLF25) is obtained from Yahoo Finance using asset-specific exchange suffix tickers (e.g., GCZ24.CMX for COMEX contracts, CLF25.NYM for NYMEX contracts). Contract data is maintained as a separate dataset used exclusively for term structure analysis. It is never used in signal generation or backtesting.

4. `OHLCVValidator` uses `strict_ohlc=False` for all Yahoo Finance data (both continuous and contract-level). Yahoo Finance settlement prices are volume-weighted averages of the closing range and can legally fall outside the intraday High/Low. OHLC constraint flags from `QCReport` are expected artifacts for 5 of 6 assets (Gold 25, Silver 57, Copper 29, Brent 34, NatGas 1 violations; WTI 0) — these are data artifacts, not errors. The 2020-04-20 WTI negative price event (−$37.63) is genuine historical data, not a data error.

5. CFTC COT data uses the Managed Money category (`m_money_positions_long/short_all`). URL format: `dea/history/fut_disagg_txt_{year}.zip`. Requires `User-Agent: Mozilla/5.0` header. Brent has no CFTC COT coverage (ICE London, not CME). COT `percentile_rank` is on a 0–100 scale throughout the entire pipeline — frontend must NOT multiply by 100 again.

6. EIA petroleum inventory uses `WCRSTUS1` (WTI) and `WCSSTUS1` (Brent proxy). API key required (`EIA_API_KEY`). Only meaningful for WTI and Brent crude — signals for other assets are flat/zero by design.

7. Open Interest field is optional; Yahoo Finance does not provide reliable OI data for commodity futures.

### 3.2 Backtesting Assumptions

1. Signals are generated using Close[t].
2. Trades are executed at Open[t+1].
3. Bar frequency is daily.
4. The backtester is vectorized. It does not simulate an event-driven order queue, partial fills, margin calls, or forced liquidations.
5. Short selling is permitted on all assets, reflecting the symmetric long/short capability of futures markets.
6. Roll handling is not modeled. The continuous series is treated as a single uninterrupted price stream.
7. Position sizers implement the `configure(ohlcv)` protocol. `VectorizedBacktester.run()` calls `sizer.configure(ohlcv)` before the simulation loop.

### 3.3 Infrastructure Constraints

1. Single developer. Architecture prioritizes clarity and correctness over engineering throughput.
2. All data is stored on the local filesystem. No cloud storage in Phase 1, 2, or 3.
3. No paid data subscriptions. Free data sources only (Yahoo Finance, CFTC public, EIA API free tier).
4. No hardcoded credentials, API keys, or filesystem paths. Secrets via `config/local.yaml` (gitignored). Paths via `config.yaml`.
5. Python ecosystem for all `src/` analytics. React/TypeScript for the frontend.
6. FastAPI serves the HTTP boundary between the frontend and all `src/` analytics.
7. MLflow 3.x requires `MLFLOW_ALLOW_FILE_STORE=true` for local filesystem tracking. Set programmatically in `_try_log_to_mlflow()` and exported by launcher scripts.

---

## 4. Architecture Overview

The platform is organized into nine logical layers. Dependencies flow strictly downward. No layer imports from or depends on a layer above it. The FastAPI layer and React frontend consume layer outputs via clean HTTP interfaces.

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0 — DATA INFRASTRUCTURE                                  │
│  ContinuousDataSource + ContractDataSource                       │
│  COTDataLoader (CFTC) + EIADataLoader (EIA API)                 │
│  QCReport — data quality assessment per asset                   │
│  run_index.py — SQLite run index (sub-second GET /api/runs)     │
│  Storage: raw/ (CSV) → processed/ (Parquet + COT + EIA)        │
└──────────────────────────────┬──────────────────────────────────┘
                               │  NormalizedOHLCV + Alternative DataFrames
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 1 — FEATURE ENGINEERING                                  │
│  Indicator registry → FeaturePipeline → FeatureFrame            │
│  FeaturePipeline([]) valid for data-owning signals              │
└──────────────────────────────┬──────────────────────────────────┘
                               │  FeatureFrame
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 2 — SIGNAL RESEARCH                                      │
│  8 Signals: EMA, Momentum, RSI, Donchian, Carry,               │
│             WTIBrentSpread, COTPositioning, EIAInventory         │
│  SignalEvaluator: IC, ICIR, Rolling IC (EM6)                    │
│  PositionSignalConstructor → PositionSignal {+1, 0, -1}        │
└──────────────────────────────┬──────────────────────────────────┘
                               │  PositionSignal + RawSignal
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 3 — BACKTESTING ENGINE                                   │
│  VectorizedBacktester + CostModel                               │
│  PositionSizer (Fixed | VolatilityScaled) + RunManager          │
│  pipeline_builder.py — canonical 2-tuple strategy dispatch      │
│  SweepRunner — parameter grid with progress_callback (EM9+EM14) │
│  WalkForwardValidator — expanding splits with embargo (EM5)     │
└──────────────────────────────┬──────────────────────────────────┘
                               │  BacktestResult / SweepResult / ValidationReport
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 4 — PERFORMANCE AND ATTRIBUTION                          │
│  PerformanceEngine (src.performance.report)                     │
│  PortfolioPerformanceEngine                                     │
│  StatisticalValidation: PSR, DSR (scipy-free) (EM5)            │
└──────────────────────────────┬──────────────────────────────────┘
                               │  PerformanceReport / PortfolioPerformanceReport
             ┌─────────────────┴──────────────────┐
             │                                     │
┌────────────▼───────────────┐     ┌───────────────▼──────────────┐
│  LAYER 5 — COMMODITY       │     │  LAYER 6 — RISK ANALYTICS    │
│  INTELLIGENCE (Complete)   │     │  VaR 95/99, ES, Kupiec LR,  │
│  FuturesCurveBuilder        │     │  contribution-to-risk (EM4) │
│  TermStructureAnalyzer      │     └──────────────────────────────┘
│  CurvePCAEngine (EM11)      │     ┌──────────────────────────────┐
│  PC1=Level, PC2=Slope       │     │  LAYER 7 — CROSS-ASSET       │
└────────────────────────────┘     │  CorrelationEngine           │
                                   │  RegimeAttributionEngine (EM8)│
                                   └──────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  FASTAPI LAYER (F0 + EM endpoints) — COMPLETE                  │
│  Serialization shell: 30+ endpoints, async job pattern          │
│  Pydantic → OpenAPI → TypeScript schema.d.ts                   │
│  SQLite run index: GET /api/runs < 0.5s for 925+ runs          │
└──────────────────────────────┬──────────────────────────────────┘
                               │  HTTP / JSON
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 8 — PRESENTATION LAYER                                   │
│                                                                 │
│  Streamlit (Phase 1/2/3 reference — 7 pages, all complete)     │
│                                                                 │
│  React/TypeScript SPA (F-Track + FEP — COMPLETE)               │
│  IC Gate in UI, TanStack Query, Zustand, ECharts               │
│  13 screens, 406 vitest, 114 E2E passing                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Layer Responsibilities

### Layer 0 — Data Infrastructure

**Purpose:** Single source of truth for all data access. The only layer that reads from the filesystem, external APIs, or external data sources.

**Phase 1/2/3 responsibilities (implemented):**
- `ContinuousDataSource` abstraction → `LocalCSVSource` implementation
- OHLCV validation: gap detection, anomaly flagging, consistency checks (`strict_ohlc=False` for Yahoo Finance)
- Field normalization: standard column names, float64 dtypes, UTC DatetimeIndex
- `ParquetStore`: read/write normalized continuous series at `data/processed/continuous/{asset}.parquet`
- `DataLoader`: orchestrates Source → Validator → Normalizer → Store pipeline
- `FuturesContractSource`, `ContractParquetStore`, `ContractDataLoader` (Phase 2)

**Enhancement module additions:**

- `src/data/acquisition_qc.py`: `compute_qc(ohlcv, asset)` → `QCReport`. Checks: bar count, OHLC constraint violations (expected for Yahoo Finance), zero-volume days, large gap flags. Health classification: ok/warn/crit. OHLC flags are expected artifacts — not actionable errors.

- `src/data/cot_loader.py`: `COTDataLoader.load(asset)` → DataFrame. Columns: `net_speculative`, `long_specs`, `short_specs`, `percentile_rank` (0–100 scale). Brent returns empty (no CFTC coverage). `available_assets()` → list.

- `src/data/eia_loader.py`: `EIADataLoader.load(asset)` → DataFrame. `EIA_SUPPORTED_ASSETS` (public constant) = `{"wti", "brent"}`. Columns: `inventory`, `inventory_change`, `surprise`, `surprise_zscore`. Non-crude returns empty.

- `src/data/run_index.py`: SQLite run index at `data/runs/index.db`. `upsert_run()` called by `RunManager.save_metrics()` after every backtest. `query_runs(strategy, asset, limit, offset, sort_by, sort_order)` — sub-millisecond. `backfill_from_disk()` on startup (async, background). `SAFE_SORT_COLUMNS` allowlist prevents SQL injection. WAL journal mode (Windows uses DELETE journal).

**Acquisition scripts (all in `scripts/`):** `acquire_data.py`, `acquire_contract_data.py`, `acquire_cot_data.py`, `acquire_eia_data.py`, `reproduce_run.py`.

**Does NOT do:** Indicator computation, signal generation, or any analytical transformation.

---

### Layer 1 — Feature Engineering

**Purpose:** Transform normalized price data into a feature space suitable for signal research.

**Responsibilities:**
- `Indicator` ABC defining `compute(df: DataFrame) -> Series` interface
- Implementations: SMA, EMA, RSI, RVGI, Momentum
- `FeaturePipeline`: applies a list of Indicator specs to NormalizedOHLCV, returns FeatureFrame
- `FeaturePipeline([])` — empty indicators list — is valid. Data-owning signals (Carry, WTI-Brent Spread, COT, EIA) pass an empty list and own their data dependency in `generate()`.

**Does NOT do:** Signal generation, threshold decisions, or position logic.

**Output contract:** `FeatureFrame` + `List[FeatureSpec]`.

---

### Layer 2 — Signal Research

**Purpose:** Generate and evaluate signals from feature data. This is the primary research layer.

**All 8 signal generators:**

| Signal | File | Key data dependency |
|---|---|---|
| EMA Crossover | signal/ema.py | OHLCV features (EMA fast/slow) |
| Momentum | signal/momentum.py | OHLCV features (lookback return) |
| RSI Reversion | signal/rsi.py | OHLCV features (RSI period) |
| Donchian Breakout | signal/donchian.py | OHLCV features (channel period) |
| Carry | signal/carry.py | FuturesCurveBuilder.build_historical_curves() |
| WTI-Brent Spread | signal/spread.py | Continuous OHLCV, both assets |
| COT Positioning | signal/cot.py | CFTC COT Parquet (weekly, forward-filled) |
| EIA Inventory | signal/eia.py | EIA Parquet (weekly, forward-filled) |

**Signal generator interface (all signals must conform — DEV-EM7-1/2/3):**
- `@property name` — returns strategy identifier string; must be `@property`, not class attribute
- `generate(feature_frame) → pd.Series` with `series.name = self.name` set before returning
- `feature_frame.data.index` for DatetimeIndex; `feature_frame.asset` is `@property`
- Graceful degradation: flat signal (all zeros) when data unavailable, not exception

**Rolling IC (EM6):** `SignalEvaluator.compute_rolling_ic()` — raw signal, consistent with static IC definition. File: `src/signal/evaluation.py`. `SignalEvaluator(asset, ic_rolling_window)`.

**IC Gate (confirmed by E2E):** IC state is TanStack Query cache (not Zustand) — resets on full page navigation. ICGateStrip gate: `isEnabled = evaluation !== null && band !== 'noise' && band !== null`. Doctrine-with-override: backtest launch available without evaluation but override recorded in run artifacts.

**Critical rule:** IC evaluation precedes backtesting. IC is a precondition for deciding whether a backtest is warranted, not a post-hoc diagnostic.

**Output contract:** `RawSignal` (pd.Series, float64) + `PositionSignal` (pd.Series, {-1, 0, +1}).

---

### Layer 3 — Backtesting Engine

**Purpose:** Simulate strategy execution over historical data under realistic cost assumptions.

**Phase 1/2/3 responsibilities (implemented):** `VectorizedBacktester`, `CostModel`, `FixedNotionalSizer`, `VolatilityScaledSizer`, `TradeLog`, `EquityCurve`, `RunManager`, MLflow integration.

**`pipeline_builder.py` (canonical — EM1):**
Sequential if-blocks with early return, always returns 2-tuple `(indicators, signal_gen)`. This is the canonical dispatch — both `api/routers/backtests.py` and `api/routers/signals.py` use it.

**`RunManager` (confirmed EM8):**
- `load_run(run_id)` → dict: `{params, trades (pd.DataFrame), equity_curve (pd.Series), pnl_series, positions}`
- `save(backtest_result)` → Path
- `save_metrics(run_id, report)` → None; upserts into SQLite run index via `try/except` guard
- No `.load()` method (DEV-EM8-1)

**`SweepRunner` (`src/backtesting/sweep_runner.py`):**
- OHLCV loaded once before combination loop
- Each combination in try/except → `SweepRunSummary(status="failed")` on error
- MLflow tagging: `sweep_id` tag per combination for DSR trial count
- `progress_callback: Callable[[int], None] | None = None` — increments `n_complete` after each successful combination (EM14)

**`WalkForwardValidator` (`src/validation/walk_forward.py`):**
- Expanding windows: `test_size = (n - min_train_bars - embargo_bars) // n_splits`
- 5 folds, 10-bar embargo default
- PSR → DSR with MLflow n_trials correction
- scipy-free: Beasley-Springer-Moro rational approximation for normal CDF

**configure() protocol:** `VectorizedBacktester.run()` calls `self._sizer.configure(ohlcv)` before simulation begins. Rolling MTM equity (TD-B) and point-in-time vol scaling (TD-C) resolved in EM2.

**Does NOT do:** Performance metric computation, signal generation, or indicator calculation.

**Output contract:** `BacktestResult`.

---

### Layer 4 — Performance and Attribution

**Purpose:** Compute performance metrics and assemble structured reports from BacktestResult.

**Phase 1/2/3 responsibilities (unchanged):** 16 scalar metrics, rolling metrics, trade statistics, signal metrics.

**EM5 additions:**
- `src/validation/walk_forward.py`, `inference.py`, `mlflow_client.py`, `report.py`
- `PerformanceEngine` is at `src.performance.report` (DEV-EM5-2)
- `ValidationReport`: walk-forward folds, PSR, DSR, IS/OOS Sharpe, overfitting ratio

---

### Layer 5 — Commodity Intelligence (Implemented — Phase 2 + EM11)

**Purpose:** Futures term structure analysis using contract-level data.

**Phase 2 responsibilities:** `ContractDataLoader`, `FuturesCurveBuilder`, `TermStructureAnalyzer`.

**`CurvePCAEngine` (`src/commodity/pca.py` — EM11):**
- `compute(asset, n_components=3, n_contracts=4, from_date, to_date)` → `CurvePCAResult`
- Price matrix normalization: `price[t,i] / price[t,0]` (shape PCA, not level PCA)
- sklearn PCA preferred, numpy SVD fallback (mathematically equivalent)
- Gold: PC1≈100% — correct, near-constant term structure. WTI/NatGas: meaningful 3-factor decompositions.

**`FuturesCurve` attribute access (confirmed EM11):** `.prices` property → `list[float]` (primary). `.points[N].close` (fallback). (DEV-EM11)

**`FuturesCurveBuilder.build_historical_curves()` is the expensive call** — used by CarrySignal, RegimeAttributionEngine, CurvePCAEngine. Endpoints handle this two ways: `CurvePCAEngine` and `RegimeAttributionEngine` run via `asyncio.run_in_executor()` to avoid blocking Uvicorn's event loop, with 3-year and default date windows respectively to bound computation; the signal-evaluate endpoint (sync) wraps `CarrySignal` generation in a `ThreadPoolExecutor` with a hard 120-second timeout (HTTP 408 on expiry) plus a 2-year default date range when none is supplied, since a full-history Carry evaluation on Gold takes 4–40 minutes uncapped.

**Layer 5 / Layer 0 connection for basis:** `TermStructureAnalyzer.compute_basis()` receives `continuous_close` as a parameter — the analyzer never calls `DataLoader` directly. The API router is the orchestration point.

---

### Layer 6 — Risk Analytics (Implemented — Phase 3 + EM4)

**Purpose:** Portfolio-level risk measurement on a notional-aware basis.

**Phase 3 responsibilities:** Historical VaR 95/99%, ES 95/99%, notional exposure, diversification benefit.

**EM4 additions to `RiskReport` (9 new fields):**
- `n_backtesting_days`, `exceptions_95`, `exceptions_99`, `exception_rate_95`, `exception_rate_99`
- `kupiec_lr_99`, `kupiec_pvalue_99` — Kupiec LR test: p < 0.05 indicates miscalibrated VaR model
- `asset_contribution_to_vol`, `asset_contribution_to_vol_pct` — contribution-to-risk (sums to ~1.0)

**Known gap:** VaR is backward-looking (realized strategy P&L). Forward-looking VaR (current positions × return scenarios) is not implemented.

---

### Layer 7 — Cross-Asset Analytics (Implemented — Phase 3 + EM8)

**Purpose:** Multi-asset statistical analysis and regime-conditional attribution.

**Phase 3 responsibilities:** `CorrelationEngine` — pairwise Pearson matrix, rolling 63/126-day, realized strategy vol.

**`RegimeAttributionEngine` (`src/analytics/regime_attribution.py` — EM8 + TD-EM8-C):**
- Regime keys always **lowercase**: "contango", "backwardation", "flat" (DEV-EM8-3)
- `compute(backtest_result, asset, n_contracts)` → `RegimeAttributionReport`
- `compute_portfolio(portfolio_run_id, n_contracts)` → `PortfolioRegimeAttributionReport` (TD-EM8-C)
- Portfolio: ThreadPoolExecutor (6 assets parallel, ~90s)
- P&L-weighted Sharpe aggregation per regime; minimum 20 days per regime for valid statistics
- `_RunProxy`, `_TradeProxy`, `_convert_trades`, `_make_run_proxy` live in `src/analytics/` (Layer 7 owns these — no upward import to api/)

**Note on strategy vol vs price vol:** `realized_vol_by_asset` values (2–8%/yr for EMA 50/200) are strategy P&L vols, not commodity price vols (15–60%/yr). Labels must say "Strategy Realized Vol" not "Asset Volatility."

---

### Layer 8 — Dashboard

**Purpose:** Interactive presentation layer. Orchestrates user interaction and displays layer outputs.

**Rule (unchanged from Phase 1):** No data manipulation, computation, or business logic in presentation code. All computation in `src/` modules. This applies identically to Streamlit and to FastAPI route handlers.

**Streamlit dashboard (Phase 1/2/3 reference — all 7 pages functional):** The Streamlit implementation remains the working reference implementation. All pages consume `src/` functions only. No data manipulation in page code. Dark institutional theme (#0e1628 navy) applied via `inject_global_css()` from `_theme.py`.

**React/TypeScript SPA (F-Track + FEP — primary interface, COMPLETE):** All research is now conducted in the React workbench. FastAPI serves as the HTTP boundary. See Section 13 for the full API and screen inventory.

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
Layer 2: SignalGenerator.generate(feature_frame) → RawSignal (series.name = self.name)
         │
         ▼
Layer 2: SignalEvaluator.evaluate(raw_signal, ohlcv) → IC, ICIR, Decay  ← IC GATE
         │
         ▼
Layer 2: PositionSignalConstructor.build(raw_signal) → PositionSignal
         │
         ▼
Layer 3: VectorizedBacktester.run(position_signal, ohlcv) → BacktestResult
         │  ↑ sizer.configure(ohlcv) called before simulation
         │
         ├─ RunManager.save() → data/runs/{run_id}/ (7 artifacts)
         ├─ run_index.upsert_run() → data/runs/index.db
         │
         ▼
Layer 4: PerformanceEngine.compute(backtest_result) → PerformanceReport
         │  ↳ RunManager.save_metrics() → metrics.json + MLflow log
         │
         ▼
Layer 8: Streamlit pages 1–5 / React screens render PerformanceReport
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
         │       [+ Kupiec LR, contribution-to-risk (EM4)]
         │
         ├──▶ CorrelationEngine.compute() → CorrelationReport
         │       [correlation matrix, rolling correlations, strategy realized vol]
         │
         ├──▶ save_portfolio_summary() → portfolio_summary.json
         │       [includes asset_run_ids, has_regime_attribution flag]
         │
         └──▶ Layer 8: Dashboard Page 7 / React Portfolio screen
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
Layer 8: Dashboard Page 6 / React Intelligence screen renders term structure
```

### Enhancement Module Pipelines (EM5, EM9, EM13, EM8)

```
Statistical Validation (EM5):
WalkForwardValidator.validate(asset, strategy, params, n_splits=5, embargo_bars=10)
  → data/validation/{id}/validation_report.json

Parameter Sweep (EM9):
SweepRunner.run_sweep(asset, strategy, param_grid, sweep_id, progress_callback)
  → data/sweeps/{sweep_id}/sweep_result.json

Alternative Data Signals (EM13):
COT: CFTC ZIP → Managed Money positions → 52-week percentile rank (0–100)
     → data/processed/cot/{asset}.parquet → forward-filled to daily in generate()
EIA: EIA API v2 → inventory surprise z-score
     → data/processed/eia/{asset}.parquet → forward-filled to daily in generate()

Portfolio Regime Attribution (EM8 + TD-EM8-C):
RegimeAttributionEngine.compute_portfolio(portfolio_run_id)
  → ThreadPoolExecutor: 6 assets parallel (~90s)
  → P&L-weighted Sharpe aggregation per regime
  → data/regime_attribution/{job_id}/result.json
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
  OHLC constraint violations logged as WARNING (strict_ohlc=False for Yahoo Finance)
  5 of 6 assets have expected OHLC violations — not errors
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
  feature_frame.asset         → str, @property (not _asset)
Index: same DatetimeIndex as NormalizedOHLCV
Column naming convention: {indicator_name}_{primary_parameter}
```

### RawSignal / PositionSignal

```
RawSignal:
  Type: pandas.Series, float64
  series.name = self.name must be set before returning from generate()
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
  expiry_date      date | None
  first_notice_date date | None
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
  data_date        date    # Actual date of price used
  days_to_delivery int     # Approx days from observation_date to delivery month start
```

### FuturesCurve

```
Type: dataclass
Fields:
  asset            str
  observation_date date
  points           list[CurvePoint]   # Sorted nearest delivery first
Properties:
  n_points, is_empty, front_price, back_price
  prices → list[float]   # PRIMARY ACCESS PATH (DEV-EM11)
  tickers, is_contango, is_backwardation
  slope: (back_price - front_price) / (back_dtd - front_dtd)  [USD/day]
  spread(front_idx, back_idx): price difference between two points
```

### TermStructureRegime

```
Type: str, Enum
Values:
  CONTANGO      = "contango"       # annualized_slope_pct > threshold (default 0.5%/yr)
  BACKWARDATION = "backwardation"  # annualized_slope_pct < -threshold
  FLAT          = "flat"           # |annualized_slope_pct| <= threshold or < 2 contracts
str() returns lowercase value — regime dict keys are ALWAYS lowercase (DEV-EM8-3)
```

### TermStructureSnapshot

```
Type: dataclass
Fields:
  asset, observation_date, regime, front_price, back_price, n_contracts
  raw_slope              float    # USD/day; NaN if < 2 contracts
  annualized_slope_pct   float    # (back/front - 1) / years_to_back; NaN if < 2
  roll_yield_annualized  float    # Positive in backwardation (tailwind for longs)
  basis                  float    # continuous_close - front_price; NaN if not provided
  basis_pct              float    # basis / continuous_close
  curve                  FuturesCurve   # source curve reference
```

### MultiAssetBacktestResult

```
Type: dataclass
Fields:
  strategy_name, signal_name, parameters
  assets             list[str]          # successfully backtested assets
  skipped_assets     list[str]
  run_id             str                # YYYYMMDD_HHMMSS_portfolio_{strategy}
  executed_at        datetime.datetime
  asset_results      dict[str, BacktestResult]  # primary per-asset data
  portfolio_equity_curve  pd.Series    # sum of per-asset equity curves (inner-join)
  portfolio_pnl_series    pd.Series    # sum of per-asset PnL (zero-filled)
Capital model: each asset runs with same initial capital independently.
Portfolio equity starts at n_assets × initial_capital_per_asset.
Alignment: inner-join (intersection of all asset date ranges).
```

### PortfolioPerformanceReport

```
Type: dataclass
Fields:
  strategy_name, run_id, assets, skipped_assets
  initial_capital_per_asset   float
  initial_capital_total       float
  portfolio_date_range        tuple[datetime.date, datetime.date]
  portfolio_metrics           dict[str, float]   # total_return, cagr, sharpe, sortino,
                                                 # calmar, max_drawdown, portfolio_vol
  asset_contributions         dict[str, float]   # fractional P&L (unstable near zero)
  absolute_pnl_by_asset       dict[str, float]   # USD P&L per asset (always stable)
  per_asset_reports           dict[str, PerformanceReport]
Note: use absolute_pnl_by_asset (not asset_contributions) when |total_pnl/capital| < 1%
```

### RiskReport

```
Type: dataclass
Phase 3 fields:
  portfolio_var_95/99      float   # positive USD loss magnitude (historical simulation)
  portfolio_var_95/99_pct  float   # as fraction of initial_capital_total
  portfolio_es_95/99       float   # Expected Shortfall (always >= VaR)
  asset_var_95/99          dict[str, float]
  avg_gross_notional_by_asset, avg_net_notional_by_asset  dict[str, float]
  total_avg_gross_notional, total_avg_net_notional        float
  portfolio_diversification_benefit  (property) sum(asset_var_99) / portfolio_var_99

EM4 additions (9 new fields):
  n_backtesting_days       int
  exceptions_95/99         int     # actual VaR exceedances
  exception_rate_95/99     float   # exceptions / n_backtesting_days
  kupiec_lr_99             float   # likelihood ratio statistic
  kupiec_pvalue_99         float   # p < 0.05 → miscalibrated
  asset_contribution_to_vol     dict[str, float]
  asset_contribution_to_vol_pct dict[str, float]   # sums to ~1.0
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
  most_correlated_pair       tuple[str, str, float]
  least_correlated_pair      tuple[str, str, float]
Upper-triangle rolling lookup (TD-M17-A):
  Always look up as: a, b = min(x,y), max(x,y)
Return normalization: pnl_series / initial_capital_per_asset
```

### BacktestResult / PerformanceReport

```
BacktestResult:
  run_id (set by VectorizedBacktester.run() — DEV-EM9-3)
  asset, trades: List[TradeRecord], equity_curve, positions, pnl_series
  metadata: BacktestMetadata, signal_evaluation: Optional[SignalEvaluation]
  Trade attrs: .entry_date, .net_pnl (DEV-EM8-5)

PerformanceReport:
  run_id, initial_capital_usd,
  scalar_metrics: Dict[str, float]  # 16 keys including initial_capital
  rolling_metrics: Dict[str, pd.Series]
  trade_statistics: Dict[str, Any]
  signal_metrics: Dict[str, float]
```

### New contracts (Enhancement Modules)

**ValidationReport (EM5):**
```
Type: dataclass
Fields:
  validation_run_id, asset, strategy_name, parameters
  n_splits, embargo_bars
  folds: list[WalkForwardFold]
  insample_sharpe, outsample_sharpe, overfitting_ratio
  sharpe_se        # Newey-West standard error
  psr              # P[true SR > 0]
  n_trials         # from MLflow experiment (for DSR)
  sr_benchmark     # E[max SR | n_trials]
  dsr              # Deflated Sharpe Ratio
  is_significant   # dsr >= 0.95
```

**SweepResult (EM9):**
```
Type: dataclass
Fields:
  sweep_id, asset, strategy_name, param_grid
  n_combinations, n_complete (set on completion only), n_failed
  runs: list[SweepRunSummary]
```

**RegimeAttributionReport (EM8):**
```
Type: dataclass
Fields:
  run_id, asset, strategy_name, n_contracts, computation_date
  regime_metrics: dict[str, RegimeMetrics]   # keys ALWAYS lowercase
  regime_coverage: dict[str, float]
  dominant_regime: str                        # lowercase
  total_days_with_regime, total_days_in_run
```

**PortfolioRegimeAttributionReport (TD-EM8-C):**
```
Type: dataclass
Fields:
  portfolio_run_id, n_assets_computed, assets_computed
  computation_date
  portfolio_regime_metrics: dict[str, RegimeMetrics]  # P&L-weighted aggregation
  per_asset_metrics: dict[str, RegimeAttributionReport]
  dominant_regime: str
  asset_weights: dict[str, float]
```

**CurvePCAResult (EM11):**
```
Type: dataclass
Fields:
  asset, n_components, n_contracts, n_observation_dates
  explained_variance_ratio: list[float]
  cumulative_variance_ratio: list[float]
  loadings: dict[str, list[float]]       # {"PC1": [...], "PC2": [...]}
  factor_series: dict[str, list[float]]
  factor_index_epoch_ms: list[int]       # epoch-ms, aligns with factor_series
  pc_labels: list[str]
```

---

## 8. Data Sources

### 8.1 Continuous Futures (Phase 1 and 2)

| Asset | Yahoo Ticker | Exchange | Price Unit | Contract Multiplier | Tick Size | Tick Value |
|-------|-------------|----------|------------|-------------------|-----------|-----------  |
| Gold | GC=F | COMEX | USD/troy oz | 100 oz | $0.10 | $10.00 |
| Silver | SI=F | COMEX | USD/troy oz | 5,000 oz | $0.005 | $25.00 |
| Copper | HG=F | COMEX | USD/lb | 25,000 lb | $0.0005 | $12.50 |
| WTI Crude | CL=F | NYMEX | USD/barrel | 1,000 bbl | $0.01 | $10.00 |
| Brent Crude | BZ=F | ICE | USD/barrel | 1,000 bbl | $0.01 | $10.00 |
| Natural Gas | NG=F | NYMEX | USD/MMBtu | 10,000 MMBtu | $0.001 | $10.00 |

Data coverage: 4,100–4,150 bars per asset (2010–2026, varying by asset).

### 8.2 Contract-Level Futures (Phase 2 — Implemented)

Individual expiry contracts obtained from Yahoo Finance using exchange-suffix API tickers.

**Ticker convention:**
- Canonical ticker (storage): `{root}{month_code}{2-digit-year}` — e.g., `GCZ24`
- yfinance API ticker: `{canonical}.{exchange_suffix}` — e.g., `GCZ24.CMX`
- Exchange suffix: `.CMX` for COMEX assets (Gold, Silver, Copper), `.NYM` for NYMEX/ICE assets (WTI, Brent, Natural Gas)
- Month codes: F(Jan) G(Feb) H(Mar) J(Apr) K(May) M(Jun) N(Jul) Q(Aug) U(Sep) V(Oct) X(Nov) Z(Dec)

**Asset configuration (in `assets.yaml`):**

| Asset | Root | Exchange Suffix |
|-------|------|-----------------  |
| Gold | GC | CMX |
| Silver | SI | CMX |
| Copper | HG | CMX |
| WTI Crude | CL | NYM |
| Brent Crude | BZ | NYM |
| Natural Gas | NG | NYM |

### 8.3 Alternative Data (EM13)

| Source | Assets | Coverage | Notes |
|---|---|---|---|
| CFTC COT Disaggregated | Gold/Silver: 2015+ (604 wk), Copper/WTI/NatGas: 2022+ (234 wk) | Weekly (Tuesday) | Managed Money category. Brent: no coverage (ICE London). |
| EIA API v2 | WTI (WCRSTUS1), Brent proxy (WCSSTUS1) | 1982+ (2,287 wk) | Free API key required. |

---

## 9. Storage Strategy

### 9.0 Repository Structure (Current — Post EM14)

```
commodity_research/
│
├── config/
│   ├── config.yaml                    # System config: paths, logging, costs, sizing, mlflow
│   ├── assets.yaml                    # Per-asset metadata
│   ├── strategies.yaml                # All 8 strategy parameter defaults
│   └── local.yaml                     # Gitignored — EIA API key
│
├── data/                              # All data files — never committed to git
│   ├── raw/
│   │   ├── continuous/
│   │   ├── contracts/
│   │   └── cot/                       # 17 CFTC ZIP files cached (2010–2026)
│   ├── processed/
│   │   ├── continuous/
│   │   ├── contracts/
│   │   ├── cot/                       # Per-asset Parquets (percentile_rank 0–100)
│   │   └── eia/                       # Per-asset Parquets (surprise_zscore)
│   ├── runs/
│   │   ├── index.db                   # SQLite run index (WAL mode; gitignored)
│   │   └── {run_id}/                  # 7 artifacts per backtest run
│   │       ├── params.json
│   │       ├── trades.parquet
│   │       ├── equity_curve.parquet
│   │       ├── pnl_series.parquet
│   │       ├── positions.parquet
│   │       ├── metrics.json
│   │       └── portfolio_summary.json # Portfolio runs only
│   ├── sweeps/                        # {sweep_id}/sweep_result.json
│   ├── validation/                    # {id}/validation_report.json
│   ├── regime_attribution/            # {job_id}/result.json
│   └── mlruns/
│
├── src/
│   ├── core/types.py, registry.py, config.py, logging_config.py
│   ├── data/
│   │   ├── sources/, validator.py, normalizer.py, store.py, loader.py
│   │   ├── contract_store.py, contract_loader.py
│   │   ├── acquisition_qc.py          # QCReport (EM10)
│   │   ├── cot_loader.py              # COTDataLoader (EM13)
│   │   ├── eia_loader.py              # EIADataLoader, EIA_SUPPORTED_ASSETS (EM13)
│   │   └── run_index.py               # SQLite run index (TD-RUN-EXPLORER-PERF)
│   ├── signal/
│   │   ├── [ema, momentum, rsi, donchian].py
│   │   ├── carry.py (EM7), spread.py (EM12), cot.py (EM13), eia.py (EM13)
│   │   └── evaluation.py              # SignalEvaluator + compute_rolling_ic() (EM6)
│   ├── backtesting/
│   │   ├── engine.py, costs.py, sizing.py, trade_log.py, run_manager.py
│   │   ├── pipeline_builder.py        # Canonical 2-tuple strategy dispatch (EM1)
│   │   ├── multi_asset.py             # MultiAssetRunner with from_date/to_date
│   │   └── sweep_runner.py            # SweepRunner with progress_callback (EM9+EM14)
│   ├── performance/
│   │   ├── report.py                  # PerformanceEngine (import from here — DEV-EM5-2)
│   │   └── portfolio.py               # PortfolioPerformanceEngine, save_portfolio_summary()
│   ├── analytics/
│   │   └── regime_attribution.py      # RegimeAttributionEngine + _RunProxy (EM8+TD-EM8-C)
│   ├── commodity/
│   │   ├── curve.py, term_structure.py
│   │   └── pca.py                     # CurvePCAEngine (EM11)
│   ├── risk/risk_engine.py
│   └── validation/
│       ├── walk_forward.py, inference.py, mlflow_client.py, report.py (EM5)
│
├── api/
│   ├── main.py                        # Startup backfill of run_index
│   ├── models.py                      # All Pydantic models
│   └── routers/
│       ├── backtests.py               # _build_full_pipeline (all 8 strategies)
│       ├── signals.py                 # _build_signal_pipeline (all 8 strategies)
│       ├── portfolio.py, runs.py, sweeps.py, validation.py
│       ├── intelligence.py, regime_attribution.py, system.py
│
├── dashboard/
│   ├── app.py
│   ├── components/
│   │   ├── _theme.py, price_chart.py, equity_curve_chart.py
│   │   ├── metrics_table.py, signal_chart.py, curve_chart.py
│   │   └── correlation_heatmap.py
│   └── pages/
│       ├── 1_market_overview.py through 7_cross_asset_analytics.py
│
├── frontend/
│   ├── tests/e2e/                     # 11 spec files + helpers.ts
│   └── src/api/, features/, lib/
│
├── scripts/
│   ├── acquire_data.py, acquire_contract_data.py
│   ├── acquire_cot_data.py, acquire_eia_data.py (EM13)
│   └── reproduce_run.py (EM10)
│
└── tests/
    ├── fixtures/engine_golden_master.json  # n_trades=21, final_equity=1,086,124.91
    └── [429 total tests]
```

### 9.1 Storage Rules

- Raw files are immutable once written.
- Processed Parquet files are regenerated from raw on demand (idempotent normalization).
- Run artifacts are immutable once written. Reruns create new run IDs.
- File paths are never hardcoded. All paths resolved via `config.yaml` + `src/core/config.py`.
- MLflow run artifacts duplicate a subset of the file-based artifacts. MLflow is the searchable interface; file-based storage is the authoritative source.
- SQLite run index (`data/runs/index.db`) is a queryable cache. Gitignored — regenerated from disk on startup.

### 9.2 ClickHouse (Implemented — Phase 3)

ClickHouse is available as an opt-in analytical backend for OHLCV data.

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

**Current state:** 24,862 rows across 6 assets. Parquet vs ClickHouse numerical equivalence confirmed at rtol=1e-6. `storage.backend = "parquet"` remains the default.

**Honest sizing note:** 24,862 rows does not require ClickHouse. ClickHouse is retained as a migration-seam demonstration and production-infrastructure resemblance exercise. Run metadata uses the SQLite run index — ClickHouse is not involved in run tracking. See ADR-004.

---

## 10. Signal Research Workflow

```
1. Load asset data
   └─ DataLoader.load(asset="gold") → NormalizedOHLCV

2. Build feature frame
   └─ FeaturePipeline.compute(ohlcv, specs=[...]) → FeatureFrame
   Note: FeaturePipeline([]) valid — data-owning signals bypass this step

3. Generate raw signal
   └─ SignalGenerator.generate(feature_frame) → RawSignal
      series.name = self.name must be set before returning

4. Evaluate signal quality  ← IC GATE — enforced in Research Workbench UI
   └─ SignalEvaluator.evaluate(raw_signal, ohlcv)
      ├─ IC    = Pearson(signal[t], log_return[t+1])   ← raw signal, not position
      ├─ ICIR  = mean(IC_rolling) / std(IC_rolling)
      └─ Decay = IC at horizons {1, 2, 5, 10, 20 bars}
   "Configure backtest →" carries evaluation JSON to Strategy Builder via URL params

5. Construct position signal
   └─ PositionSignalConstructor.build(raw_signal, threshold=0.0) → PositionSignal

6. Run backtest
   └─ VectorizedBacktester.run(position_signal, ohlcv) → BacktestResult
      └─ run_id set by VectorizedBacktester.run() (DEV-EM9-3)

7. Statistical validation (EM5, async)
   └─ WalkForwardValidator.validate(...) → PSR, DSR

8. Store run
   └─ RunManager.save(backtest_result) + RunManager.save_metrics(run_id, report)
      ↳ Writes 7 file artifacts + upserts SQLite index + logs to MLflow (best-effort)
```

### IC Interpretation Guidelines

| IC Value | Interpretation |
|----------|---------------|
| \|IC\| < 0.02 | Signal likely noise. Backtest not warranted. |
| 0.02 ≤ \|IC\| < 0.05 | Weak signal. Investigate further before backtesting. |
| \|IC\| ≥ 0.05 | Meaningful predictive content. Proceed to backtest. |
| ICIR ≥ 0.5 | Signal consistent across time. |

**Direction matters:** Negative IC (e.g., −0.129 for EMA Crossover on Gold) indicates an inverse signal — predictive but in the opposite direction. Five-way classification: positive meaningful / inverse meaningful / weak positive / weak inverse / noise.

**Window length matters:** Alternative data signals (COT, EIA) and EMA-200 require 3Y+ date windows for non-noise IC. On 1-year windows, noise-band IC is expected — not a regression.

---

## 11. Backtesting Assumptions

| Parameter | Value | Rationale |
|-----------|-------|-----------  |
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

**Limitation:** Equal notional ≠ equal risk. Natural Gas (~60%/yr vol) with $100K notional carries 4× the risk of Gold (~15%/yr vol).

### Phase 2 — Volatility-Scaled Sizing (Implemented)

```
realized_vol   = std(daily_returns[-lookback_days:]) * sqrt(252)   # annualized
                 capped at vol_cap (default 50%/yr)
target_notional = (target_annual_vol * current_equity) / realized_vol
position_size  = target_notional * |signal|
```

`VolatilityScaledSizer` parameters: `target_annual_vol`, `lookback_days` (default 63), `vol_cap` (default 0.50), `min_notional`, `max_notional`.

**EM2 corrections (both resolved):**
- **TD-B (static equity):** RESOLVED. `VectorizedBacktester` now passes rolling MTM equity — not static initial capital.
- **TD-C (end-of-sample vol estimate):** RESOLVED. `VolatilityScaledSizer.configure()` stores rolling `_vol_series` (not scalar).

**Verified:** Gold (~23%/yr vol) at $1M equity with 1%/yr target produces ~$42,567 notional vs. $100,000 fixed. Equal vol contributions confirmed.

### Phase 3 — Risk Budgeting (Planned)

Portfolio-level risk budgeting allocates capital across strategies and assets based on risk targets and correlation structure.

---

## 13. Dashboard and API Architecture

The platform has two presentation layers: the Streamlit dashboard (Phase 1/2/3 reference implementation) and the React/TypeScript SPA (F-Track + FEP — primary interface).

**Architectural rule (unchanged):** No data manipulation, computation, or business logic in presentation code. All computation in `src/` modules. FastAPI route handlers are a serialization shell only.

### Streamlit Dashboard (Phase 1/2/3 Reference — All 7 Pages Complete)

**Visual theme:** Institutional dark navy (#0e1628 background, #162033 sidebar), teal-green/red P&L encoding, monospace throughout. Defined in `dashboard/components/_theme.py`. Applied via `inject_global_css()` called at the top of every page file.

**Rules:**
- No data manipulation, computation, or business logic in dashboard code
- `render_kpi_row()` for structured KPI displays (HTML table — no st.metric fingerprint)
- `section_header()` for labeled section dividers
- `@st.cache_data` / `@st.cache_resource` for expensive computations
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
                            render_rolling_correlation_chart()
```

Component rules: Pure functions returning Plotly figures. No `st.*` calls. No `src/` imports at module level (TYPE_CHECKING guard for type annotations only). Components do not import from other components.

### FastAPI + React/TypeScript SPA (F-Track + FEP — Primary Interface, COMPLETE)

**API endpoint surface (selected):**

| Method | Path | Description |
|---|---|---|
| POST | /api/backtests/run | Single-asset backtest (async 202) |
| GET | /api/strategies | All 8 strategies with param schemas |
| GET | /api/runs | Run list (SQLite index, <0.5s) |
| POST | /api/portfolio/run | Multi-asset portfolio (async 202, persisting status) |
| GET | /api/signals/evaluate | IC evaluation |
| GET | /api/signals/rolling-ic | Rolling IC time series (EM6) |
| POST | /api/validation/run | Walk-forward validation (async 202, EM5) |
| POST | /api/sweeps | Parameter sweep (async 202, EM9) |
| GET | /api/system/data/qc | QC report per asset (EM10) |
| GET | /api/intelligence/pca | Curve PCA (async thread pool, EM11) |
| GET | /api/system/data/cot, /data/eia | Alternative data history (EM13) |
| POST | /api/regime-attribution/compute | Async per-asset regime (EM14) |
| POST | /api/regime-attribution/compute-portfolio | Async portfolio regime (TD-EM8-C) |
| GET | /api/regime-attribution/{id}/portfolio-result | Portfolio regime result (TD-EM8-C) |

**Async job pattern (all long-running computations):**
```
POST /api/{resource}        → 202 + {id, status: "queued"}
GET  /api/{resource}/{id}/status → queued | running | [persisting] | complete | failed
GET  /api/{resource}/{id}/result → full result when complete
```
`persisting` status (portfolio only): set before disk writes, flipped to `complete` after all 7 artifacts confirmed written. Eliminates 404 race condition.

**React screen map:**

| Route | Screen |
|---|---|
| /market | Market Overview |
| /market/:asset | Asset Detail |
| /research | Research Workbench (IC Gate) |
| /backtest/new | Strategy Builder |
| /runs | Run Explorer |
| /runs/:runId | Run Detail (Overview / Signal Quality / Validation / Trades / Artifacts) |
| /runs/compare | Run Comparison |
| /intelligence | Futures Curve |
| /intelligence/compare | Curve Comparison |
| /intelligence/pca | Curve PCA |
| /sweeps | Sweep Explorer |
| /portfolio | Portfolio Analytics |
| /system | Data Manager |

**Strategy registration — two required locations (DEV-EM7-5):**
1. `api/routers/signals.py` — `_build_signal_pipeline()` AND catalog entry
2. `api/routers/backtests.py` — `_build_full_pipeline()`

Both must be updated when adding a strategy. Missing either produces `400 UNKNOWN_STRATEGY`.

---

## 14. Configuration Reference

### config.yaml (Current — Post EM14)

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

storage:
  backend: "parquet"     # default; "clickhouse" opt-in after docker-compose up
  clickhouse:
    host: "localhost"
    port: 8123
    database: "commodity_research"
    table_ohlcv: "ohlcv_continuous"
    connect_timeout: 10
    send_receive_timeout: 30
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

### strategies.yaml (Current — All 8 Strategies)

```yaml
ema_crossover:
  fast_period: 50
  slow_period: 200

momentum:
  lookback_period: 20
  z_score_window: 63

donchian_breakout:
  channel_period: 20

rsi_reversion:
  period: 14
  oversold_threshold: 30
  overbought_threshold: 70

carry:
  threshold: 0.0
  n_contracts: 4

wti_brent_spread:
  lookback: 63
  threshold: 1.0

cot_positioning:
  upper_pct: 80.0
  lower_pct: 20.0

eia_inventory:
  threshold: 1.0
```

### config/local.yaml (Gitignored)

```yaml
eia:
  api_key: your_key_here
```

---

## 15. Phase Roadmap

### Phase 1 — Research MVP (COMPLETE)

**Tag:** `phase-1-complete` | **Tests:** 107
M01–M07: end-to-end single-asset research pipeline, 4 signal generators, vectorized backtester, 16 scalar performance metrics, dashboard pages 1–5, real continuous futures data for all 6 assets.

### Phase 2 — Commodity Intelligence (COMPLETE)

**Tag:** `phase-2-complete` | **Tests:** 186
M08–M13: contract-level data ingestion, FuturesCurve term structure, contango/backwardation/flat regime classification, roll yield, basis, VolatilityScaledSizer with configure() protocol, MLflow tracking, dashboard page 6.

### Phase 3 — Portfolio Analytics and Infrastructure (COMPLETE)

**Tag:** `phase-3-complete` | **Tests:** 267
M14–M19: MultiAssetRunner, PortfolioPerformanceEngine, RiskEngine (VaR/ES), CorrelationEngine, ClickHouseStore (opt-in), portfolio persistence, dashboard page 7.

### Enhancement Modules EM1–EM14 (COMPLETE)

**Final tag:** `EM14-complete` | **Tests:** 429

| Tag | Tests | Key deliverable |
|---|---|---|
| EM1-complete | 334 | Foundation: golden master, CI, pipeline_builder.py, epoch-ms fix |
| EM2-complete | 339 | Engine correctness: rolling MTM equity, point-in-time vol |
| EM3-complete | 342 | Portfolio persistence: 7 disk artifacts, disk fallback |
| EM4-complete | 348 | Risk depth: Kupiec LR, contribution-to-risk |
| EM5-complete | 369 | Statistical validation: PSR, DSR (scipy-free), walk-forward |
| EM6-complete | 376 | Rolling IC endpoint |
| EM7-complete | 382 | Carry signal (Gold structural contango confirmed correct) |
| EM8-complete | 388 | Regime attribution engine |
| EM9-complete | 396 | SweepRunner with async API and MLflow tagging |
| EM10-complete | 402 | Hypothesis property tests, QCReport, reproduce_run.py |
| EM11-complete | 407 | Curve PCA (Gold PC1=100%, WTI meaningful 3-factor) |
| EM12-complete | 411 | WTI-Brent spread (ADF p=0.0030, cointegrated) |
| EM13-complete | 424 | CFTC COT + EIA inventory signals |
| EM14-complete | 429 | Async regime, portfolio persisting status, sweep progress, mypy CI |

**Golden master:** `tests/fixtures/engine_golden_master.json` — n_trades=21, final_equity=1,086,124.91. Locked.

### F-Track + FEP — React + FastAPI Frontend (COMPLETE)

**Tags:** `FEP-complete` | **Tests:** 406 vitest, 114 E2E passed / 3 skipped / 0 failed

F0: FastAPI shell. F1–F18: React/TypeScript SPA, IC Gate, 9 initial screens. FEP: All deferred frontend work. TD-EM8-C: Portfolio regime frontend. E2E: 117 Playwright tests.

---

## 16. Known Limitations

1. **Yahoo Finance OHLC violations are expected data artifacts.** Settlement prices are VWAP-based. QCReport flags for 5 of 6 assets are correct and not actionable (Gold 25, Silver 57, Copper 29, Brent 34, NatGas 1; WTI 0). `strict_ohlc=False` is the correct setting.

2. **Yahoo Finance roll gaps.** Continuous series are not back-adjusted. Price-level indicators spanning roll dates include artificial discontinuities. Mitigated by preferring log-return-based signals.

3. **Vectorized backtester.** Does not simulate order routing, partial fills, margin calls, or forced liquidations. Suitable for signal research; insufficient for execution simulation.

4. **No real-time data.** Platform is entirely historical.

5. **No roll calendar.** The platform does not know when roll events occurred in the Yahoo Finance continuous series. `days_to_delivery` uses delivery month start as proxy.

6. **Basis is pseudo-basis.** `TermStructureAnalyzer.compute_basis()` uses the continuous front-month series as a spot proxy. Labeled "Continuous-Contract Basis" throughout.

7. **COT percentile_rank is 0–100 scale** throughout the entire pipeline. Frontend must not multiply by 100 again — double-multiply produces values like 3137.

8. **Alternative data signals produce noise-band IC on 1-year windows.** COT and EIA require 3Y+ windows for non-noise IC. This is expected behavior, not a regression.

9. **Carry signal flat on Gold.** Gold is structurally in contango — carry signal near-flat (0 long, 443 short, 3705 flat on full history). Carry is more meaningful for energy and agricultural commodities with regime-switching term structure.

10. **WTI-Brent Spread: Brent leg not in P&L.** The spread signal is a single-asset approximation. True spread P&L requires a multi-asset engine.

11. **Regime attribution latency.** ~30–90 seconds per asset (`build_historical_curves` cost). Portfolio Combined takes ~90 seconds via ThreadPoolExecutor.

12. **Gold PCA EVR collapse.** PC1=100% is correct for Gold's near-constant term structure over 2–3yr windows.

13. **OI-EM5-1: Features computed on full history before fold splitting.** WalkForwardValidator slices the pre-computed signal by date. Acceptable for slow-moving indicators.

14. **Brent has no CFTC COT data** (ICE London, not CME). COT signal on Brent returns flat — correct.

15. **No statistical inference in Phase 1–3 full-sample backtests.** EM5 walk-forward validation provides out-of-sample correction.

16. **No data manifests or run provenance recording.** `BacktestMetadata` does not record git SHA or package versions. `scripts/reproduce_run.py` provides equity curve hash verification as a proxy.

17. **MLflow 3.x filesystem restriction.** `MLFLOW_ALLOW_FILE_STORE=true` required. Set programmatically and in launcher scripts.

18. **Strategy vol vs price vol.** `CorrelationEngine.realized_vol_by_asset` values (2–8%/yr for EMA 50/200) are strategy P&L vols, not commodity price vols (15–60%/yr).

---

## 17. Future Evolution Path

### Research Workflow Evolution

```
Phase 1: Per-asset signal research → single-asset backtest → performance report [DONE]
Phase 2: Term structure analytics + volatility sizing → regime display [DONE]
Phase 3: Portfolio construction → risk analytics → correlation → ClickHouse [DONE]
EM1–EM14: Engine correctness, validation, alternative data, async infrastructure [DONE]
F-Track + FEP: React/TypeScript research workbench, IC Gate, 13 screens [DONE]
E2E: 114 Playwright tests, full platform coverage [DONE]
Future (high-value):
  - In-house back-adjusted continuous series from contract data (ADR-001 migration step 3)
  - Seasonality signal (calendar-based commodity factor)
  - Cross-sectional IC (rank signals across assets)
  - CapitalAllocator (risk-budgeted multi-strategy allocation)
  - Multi-user deployment with authentication and data isolation
```

### Infrastructure Evolution

```
Data:     CSV (done) → Parquet (done) → ClickHouse OLAP (done M18, opt-in)
Runs:     File artifacts (done) → SQLite index (done TD-RUN-EXPLORER-PERF)
Tracking: File-based (done) → MLflow local (done M12) → MLflow remote (future)
Frontend: Streamlit (done, reference) → React + FastAPI (done F-Track + FEP)
Testing:  pytest (429) + hypothesis (EM10) + vitest (406) + Playwright E2E (114)
Hosting:  Local (current) → Render/Vercel deployment (under consideration)
Auth:     Single-user (current) → JWT-based multi-user (under consideration)
```

### Backtesting Evolution

```
Phase 1: Vectorized engine (done — signal research)
EM1:     Golden-master + property tests on the engine (done)
EM2:     Rolling equity + point-in-time vol (done)
Future:  Event-driven engine (realistic execution simulation)
Future:  Roll-cost modeling (requires roll calendar)
```

---

## 18. ADR Index

All Architecture Decision Records are maintained in `ADRs_final.md`.

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | Continuous vs. Contract-Level Futures Data | Accepted |
| ADR-002 | Signal Timing Convention (Close[t] → Open[t+1]) | Accepted |
| ADR-003 | Vectorized Backtesting Engine | Accepted |
| ADR-004 | Storage Strategy: Parquet + ClickHouse + SQLite Run Index | Accepted |
| ADR-005 | Position Sizing Methodology | Accepted |
| ADR-006 | FeatureFrame and FeatureSpec Design | Accepted |
| ADR-007 | Signal Research Layer: RawSignal, PositionSignal, IC Evaluation | Accepted |
| ADR-008 | Dashboard Architecture | Superseded by FRONTEND_TDR-001 |
| ADR-009 | Run Tracking Strategy | Accepted |
| ADR-010 | Multi-Asset Research Scope and Phasing | Accepted |
| ADR-011 | Statistical Validation Layer (Walk-Forward + PSR/DSR) | Accepted |
| ADR-012 | Alternative Data Integration (COT + EIA) | Accepted |
| ADR-013 | Async Job Pattern for Long-Running Computations | Accepted |
| ADR-014 | Signal Generator Interface Standards | Accepted |
