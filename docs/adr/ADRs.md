# Architecture Decision Records
## Commodity Systematic Research Platform

**Format:** Each ADR documents a single architectural decision with context, rationale, alternatives considered, and migration path.
**Status values:** Proposed | Accepted | Superseded | Deprecated
**Last Updated:** EM14 + FEP + E2E completion (M01–M19 + EM1–EM14, 429 tests)

---

## ADR-001 — Continuous vs. Contract-Level Futures Data

**Status:** Accepted
**Layers Affected:** Layer 0 (Data Infrastructure), Layer 5 (Commodity Intelligence)

### Context

Commodity futures markets do not have a single continuous price series. Each commodity is traded as a series of individual contracts with fixed expiry dates (e.g., CLN26 = WTI Crude August 2026). To perform long-horizon strategy research and backtesting, practitioners must either use individual contract data and handle rolls explicitly, or use a pre-constructed continuous series that stitches contracts together.

The two approaches serve different analytical purposes:
- Continuous series: signal generation, indicator computation, backtesting
- Individual contract series: term structure analysis, contango/backwardation detection, roll yield calculation, basis analysis, carry signal generation

These cannot be combined without careful design. A single price stream cannot simultaneously serve both purposes accurately.

### Decision

Maintain two separate datasets:

**A. Continuous Futures Series** (Phase 1, 2, 3):
- Obtained from Yahoo Finance (GC=F, CL=F, SI=F, HG=F, NG=F, BZ=F)
- Used exclusively for: feature engineering, signal generation, backtesting, performance analytics
- Roll methodology: undocumented. Treated as opaque vendor-provided continuous price stream.
- Known limitation: not back-adjusted. Roll gaps will appear at contract transition dates.

**B. Contract-Level Series** (Phase 2 — Implemented):
- Individual contract tickers in canonical format (e.g., GCZ24) stored without exchange suffix
- yfinance API access uses exchange-suffix tickers (e.g., GCZ24.CMX for COMEX, CLF25.NYM for NYMEX/ICE)
- Brent (BZ) is ICE-listed but Yahoo Finance exposes the NYMEX-cleared version; `.NYM` is the correct suffix
- Used for: futures curve construction, term structure analytics, carry signal generation (EM7), curve PCA (EM11)
- Never used directly in backtesting (Carry and WTI-Brent Spread own their data dependency in `generate()`)

The `DataSource` abstraction in Layer 0 implements both `ContinuousDataSource` and `ContractDataSource` as separate implementations of the same base class. Upper layers never need to know which source they are working with once data is normalized.

The basis calculation in `TermStructureAnalyzer.compute_basis()` is the only point where the two pipelines interact. The continuous close is provided as a parameter to the analyzer; the analyzer never calls `DataLoader` directly. The API router is the orchestration point.

### Alternatives Considered

**Option A: Build back-adjusted continuous series from contract-level data.**
*Rejected for Phase 1.* Requires individual contract data, roll calendar, and back-adjustment methodology decision (Panama vs. ratio). Significant upfront complexity for a research MVP. Appropriate for a future phase.

**Option B: Use only continuous series for everything, including term structure.**
*Rejected.* A continuous series conflates prices from different contracts and cannot reconstruct the actual term structure at any given date.

**Option C: Use Yahoo Finance data with Panama back-adjustment applied in-house.**
*Deferred.* Would require identifying roll dates, which are not documented. Reverse-engineering roll dates from price discontinuities is feasible but adds complexity.

### Consequences

**Positive:**
- Clean separation between systematic strategy research and commodity structure analysis
- Reflects institutional practice
- Term structure analysis uses accurate individual contract prices
- Carry signal correctly uses contract-level roll yield (EM7)

**Negative:**
- Continuous series roll gaps affect price-level indicators computed across roll dates
- Phase 1 and Phase 2 PnL calculations do not account for roll costs explicitly
- Two data ingestion pipelines to maintain

### Implementation Notes (Phase 2)

- `strict_ohlc=False` applied to all Yahoo Finance data (both continuous and contract-level). Settlement prices can legally fall outside intraday High/Low range. The 2020-04-20 WTI event (−$37.63) is genuine historical data.
- OHLC constraint flags in QCReport are expected artifacts for 5 of 6 assets — not actionable errors.
- Brent contract coverage from yfinance is historically thinner than WTI or Gold. Dashboard and API handle this gracefully.

### Future Migration Path

1. ~~Phase 2: Add `ContractDataSource` and contract-level Parquet ingestion.~~ **DONE (M08)**
2. Phase 3 or later: Identify Yahoo Finance roll dates from price discontinuities; flag roll-date returns in continuous series. No roll calendar implemented.
3. Phase 3 or later: Construct in-house back-adjusted series from individual contracts using a defined roll methodology (Panama additive or ratio multiplicative), replacing Yahoo Finance continuous series for backtesting to eliminate roll gap artifacts.

---

## ADR-002 — Signal Timing Convention (Close[t] → Open[t+1])

**Status:** Accepted
**Layers Affected:** Layer 2 (Signal Research), Layer 3 (Backtesting Engine)

### Context

Backtesting engines can introduce look-ahead bias if the price used to generate a signal and the price at which the trade is executed are not separated in time.

### Decision

- Signals are generated using data available at Close[t].
- Trades are executed at Open[t+1].
- This convention is enforced as an architectural constraint in `VectorizedBacktester`.

The shift is implemented by aligning PositionSignal[t] with OHLCV[t+1].open during backtesting. The `VectorizedBacktester` is the single place where this shift is applied.

### Alternatives Considered

**Option A: Signal at Close[t], execute at Close[t] (same bar).** *Rejected.* Look-ahead bias.

**Option B: Signal at Close[t-1], execute at Open[t].** *Equivalent but conceptually confusing.*

**Option C: Signal at Close[t], execute at Close[t+1].** *Overly conservative.*

### Consequences

- Eliminates the most common source of look-ahead bias in daily backtesting
- Consistent with standard practice in institutional systematic research on daily commodity futures
- Golden master (n_trades=19, final_equity=1,108,823.88) locked to this convention — any engine change breaks this test intentionally

### Future Migration Path

In Phase 3 or later, if execution quality analysis is needed, the `CostModel` can be extended to model VWAP or implementation shortfall relative to Open[t+1]. The BacktestEngine interface does not need to change.

---

## ADR-003 — Vectorized Backtesting Engine

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine)

### Context

Backtesting engines fall into two architectural categories: vectorized (fast, simple) and event-driven (realistic but complex). The choice determines how realistic results are and how complex the implementation is.

### Decision

Phase 1 and Phase 2 use a vectorized backtesting engine (`VectorizedBacktester`).

The engine is isolated behind the `BacktestEngine` abstract interface. `VectorizedBacktester` is the implementation. The interface contract (input: PositionSignal + OHLCV; output: BacktestResult) is engine-agnostic.

### Alternatives Considered

**Option A: Event-driven engine from Phase 1.** *Rejected.* Significantly more complex for a single-developer research platform. Primary risk is building it incorrectly and introducing subtle execution simulation errors.

**Option B: Third-party framework (Zipline, Backtrader, vectorbt).** *Rejected for Phase 1/2.* Reduces architectural transparency. Precludes custom cost model and sizer integration.

### Consequences

**Positive:** Simple to implement correctly. Fast. Sufficient for signal research and screening.

**Negative:** Cannot model partial fills, margin calls, or position-level order effects.

### Implementation Notes (confirmed EM2)

- `VectorizedBacktester.__init__()` accepts `sizer: PositionSizer | None = None` for dependency injection.
- `VectorizedBacktester.run()` calls `self._sizer.configure(ohlcv)` before the simulation loop.
- Internal attribute is `self._sizer`.
- `run()` sets `BacktestResult.run_id` — use `result.run_id` directly (DEV-EM9-3).
- Rolling MTM equity (TD-B) and point-in-time volatility scaling (TD-C) resolved in EM2.

### Future Migration Path

Implement `EventDrivenBacktester` as an alternative `BacktestEngine` implementation. Strategy logic and performance computation remain unchanged. Migration is confined to Layer 3.

---

## ADR-004 — Storage Strategy: Parquet + ClickHouse + SQLite Run Index

**Status:** Accepted
**Layers Affected:** Layer 0 (Data Infrastructure)

### Context

The platform requires persistent storage for raw data, normalized research data, backtest run artifacts, alternative data (COT, EIA), and run metadata queryable at sub-second speed regardless of run count.

### Decision

**Phase 1 and 2 — File-based storage (Implemented):**
- Raw data: CSV in `data/raw/` (immutable after download)
- Processed data: Parquet in `data/processed/` (idempotent regeneration)
- Run artifacts: Parquet + JSON in `data/runs/{run_id}/`
- Experiment tracking: MLflow local filesystem at `data/mlruns/`

**Alternative data (EM13 — Implemented):**
- `data/processed/cot/{asset}.parquet` — CFTC COT Managed Money, percentile_rank 0–100
- `data/processed/eia/{asset}.parquet` — EIA inventory surprise z-scores

**SQLite run index (TD-RUN-EXPLORER-PERF — Implemented):**
- `data/runs/index.db` (WAL mode; Windows uses DELETE journal)
- `upsert_run()` called by `RunManager.save_metrics()` after every backtest
- `query_runs(strategy, asset, limit, offset, sort_by, sort_order)` — sub-millisecond
- `SAFE_SORT_COLUMNS` allowlist prevents SQL injection on dynamic ORDER BY
- `backfill_from_disk()` on startup (async, background) — idempotent
- Performance: GET /api/runs 30s → 0.45s first request, 0.073s subsequent
- Gitignored — regenerated from disk artifacts

**Phase 3 — ClickHouse as analytical query layer (Implemented — opt-in):**
- `ClickHouseStore` implements `DataStore` ABC
- Config-switchable: `storage.backend: "parquet"` (default) or `"clickhouse"`
- 24,862 OHLCV rows migrated; equivalence confirmed at rtol=1e-6
- Run metadata uses SQLite index, not ClickHouse

**DuckDB:** Available for local development exploration via queries over Parquet. Not a production target.

### Alternatives Considered

**Option A: DuckDB as Phase 3 analytical store.** *Not chosen as primary.* Retained for development utility. ClickHouse chosen for production infrastructure resemblance.

**Option B: PostgreSQL with TimescaleDB.** *Rejected.* TimescaleDB targets operational OLAP; ClickHouse more appropriate for columnar analytical queries.

**Option C: ClickHouse for run metadata too.** *Rejected.* ClickHouse requires Docker and adds infrastructure complexity. SQLite is the correct right-sized solution for run metadata lookup — requires no additional infrastructure and persists alongside Parquet files on the same disk.

### Consequences

- `DataStore` abstraction allows backend switching without changing upper layers
- DuckDB available as development utility throughout all phases
- MLflow `data/mlruns/` covered by the existing `/data/` gitignore pattern

### Implementation Notes (Phase 2 + TD-RUN-EXPLORER-PERF)

- `ContractParquetStore` writes `.meta.json` sidecar alongside each Parquet for `ContractMetadata` persistence.
- `OHLCVNormalizer.normalize()` clears `result.attrs = {}` before returning to prevent pyarrow UserWarning. `DataLoader.load()` re-populates `asset`, `source`, `continuous` attrs after both fast and slow paths.
- MLflow 3.x requires `MLFLOW_ALLOW_FILE_STORE=true`. Set via `os.environ.setdefault()` in `_try_log_to_mlflow()`.
- COT `percentile_rank` is 0–100 throughout the entire pipeline — acquisition → storage → API → frontend. Frontend must not multiply by 100 again.

### Future Migration Path

1. ~~Phase 1/2: `ParquetStore` only.~~ **DONE**
2. ~~Phase 2: MLflow logging.~~ **DONE (M12)**
3. ~~Phase 3: `ClickHouseStore` implementing the `DataStore` ABC.~~ **DONE (M18)**
4. ~~Run metadata: SQLite index for sub-second GET /api/runs.~~ **DONE (TD-RUN-EXPLORER-PERF)**

---

## ADR-005 — Position Sizing Methodology

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine)

### Context

Position sizing determines how much notional or risk is allocated to each signal. The sizing model significantly affects backtest results, especially when comparing across assets with different volatility profiles.

### Decision

**Phase 1 — Fixed Notional Sizing (Implemented):**
Each signal receives a fixed USD notional exposure (default: $100,000). `FixedNotionalSizer(notional_usd=...)`.

**Phase 2 — Volatility-Scaled Sizing (Implemented):**
Position size is scaled to target a fixed annualized volatility contribution per asset.
```
realized_vol   = std(daily_returns[-lookback_days:]) * sqrt(252)   [annualized, capped at vol_cap]
target_notional = (target_annual_vol * current_equity) / realized_vol
```
`VolatilityScaledSizer(target_annual_vol, lookback_days, vol_cap, min_notional, max_notional)`.

The `PositionSizer` ABC provides a `configure(ohlcv)` no-op hook. `VectorizedBacktester.run()` calls `sizer.configure(ohlcv)` before the simulation loop.

**EM2 — Engine Correctness (Resolved):**
- TD-B (static equity): resolved. `VectorizedBacktester` passes rolling MTM equity — not static initial capital.
- TD-C (end-of-sample vol estimate): resolved. `configure()` stores rolling `_vol_series` (not scalar).

**Phase 3 — Portfolio Analytics (Implemented — note on scope):**
Phase 3 implemented `MultiAssetRunner` (M14), `PortfolioPerformanceEngine` (M15), `RiskEngine` (M16), and `CorrelationEngine` (M17). Risk *budgeting* (CapitalAllocator) and portfolio *optimization* were not implemented — deferred beyond Phase 3. The portfolio equity curve is the sum of independent per-asset equity curves with no active capital allocation.

### Implementation Notes (Phase 2 — confirmed EM2)

- The ABC method is `compute_size(signal, asset, equity)` not `size(signal, equity)`. `VolatilityScaledSizer` implements `compute_size()` as a bridge delegating to internal `size()`.
- `FixedNotionalSizer` constructor: `notional_usd=` parameter name (not `notional=`).
- `configure()` placed before `trade_log.build()` in the vectorized engine.
- Vol-scaled verified: Gold (23.49%/yr vol) at $1M equity, 1%/yr target → $42,567 notional vs $100,000 fixed. Equal vol contributions confirmed.

### Future Migration Path

The `PositionSizer` class in Layer 3 implements sizing as a pluggable component. A future `CapitalAllocator` adds risk-budgeted portfolio sizing across assets, choosing allocation weights based on correlation structure and risk targets.

---

## ADR-006 — FeatureFrame and FeatureSpec Design

**Status:** Accepted
**Layers Affected:** Layer 1 (Feature Engineering), Layer 2 (Signal Research)

### Context

The Research Layer must provide a structured, reproducible way to compute, name, and track indicator columns. Without explicit naming conventions and metadata tracking, a DataFrame with many indicator columns becomes ambiguous.

### Decision

**FeatureFrame:** A thin Python class wrapping a pandas DataFrame. Provides a named type for function signatures, enforced access to feature_specs, and a controlled surface for adding properties.

Column naming convention: `{indicator_name}_{primary_parameter}` (e.g., `ema_50`, `rsi_14`). Enforced by the Indicator base class `column_name` property.

`FeaturePipeline([])` — empty indicators list — is valid for signals that own their data dependency (Carry, WTI-Brent Spread, COT, EIA). These signals pass an empty list and load their own data directly in `generate()`.

**FeatureSpec:** A dataclass recording `{indicator_name, parameters, column_name, asset, computed_at}` for each feature in the FeatureFrame. Serialized with every backtest run artifact.

**FeaturePipeline:** Accepts a list of Indicator instances and produces a FeatureFrame.

### Consequences

- Column naming convention enforced by the Indicator base class
- FeatureSpec list serialized with every backtest run for reproducibility
- FeaturePipeline([]) extending support to data-owning signals without structural changes (EM7, EM12, EM13)

### Future Migration Path

If the feature space grows beyond ~30–50 columns, formalize into a lightweight feature store with persistent caching: `data/processed/features/{asset}_{feature_hash}.parquet`.

---

## ADR-007 — Signal Research Layer: RawSignal, PositionSignal, and IC Evaluation

**Status:** Accepted
**Layers Affected:** Layer 2 (Signal Research), Layer 4 (Performance and Attribution)

### Context

Most retail backtesting platforms conflate signal generation and position sizing. Institutional systematic research separates these steps: a signal is evaluated for predictive content before it is committed to a backtest.

### Decision

**RawSignal:** Continuous float-valued `pd.Series`. Represents raw conviction output before thresholding. `series.name = self.name` must be set before returning from `generate()`. This is the `@property name` of the SignalGenerator, not a class attribute (DEV-EM7-1/2).

**PositionSignal:** Integer or fractional Series {+1, 0, -1} derived from RawSignal by thresholding.

**Signal Evaluation:** IC = Pearson correlation(RawSignal[t], log_return[t+1]) — computed on the raw signal, not the position signal. ICIR = rolling_mean(IC) / rolling_std(IC). Decay at horizons {1, 2, 5, 10, 20 bars}.

**IC Gate (confirmed by E2E — updated from original spec):** IC state in the Research Workbench is managed by TanStack Query cache, not Zustand. Cache resets on full page navigation (`page.goto()`). ICGateStrip condition: `isEnabled = evaluation !== null && band !== 'noise' && band !== null`. The IC Gate is doctrine-with-override, not a hard block — backtest launches available without evaluation but override is recorded in run artifacts.

**Rolling IC (EM6):** `SignalEvaluator.compute_rolling_ic()` — raw signal, consistent with static IC definition.

### Consequences

- IC evaluation precedes backtesting. Five-way IC classification: positive meaningful / inverse meaningful / weak positive / weak inverse / noise.
- Direction matters: negative IC indicates an inverse signal, not a poor signal.
- Both the Streamlit Research Workbench and the React Research Workbench surface IC evaluation before the backtest trigger.
- All strategies currently return noise-band IC on 1-year windows — expected for alternative data signals.

### Future Migration Path

Phase 3 or later: Cross-sectional IC, turnover analysis by asset, signal correlation matrix, composite signal construction.

---

## ADR-008 — Dashboard Architecture

**Status:** Superseded by FRONTEND_TDR-001
**Layers Affected:** Layer 8 (Dashboard)

### Context

The dashboard must present research outputs interactively. The key risk is allowing dashboard code to perform data manipulation. The choice of framework determines extensibility, testability, and the depth of the UI possible.

### Decision

**Original framework:** Streamlit. All 7 pages delivered and remain functional as the Phase 3 reference implementation.

**Superseded by:** React/TypeScript SPA + FastAPI backend (F-Track + FEP — COMPLETE).

**Core architectural rule preserved:** Presentation layer performs no computation. All analytics in `src/`. Route handlers are a serialization shell only. This rule applies identically to both Streamlit pages and FastAPI route handlers.

### Alternatives Considered

**Option A: Jupyter notebooks as primary interface.** *Rejected.* Streamlit provides more professional presentation artifact. Notebooks retained in `notebooks/` for exploratory research.

**Option B: Dash (Plotly) instead of Streamlit.** *Rejected for Phase 1/2.*

**Option C: React/TypeScript frontend with FastAPI backend.** *Planned for F-Track. Delivered.*

### Consequences

- Dashboard cannot perform data manipulation; enforces clean module boundaries
- The Streamlit → React migration was a presentation layer change only. All business logic in `src/` transferred without modification.
- The React frontend adds IC Gate enforcement in UI, URL-shareable state, Run Comparison, and the full commodity-intelligence + alternative data screen.

### Current State (F-Track Complete)

The React/TypeScript SPA is now the primary research interface. The Streamlit dashboard is the Phase 3 reference implementation. All 7 Streamlit pages remain functional; all 13 React screens are complete and tested (406 vitest, 114 E2E).

**React frontend rules:**
- Route handlers perform no computation — serialization shell only
- `staleTime: Infinity` on run artifacts (derived from ADR-009 immutability)
- IC state: TanStack Query cache (not Zustand) — confirmed by E2E testing
- `useRef + useEffect` pattern for all ECharts — not the ECharts React wrapper
- `resolveCssVar()` for all colors — never hardcoded hex

### Future Migration Path

If the platform grows to serve multiple users, add authentication and data isolation to the existing FastAPI + React stack. All business logic in `src/` requires no changes — this is an API and infrastructure change only.

---

## ADR-009 — Run Tracking Strategy

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine), Layer 4 (Performance)

### Context

Systematic research produces many backtest runs. Without structured run tracking, results are not reproducible, comparison is manual, and research drift is inevitable.

### Decision

**Phase 1 — File-based run tracking (Implemented):**

Each run assigned `run_id` in format `YYYYMMDD_HHMMSS_{strategy}_{asset}`.

7 artifacts per run at `data/runs/{run_id}/`:
- `params.json` — complete parameter snapshot
- `trades.parquet` — trade log
- `equity_curve.parquet` — cumulative PnL
- `pnl_series.parquet` — daily PnL
- `positions.parquet` — position size series
- `metrics.json` — scalar PerformanceReport metrics
- `portfolio_summary.json` — portfolio runs only; includes `asset_run_ids`, `has_regime_attribution`

`RunManager` provides: `save(backtest_result) → Path`, `save_metrics(run_id, report) → None`, `load_run(run_id) → dict`. No `.load()` method (DEV-EM8-1).

**Phase 2 — MLflow integration (Implemented — M12):**

MLflow local filesystem tracking backend alongside file artifacts. MLflow is additive — file artifacts always written first; MLflow failure is non-fatal. Experiments named `{mlflow_experiment_prefix}_{asset}`.

**SQLite run index (TD-RUN-EXPLORER-PERF — Implemented):**

`run_index.upsert_run()` called by `save_metrics()` with a try/except guard — index failure never breaks the backtest save path. `SAFE_SORT_COLUMNS` allowlist for dynamic ORDER BY. Sub-millisecond queries regardless of run count.

**Immutability rule (frontend consequence):** Run artifacts immutable once written. `staleTime: Infinity` on all run artifact queries in TanStack Query. Revisiting a run produces zero refetches.

### Implementation Notes

- `RunManager.load_run(run_id)` returns a dict — `pnl_series` is `pd.Series`, use `.sum()` directly (DEV-EM8-1)
- `BacktestResult.run_id` is set by `VectorizedBacktester.run()` (DEV-EM9-3)
- params.json key: `strategy_name` (fallback `strategy`) (DEV-EM8-6)
- `portfolio_summary.json` includes `has_regime_attribution: bool` flag written as `false` on run completion; flipped to `true` after regime attribution compute (TD-EM8-C-6)

### Future Migration Path

~~Phase 2: Add MLflow logging in `RunManager`.~~ **DONE (M12)**

~~Phase 3: Portfolio persistence for `MultiAssetBacktestResult` artifacts.~~ **DONE (M19 + EM3)**
- `save_portfolio_summary(report, run_dir)` writes `portfolio_summary.json` to `data/runs/{run_id}/`
- Contains: run_id, strategy, assets, portfolio_metrics, asset_contributions, absolute_pnl_by_asset, asset_run_ids, has_regime_attribution
- Called from portfolio background task after all 7 artifacts confirmed written

~~Run metadata indexing: SQLite for sub-second GET /api/runs.~~ **DONE (TD-RUN-EXPLORER-PERF)**

Phase 3 deferred: MLflow portfolio experiment logging (`commodity_research_portfolio` experiment). The per-asset MLflow logging (M12) remains in place.

Future: Configure MLflow remote HTTP tracking server, eliminating `MLFLOW_ALLOW_FILE_STORE` requirement.

---

## ADR-010 — Multi-Asset Research Scope and Phasing

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine), Layer 4 (Performance), Layer 7 (Cross-Asset Analytics)

### Context

The platform covers 6 commodity assets. Systematic research can be conducted at three levels: per-asset, multi-asset aggregation, and portfolio construction.

### Decision

**Phase 1 (Implemented):** Single-asset backtesting. Each strategy evaluated on one asset at a time.

**Phase 2 (Implemented — commodity intelligence focus):**
Phase 2 delivered commodity term structure analytics (Modules 8–13). Multi-asset aggregation was deferred to Phase 3 to keep Phase 2 focused on the commodity intelligence layer.

**Phase 3 (COMPLETE — M14–M19):** Multi-asset runner + portfolio performance + risk analytics + cross-asset correlation + ClickHouse + Dashboard Page 7.

Phase 3 capital model: each asset runs with the same initial capital ($1,000,000) independently. Portfolio equity curve = sum of per-asset equity curves. No active capital allocation — this is measurement infrastructure, not portfolio construction.

Phase 3 calendar alignment: inner-join (intersection of all asset date ranges). `portfolio_date_range` on `PortfolioPerformanceReport` surfaces this restriction explicitly.

**EM8 + TD-EM8-C (Implemented):** `RegimeAttributionEngine.compute_portfolio()` — 6 assets in parallel via ThreadPoolExecutor, P&L-weighted Sharpe aggregation, ~90s wall clock. The 6-asset universe is fixed per this ADR — ThreadPoolExecutor cap of `min(6, n_assets)` is intentional.

**EM13:** Alternative data universe also fixed at 6 assets. COT: Gold, Silver, Copper, WTI, NatGas (Brent excluded — ICE London, no CFTC coverage). EIA: WTI, Brent only (`EIA_SUPPORTED_ASSETS` constant).

### Implementation Note

Multi-asset aggregation — running the same strategy across all 6 assets and summing equity curves into a portfolio — is M14 in Phase 3, not Phase 2. This revision reflects the correct implementation sequence: commodity intelligence (Phase 2) before portfolio construction (Phase 3).

### Consequences

- Phase 1 and Phase 2 `BacktestResult` and `PerformanceReport` are scoped to a single asset
- Phase 3 adds `PortfolioPerformanceReport`, `RiskReport`, `CorrelationReport` as new contract types
- Phase 3 `CapitalAllocator` and portfolio optimization remain deferred

### Future Migration Path

~~Phase 3 (M14): Add `MultiAssetRunner`.~~ **DONE**
~~Phase 3 (M15): Portfolio-level metrics.~~ **DONE**
~~Phase 3 (M16, M17): Risk analytics + correlation.~~ **DONE**
Phase 3+: Correlation-aware portfolio optimization (minimum variance, risk parity).
Phase 3+: `CapitalAllocator` with risk budgeting for cross-strategy allocation.

---

## ADR-011 — Statistical Validation Layer (Walk-Forward + PSR/DSR)

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine), Layer 4 (Performance and Attribution)

### Context

All Phase 1–3 backtest results are full-sample in-sample. Without out-of-sample testing and multiple-testing correction, Sharpe ratios are systematically overstated due to strategy selection bias (Bailey et al., 2014 — Deflated Sharpe Ratio).

### Decision

**Walk-forward validation (EM5):**
- Expanding windows: `test_size = (n - min_train_bars - embargo_bars) // n_splits`
- Default: 5 folds (`n_splits`), 10 embargo bars (prevents look-ahead from feature overlap at fold boundaries)
- Each fold: independent signal generation + backtest on training set, then OOS evaluation
- Implementation: `src/validation/walk_forward.py`

**Probabilistic Sharpe Ratio (PSR):**
`PSR = Φ(√(T-1) × (SR* − SR_benchmark) / σ_SR)`
- Newey-West standard error for autocorrelated P&L (IID assumption relaxed)

**Deflated Sharpe Ratio (DSR):**
`DSR = PSR(SR* − E[max SR | n_trials])`
- `n_trials` from MLflow: experiment = `{prefix}_{asset}`, filter runs by `strategy_name` in run_name
- `E[max SR]` accounts for multiple-testing inflation
- scipy-free implementation: Beasley-Springer-Moro rational approximation for normal CDF

### Alternatives Considered

**scipy.stats.norm:** Rejected in the production path — adds a non-trivial dependency for a 5-line approximation. scipy-free implementation is correct to 5 decimal places.

**Combinatorial Purged Cross-Validation (CPCV):** Considered; walk-forward preferred for commodity signals with known regime structure. CPCV is a future enhancement.

### Consequences

- `ValidationReport` is the authoritative out-of-sample performance record for any strategy
- `is_significant = (dsr >= 0.95)` is the binary gate for institutional-quality signal claims
- Walk-forward validation unlocks the Validation tab in Run Detail (React frontend)

---

## ADR-012 — Alternative Data Integration (COT + EIA)

**Status:** Accepted
**Layers Affected:** Layer 0 (Data Infrastructure), Layer 2 (Signal Research)

### Context

Systematic commodity research uses two institutional alternative data sources: CFTC Commitments of Traders (COT) for speculative positioning, and EIA petroleum inventory for supply/demand signals.

### Decision

**Data acquisition:**
- COT: CFTC public, `dea/history/fut_disagg_txt_{year}.zip`, Managed Money category (`m_money_positions_long/short_all`). Requires `User-Agent: Mozilla/5.0` header. SSL verification disabled on Windows.
- EIA: EIA API v2, `WCRSTUS1` (WTI) and `WCSSTUS1` (Brent proxy). Free API key required (`EIA_API_KEY` in `config/local.yaml`).

**Data processing:**
- COT: `net_speculative = long - short`, 52-week rolling percentile rank on **0–100 scale**. Forward-filled weekly to daily trading calendar in signal generation.
- EIA: Z-score of inventory changes relative to seasonal 5-year average. Forward-filled weekly to daily.

**Signal design:**
- `COTPositioningSignal`: net specs above `upper_pct` threshold → go short (contrarian). Below `lower_pct` → go long.
- `EIAInventorySignal`: large inventory build (surprise z-score above `threshold`) → go short.

**Confirmed asset coverage:**
- COT: Gold/Silver (2015+, 604 wk), Copper/WTI/NatGas (2022+, 234 wk). Brent has NO COT data — ICE London, not CME.
- EIA: WTI and Brent proxy (1982+, 2,287 wk). Gold/Silver/Copper return empty signal — graceful, not error.

### Consequences

- `COT percentile_rank` is 0–100 throughout the entire pipeline — frontend must not multiply by 100
- `EIA_SUPPORTED_ASSETS` is a public constant in `eia_loader.py`
- Brent COT absence is by design and fully documented — not a gap to fill

---

## ADR-013 — Async Job Pattern for Long-Running Computations

**Status:** Accepted
**Layers Affected:** Layer 8 (FastAPI)

### Context

Several platform computations take 30–360 seconds: portfolio backtest (~5 min), walk-forward validation (~300s), parameter sweep (N×30s), regime attribution per asset (~30–90s), and PCA on full history (~13.5 min unconstrained).

A synchronous HTTP request/response pattern blocks both the server worker and the browser.

### Decision

All long-running computations use the async job pattern:

```
POST /api/{resource}        → 202 + {id, status: "queued"}
GET  /api/{resource}/{id}/status → queued | running | [persisting] | complete | failed
GET  /api/{resource}/{id}/result → full result payload when complete
```

**Portfolio-specific addition — `persisting` status (EM14):**
Set before writing 7 disk artifacts; flipped to `complete` after all confirmed written. Eliminates 404 race condition.

**Persistence across server restarts:** All job results written to disk (`data/sweeps/`, `data/validation/`, `data/regime_attribution/`). Result endpoints serve from disk when in-memory status dict is empty.

**Thread pool for sync compute:** `CurvePCAEngine.compute()` and `RegimeAttributionEngine.compute()` run via `asyncio.get_event_loop().run_in_executor(None, ...)` to avoid blocking Uvicorn's event loop.

**Carry/evaluate timeout (44a75f1):** 2-year default date range when no `from_date` provided for `carry` strategy. Hard 120s timeout with HTTP 408 response.

**PCA default date range (44a75f1):** 3-year default when no `from_date` provided — prevents 13.5-minute full-history computation.

### Alternatives Considered

**Celery + Redis queue:** Correct production solution for high concurrency; adds infrastructure complexity not warranted for a single-user platform.

**Server-Sent Events (SSE) for progress:** Considered for sweep progress; rejected in favour of polling — simpler implementation, identical UX at poll intervals used.

### Consequences

- All frontend job launches expect 202 and poll status
- `staleTime: Infinity` on result queries (immutable once written — ADR-009)
- `persisting` status prevents UI from showing 404 during portfolio disk write window

---

## ADR-014 — Signal Generator Interface Standards

**Status:** Accepted
**Layers Affected:** Layer 2 (Signal Research), Layer 3 (Backtesting Engine)

### Context

As the signal library grew from 4 (Phase 1) to 8 (EM13), implementation divergence emerged. Several bugs were caused by signals using incorrect return types, missing the `name` property, or accessing FeatureFrame attributes incorrectly.

### Decision

All SignalGenerators must conform to these implementation standards (DEV-EM7-1 through DEV-EM7-5):

**`SignalGenerator.name`** is a `@property abstractmethod` returning `str`. Never a class attribute. Failure to use `@property` breaks the StrategyMeta catalog lookup.

**`RawSignal` return type** is `pd.Series` with `series.name = self.name` set before returning. No custom type.

**FeatureFrame access patterns:**
- `feature_frame.data.index` for DatetimeIndex (not `feature_frame.index`)
- `feature_frame.asset` is `@property` (not `feature_frame._asset`)

**`pipeline_builder.py` dispatch (DEV-EM7-4):**
Sequential `if strategy_name == "..."` blocks with `return` — no `elif`, no `else`, no dict dispatch. Each block: `indicators, signal_gen = build_pipeline_components(...)` → 2-tuple always.

**Strategy catalog — four required registration locations:**
1. `api/routers/signals.py`: `_build_signal_pipeline()` + StrategyMeta + ParamSpec
2. `api/routers/backtests.py`: `_build_full_pipeline()`
3. `src/backtesting/pipeline_builder.py`: canonical dispatch
4. `config/strategies.yaml`: flat parameter defaults

All four must be updated when adding a new strategy. Missing any one produces a `400 UNKNOWN_STRATEGY` error.

### Consequences

- DEV-EM7 corrections are permanent and apply to all future signal implementations
- Data-owning signals (Carry, WTI-Brent Spread, COT, EIA) pass `FeaturePipeline([])` — valid per ADR-006
- Carry returns `ic=null` on Gold with 1-year window — flat signal due to structural contango — correct behavior
- WTI-Brent Spread requires `asset='wti'` validation — raise `ValueError` for other assets
