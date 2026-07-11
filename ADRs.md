# Architecture Decision Records
## Commodity Systematic Research Platform

**Format:** Each ADR documents a single architectural decision with context, rationale, alternatives considered, and migration path.
**Status values:** Proposed | Accepted | Superseded | Deprecated
**Last Updated:** Phase 2 complete (M01–M13, 186 tests, phase-2-complete tag)

---

## ADR-001 — Continuous vs. Contract-Level Futures Data

**Status:** Accepted
**Layers Affected:** Layer 0 (Data Infrastructure), Layer 5 (Commodity Intelligence)

### Context

Commodity futures markets do not have a single continuous price series. Each commodity is traded as a series of individual contracts with fixed expiry dates (e.g., CLN26 = WTI Crude August 2026). To perform long-horizon strategy research and backtesting, practitioners must either use individual contract data and handle rolls explicitly, or use a pre-constructed continuous series that stitches contracts together.

The two approaches serve different analytical purposes:
- Continuous series: signal generation, indicator computation, backtesting
- Individual contract series: term structure analysis, contango/backwardation detection, roll yield calculation, basis analysis

These cannot be combined without careful design. A single price stream cannot simultaneously serve both purposes accurately.

### Decision

Maintain two separate datasets:

**A. Continuous Futures Series** (Phase 1, 2, 3):
- Obtained from Yahoo Finance (GC=F, CL=F, SI=F, HG=F, NG=F, BZ=F)
- Used exclusively for: feature engineering, signal generation, backtesting, performance analytics
- Roll methodology: undocumented. Treated as opaque vendor-provided continuous price stream.
- Known limitation: not back-adjusted. Roll gaps will appear at contract transition dates.

**B. Contract-Level Series** (Phase 2 — Implemented):
- Individual contract tickers in canonical format (e.g., GCZ24, CLF25) stored without exchange suffix
- yfinance API access uses exchange-suffix tickers (e.g., GCZ24.CMX for COMEX, CLF25.NYM for NYMEX/ICE)
- Brent (BZ) is ICE-listed but Yahoo Finance exposes the NYMEX-cleared version; `.NYM` is the correct suffix
- Used exclusively for: futures curve construction, term structure analytics, contango, backwardation, basis, roll yield
- Never used in signal generation or backtesting
- Coverage: typically 2–3 years per contract from yfinance

The `DataSource` abstraction in Layer 0 implements both `ContinuousDataSource` and `ContractDataSource` as separate implementations of the same base class. Upper layers never need to know which source they are working with once data is normalized.

The basis calculation in `TermStructureAnalyzer.compute_basis()` is the only point where the two pipelines interact. The continuous close is provided as a parameter to the analyzer; the analyzer never calls `DataLoader` directly. The dashboard is the orchestration point.

### Alternatives Considered

**Option A: Build back-adjusted continuous series from contract-level data.**
*Rejected for Phase 1.* Requires individual contract data, roll calendar, and back-adjustment methodology decision (Panama vs. ratio). Significant upfront complexity for a research MVP. Appropriate for Phase 3.

**Option B: Use only continuous series for everything, including term structure.**
*Rejected.* A continuous series conflates prices from different contracts and cannot reconstruct the actual term structure at any given date.

**Option C: Use Yahoo Finance data with Panama back-adjustment applied in-house.**
*Deferred to Phase 3.* Would require identifying roll dates, which are not documented. Reverse-engineering roll dates from price discontinuities is feasible but adds complexity.

### Consequences

**Positive:**
- Clean separation between systematic strategy research and commodity structure analysis
- Reflects institutional practice
- Term structure analysis in Phase 2 uses accurate individual contract prices
- Basis calculation confirmed viable using continuous close as pseudo-spot proxy

**Negative:**
- Continuous series roll gaps affect price-level indicators computed across roll dates
- Phase 1 and Phase 2 PnL calculations do not account for roll costs explicitly
- Two data ingestion pipelines to maintain

### Implementation Notes (Phase 2)

- `strict_ohlc=False` applied to all Yahoo Finance data (both continuous and contract-level). Settlement prices can legally fall outside intraday High/Low range. The 2020-04-20 WTI event (−$37.63) is genuine historical data.
- Brent contract coverage from yfinance is historically thinner than WTI or Gold. Dashboard handles this gracefully.

### Future Migration Path

1. ~~Phase 2: Add `ContractDataSource` and contract-level Parquet ingestion.~~ **DONE (M08)**
2. Phase 2 (deferred to Phase 3): Identify Yahoo Finance roll dates from price discontinuities; flag roll-date returns in continuous series. No roll calendar implemented.
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

### Future Migration Path

In Phase 3, if execution quality analysis is needed, the `CostModel` can be extended to model VWAP or implementation shortfall relative to Open[t+1]. The BacktestEngine interface does not need to change.

---

## ADR-003 — Vectorized Backtesting Engine

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine)

### Context

Backtesting engines fall into two architectural categories: vectorized (fast, simple) and event-driven (realistic but complex). The choice determines how realistic results are and how complex the implementation is.

### Decision

Phase 1 and Phase 2 use a vectorized backtesting engine (`VectorizedBacktester`).

The engine is isolated behind the `BacktestEngine` abstract interface. `VectorizedBacktester` is the Phase 1/2 implementation. The interface contract (input: PositionSignal + OHLCV; output: BacktestResult) is engine-agnostic.

### Alternatives Considered

**Option A: Event-driven engine from Phase 1.** *Rejected.* Significantly more complex for a single-developer research platform. Primary risk is building it incorrectly and introducing subtle execution simulation errors.

**Option B: Third-party framework (Zipline, Backtrader, vectorbt).** *Rejected for Phase 1/2.* Reduces architectural transparency.

### Consequences

**Positive:** Simple to implement correctly. Fast. Sufficient for signal research and screening.

**Negative:** Cannot model partial fills, margin calls, or position-level order effects.

### Implementation Notes (Phase 2)

- `VectorizedBacktester.__init__()` now accepts optional `sizer: PositionSizer | None = None` for dependency injection.
- `VectorizedBacktester.run()` calls `self._sizer.configure(ohlcv)` before the simulation loop.
- Internal attribute is `self._sizer` (renamed from `self._position_sizer` during Phase 2 for clarity).
- The `compute_size(signal, asset, equity)` ABC method (not `size(signal, equity)` as originally specified) is the actual interface. `VolatilityScaledSizer` implements `compute_size()` as an ABC bridge delegating to internal `size()`.

### Future Migration Path

Phase 3 or later: Implement `EventDrivenBacktester` as an alternative `BacktestEngine` implementation. Strategy logic and performance computation remain unchanged. Migration is confined to Layer 3.

---

## ADR-004 — Storage Strategy: Parquet + ClickHouse Migration Path

**Status:** Accepted
**Layers Affected:** Layer 0 (Data Infrastructure)

### Context

The platform requires persistent storage for raw data, normalized research data, backtest run artifacts, and (Phase 2) experiment tracking metadata.

### Decision

**Phase 1 and 2 — File-based storage (Implemented):**
- Raw data: CSV in `data/raw/` (immutable after download)
  - Continuous: `data/raw/continuous/{asset}_{date}.csv`
  - Contracts: `data/raw/contracts/{asset}/{ticker}.csv` (Phase 2)
- Processed data: Parquet in `data/processed/` (one file per asset/contract, regenerated idempotently)
  - Continuous: `data/processed/continuous/{asset}.parquet`
  - Contracts: `data/processed/contracts/{asset}/{ticker}.parquet` + sidecar `{ticker}.meta.json` (Phase 2)
- Run artifacts: Parquet + JSON in `data/runs/{run_id}/`
- Experiment tracking: MLflow local filesystem at `data/mlruns/` (Phase 2)

**Phase 3:** ClickHouse as analytical query layer.

**DuckDB:** Available for local development exploration via queries over Parquet. Not the Phase 3 production target.

### Alternatives Considered

**Option A: DuckDB as Phase 3 analytical store.** *Not chosen as primary.* Retained for development utility. ClickHouse chosen for prior experience and production infrastructure resemblance.

**Option B: PostgreSQL with TimescaleDB.** *Rejected.* TimescaleDB targets operational OLAP; ClickHouse is more appropriate.

### Consequences

- `DataStore` abstraction required before Phase 3 to prevent storage coupling
- DuckDB available as development utility throughout all phases
- MLflow `data/mlruns/` is covered by the existing `/data/` gitignore pattern

### Implementation Notes (Phase 2)

- `ContractParquetStore` writes `.meta.json` sidecar alongside each Parquet for `ContractMetadata` persistence (Parquet cannot store arbitrary Python objects).
- `OHLCVNormalizer.normalize()` clears `result.attrs = {}` before returning to prevent pyarrow UserWarning during Parquet serialization. `DataLoader.load()` re-populates `asset`, `source`, `continuous` attrs from known parameters after both fast (Parquet) and slow (CSV pipeline) paths.
- MLflow 3.x requires `MLFLOW_ALLOW_FILE_STORE=true` for filesystem tracking URIs. Set programmatically in `_try_log_to_mlflow()` via `os.environ.setdefault`. Launcher scripts export the variable.

### Future Migration Path

1. ~~Phase 1/2: `ParquetStore` only.~~ **DONE**
2. ~~Phase 2: Add DuckDB utility queries.~~ DuckDB available but not formalized.
3. ~~Phase 2: Add MLflow logging.~~ **DONE (M12)**
4. ~~Phase 3: Add `ClickHouseStore` implementing the same `DataStore` interface.~~ **DONE (M18)**
   - ClickHouse 24.3 via Docker Compose. 24,862 rows migrated. Config-switchable (default: parquet).
   - `storage.backend = "parquet"` preserves all existing behavior. Switch to `"clickhouse"` after migration.
   - Honest sizing note: DuckDB is the right-sized alternative for 25k rows. ClickHouse retained as migration-seam demonstration and production-infrastructure analogue. See §9.2 of ARCHITECTURE.md.

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
realized_vol   = std(daily_returns[-lookback_days:]) * sqrt(252)   [annualized]
target_notional = (target_annual_vol * current_equity) / realized_vol
```
`VolatilityScaledSizer(target_annual_vol, lookback_days, vol_cap, min_notional, max_notional)`.

The `PositionSizer` ABC provides a `configure(ohlcv)` no-op hook. `VectorizedBacktester.run()` calls `sizer.configure(ohlcv)` before the simulation loop. `VolatilityScaledSizer.configure()` pre-computes realized volatility from the OHLCV close series.

**Phase 3 — Portfolio Analytics (Implemented — note on scope):**
Phase 3 implemented `MultiAssetRunner` (M14), `PortfolioPerformanceEngine` (M15), `RiskEngine` (M16), and `CorrelationEngine` (M17). Risk *budgeting* (CapitalAllocator) and portfolio *optimization* were not implemented — they were deferred beyond Phase 3. The portfolio equity curve is the sum of independent per-asset equity curves with no active capital allocation.

The two known technical debts in the sizing model are formally deferred to F-track or future modules:
- **TD-B (static equity):** `current_equity` passed as initial capital rather than rolling MTM. The fix is in the engine call site — the `compute_size(signal, asset, equity)` interface already has the parameter.
- **TD-C (end-of-sample vol estimate):** `configure()` called once with full OHLCV creates mild look-ahead vol bias for early bars. Fix: rolling vol Series indexed by bar_date.

### Implementation Notes (Phase 2)

- The ABC method is `compute_size(signal, asset, equity)` not `size(signal, equity)`. `VolatilityScaledSizer` implements `compute_size()` as a bridge delegating to internal `size()`.
- `FixedNotionalSizer` constructor uses `notional_usd=` parameter name (not `notional=`).
- Vol-scaled verified: Gold (23.49%/yr vol) at $1M equity, 1%/yr target → $42,567 notional vs $100,000 fixed.
- Known limitations: static equity (TD-B) and end-of-sample vol estimate (TD-C) — both deferred to Phase 3.

### Future Migration Path

The `PositionSizer` class in Layer 3 implements sizing as a pluggable component. Phase 3 adds `CapitalAllocator` for risk-budgeted portfolio sizing across assets.

---

## ADR-006 — FeatureFrame and FeatureSpec Design

**Status:** Accepted
**Layers Affected:** Layer 1 (Feature Engineering), Layer 2 (Signal Research)

### Context

The Research Layer must provide a structured, reproducible way to compute, name, and track indicator columns. Without explicit naming conventions and metadata tracking, a DataFrame with many indicator columns becomes ambiguous.

### Decision

**FeatureFrame:** A thin Python class wrapping a pandas DataFrame. Provides a named type for function signatures, enforced access to feature_specs, and a controlled surface for adding properties.

Column naming convention: `{indicator_name}_{primary_parameter}` (e.g., `ema_50`, `rsi_14`). Enforced by the Indicator base class `column_name` property.

**FeatureSpec:** A dataclass recording `{indicator_name, parameters, column_name, asset, computed_at}` for each feature in the FeatureFrame. Serialized with every backtest run artifact.

**FeaturePipeline:** Accepts a list of Indicator instances and produces a FeatureFrame.

### Consequences

- Column naming convention enforced by the Indicator base class
- FeatureSpec list serialized with every backtest run for reproducibility

### Future Migration Path

If the feature space grows beyond ~30–50 columns, formalize into a lightweight feature store with persistent caching: `data/processed/features/{asset}_{feature_hash}.parquet`.

---

## ADR-007 — Signal Research Layer: RawSignal, PositionSignal, and IC Evaluation

**Status:** Accepted
**Layers Affected:** Layer 2 (Signal Research), Layer 4 (Performance and Attribution)

### Context

Most retail backtesting platforms conflate signal generation and position sizing. Institutional systematic research separates these steps: a signal is evaluated for predictive content before it is committed to a backtest.

### Decision

**RawSignal:** Continuous float-valued Series. Represents raw conviction output before thresholding.

**PositionSignal:** Integer or fractional Series {+1, 0, -1} derived from RawSignal by thresholding.

**Signal Evaluation:** IC = Pearson correlation(RawSignal[t], log_return[t+1]). ICIR = rolling_mean(IC) / rolling_std(IC). Decay at horizons {1, 2, 5, 10, 20 bars}.

**Architectural rule:** IC evaluation precedes backtesting. Five-way IC classification: positive meaningful / inverse meaningful / weak positive / weak inverse / noise. Direction matters — negative IC indicates an inverse signal, not a poor signal.

### Consequences

- IC evaluation is implemented and surfaced in both Page 2 (Research Workbench) and Page 5 (Performance Analysis)
- Both pages use directional IC classification

### Future Migration Path

Phase 3: Cross-sectional IC, turnover analysis by asset, signal correlation, composite signal construction.

---

## ADR-008 — Dashboard Architecture

**Status:** Superseded by FRONTEND_TDR-001
**Layers Affected:** Layer 8 (Dashboard)

### Context

The dashboard must present research outputs interactively. The key risk is allowing dashboard code to perform data manipulation.

### Decision

**Framework:** Streamlit.

**Architectural rule:** Dashboard pages are a pure presentation layer. All computation in `src/` modules. Dashboard pages call `src/` functions only.

**Visual design:** Institutional dark theme (#0e1628 navy background). Monospace font throughout. Custom KPI display via `render_kpi_row()` replacing `st.metric()` on research pages. Defined in `dashboard/components/_theme.py`.

**Supersession note:** ADR-008's core rule — presentation layer performs no computation; all analytics in `src/` — is preserved in FRONTEND_TDR-001. The technology (Streamlit) is replaced by React + FastAPI. The Streamlit implementation delivered all 7 pages and remains the working reference implementation.

**Page structure (Streamlit — all delivered):**

| Page | Phase | Status |
|------|-------|--------|
| 1. Market Overview | 1 | Complete |
| 2. Research Workbench | 1 | Complete |
| 3. Strategy Builder | 1 | Complete |
| 4. Backtest Results | 1 | Complete |
| 5. Performance Analysis | 1 | Complete |
| 6. Futures Curve | 2 | Complete |
| 7. Cross-Asset Analytics | 3 | Complete |

**F-Track (React + FastAPI):** Pages 1–7 will be rebuilt in the React workstation (F1–F15) with IC Gate enforcement, URL-shareable state, Run Comparison, and the full commodity-intelligence screen. The Streamlit implementation is the reference specification.

**Component organization:** Reusable chart functions in `dashboard/components/`. Components are pure functions returning Plotly figures. No `st.*` calls in component files. No `src/` imports at module level in component files (TYPE_CHECKING guard only). Components do not import from other components.

**Current components:** `_theme.py`, `price_chart.py`, `equity_curve_chart.py`, `metrics_table.py`, `signal_chart.py`, `curve_chart.py`.

### Alternatives Considered

**Option A: Jupyter notebooks as primary interface.** *Rejected.* Streamlit provides more professional presentation artifact. Notebooks retained in `notebooks/` for exploratory research.

**Option B: Dash (Plotly) instead of Streamlit.** *Rejected for Phase 1/2.*

**Option C: React/TypeScript frontend with FastAPI backend.** *Planned for Phase 3 as optional enhancement.*

### Consequences

- Dashboard cannot perform data manipulation; enforces clean module boundaries
- No pytest unit tests for dashboard pages (integration-level testing only)
- Manual verification checklist per page

### Future Migration Path

If the platform grows to serve multiple users, replace Streamlit with a React frontend and FastAPI backend. All business logic in `src/` transfers without modification. This is a presentation layer change only.

---

## ADR-009 — Run Tracking Strategy

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine), Layer 4 (Performance)

### Context

Systematic research produces many backtest runs. Without structured run tracking, results are not reproducible, comparison is manual, and research drift is inevitable.

### Decision

**Phase 1 — File-based run tracking (Implemented):**

Each run is assigned a unique `run_id` in the format `YYYYMMDD_HHMMSS_{strategy}_{asset}`.

Run artifacts at `data/runs/{run_id}/`:
- `params.json` — complete parameter snapshot
- `trades.parquet` — trade log
- `equity_curve.parquet` — cumulative PnL
- `pnl_series.parquet` — daily PnL
- `positions.parquet` — position size series
- `metrics.json` — scalar PerformanceReport metrics

`RunManager` provides: `save()`, `save_metrics()`, `compare_runs()`, `delete_run()`.

**Phase 2 — MLflow integration (Implemented — M12):**

MLflow local filesystem tracking backend alongside file-based artifacts. MLflow is additive — file artifacts always written first; MLflow failure is non-fatal.

Implementation details:
- `RunManager._try_log_to_mlflow(run_id, report)` private method called at end of `save_metrics()`
- MLflow logging in `save_metrics()` (not `save()`); reads `params.json` from disk for parameters
- Experiments named `{mlflow_experiment_prefix}_{asset}` (e.g., `commodity_research_gold`)
- Tracking URI: `file:./data/mlruns` (relative to repository root)
- MLflow 3.x requires `MLFLOW_ALLOW_FILE_STORE=true` for filesystem URIs; set via `os.environ.setdefault()` in `_try_log_to_mlflow()` and exported by launcher scripts
- 16 scalar metrics logged (all finite values from `PerformanceReport.scalar_metrics` + `signal_metrics`)
- MLflow run name = `run_id` for cross-reference with file artifacts; `file_run_id` tag set

### Consequences

- File-based artifacts remain the authoritative source of truth; MLflow is the searchable interface
- Run artifacts immutable once written; reruns create new run IDs
- `data/mlruns/` covered by existing `/data/` gitignore entry

### Future Migration Path

~~Phase 2: Add MLflow logging in `RunManager`.~~ **DONE (M12)**

~~Phase 3: Portfolio persistence for `MultiAssetBacktestResult` artifacts.~~ **DONE (M19)**
- `save_portfolio_summary(report, run_dir)` writes `portfolio_summary.json` to `data/runs/{run_id}/`
- Contains: run_id, strategy, assets, portfolio_metrics, asset_contributions, absolute_pnl_by_asset
- Called from Dashboard Page 7 after each portfolio analysis run

Phase 3 deferred: MLflow portfolio experiment logging (`commodity_research_portfolio` experiment). Deferred to F-track. The per-asset MLflow logging (M12) remains in place.

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
Phase 2 delivered commodity term structure analytics (Modules 8–13). Multi-asset aggregation was deferred to Phase 3 (Module 14). The original ADR described Phase 2 as including multi-asset aggregation; this was revised during implementation planning to keep Phase 2 focused on the commodity intelligence layer.

**Phase 3 (COMPLETE — M14–M19):** Multi-asset runner + portfolio performance + risk analytics + cross-asset correlation + ClickHouse + Dashboard Page 7.

Phase 3 capital model (M14): each asset runs with the same initial capital ($1,000,000) independently. Portfolio equity curve = sum of per-asset equity curves. Portfolio starts at n_assets × initial_capital. No active capital allocation — this is measurement infrastructure, not portfolio construction.

Phase 3 calendar alignment (M14): inner-join (intersection of all asset date ranges). The portfolio is computed only over dates where all assets have data. `portfolio_date_range` on `PortfolioPerformanceReport` surfaces this restriction explicitly.

### Implementation Note

Multi-asset aggregation — running the same strategy across all 6 assets and summing equity curves into a portfolio — is M14 in Phase 3, not Phase 2. This revision reflects the correct implementation sequence: commodity intelligence (Phase 2) before portfolio construction (Phase 3).

### Consequences

- Phase 1 and Phase 2 `BacktestResult` and `PerformanceReport` are scoped to a single asset
- Phase 3 requires `PortfolioBacktestResult` and `PortfolioPerformanceReport` as new contract types in Layer 4
- Phase 3 requires `CapitalAllocator` component in Layer 3

### Future Migration Path

Phase 3 (M14): Add `MultiAssetRunner` utility that executes `VectorizedBacktester` across all assets. Phase 3 (M15): Portfolio-level metrics. Phase 3 (M16, M17): `CapitalAllocator` with risk budgeting. Phase 3+: Correlation-aware portfolio optimization (minimum variance, risk parity).
