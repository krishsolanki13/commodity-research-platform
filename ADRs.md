# Architecture Decision Records
## Commodity Systematic Research Platform

**Format:** Each ADR documents a single architectural decision with context, rationale, alternatives considered, and migration path.
**Status values:** Proposed | Accepted | Superseded | Deprecated

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

**B. Contract-Level Series** (Phase 2):
- Individual contract tickers (e.g., CLN26, CLQ26, CLU26)
- Used exclusively for: futures curve construction, term structure analytics, contango, backwardation, basis, roll yield
- Never used in signal generation or backtesting

The `DataSource` abstraction in Layer 0 implements both `ContinuousDataSource` and `ContractDataSource` as separate implementations of the same base class. Upper layers never need to know which source they are working with once data is normalized.

### Alternatives Considered

**Option A: Build back-adjusted continuous series from contract-level data.**
*Rejected for Phase 1.* Requires individual contract data (no free source confirmed), roll calendar, and back-adjustment methodology decision (Panama vs. ratio). Significant upfront complexity for a research MVP. Appropriate for Phase 2.

**Option B: Use only continuous series for everything, including term structure.**
*Rejected.* A continuous series conflates prices from different contracts and cannot reconstruct the actual term structure at any given date. The forward curve is a snapshot of simultaneously traded contracts, which a continuous series cannot represent.

**Option C: Use Yahoo Finance data with Panama back-adjustment applied in-house.**
*Deferred to Phase 2.* Would require identifying roll dates in the Yahoo Finance series, which are not documented. Reverse-engineering roll dates from price discontinuities is feasible but adds complexity inappropriate for Phase 1.

### Consequences

**Positive:**
- Clean separation between systematic strategy research and commodity structure analysis
- Reflects institutional practice (commodity desks maintain separate data infrastructure for each purpose)
- Allows Phase 1 to proceed with freely available data
- Term structure analysis in Phase 2 will use accurate individual contract prices

**Negative:**
- Continuous series roll gaps affect price-level indicators computed across roll dates
- Phase 1 PnL calculations do not account for roll costs (roll returns are embedded in the price series in an opaque way)
- Two data ingestion pipelines to maintain

### Justification

This separation mirrors how systematic commodity research teams structure their data infrastructure. Research and risk analysts at commodity trading firms maintain separate time series for strategy signals (continuous) and market structure analysis (individual contracts). Mixing them would produce analytically incorrect results in one or both use cases.

### Future Migration Path

1. Phase 2: Add `ContractDataSource` and contract-level Parquet ingestion.
2. Phase 2: Identify Yahoo Finance roll dates from price discontinuities; flag roll-date returns in continuous series.
3. Phase 3 or later: Construct in-house back-adjusted series from individual contracts using a defined roll methodology (Panama additive or ratio multiplicative), replacing Yahoo Finance continuous series for backtesting to eliminate roll gap artifacts.

---

## ADR-002 — Signal Timing Convention (Close[t] → Open[t+1])

**Status:** Accepted
**Layers Affected:** Layer 2 (Signal Research), Layer 3 (Backtesting Engine)

### Context

Backtesting engines can introduce look-ahead bias if the price used to generate a signal and the price at which the trade is executed are not separated in time. For daily bar data, the key question is: at what price can a signal that uses Close[t] information be realistically traded?

### Decision

- Signals are generated using data available at Close[t].
- Trades are executed at Open[t+1].
- This convention is enforced as an architectural constraint in `VectorizedBacktester`.

The shift is implemented by aligning PositionSignal[t] with OHLCV[t+1].open during backtesting. The `VectorizedBacktester` is the single place where this shift is applied.

### Alternatives Considered

**Option A: Signal at Close[t], execute at Close[t] (same bar).**
*Rejected.* Execution at the same bar close as signal generation constitutes look-ahead bias. A signal computed from Close[t] cannot be acted on until after the bar closes, at which point the next tradable price is Open[t+1].

**Option B: Signal at Close[t-1], execute at Open[t] (one-bar delayed signal).**
*Equivalent to the chosen approach for daily bars, but adds conceptual confusion.* The chosen convention is cleaner.

**Option C: Signal at Close[t], execute at Close[t+1] (next day's close).**
*Overly conservative.* Most liquid futures markets allow execution at or near the open. Close[t+1] execution adds unnecessary slippage modeling complexity.

### Consequences

- Eliminates the most common source of look-ahead bias in daily backtesting
- Slightly penalizes strategies with fast-moving signals that could theoretically act intraday
- Consistent with standard practice in published academic and institutional systematic research on daily commodity futures

### Justification

This is the standard convention in institutional systematic research for daily bar strategies. Any deviation from this convention would require explicit documentation and justification. The Open[t+1] fill price is a conservative but realistic assumption for liquid commodity futures markets (COMEX, NYMEX, ICE).

### Future Migration Path

In Phase 3, if intraday execution simulation is needed (e.g., for execution quality analysis), the `CostModel` can be extended to model VWAP or implementation shortfall relative to Open[t+1]. The BacktestEngine interface does not need to change.

---

## ADR-003 — Vectorized Backtesting Engine

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine)

### Context

Backtesting engines fall into two architectural categories:

1. **Vectorized engines**: Apply strategy logic across entire time series using array operations (NumPy/Pandas). Fast, simple, but cannot accurately model market microstructure, margin calls, or sequential order effects.

2. **Event-driven engines**: Simulate markets event by event (bar by bar or tick by tick), enabling accurate modeling of order queues, partial fills, and margin calls. Realistic but complex to build correctly.

The choice of engine architecture determines how realistic the backtest results are and how complex the implementation is.

### Decision

Phase 1 will use a vectorized backtesting engine.

The engine is isolated behind the `BacktestEngine` abstract interface. `VectorizedBacktester` is the Phase 1 implementation. The interface contract (input: PositionSignal + OHLCV; output: BacktestResult) is engine-agnostic, ensuring that an event-driven engine can be introduced in a future phase without modifying Layer 2 (Signal Research) or Layer 4 (Performance).

### Alternatives Considered

**Option A: Event-driven engine from Phase 1.**
*Rejected.* An event-driven engine is significantly more complex to build correctly. For a single-developer research platform focused on signal research and strategy screening, this complexity is not justified in Phase 1. The primary risk is building an event-driven engine incorrectly and introducing subtle execution simulation errors that are harder to detect than vectorized bugs.

**Option B: Third-party backtesting framework (Zipline, Backtrader, vectorbt).**
*Rejected for Phase 1.* Third-party frameworks reduce architectural transparency and limit extensibility. Building a custom vectorized engine is straightforward and produces a more educational and defensible codebase. `vectorbt` is noted as a potential Phase 3 candidate for high-performance parameter sweeps.

**Option C: Vectorized engine with event-driven layer on top.**
*Deferred to Phase 3.* The current architecture supports this evolution.

### Consequences

**Positive:**
- Simple to implement correctly
- Fast execution over long historical periods
- Sufficient for signal research and strategy screening
- Clean interface enables future engine substitution

**Negative:**
- Cannot model partial fills, margin calls, or position-level order effects
- Simultaneous multi-asset trades are not sequenced realistically
- Not suitable for execution quality analysis or HFT research

### Justification

Vectorized backtesting is the standard approach for daily systematic strategy research at hedge funds, commodity trading firms, and bank systematic desks. Event-driven engines are reserved for execution simulation and live strategy monitoring, not research-phase signal evaluation. The abstraction behind `BacktestEngine` ensures this distinction is preserved architecturally.

### Future Migration Path

Phase 3 or later: Implement `EventDrivenBacktester` as an alternative `BacktestEngine` implementation. Strategy logic and performance computation remain unchanged. The migration is confined to Layer 3.

---

## ADR-004 — Storage Strategy: Parquet + ClickHouse Migration Path

**Status:** Accepted
**Layers Affected:** Layer 0 (Data Infrastructure)

### Context

The platform requires persistent storage for three categories of data:
1. Raw source data (CSV files)
2. Normalized research data (time-series OHLCV + features)
3. Backtest run artifacts (trades, equity curves, metrics)

The storage solution must support: local development, fast pandas reads, analytical queries, and a realistic migration path to a production-style analytical database.

### Decision

**Phase 1 and 2:** File-based storage.
- Raw data: CSV in `data/raw/` (immutable after download)
- Processed data: Parquet in `data/processed/` (one file per asset, regenerated idempotently)
- Run artifacts: Parquet + JSON in `data/runs/{run_id}/`

**Phase 3:** ClickHouse as analytical query layer.
- ClickHouse is introduced alongside (not replacing) Parquet. Parquet remains the canonical source.
- ClickHouse provides fast SQL queries over time-series data, appropriate for cross-asset analytics and rolling computations over long historical periods.
- The `DataStore` abstraction (`ParquetStore` in Phase 1/2, `ClickHouseStore` in Phase 3) isolates all storage implementation from upper layers.

**DuckDB:** Used for local development and unit testing as a zero-infrastructure SQL layer over Parquet. Not the Phase 3 production target given existing ClickHouse experience, but useful throughout development for exploratory SQL queries against processed Parquet files.

### Alternatives Considered

**Option A: DuckDB as the Phase 3 analytical store.**
*Not chosen as primary, but retained for development use.* DuckDB runs in-process, requires no server, and natively queries Parquet. For a single-developer platform, it is simpler than ClickHouse. It is retained as a development utility.
*Reason ClickHouse was chosen instead:* Prior internship experience with ClickHouse has direct interview value. ClickHouse more closely resembles production analytical infrastructure at trading firms with larger data volumes.

**Option B: PostgreSQL with TimescaleDB extension.**
*Rejected.* TimescaleDB is designed for operational time-series workloads (IoT, monitoring). ClickHouse is more appropriate for analytical (OLAP) queries over commodity research data.

**Option C: SQLite for run tracking.**
*Considered.* SQLite is simpler than file-based JSON + Parquet for run tracking. Deferred in favor of file-based approach for Phase 1 (zero dependencies, transparent artifacts) with MLflow as Phase 2 upgrade.

### Consequences

- `DataStore` abstraction required in Layer 0 before Phase 3 to prevent storage coupling
- DuckDB available as development utility throughout all phases
- ClickHouse requires a running server in Phase 3 (Docker-based for local development)
- Run artifacts are always file-based (Parquet + JSON) regardless of ClickHouse integration

### Justification

Parquet is the de facto standard columnar format for quantitative research data pipelines. It integrates natively with Pandas, DuckDB, and ClickHouse. ClickHouse is increasingly common at commodity trading firms and hedge funds for analytical query workloads over time-series data.

### Future Migration Path

1. Phase 1/2: `ParquetStore` only.
2. Phase 2: Add DuckDB utility queries for development exploration.
3. Phase 3: Add `ClickHouseStore` implementing the same `DataStore` interface. Write a migration script that loads processed Parquet into ClickHouse tables. Upper layers switch storage backend via config.

---

## ADR-005 — Position Sizing Methodology

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine)

### Context

Position sizing determines how much notional or risk is allocated to each signal. The sizing model significantly affects backtest results, especially when comparing results across assets with different volatility profiles (e.g., Natural Gas vs. Gold). The sizing methodology must be chosen before building the backtester, as it determines the units of the equity curve.

### Decision

**Phase 1 — Fixed Notional Sizing:**
Each signal receives a fixed USD notional exposure (default: $100,000).
Position size does not vary with asset volatility.

**Phase 2 — Volatility-Scaled Sizing:**
Position size is scaled to target a fixed annualized volatility per position (default: 15%).
Realized volatility is estimated from a 63-bar rolling window of log returns, annualized by √252.

**Phase 3 — Risk Budgeting:**
Portfolio-level risk budgeting allocates capital across strategies and assets based on risk targets and inter-asset correlation structure.

### Alternatives Considered

**Option A: Start with volatility-scaled sizing in Phase 1.**
*Evaluated seriously.* Volatility scaling is the standard approach at institutional commodity systematic desks and is more realistic than fixed notional. It ensures risk comparability across assets.
*Why deferred:* Fixed notional is simpler to implement and explain. For Phase 1 signal research (where the goal is signal quality evaluation, not realistic dollar PnL), fixed notional is adequate. Adding volatility scaling before the signal and backtesting infrastructure is stable adds unnecessary complexity.

**Option B: Percent-of-equity sizing (fixed percentage of running equity).**
*De-prioritized.* Percent equity sizing is common in retail trading software but less common on institutional commodity systematic desks, which prefer explicit risk targets over equity-fraction sizing. Volatility scaling is skipped directly in the Phase 2 plan.

**Option C: Fixed contract sizing (one contract per signal).**
*Rejected.* Contract notional values differ dramatically across assets ($100 per point for Gold vs. $10,000 per MMBtu for Natural Gas). Fixed contract sizing produces incomparable results across assets.

### Consequences

**Fixed Notional (Phase 1):**
- Equal risk comparison across assets is not achievable
- Results represent relative signal performance, not realistic dollar PnL
- Must be documented clearly in run metadata and ARCHITECTURE.md
- Simple to implement and validate

**Volatility-Scaled (Phase 2):**
- Comparable risk across assets
- More realistic PnL when contract multipliers are applied
- Requires rolling volatility calculation
- Results are sensitive to volatility estimation window choice

### Justification

Fixed notional is a defensible Phase 1 simplification for a single-asset signal research platform. The planned progression to volatility scaling in Phase 2 is consistent with institutional practice. Skipping percent-equity sizing (going directly from fixed notional to volatility scaling) is more realistic than the traditional retail trading platform progression.

### Future Migration Path

The `PositionSizer` class in Layer 3 implements sizing as a pluggable component. Phase 2 adds `VolatilityScaledSizer` implementing the same `PositionSizer` interface. The sizing method is configured in `config.yaml` under `sizing.method`.

---

## ADR-006 — FeatureFrame and FeatureSpec Design

**Status:** Accepted
**Layers Affected:** Layer 1 (Feature Engineering), Layer 2 (Signal Research)

### Context

The Research Layer must provide a structured, reproducible way to compute, name, and track indicator columns. Without explicit naming conventions and metadata tracking, a DataFrame with many indicator columns becomes ambiguous: an `ema` column gives no information about which EMA period was used. Signal research requires knowing exactly which features were consumed to reproduce results.

### Decision

**FeatureFrame:** A thin Python class wrapping a pandas DataFrame. It is NOT a plain DataFrame with informal naming conventions. Using a class provides: (1) a named type for function signatures (`def generate(feature_frame: FeatureFrame)`), (2) enforced access to feature_specs without relying on `DataFrame.attrs` conventions, and (3) a controlled surface for adding properties without inheriting all of pandas' complexity. The underlying DataFrame is accessible via `feature_frame.data`. The FeatureFrame class is defined in `src/research/feature_frame.py` and imported in `src/core/types.py` for cross-layer use.

Column naming convention: `{indicator_name}_{primary_parameter}` (e.g., `ema_50`, `rsi_14`, `momentum_20`). This convention is enforced by the Indicator base class `column_name` property, not by FeatureFrame itself.

**FeatureSpec:** A dataclass recording `{indicator_name, parameters, column_name, asset, computed_at}` for each feature in the FeatureFrame. Accessible via `feature_frame.feature_specs`. A list of FeatureSpec objects is serialized with every backtest run artifact.

**FeaturePipeline:** A class that accepts a list of Indicator instances and produces a FeatureFrame by applying each Indicator to a NormalizedOHLCV DataFrame.

### Alternatives Considered

**Option A: Store features in a separate file keyed by asset + parameter hash.**
*Deferred.* This is the architecture of a proper feature store (Feast, Tecton, or proprietary). Appropriate when feature computation is expensive or shared across many researchers. Unnecessary for a single-developer local platform.

**Option B: No naming convention — columns named by indicator class attribute.**
*Rejected.* Would produce non-descriptive column names that don't convey parameter values. Ambiguity in the feature space is a research reproducibility risk.

**Option C: Typed feature columns with a schema enforcer.**
*Considered for Phase 2.* A Pydantic schema for FeatureFrame columns would catch errors at runtime. Deferred as over-engineering for Phase 1.

### Consequences

- Column naming convention must be enforced by the Indicator base class (each Indicator computes its column name from its parameters)
- FeatureSpec list must be serialized with every backtest run for reproducibility
- Parameter sweeps require calling FeaturePipeline multiple times with different specs (FeatureFrame width grows with parameter count — this is the intended behavior)

### Justification

FeatureFrame + FeatureSpec provides the minimum necessary metadata to reproduce any signal research result. The flat DataFrame with parameter-aware column names is a well-understood pattern that scales to moderate feature spaces without the overhead of a dedicated feature store.

### Future Migration Path

If the feature space grows beyond ~30–50 columns, or if features are shared across multiple researchers, formalize the FeatureFrame into a lightweight feature store with persistent caching: cache FeatureFrames to `data/processed/features/{asset}_{feature_hash}.parquet`. This eliminates recomputation for repeated backtests over the same feature set.

---

## ADR-007 — Signal Research Layer: RawSignal, PositionSignal, and IC Evaluation

**Status:** Accepted
**Layers Affected:** Layer 2 (Signal Research), Layer 4 (Performance and Attribution)

### Context

Most retail backtesting platforms conflate signal generation and position sizing: a signal is immediately expressed as a position without intermediate evaluation. Institutional systematic research workflows separate these steps. A signal is evaluated for predictive content (IC analysis) before it is committed to a backtest. This separation prevents wasting compute and research time on signals with no predictive value.

Additionally, a raw signal (continuous float conveying conviction) is architecturally distinct from a position signal (discretized position instruction). This distinction allows the same raw signal to be expressed with different sizing or thresholding rules.

### Decision

**RawSignal:** A continuous float-valued Pandas Series aligned to the FeatureFrame index. Represents the signal generator's raw conviction output (e.g., EMA spread z-score, RSI oscillator value). No thresholding or discretization applied.

**PositionSignal:** An integer or fractional Pandas Series derived from RawSignal by applying thresholding or ranking rules. Values: {+1, 0, -1} for discrete strategies, or fractional values for continuous sizing.

**Signal Evaluation (IC/ICIR/Decay):** Computed from RawSignal and forward returns. IC = Pearson correlation(RawSignal[t], log_return[t+1]). ICIR = rolling_mean(IC) / rolling_std(IC). Signal decay: IC computed at forward horizons {1, 2, 5, 10, 20 bars}. Turnover: mean(|PositionSignal[t] - PositionSignal[t-1]|).

**Architectural rule:** Signal evaluation must be computed before running a backtest. IC is a precondition for backtest justification, not a post-backtest diagnostic.

### Alternatives Considered

**Option A: Skip IC evaluation; evaluate signals only through backtesting.**
*Rejected.* Backtesting alone is insufficient for signal quality assessment. A signal with zero IC can produce a positive backtest Sharpe ratio through favorable market regime coincidence or data snooping. IC analysis is a prerequisite, not a supplement.

**Option B: Compute IC only after backtesting as a post-hoc diagnostic.**
*Rejected.* Post-hoc IC is still useful but loses the gatekeeping function. IC should determine whether a backtest is warranted, not validate one after the fact.

**Option C: Use a single signal value (no RawSignal / PositionSignal separation).**
*Rejected.* Without the separation, the same signal cannot be evaluated with different sizing rules or combined into composite signals. The separation is a minimal but important architectural decision that mirrors institutional alpha research workflows.

### Consequences

- SignalGenerator must output RawSignal; a separate PositionSignalConstructor handles discretization
- IC evaluation module must access forward returns (derived from NormalizedOHLCV in Layer 0) — this requires passing OHLCV data into SignalEvaluator alongside the RawSignal
- IC, ICIR, and decay metrics appear in PerformanceReport (Layer 4), surfacing signal quality metrics alongside execution performance

### Justification

The RawSignal → IC evaluation → PositionSignal workflow mirrors how systematic research analysts at hedge funds and commodity trading firms evaluate new signals. IC and ICIR are standard vocabulary in factor investing and systematic strategy research. Including them elevates the platform from a backtesting tool to a research platform.

### Future Migration Path

Phase 2: Extend signal evaluation to include cross-sectional IC (ranking signals across assets), turnover analysis by asset, and signal correlation analysis. Phase 3: Composite signal construction (weighted combination of RawSignals), alpha combination frameworks.

---

## ADR-008 — Dashboard Architecture

**Status:** Accepted
**Layers Affected:** Layer 8 (Dashboard)

### Context

The dashboard must present research outputs interactively. The key architectural risk is allowing dashboard code to perform data manipulation, which creates two paths to the same output and makes testing and debugging difficult.

### Decision

**Framework:** Streamlit.

**Architectural rule:** Dashboard pages are a pure presentation layer. All data manipulation, computation, and business logic must be in `src/` modules. Dashboard pages call `src/` functions only.

**Page structure:**

| Page | Phase |
|------|-------|
| 1. Market Overview | 1 |
| 2. Research Workbench | 1 |
| 3. Strategy Builder | 1 |
| 4. Backtest Results | 1 |
| 5. Performance Analysis | 1 |
| 6. Commodity Intelligence | 2 |
| 7. Cross-Asset Analytics | 3 |

**Component organization:** Reusable chart functions in `dashboard/components/`. Dashboard pages import components; components do not import from other components.

### Alternatives Considered

**Option A: Jupyter notebooks as primary research interface.**
*Considered as Phase 1 alternative.* Jupyter is faster to prototype and is used by quant researchers at many funds. Rejected as primary interface because Streamlit provides a more professional presentation artifact. Notebooks are retained in `notebooks/` for exploratory research.

**Option B: Dash (Plotly) instead of Streamlit.**
*Considered.* Dash provides more control over UI structure and is used in some institutional research portals. Rejected for Phase 1 because Streamlit's development speed advantage is significant for a single developer.

**Option C: React/TypeScript frontend with FastAPI backend.**
*Rejected.* Appropriate for a production research portal with multiple users. Not appropriate for a single-developer research platform.

### Consequences

- Dashboard cannot perform data manipulation; enforces clean module boundaries
- Testing of dashboard pages is limited to integration tests against `src/` module outputs
- Streamlit's re-execution model requires attention to caching (`@st.cache_data`) for expensive computations

### Future Migration Path

If the platform grows to serve multiple users or requires more sophisticated UI, replace Streamlit with a React frontend and FastAPI backend. All business logic in `src/` modules transfers without modification. Dashboard replacement is a presentation layer change only.

---

## ADR-009 — Run Tracking Strategy

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine), Layer 4 (Performance)

### Context

Systematic research produces many backtest runs across different assets, parameters, and strategies. Without structured run tracking, results are not reproducible, comparison is manual, and research drift (where the parameters of a remembered result are forgotten) is inevitable.

### Decision

**Phase 1 — File-based run tracking:**

Each run is assigned a unique `run_id` in the format `YYYYMMDD_HHMMSS_{strategy}_{asset}`.

Run artifacts stored at `data/runs/{run_id}/`:
- `params.json` — complete parameter snapshot: strategy params, data source metadata, cost model, sizing model, data start/end, execution timestamp
- `trades.parquet` — trade log (TradeRecord objects serialized)
- `equity_curve.parquet` — cumulative PnL series
- `pnl_series.parquet` — daily PnL series
- `positions.parquet` — position size series
- `metrics.json` — scalar PerformanceReport metrics

A `RunRegistry` class provides: `list_runs()`, `load_run(run_id)`, `compare_runs(run_ids)`, `delete_run(run_id)`.

**Phase 2 — MLflow integration:**

MLflow's file-based tracking backend (no server required) is introduced alongside the file-based approach. MLflow logs: params, metrics, and artifacts (same Parquet files). MLflow UI provides run comparison, parameter search, and metric visualization.

### Alternatives Considered

**Option A: MLflow from Phase 1.**
*Considered.* MLflow is widely used in quantitative research at hedge funds and systematic funds. It provides a UI for run comparison from day one.
*Deferred to Phase 2.* Adding MLflow before the core research pipeline is stable introduces a dependency before its value is demonstrated. File-based tracking is sufficient for Phase 1 and preserves optionality.

**Option B: Weights & Biases (W&B).**
*Rejected.* W&B is cloud-first and aimed at machine learning training runs. MLflow is more natural for quantitative research workflows and runs fully locally.

**Option C: SQLite run registry.**
*Considered.* A SQLite database for run metadata with separate Parquet files for time-series artifacts is a reasonable alternative. Rejected in favor of pure file-based approach for Phase 1 to minimize dependencies.

### Consequences

- RunManager must be built as part of the backtesting layer, not deferred
- Run artifacts are immutable once written; reruns create new run IDs
- File-based approach produces transparent, inspectable artifacts without tooling
- Phase 2 MLflow migration requires adding MLflow logging calls inside RunManager; existing file artifacts remain

### Justification

Experiment tracking is a non-optional component of a research platform. A backtest without a stored parameter snapshot cannot be reproduced. The file-based approach is the minimum viable tracking system; MLflow in Phase 2 is the standard tool used by systematic research teams.

### Future Migration Path

Phase 2: Add MLflow logging in `RunManager.save()`. Continue writing file-based artifacts (immutable, inspectable without MLflow). Phase 3: If research scale warrants it, configure MLflow to use a remote tracking server.

---

## ADR-010 — Multi-Asset Research Scope and Phasing

**Status:** Accepted
**Layers Affected:** Layer 3 (Backtesting Engine), Layer 4 (Performance), Layer 7 (Cross-Asset Analytics)

### Context

The platform covers 6 commodity assets. Systematic research can be conducted at three levels:
1. **Per-asset research:** Signal and strategy evaluated independently on each asset
2. **Multi-asset aggregation:** Results from per-asset backtests combined into a portfolio equity curve for aggregate metrics
3. **Portfolio construction:** Capital allocation engine that manages risk and correlation across assets simultaneously

These three levels have different analytical complexity and implementation requirements.

### Decision

**Phase 1:** Single-asset backtesting. Each strategy is evaluated on one asset at a time. No portfolio equity curve or portfolio-level metrics.

**Phase 2:** Multi-asset aggregation. The same strategy can be run across all 6 assets independently. Results are aggregated into a portfolio equity curve (sum of individual asset equity curves) for portfolio-level metric computation (portfolio Sharpe, portfolio drawdown). No active capital allocation.

**Phase 3:** Portfolio construction engine. A formal capital allocation layer manages risk budgeting, position sizing with correlation awareness, and portfolio-level risk analytics.

### Alternatives Considered

**Option A: Portfolio backtesting from Phase 1.**
*Rejected.* Portfolio construction before per-asset signal quality is established inverts the research workflow. Institutional practice is to research and validate signals on individual instruments before constructing portfolios.

**Option B: Never implement a portfolio construction engine; keep research per-asset.**
*Rejected.* Portfolio-level analytics (Sharpe, drawdown, correlation) are essential for evaluating systematic commodity programs as practiced at trading firms. The Phase 3 portfolio engine is a necessary destination.

### Consequences

- Phase 1 BacktestResult is scoped to a single asset
- Phase 1 PerformanceReport is scoped to a single asset
- Phase 3 requires a `PortfolioBacktestResult` and `PortfolioPerformanceReport` as new contract types in Layer 4
- Phase 3 requires a `CapitalAllocator` component in Layer 3

### Justification

Per-asset research → aggregation → portfolio construction is the standard progression in systematic strategy development at hedge funds and commodity trading firms. Attempting portfolio construction before individual signal validation increases the risk of constructing portfolios around signals that have no independent predictive content.

### Future Migration Path

Phase 2: Add `MultiAssetRunner` utility that executes `VectorizedBacktester` across all assets and aggregates `BacktestResult` objects into a portfolio equity curve. Phase 3: Implement `CapitalAllocator` that applies risk budgeting weights to multi-asset position signals before backtesting. Phase 3+: Correlation-aware portfolio optimization (minimum variance, risk parity).
