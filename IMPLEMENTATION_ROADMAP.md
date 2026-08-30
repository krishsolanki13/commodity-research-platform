# Implementation Roadmap
## Commodity Systematic Research Platform

**Purpose:** Defines the module development sequence for the full platform. Covers all completed phases (Phase 1, Phase 2, Phase 3, EM1–EM14, F-Track + FEP) with actual deliverables, deviations, and final platform state.

**Principle:** Build one vertical slice end-to-end before expanding horizontally. Validate per-asset signal quality before building portfolio infrastructure.

**Status:** Phase 1 COMPLETE (M01–M07). Phase 2 COMPLETE (M08–M13). Phase 3 COMPLETE (M14–M19). Enhancement Modules COMPLETE (EM1–EM14). F-Track + FEP COMPLETE. E2E Suite COMPLETE.

---

## Phase 1 — Research MVP (COMPLETE)

**Tag:** `phase-1-complete` after M07, `pre-phase-2-complete` after sprint
**Tests:** 107 passing
**Branch history:** M01–M07 on main, pre-phase-2 sprint on main

### Module 1: Repository Initialization (COMPLETE — 17 tests)

**Deliverables:**
- Full repository skeleton, `config.yaml`, `assets.yaml`, `strategies.yaml`
- `src/core/types.py` — all Phase 1 type stubs
- `src/core/registry.py` — abstract base classes: DataSource, Indicator, SignalGenerator, BacktestEngine, PositionSizer
- `src/core/config.py` — config loader with YAML validation
- `tests/conftest.py` — synthetic Gold OHLCV fixture (252 bars), loaded config

---

### Module 2: Data Layer (COMPLETE — 30 tests)

**Deliverables:**
- `LocalCSVSource` with `strict_ohlc=False` for Yahoo Finance continuous data
- `OHLCVValidator(strict_ohlc: bool = True)` — configurable OHLC strictness
- `OHLCVNormalizer` — clears `attrs = {}` before return (prevents pyarrow UserWarning)
- `ParquetStore` — read/write with pyarrow engine
- `DataLoader` — re-populates `asset`, `source`, `continuous` attrs after both fast and slow paths

**Key deviation from original spec:** `strict_ohlc=False` added to validator for Yahoo Finance settlement price mixing artifact and WTI negative price event (2020-04-20: −$37.63).

---

### Module 3: Feature Engineering Layer (COMPLETE — 53 tests)

**Deliverables:**
- `Indicator` ABC with `column_name` property
- `FeatureFrame` wrapper + `FeatureSpec` dataclass
- SMA, EMA, RSI, RVGI, Momentum implementations
- `FeaturePipeline.compute(ohlcv, indicators)` → FeatureFrame

---

### Module 4: Signal Research Layer (COMPLETE — 66 tests)

**Deliverables:**
- `SignalGenerator` ABC
- `SignalEvaluator`: IC, ICIR, signal decay at 5 horizons, turnover
- `EMACrossoverSignal`, `MomentumSignal`, `RSIReversionSignal`, `DonchianBreakoutSignal`
- `PositionSignalConstructor.build(raw_signal, threshold)` → PositionSignal

---

### Module 5: Backtesting Engine (COMPLETE — 86 tests)

**Deliverables:**
- `CostModel(commission_per_trade, slippage_ticks)`
- `FixedNotionalSizer(notional_usd=100_000.0)`
- `TradeLog` — trade boundary detection, force-close at period end
- `VectorizedBacktester.run(position_signal, ohlcv)` → BacktestResult
- `RunManager.save(result)` → file artifacts at `data/runs/{run_id}/`

---

### Module 6: Performance Layer (COMPLETE — 107 tests)

**Deliverables:**
- All 16 scalar metrics: total_return, cagr, sharpe, sortino, calmar, max_drawdown, avg_drawdown, win_rate, profit_factor, avg_trade_duration_bars, turnover, avg_win, avg_loss, largest_win, largest_loss, initial_capital
- Rolling metrics: rolling_sharpe_63, rolling_sharpe_126, rolling_vol_63, rolling_drawdown
- `PerformanceEngine.compute(backtest_result)` → PerformanceReport
- `RunManager.save_metrics(run_id, report)` → writes `metrics.json`

---

### Module 7: Dashboard Pages 1–5 (COMPLETE — 107 tests)

**Deliverables:**
- Institutional dark theme (#0e1628) with CSS injection, monospace font
- `_theme.py`: `inject_global_css()`, `section_header()`, `render_kpi_row()`
- Pages 1–5 with dark theme, no emoji, `use_container_width` removed
- IC direction labels: 5-way classification (positive/inverse/weak positive/weak inverse/noise)
- Launcher scripts (`launch_dashboard.ps1`, `launch_dashboard.sh`) calling `.venv` streamlit directly
- Real continuous futures data: 6 assets, 4,100–4,150 bars each (2010–2026)

**Additional sprint deliverables (pre-phase-2-complete):**
- `scripts/acquire_data.py` — downloads all 6 continuous assets
- README with IC-before-backtest workflow documentation
- Git cleanup: 23 Cursor attribution commits removed via git filter-repo

---

## Phase 2 — Commodity Intelligence (COMPLETE)

**Tag:** `phase-2-complete` after M13
**Tests:** 186 passing
**Branch history:** M08–M13 merged to main

Phase 2 began after Phase 1 is complete and all tests pass.

### Module 8: Contract Data Layer (COMPLETE — 128 tests)

**Purpose:** Individual futures contract OHLCV data ingestion, validation, storage.

**Files created:**
- `src/data/sources/futures_contract.py` — `FuturesContractSource`, `parse_contract_ticker()`
- `src/data/contract_store.py` — `ContractStore` ABC, `ContractParquetStore` (with `.meta.json` sidecar)
- `src/data/contract_loader.py` — `ContractDataLoader`
- `scripts/acquire_contract_data.py`
- `tests/test_contract_data.py` — 21 tests

**Files modified:**
- `config/config.yaml` — added `contracts_raw`, `contracts_processed` path keys
- `config/assets.yaml` — added `contract_root`, `exchange_suffix` to all 6 assets
- `src/core/types.py` — added `ContractMetadata` dataclass

**Key design:** Exchange suffix (`.CMX`/`.NYM`) is a yfinance API concern only. Canonical tickers (GCZ24) used for storage. `yf.Ticker(yf_ticker).history(period="max")` for download. Dividends and Stock Splits dropped before CSV write. Timezone stripped before `to_csv()` for OHLCVNormalizer compatibility.

**End-to-end gate:** GCZ25 loaded with 1,510 bars; 3-contract forward curve constructed.

---

### Module 9: Futures Curve Layer (COMPLETE — 145 tests)

**Purpose:** Construct `FuturesCurve` snapshots from contract data.

**Files created:**
- `src/commodity/curve.py` — `FuturesCurveBuilder`
- `tests/test_futures_curve.py` — 17 tests

**Files modified:**
- `src/core/types.py` — added `CurvePoint`, `FuturesCurve` dataclasses

**Key design:** `_build_curve_point()` finds last available price on or before observation_date. `FuturesCurveBuilder.build()` re-raises with own `ValueError` using `from None` — each layer owns its error surface.

**End-to-end gate:** Gold 6-contract forward curve in contango, slope 0.482 USD/day.

---

### Module 10: Term Structure Analytics (COMPLETE — 160 tests)

**Purpose:** Compute contango/backwardation slope, roll yield, basis, and regime classification.

**Files created:**
- `src/commodity/term_structure.py` — `TermStructureAnalyzer`
- `tests/test_term_structure.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `TermStructureRegime(str, Enum)`, `TermStructureSnapshot` dataclass

**Key implementation notes:**
- `TermStructureRegime` uses `str, Enum` (not `StrEnum` — Python 3.11+ only). Requires explicit `__str__` returning `self.value` in Python 3.11 due to MRO change.
- `continuous_close` passed as parameter to `analyze()` — analyzer never calls `DataLoader` directly.
- Default `regime_threshold`: 0.005 (0.5%/yr annualized slope).

**End-to-date gate:** Gold contango 4.33% annualized, roll yield −3.57%, basis −95.90.

---

### Module 11: Volatility Scaled Sizer (COMPLETE — 176 tests)

**Purpose:** Risk-normalized position sizing targeting fixed annualized vol contribution.

**Files created:**
- `tests/test_volatility_sizer.py` — 16 tests

**Files modified:**
- `src/core/registry.py` — added `configure(ohlcv)` no-op to `PositionSizer` ABC
- `src/backtesting/sizing.py` — appended `VolatilityScaledSizer`
- `src/backtesting/engine.py` — added `sizer` parameter + `sizer.configure(ohlcv)` call

**Key implementation notes:**
- ABC method is `compute_size(signal, asset, equity)` not `size(signal, equity)`. Bridge pattern used.
- `FixedNotionalSizer` constructor: `notional_usd=` (not `notional=`).
- `configure()` placed before `trade_log.build()` (vectorized engine has no explicit for loop).
- Known technical debt: TD-B (static equity), TD-C (end-of-sample vol estimate) — both resolved in EM2.

**End-to-end gate:** Gold realized vol 23.49%/yr → vol-scaled max position $42,567 vs $100,000 fixed. Equal 1.00% vol contributions confirmed.

---

### Module 12: MLflow Integration (COMPLETE — 186 tests)

**Purpose:** Experiment tracking via MLflow local filesystem backend.

**Files created:**
- `tests/test_mlflow_integration.py` — 10 tests

**Files modified:**
- `config/config.yaml` — added `mlflow.tracking_uri`, `mlflow.experiment_prefix`
- `src/core/config.py` — added `mlflow_tracking_uri`, `mlflow_experiment_prefix` properties
- `src/backtesting/run_manager.py` — added `_try_log_to_mlflow()`, `_sanitize_mlflow_key()`
- `pyproject.toml` — added `mlflow>=2.0` (installed: mlflow 3.14.0)

**Key implementation notes:**
- MLflow logging in `save_metrics()` (not `save()`); reads `params.json` from disk.
- MLflow 3.x requires `MLFLOW_ALLOW_FILE_STORE=true`; set via `os.environ.setdefault()`.
- Deferred `import mlflow` inside function body for graceful degradation.
- All 16 scalar metrics logged. `file_run_id` tag cross-references file artifacts.

**End-to-end gate:** `commodity_research_gold` experiment created, all metrics logged, `file_run_id` tag confirmed.

---

### Module 13: Dashboard Page 6 — Futures Curve (COMPLETE — 186 tests)

**Purpose:** Presentation layer for commodity intelligence — forward curve, regime KPIs, history.

**Files created:**
- `dashboard/components/curve_chart.py`
- `dashboard/pages/6_futures_curve.py`

**Page 6 structure:**
- Sidebar: asset selector (from `available_assets()`), n_contracts slider, lookback slider, Refresh button
- Section 1: KPI row — Regime, Front Price, Slope, Roll Yield, Basis
- Section 2: Forward curve bar chart with line overlay
- Section 3: Basis display
- Section 4: Historical dual-subplot chart (slope + roll yield)
- Section 5: Data Quality expander with contract inventory

**Known technical debt at time (resolved pre-Phase 3):** `builder._loader.list_contracts(asset)` accesses private attribute — resolved by adding public `list_contracts()` to `FuturesCurveBuilder`.

---

## Phase 3 — Portfolio Analytics (COMPLETE)

**Tag:** `phase-3-complete` after M19
**Tests:** 267 passing (188 after Phase 2 + 79 in Phase 3)
**Infrastructure:** ClickHouse 24.3 running via Docker, 24,862 rows migrated

Phase 3 began after Phase 2 was complete and all 188 tests passed.

### Pre-Phase 3 Housekeeping (COMPLETE)

- Added `FuturesCurveBuilder.list_contracts(asset)` public method (resolved private attr access from Page 6)
- Acquired contract data for silver, copper, wti, brent, natural_gas
- All 6 assets confirmed in `data/processed/contracts/`

---

### Module 14: Multi-Asset Runner (COMPLETE — 203 tests)

**Purpose:** Execute `VectorizedBacktester` across all 6 assets, aggregate into portfolio equity curve.

**Files created:**
- `src/backtesting/multi_asset.py` — `MultiAssetRunner`
- `tests/test_multi_asset.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `MultiAssetBacktestResult` dataclass

**Key design:**
- Per-asset pipeline: DataLoader → FeaturePipeline → SignalGenerator → SignalEvaluator → PositionSignalConstructor → VectorizedBacktester
- Portfolio equity = sum of per-asset equity curves (inner-join alignment)
- Portfolio PnL = zero-filled sum of per-asset PnL series
- Skips failed assets gracefully; raises ValueError only if all fail
- Capital model: each asset gets same initial capital ($1,000,000) independently
- TD-M14-A: `_build_pipeline_components()` duplicates dashboard logic — deferred to EM1

**End-to-end gate:** EMA 50/200 on all 6 assets, 166 total trades, portfolio equity $6,000,000→$6,074,759 (+1.25%).

---

### Module 15: Portfolio Performance (COMPLETE — 218 tests)

**Purpose:** Portfolio-level Sharpe, drawdown, attribution; portfolio run persistence.

**Files created:**
- `src/performance/portfolio.py` — `PortfolioPerformanceEngine`, `save_portfolio_summary()`
- `tests/test_portfolio_performance.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `PortfolioPerformanceReport` dataclass

**Key design:**
- `asset_contributions`: fractional P&L (unstable near-zero denominator — see TD-M15-C)
- `absolute_pnl_by_asset`: USD P&L per asset (always stable, added pre-M19 housekeeping)
- `portfolio_date_range`: surfaces inner-join date restriction explicitly
- `save_portfolio_summary()`: writes JSON artifact to `data/runs/{run_id}/`

**End-to-end gate:** Portfolio Sharpe 0.0018, CAGR 0.08%, max_drawdown -7.37%, portfolio vol 2.54%.

---

### Module 16: Risk Analytics (COMPLETE — 233 tests)

**Purpose:** Portfolio-level VaR, ES, and notional exposure.

**Files created:**
- `src/risk/__init__.py`
- `src/risk/risk_engine.py` — `RiskEngine`
- `tests/test_risk_analytics.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `RiskReport` dataclass

**Key design:**
- Historical simulation VaR (no parametric assumption — correct for fat-tailed commodity returns)
- `_compute_var()`: abs(quantile(1-confidence)) over lookback_days; NaN if < 20 obs
- `portfolio_diversification_benefit` property: sum(asset_var_99) / portfolio_var_99

**End-to-end gate:** Portfolio VaR95 $31,948 (0.53%), VaR99 $44,490 (0.74%), ES99 $99,095, diversification benefit 2.23×.

---

### Module 17: Cross-Asset Correlation (COMPLETE — 248 tests)

**Purpose:** Pairwise correlation matrix and rolling correlations of strategy returns.

**Files created:**
- `src/analytics/__init__.py`
- `src/analytics/correlation.py` — `CorrelationEngine`
- `tests/test_correlation.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `CorrelationReport` dataclass

**Key design:**
- Returns computed as `pnl_series / initial_capital_per_asset` (not equity.pct_change())
- Rolling correlations: upper triangle only (a < b alphabetically) — TD-M17-A
- `min_periods=window` for rolling to avoid noisy early estimates

**End-to-end gate (adjusted):** Gold-Silver strategy corr 0.65, WTI-Brent 0.62, avg_pairwise 0.12.

---

### Module 18: ClickHouse Integration (COMPLETE — 264 tests)

**Purpose:** Analytical query layer over processed Parquet data.

**Files created:**
- `docker-compose.yml` — ClickHouse 24.3-alpine container
- `scripts/setup_clickhouse_schema.py`, `scripts/migrate_to_clickhouse.py`
- `src/data/clickhouse_store.py` — `ClickHouseStore` implementing `DataStore` ABC
- `tests/test_clickhouse_store.py` — 16 mocked tests

**Files modified:**
- `config/config.yaml` — added `storage` section (backend: "parquet" default)
- `src/core/config.py` — added 6 ClickHouse config properties
- `src/data/loader.py` — conditional ClickHouseStore vs ParquetStore

**Key deviations from spec:**
- D1: config.xml thread settings removed (ClickHouse 24.3 incompatible)
- D2: setup_clickhouse_schema.py handles `CREATE DATABASE IF NOT EXISTS` first
- D3: `send_receive_timeout` wired through as 6th config property

**End-to-end gate:** 24,862 rows across 6 assets. Parquet vs ClickHouse equivalence at rtol=1e-6.

---

### Pre-M19 Housekeeping (COMPLETE — 265 tests)

- Added `absolute_pnl_by_asset: dict[str, float]` to `PortfolioPerformanceReport` (resolves TD-M15-C: asset_contributions near-zero denominator collapse — Gold +2379%, NG -2561% observed on real data)
- Updated `PortfolioPerformanceEngine._compute_asset_contributions()` to compute it
- Added 1 test to `tests/test_portfolio_performance.py`

---

### Module 19: Dashboard Page 7 — Cross-Asset Analytics (COMPLETE — 267 tests)

**Purpose:** Final Phase 3 module. Surfaces all Phase 3 analytics in Streamlit dashboard.

**Files created:**
- `dashboard/components/correlation_heatmap.py`
- `dashboard/pages/7_cross_asset_analytics.py`

**Files modified:**
- `src/performance/portfolio.py` — added `save_portfolio_summary()` function
- `src/core/types.py` — `absolute_pnl_by_asset` field (pre-M19 housekeeping)
- `tests/test_portfolio_performance.py` — 2 new tests for `save_portfolio_summary()`

**Page 7 structure (7 sections):**
1. Portfolio Performance KPIs (Sharpe, Max DD, Total Return, CAGR, Vol)
2. Portfolio Equity Curve
3. Asset Attribution (absolute USD P&L, conditional fractional)
4. Risk Summary (VaR 95/99, ES 99, Diversification Benefit)
5. Correlation Matrix Heatmap (6×6 annotated)
6. Rolling Correlations (63 or 126-day, selectable pairs)
7. Strategy Realized Volatility per asset + portfolio

**Phase 3 open points disposition:**
- TD-M15-C (absolute_pnl denominator): CLOSED
- TD-M17-A (upper-triangle rolling): CLOSED
- Portfolio persistence (ADR-009 Phase 3): CLOSED
- Strategy vol vs price vol labeling: CLOSED
- TD-M14-A (pipeline_builder): DEFERRED to EM1
- TD-B (static equity), TD-C (end-of-sample vol): DEFERRED to EM2

**Tags on main after M19:** `M19-complete`, `phase-3-complete`

---

## Enhancement Modules EM1–EM14 (COMPLETE)

**Final tag:** `EM14-complete`
**Tests:** 429 passing (fast suite: 409, full suite: 429 including 20 `@slow`)
**CI:** mypy enforced (0 errors, 67 source files), ruff 0 errors
**Repository:** `C:\Dev\Commodity-Systematic-Research-Platform` (local disk, not OneDrive)

---

### EM1 — Foundation and Engine Correctness (COMPLETE — 334 tests)

**Deliverables:**
- `tests/fixtures/engine_golden_master.json` — n_trades=21, final_equity=1,086,124.91. Locked.
- `src/backtesting/pipeline_builder.py` — canonical strategy dispatch extracted from dashboard. Sequential `if`-blocks with early return, always returns 2-tuple `(indicators, signal_gen)`. Closes TD-M14-A.
- Epoch-ms timestamp fix: all OHLCV datetime indices serialized as epoch milliseconds in API responses.
- CI via GitHub Actions: ruff + pytest on every push.

**Permanent corrections (DEV-EM5-1):** `build_pipeline_components` → `(indicators, signal_gen)` 2-tuple always.

---

### EM2 — Engine Correctness: Rolling Equity + Point-in-Time Vol (COMPLETE — 339 tests)

**Deliverables:**
- Rolling MTM equity in `VectorizedBacktester` (TD-B resolved — Option A proxy)
- Point-in-time volatility scaling in `VolatilityScaledSizer.configure()` — stores rolling `_vol_series` indexed by date (TD-C resolved)
- `PerformanceEngine` confirmed at `src.performance.report` (DEV-EM6 correction)

---

### EM3 — Portfolio Persistence (COMPLETE — 342 tests)

**Deliverables:**
- All 7 artifact types confirmed written before status flips to `complete`
- Disk fallback in portfolio API: reads from `data/runs/{run_id}/portfolio_summary.json` post-restart
- `load_run(run_id)` → dict confirmed as the correct `RunManager` read interface (DEV-EM8-1)

---

### EM4 — Risk Analytics Depth (COMPLETE — 348 tests)

**Deliverables:**
- 9 new `RiskReport` fields: `n_backtesting_days`, `exceptions_95/99`, `exception_rate_95/99`, `kupiec_lr_99`, `kupiec_pvalue_99`, `asset_contribution_to_vol`, `asset_contribution_to_vol_pct`
- Kupiec LR test: p < 0.05 → model is miscalibrated
- Contribution-to-risk: marginal vol contribution via incremental removal, normalized to sum ~1.0

**End-to-end gate:** Gold + Silver 2-asset portfolio, 252 days, Kupiec p=0.7680 (well-calibrated).

---

### EM5 — Statistical Validation (COMPLETE — 369 tests)

**Files created:**
- `src/validation/walk_forward.py` — `WalkForwardValidator`
- `src/validation/inference.py` — `sharpe_se()`, `psr()`, `dsr()` (scipy-free)
- `src/validation/mlflow_client.py` — `get_trial_count(asset, strategy)`
- `src/validation/report.py` — `ValidationReport` assembly

**Key design:**
- Expanding windows: `test_size = (n - min_train_bars - embargo_bars) // n_splits`
- Default: 5 folds, 10 embargo bars
- scipy-free: Beasley-Springer-Moro approximation for normal CDF

**API:** `POST /api/validation/run` → 202 + job_id. `GET /api/validation/{id}/status`. `GET /api/validation/{id}/report`.

**Permanent corrections (DEV-EM5-2):** `PerformanceEngine` at `src.performance.report`.

---

### EM6 — Rolling IC Endpoint (COMPLETE — 376 tests)

**Files modified:**
- `src/signal/evaluation.py` — `SignalEvaluator.compute_rolling_ic()`
- `api/routers/signals.py` — `GET /api/signals/rolling-ic`

**Key design:** Uses raw signal (not position signal), consistent with static IC. `SignalEvaluator(asset, ic_rolling_window)`.

**Permanent corrections (DEV-EM6):** `src/signal/evaluation.py`; `SignalEvaluator(asset, ic_rolling_window)`.

---

### EM7 — Carry Signal (COMPLETE — 382 tests)

**Files created:**
- `src/signal/carry.py` — `CarrySignal`

**Key design:** Loads `FuturesCurve` snapshots via `FuturesCurveBuilder.build_historical_curves()`. Roll yield z-score as carry measure. Graceful flat signal when FuturesCurve unavailable.

**Confirmed behavior on real data (Gold full history):** 0 long, 443 short, 3705 flat. Gold structurally in contango — near-flat carry signal is the institutionally correct finding.

**API timeout fix (44a75f1):** 2-year default date range when no `from_date` provided. 120s hard timeout with HTTP 408.

**Permanent corrections (DEV-EM7-1 through DEV-EM7-4):** See ADR-014.

---

### EM8 — Regime Attribution Engine (COMPLETE — 388 tests)

**Files created:**
- `src/analytics/regime_attribution.py` — `RegimeAttributionEngine`

**Key design:**
- Regime keys always lowercase: "contango", "backwardation", "flat" (DEV-EM8-3)
- Minimum 20 days per regime for valid statistics
- `_RunProxy`, `_TradeProxy`, `_convert_trades`, `_make_run_proxy` live in `src/analytics/` (Layer 7 owns these — no upward import to api/)
- `trades` from `load_run()` is `pd.DataFrame` — `_convert_trades()` handles conversion

**Post-validation (TD-EM8-C):** Portfolio regime via `compute_portfolio()` — ThreadPoolExecutor 6 assets parallel, ~90s. `_regime_report_to_dict()` replaced with `dataclasses.asdict()` + `_make_json_safe()` (TD-EM8-C-4). `has_regime_attribution` flag in `portfolio_summary.json` (TD-EM8-C-6).

**Permanent corrections (DEV-EM8-1 through DEV-EM8-6):** See ARCHITECTURE §5 Layer 7.

---

### EM9 — SweepRunner (COMPLETE — 396 tests)

**Files created:**
- `src/backtesting/sweep_runner.py` — `SweepRunner`

**Key design:**
- OHLCV loaded once before combination loop
- Each combination in try/except → graceful `SweepRunSummary(status="failed")` on error
- MLflow `sweep_id` tag per combination for DSR trial count
- `progress_callback: Callable[[int], None] | None = None` — increments `n_complete` (EM14)

**API:** `POST /api/sweeps` → 202 + sweep_id. `GET /api/sweeps/{id}/status`. `GET /api/sweeps/{id}/results`.

**Permanent corrections (DEV-EM9-1 through DEV-EM9-4):** MLflow search needs concrete experiment_id; `RunManager.save()` returns Path; `BacktestResult.run_id` set by `VectorizedBacktester.run()`.

---

### EM10 — Testing Infrastructure (COMPLETE — 402 tests)

**Files created:**
- `tests/test_engine_properties.py` — Hypothesis property tests (`@pytest.mark.slow`)
- `src/data/acquisition_qc.py` — `compute_qc()` → `QCReport`
- `scripts/reproduce_run.py` — equity curve hash verification

**Key notes:**
- Hypothesis registered as `@pytest.mark.slow` — excluded from fast suite with `-m "not slow"`
- OHLC constraint flags in QCReport are expected Yahoo Finance artifacts: Gold 25, Silver 57, Copper 29, Brent 34, NatGas 1 violations; WTI 0.
- `reproduce_run.py`: exit 0=match, 1=mismatch, 2=error

**Permanent corrections (DEV-EM10-1):** `Config.load()` — no arguments.

---

### EM11 — Curve PCA (COMPLETE — 407 tests)

**Files created:**
- `src/commodity/pca.py` — `CurvePCAEngine`

**Key design:**
- Price matrix normalization: `price[t,i] / price[t,0]` (shape PCA, not level PCA)
- sklearn PCA preferred, numpy SVD fallback
- `FuturesCurve.prices` property is primary access path (DEV-EM11)

**Confirmed results:** Gold PC1≈100% (near-constant term structure — correct). WTI and NatGas: meaningful 3-factor decompositions.

**API fix (44a75f1):** `run_in_executor` — no event loop blocking. 3-year default when no `from_date`.

---

### EM12 — WTI-Brent Spread Signal (COMPLETE — 411 tests)

**Files created:**
- `src/signal/spread.py` — `WTIBrentSpreadSignal`

**Key design:** Engle-Granger cointegration. Numpy-only ADF (no scipy). Requires `asset='wti'`.

**Confirmed cointegration:** ADF p=0.0030, cointegrated at 1% significance.

---

### EM13 — Alternative Data: COT + EIA (COMPLETE — 424 tests)

**Files created:**
- `src/data/cot_loader.py`, `src/data/eia_loader.py`
- `src/signal/cot.py`, `src/signal/eia.py`
- `scripts/acquire_cot_data.py`, `scripts/acquire_eia_data.py`

**Key implementation notes:**
- CFTC URL: `dea/history/fut_disagg_txt_{year}.zip` (not `dta/files/...`)
- Managed Money columns: `m_money_positions_long/short_all` (not Non-Commercial)
- Market name strings: copper=`COPPER- #1`, WTI=`WTI-PHYSICAL`, NatGas=`NAT GAS NYME`
- Dual date column schema (2010–2012 vs 2013+ format) handled in parser
- CFTC requires `User-Agent: Mozilla/5.0` header; SSL verification disabled on Windows
- COT `percentile_rank`: 0–100 scale throughout entire pipeline
- `EIA_SUPPORTED_ASSETS` public constant in `eia_loader.py`
- Brent has no COT data (ICE London, not CME) — correct behavior

**Confirmed COT data:** Gold/Silver 604 records (2015+), Copper/WTI/NatGas 234 records (2022+). EIA: 2,287 weekly records.

**Permanent corrections (DEV-EM13):** All CFTC URL, column name, and scale corrections above.

---

### EM14 — Async Improvements (COMPLETE — 429 tests)

**TD-FEP-PORTFOLIO-RACE:** `persisting` status for portfolio background task. Eliminates ~1–2 second window where frontend polls and receives 404.

**TD-FEP-REGIME-ASYNC:** POST/poll/result async regime attribution. `_regime_tasks` dict + disk at `data/regime_attribution/{job_id}/result.json`. Post-restart: endpoint serves from disk.

**TD-FEP-SWEEP-PROGRESS:** `progress_callback` in `SweepRunner.run_sweep()`. Updates `_sweep_tasks[sweep_id]["n_complete"]` after each successful combination.

**TD-CI-MYPY:** mypy enforced in CI. `numpy.*` ignore override in `[tool.mypy]`. `pipeline_builder.py` 3 mypy errors fixed. Result: 0 errors on 67 source files.

**Post-EM14 hotfix (f3b6b55):** `_RunProxy` typed as `@dataclass`. `_convert_trades()` named function — handles `trades` as `pd.DataFrame` from `load_run()`.

**TD-EM8-C (shipped post-EM14):** Portfolio regime attribution frontend complete.
- `_RunProxy`, `_TradeProxy`, `_convert_trades`, `_make_run_proxy` in `src/analytics/` (correct layer direction)
- `POST /api/regime-attribution/compute-portfolio` → 202 + job_id
- `GET /api/regime-attribution/{job_id}/portfolio-result` → `PortfolioRegimeAttributionResponse`
- `_regime_report_to_dict()` replaced with `dataclasses.asdict()` + `_make_json_safe()` (TD-EM8-C-4)
- `has_regime_attribution` flag in `portfolio_summary.json` (TD-EM8-C-6)

---

## F-Track + FEP — React + FastAPI Frontend (COMPLETE)

**Tags:** `FEP-complete` | **Tests:** 406 vitest, 114 E2E passed / 3 skipped / 0 failed

**F-Track Phase F0: FastAPI Shell**
- 30+ endpoints, async job pattern throughout
- Pydantic model layer, OpenAPI generation, TypeScript schema.d.ts
- `GET /api/health` (webServer startup gate)

**F-Track Phases F1–F18: React/TypeScript SPA**
- 13 screens across all platform capabilities
- IC Gate enforcement in Research Workbench
- Dark institutional theme, monospace, ECharts
- TanStack Query (server state), Zustand (workspace), URL (navigation)
- `useRef + useEffect` for all ECharts, `resolveCssVar()` for all colors

**FEP — Frontend Enhancement Pass**
All deferred frontend work consolidated. TD items closed:

| ID | Description |
|---|---|
| TD-FEP-PORTFOLIO-RACE | persisting status (EM14) |
| TD-FEP-REGIME-ASYNC | Async regime attribution endpoints (EM14) |
| TD-FEP-SWEEP-PROGRESS | Live n_complete during sweep (EM14) |
| TD-FEP-PORTFOLIO-RUNSELECTOR | Run selector with Sharpe column |
| TD-FEP-PORTFOLIO-DATERANGE | Date range pickers matching Research Workbench pattern |
| TD-RUN-EXPLORER-PERF | SQLite index: 30s → 0.45s |
| TD-RUN-SORT | ORDER BY wired with SAFE_SORT_COLUMNS allowlist |
| TD-EM8-C | Portfolio regime attribution frontend |
| TD-CI-MYPY | mypy in CI (EM14) |

**Signal registry fixes (44a75f1):** `wti_brent_spread`, `cot_positioning`, `eia_inventory` registered in both `_build_signal_pipeline` and `_build_full_pipeline`. Previously caused `400 UNKNOWN_STRATEGY` for backtest launch.

**E2E Suite**
- Files created: `helpers.ts`, `strategies.spec.ts`, `cross-screen.spec.ts`, `error-states.spec.ts`
- Files extended: `research.spec.ts`, `backtest.spec.ts`, `explorer.spec.ts`, `portfolio.spec.ts`, `inc6-screens.spec.ts`, `intelligence.spec.ts`, `inc7-data-manager.spec.ts`
- Scripts added: `test:e2e` (excludes `@slow`), `test:e2e:full`, `test:e2e:report`
- Result: 114 passed / 3 skipped / 0 failed

**Permanent skips (by design):**

| Test | Reason |
|---|---|
| Run Detail a11y | Requires live run ID — API-dependent |
| Run Explorer a11y | Same |
| Sweep row → Run Detail | By design per S-FEP-1 |

**Architectural discoveries confirmed by E2E:**
- IC state: TanStack Query cache (not Zustand) — resets on `page.goto()`
- ICGateStrip gate: `isEnabled = evaluation !== null && band !== 'noise' && band !== null`
- StrategyPicker renders as buttons — `getByRole('button', { name })` not combobox
- Tab state resets on navigation — by design per TDR-014
- POST /api/backtests (202) — not /api/backtests/run (404)
- Portfolio runs: `GET /api/portfolio/runs` (separate from `GET /api/runs`)
- Portfolio URL param: `?run_id=` (snake_case)

---

## Final Platform State

| Layer | Status | Tests |
|---|---|---|
| Backend (Phase 1–3 + EM1–EM14) | Complete | 409 fast / 429 full |
| Frontend (F-track + FEP) | Complete | 406 vitest |
| E2E suite | Complete | 114 passed / 3 skipped / 0 failed |
| TypeScript | Clean | 0 errors |
| Build | Exits 0 | — |
| ruff | Clean | 0 errors |
| mypy | Clean | 0 errors (67 source files) |
| CI | Green | ruff + pytest on every push |

**Enhancement register: fully closed.** All TD items resolved or accepted. Three permanent E2E skips documented.

---

## Development Checklist Before Starting Each Module

Before implementing any module:

- [ ] Re-read the relevant layer section in `ARCHITECTURE_final.md`
- [ ] Re-read the ADRs that apply to this module
- [ ] Confirm layer contracts for this module's inputs and outputs in `src/core/types.py`
- [ ] Write tests first (TDD) or immediately after the first working implementation
- [ ] Update `ARCHITECTURE_final.md` if implementation reveals a deviation from the design
- [ ] Log any unexpected decisions in `docs/implementation_notes/`
- [ ] `SignalGenerator.name` is `@property abstractmethod` — never a class attribute (DEV-EM7-1)
- [ ] `RawSignal` is `pd.Series` with `series.name = self.name` set before returning (DEV-EM7-2)
- [ ] `feature_frame.data.index`; `.asset` is `@property` — not `_asset` (DEV-EM7-3)
- [ ] `pipeline_builder.py`: sequential if-blocks, early return, 2-tuple always (DEV-EM7-4)
- [ ] Two catalog locations per strategy: `api/routers/signals.py` + `api/routers/backtests.py` (DEV-EM7-5)
- [ ] `RunManager.load_run(run_id)` → dict; no `.load()` method (DEV-EM8-1)
- [ ] `TermStructureRegime` str() returns lowercase — regime dict keys always lowercase (DEV-EM8-3)
- [ ] `BacktestResult.run_id` is set by `VectorizedBacktester.run()` (DEV-EM9-3)
- [ ] `Config.load()` — no arguments (DEV-EM10-1)
- [ ] `FuturesCurve.prices` property is primary access path; `.points[N].close` fallback (DEV-EM11)
- [ ] COT `percentile_rank` is 0–100 scale — frontend must not multiply by 100 (DEV-EM13)
- [ ] `PerformanceEngine` at `src.performance.report` (not `.engine`) (DEV-EM5-2)
- [ ] `FixedNotionalSizer` constructor uses `notional_usd=` (not `notional=`)
- [ ] `compute_size(signal, asset, equity)` is the ABC method name (not `size()`)
- [ ] `types.py` uses `import datetime` (module import) — all annotations use `datetime.datetime` / `datetime.date`
- [ ] `import math` is present in `types.py` (added in M16)
- [ ] Rolling correlation lookup: always `rolling[min(a,b)][max(a,b)]` (upper-triangle only, TD-M17-A)

---

## Dependency Graph Summary

```
Phase 1:
Module 1 (Init)
    └── Module 2 (Data Layer)
            └── Module 3 (Feature Engineering)
                    └── Module 4 (Signal Research)
                            └── Module 5 (Backtesting Engine)
                                    └── Module 6 (Performance)
                                            └── Module 7 (Dashboard Pages 1-5)

Phase 2:
Module 7 (Phase 1 complete)
    └── Module 8 (Contract Data Layer)
            └── Module 9 (Futures Curve Layer)
                    └── Module 10 (Term Structure Analytics)
    └── Module 11 (Volatility Scaled Sizer)  [depends on M05 Layer 3]
    └── Module 12 (MLflow Integration)        [depends on M05 Layer 3]
    └── Module 13 (Dashboard Page 6)          [depends on M09, M10, M12]

Phase 3:
Module 13 (Phase 2 complete)
    └── Module 14 (Multi-Asset Runner)        [depends on M05, M11]
            └── Module 15 (Portfolio Performance)
            └── Module 16 (Risk Analytics)
            └── Module 17 (Cross-Asset Analytics)
                    └── Module 18 (ClickHouse)
                    └── Module 19 (Dashboard Page 7)  [depends on M15, M17, M18]

Enhancement Modules:
Phase 3 complete (backend frozen for F-track)
    └── EM1 (Foundation: golden master, pipeline_builder, CI)
            └── EM2 (Engine correctness: rolling equity, PIT vol)
            └── EM3 (Portfolio persistence: 7 artifacts)
            └── EM4 (Risk depth: Kupiec, contribution-to-risk)
            └── EM5 (Validation: walk-forward, PSR, DSR)
            └── EM6 (Rolling IC endpoint)
            └── EM7 (Carry signal)
            └── EM8 (Regime attribution)
            └── EM9 (SweepRunner + async API)
            └── EM10 (Testing infrastructure: Hypothesis, QC, reproduce)
            └── EM11 (Curve PCA)
            └── EM12 (WTI-Brent spread)
            └── EM13 (Alternative data: COT + EIA)
            └── EM14 (Async: persisting status, regime async, sweep progress, mypy CI)

F-Track + FEP:
EM1–EM14 complete (all backend endpoints stable)
    └── F0 (FastAPI shell)
            └── F1–F18 (React/TypeScript SPA)
                    └── FEP (All deferred frontend work)
                            └── TD-EM8-C (Portfolio regime frontend)
                                    └── E2E (Playwright test suite: 114/3/0)
```

No module should be started until its dependency is complete and its tests pass.
