# Implementation Roadmap
## Commodity Systematic Research Platform

**Purpose:** Defines the module development sequence for the full platform. Covers all completed phases (Phase 1, Phase 2, Phase 3) with actual deliverables, and the F-track (React + FastAPI frontend) specification.

**Principle:** Build one vertical slice end-to-end before expanding horizontally. Validate per-asset signal quality before building portfolio infrastructure.

**Status:** Phase 1 COMPLETE (M01–M07). Phase 2 COMPLETE (M08–M13). Phase 3 COMPLETE (M14–M19). F-Track in design.

---

## Phase 1 — Research MVP (COMPLETE)

**Tag:** `phase-1-complete` after M07, `pre-phase-2-complete` after sprint
**Tests:** 107 passing (186 after Phase 2)
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
**Branch history:** M08–M13 merged to main, individual module branches preserved

Phase 2 begins after Phase 1 is complete and all tests pass.

### Module 8: Contract Data Layer (COMPLETE — 128 tests)

**Purpose:** Individual futures contract OHLCV data ingestion, validation, storage.

**Files created:**
- `src/data/sources/futures_contract.py` — `FuturesContractSource`, `parse_contract_ticker()`
- `src/data/contract_store.py` — `ContractStore` ABC, `ContractParquetStore` (with `.meta.json` sidecar)
- `src/data/contract_loader.py` — `ContractDataLoader`: `load_contract()`, `load_curve()`, `list_contracts()`
- `scripts/acquire_contract_data.py` — `build_ticker()`, `build_yfinance_ticker()`, `ASSET_CONFIGS`
- `tests/test_contract_data.py` — 21 tests

**Files modified:**
- `config/config.yaml` — added `contracts_raw`, `contracts_processed` path keys
- `config/assets.yaml` — added `contract_root`, `exchange_suffix` to all 6 assets
- `src/core/types.py` — added `ContractMetadata` dataclass

**Key design:** Exchange suffix (`.CMX`/`.NYM`) is a yfinance API concern only. Canonical tickers (GCZ24) used for storage. `yf.Ticker(yf_ticker).history(period="max")` used for download. Dividends and Stock Splits dropped before CSV write. Timezone stripped before `to_csv()` for OHLCVNormalizer compatibility.

**End-to-end gate:** GCZ25 loaded with 1,510 bars; 3-contract forward curve constructed.

---

### Module 9: Futures Curve Layer (COMPLETE — 145 tests)

**Purpose:** Construct `FuturesCurve` snapshots from contract data.

**Files created:**
- `src/commodity/curve.py` — `FuturesCurveBuilder`: `build()`, `build_historical_curves()`, `available_assets()`, `_build_curve_point()`
- `tests/test_futures_curve.py` — 17 tests

**Files modified:**
- `src/core/types.py` — added `CurvePoint`, `FuturesCurve` dataclasses

**Key design:** `FuturesCurveBuilder._build_curve_point()` finds last available price on or before observation_date. `days_to_delivery` uses `date(year, month, 1)` as delivery proxy (no roll calendar). `FuturesCurveBuilder.build()` re-raises with own `ValueError` message using `from None` — each layer owns its error surface.

**End-to-end gate:** Gold 6-contract forward curve in contango, slope 0.482 USD/day.

---

### Module 10: Term Structure Analytics (COMPLETE — 160 tests)

**Purpose:** Compute contango/backwardation slope, roll yield, basis, and regime classification.

**Files created:**
- `src/commodity/term_structure.py` — `TermStructureAnalyzer`: `analyze()`, `analyze_series()`, `classify_regime()`, `contango_slope_annualized()`, `roll_yield_annualized()`, `compute_basis()`, `_compute_basis_pair()`
- `tests/test_term_structure.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `TermStructureRegime(str, Enum)`, `TermStructureSnapshot` dataclass

**Key implementation notes:**
- `TermStructureRegime` uses `str, Enum` (not `StrEnum` — Python 3.11+ only). Requires explicit `__str__` returning `self.value` in Python 3.11 due to MRO change.
- `continuous_close` passed as parameter to `analyze()` — analyzer never calls `DataLoader` directly.
- Default `regime_threshold`: 0.005 (0.5%/yr annualized slope).

**End-to-end gate:** Gold contango 4.33% annualized, roll yield −3.57%, basis −95.90 (continuous $4,078.70 vs front $4,174.60).

---

### Module 11: Volatility Scaled Sizer (COMPLETE — 176 tests)

**Purpose:** Risk-normalized position sizing targeting fixed annualized vol contribution.

**Files created:**
- `tests/test_volatility_sizer.py` — 16 tests

**Files modified:**
- `src/core/registry.py` — added `configure(ohlcv)` no-op to `PositionSizer` ABC (`# noqa: B027`)
- `src/backtesting/sizing.py` — appended `VolatilityScaledSizer`; added `import pandas as pd`, `import math`
- `src/backtesting/engine.py` — added `sizer: PositionSizer | None = None` parameter; `self._sizer.configure(ohlcv)` before `trade_log.build()`

**Key implementation notes:**
- ABC method is `compute_size(signal, asset, equity)` not `size(signal, equity)`. Bridge pattern used.
- `FixedNotionalSizer` constructor: `notional_usd=` (not `notional=`).
- `configure()` placed before `trade_log.build()` (vectorized engine has no explicit for loop).
- Known technical debt: TD-B (static equity), TD-C (end-of-sample vol estimate) — Phase 3.

**End-to-end gate:** Gold realized vol 23.49%/yr → vol-scaled max position $42,567 vs $100,000 fixed. Equal 1.00% vol contributions confirmed for Gold and NG proxies.

---

### Module 12: MLflow Integration (COMPLETE — 186 tests)

**Purpose:** Experiment tracking via MLflow local filesystem backend.

**Files created:**
- `tests/test_mlflow_integration.py` — 10 tests

**Files modified:**
- `config/config.yaml` — added `mlflow.tracking_uri`, `mlflow.experiment_prefix`
- `src/core/config.py` — added `mlflow_tracking_uri`, `mlflow_experiment_prefix` properties; added `self._config` attribute storing full YAML dict (gap in existing implementation)
- `src/backtesting/run_manager.py` — added `_try_log_to_mlflow()` private method, `_sanitize_mlflow_key()` module-level function, one-line call in `save_metrics()`
- `pyproject.toml` — added `mlflow>=2.0` (installed: mlflow 3.14.0)

**Key implementation notes:**
- MLflow logging in `save_metrics()` (not `save()`); reads `params.json` from disk.
- MLflow 3.x requires `MLFLOW_ALLOW_FILE_STORE=true`; set via `os.environ.setdefault()`.
- Deferred `import mlflow` inside function body for graceful degradation.
- `isinstance(v, int | float)` union syntax (ruff UP038) used for NaN filter.
- All 16 scalar metrics logged to MLflow run. file_run_id tag cross-references file artifacts.

**End-to-end gate:** `commodity_research_gold` experiment created, all metrics logged, `file_run_id` tag confirmed.

---

### Module 13: Dashboard Page 6 — Futures Curve (COMPLETE — 186 tests)

**Purpose:** Presentation layer for commodity intelligence — forward curve, regime KPIs, history.

**Files created:**
- `dashboard/components/curve_chart.py` — `render_forward_curve_chart()`, `render_term_structure_history_chart()` (pure functions, no `st.*`, TYPE_CHECKING guard on src/ imports)
- `dashboard/pages/6_futures_curve.py` — Page 6

**Files modified (pre-M13 housekeeping):**
- `src/backtesting/run_manager.py` — added `os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")`
- `launch_dashboard.ps1` — added `$env:MLFLOW_ALLOW_FILE_STORE = "true"`
- `launch_dashboard.sh` — added `export MLFLOW_ALLOW_FILE_STORE="true"`

**Page 6 structure:**
- Sidebar: asset selector (from `available_assets()`), n_contracts slider, lookback slider, Refresh button
- Section 1: KPI row — Regime, Front Price, Slope, Roll Yield, Basis
- Section 2: Forward curve bar chart with line overlay
- Section 3: Basis display (two `st.metric()` boxes — appropriate for 2-item display)
- Section 4: Historical dual-subplot chart (slope + roll yield)
- Section 5: Data Quality expander with contract inventory

**Known technical debt:** `builder._loader.list_contracts(asset)` accesses private attribute. Mitigation: add public `list_contracts()` to `FuturesCurveBuilder` as pre-M14 housekeeping.

**Manual verification:** All 17 checklist items confirmed on real Gold data.

**Post-merge action item:** Run `scripts/acquire_contract_data.py` for silver, copper, wti, brent, natural_gas before Phase 3 begins.

---

## Phase 3 — Portfolio Analytics (COMPLETE)

**Tag:** `phase-3-complete` after M19
**Tests:** 267 passing (188 after Phase 2 + 79 in Phase 3)
**Branch history:** M14–M19 merged to main, individual module branches preserved
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
- `src/backtesting/multi_asset.py` — `MultiAssetRunner.run(assets, strategy_name, parameters, sizer, signal_threshold)` → `MultiAssetBacktestResult`
- `tests/test_multi_asset.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `MultiAssetBacktestResult` dataclass

**Key design:**
- Per-asset pipeline: DataLoader → FeaturePipeline → SignalGenerator → SignalEvaluator (ADR-010) → PositionSignalConstructor → VectorizedBacktester
- Portfolio equity = sum of per-asset equity curves (inner-join alignment)
- Portfolio PnL = zero-filled sum of per-asset PnL series
- Skips failed assets gracefully; raises ValueError only if all fail
- Capital model: each asset gets same initial capital ($1,000,000) independently
- TD-M14-A: `_build_pipeline_components()` duplicates dashboard logic — deferred

**End-to-end gate:** EMA 50/200 on all 6 assets, 166 total trades, portfolio equity $6,000,000→$6,074,759 (+1.25%), portfolio == sum verified exactly.

---

### Module 15: Portfolio Performance (COMPLETE — 218 tests)

**Purpose:** Portfolio-level Sharpe, drawdown, attribution; portfolio run persistence.

**Files created:**
- `src/performance/portfolio.py` — `PortfolioPerformanceEngine.compute(multi_result)` → `PortfolioPerformanceReport`; `save_portfolio_summary(report, run_dir)` → `portfolio_summary.json`
- `tests/test_portfolio_performance.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `PortfolioPerformanceReport` dataclass

**Key design:**
- Runs `PerformanceEngine` on each per-asset BacktestResult
- Portfolio metrics: total_return, cagr, sharpe, sortino, calmar, max_drawdown, portfolio_vol, n_trading_days
- `asset_contributions`: fractional P&L (unstable near-zero denominator — see TD-M15-C)
- `absolute_pnl_by_asset`: USD P&L per asset (always stable, added as pre-M19 housekeeping)
- `portfolio_date_range`: surfaces inner-join date restriction explicitly
- `save_portfolio_summary()`: writes JSON artifact to data/runs/{run_id}/

**End-to-end gate:** Portfolio Sharpe 0.0018, CAGR 0.08%, max_drawdown -7.37%, portfolio vol 2.54%.

---

### Module 16: Risk Analytics (COMPLETE — 233 tests)

**Purpose:** Portfolio-level VaR, ES, and notional exposure.

**Files created:**
- `src/risk/__init__.py`
- `src/risk/risk_engine.py` — `RiskEngine.compute(multi_result, lookback_days=252)` → `RiskReport`
- `tests/test_risk_analytics.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `RiskReport` dataclass; added `import math`

**Key design:**
- Historical simulation VaR (no parametric assumption — correct for fat-tailed commodity returns)
- `_compute_var()`: abs(quantile(1-confidence)) over lookback_days; NaN if < 20 obs
- `_compute_es()`: mean of losses beyond VaR threshold; always ≥ VaR
- `_compute_notional_exposure()`: avg |positions| over active days (positions != 0)
- `portfolio_diversification_benefit` property: sum(asset_var_99) / portfolio_var_99

**End-to-end gate:** Portfolio VaR95 $31,948 (0.53%), VaR99 $44,490 (0.74%), ES99 $99,095, diversification benefit 2.23x, total avg gross notional $600,000 (exactly 6×$100K).

---

### Module 17: Cross-Asset Correlation (COMPLETE — 248 tests)

**Purpose:** Pairwise correlation matrix and rolling correlations of strategy returns.

**Files created:**
- `src/analytics/__init__.py`
- `src/analytics/correlation.py` — `CorrelationEngine.compute(multi_result)` → `CorrelationReport`
- `tests/test_correlation.py` — 15 tests

**Files modified:**
- `src/core/types.py` — added `CorrelationReport` dataclass

**Key design:**
- Returns computed as `pnl_series / initial_capital_per_asset` (not equity.pct_change())
- Rolling correlations: upper triangle only (a < b alphabetically) — TD-M17-A; Module 19 uses symmetry
- `min_periods=window` for rolling to avoid noisy early estimates
- Strategy vol ≠ price vol: realized_vol_by_asset (2–8%/yr for EMA 50/200) is strategy P&L vol

**End-to-end gate (adjusted):** Gold-Silver corr 0.65 (not ~0.85 — strategy return correlation vs price correlation). WTI-Brent corr 0.62 (confirmed structural relationship in rolling 63-day: 0.84–0.96 at end of sample). avg_pairwise 0.12 (low due to frequent flat periods). Gate threshold corrected to > 0.55 for WTI-Brent.

---

### Module 18: ClickHouse Integration (COMPLETE — 264 tests)

**Purpose:** Analytical query layer over processed Parquet data.

**Files created:**
- `docker-compose.yml` — ClickHouse 24.3-alpine container (ports 8123/9000)
- `docker/clickhouse/config.xml` — logger config only (thread settings incompatible with 24.3)
- `scripts/setup_clickhouse_schema.py` — idempotent DDL, ReplacingMergeTree on (asset, date)
- `scripts/migrate_to_clickhouse.py` — Parquet→ClickHouse migration, all 6 assets
- `scripts/m18_gate.py` — reusable verification gate script
- `src/data/clickhouse_store.py` — `ClickHouseStore` implementing `DataStore` ABC
- `tests/test_clickhouse_store.py` — 16 mocked tests (no Docker required for pytest)
- `docs/clickhouse/SETUP.md` — operator runbook

**Files modified:**
- `config/config.yaml` — added `storage` section (backend: "parquet" default)
- `src/core/config.py` — added 6 ClickHouse config properties (including `clickhouse_send_receive_timeout` after Tech Lead ruling)
- `src/data/loader.py` — conditional ClickHouseStore vs ParquetStore in `__init__`
- `pyproject.toml` — added `clickhouse-connect>=0.7`

**Key deviations from spec:**
- D1: config.xml thread settings removed (ClickHouse 24.3 sanity check prevents background_pool_size=2)
- D2: `CLICKHOUSE_DB` env var doesn't auto-create database; setup_clickhouse_schema.py handles `CREATE DATABASE IF NOT EXISTS` first
- D3: `send_receive_timeout` wired through (6th config property, per Tech Lead ruling)

**End-to-end gate:** 24,862 rows across 6 assets. Parquet vs ClickHouse numerical equivalence confirmed at rtol=1e-6.

---

### Pre-M19 Housekeeping (COMPLETE — 265 tests)

- Added `absolute_pnl_by_asset: dict[str, float]` to `PortfolioPerformanceReport` (resolves TD-M15-C: asset_contributions near-zero denominator collapse — Gold +2379%, NG -2561% observed)
- Updated `PortfolioPerformanceEngine._compute_asset_contributions()` to compute it
- Added 1 test to `tests/test_portfolio_performance.py`

---

### Module 19: Dashboard Page 7 — Cross-Asset Analytics (COMPLETE — 267 tests)

**Purpose:** Final Phase 3 module. Surfaces all Phase 3 analytics in Streamlit dashboard.

**Files created:**
- `dashboard/components/correlation_heatmap.py` — `render_correlation_heatmap()`, `render_rolling_correlation_chart()` (pure functions, no `st.*`, TD-M17-A handled internally)
- `dashboard/pages/7_cross_asset_analytics.py` — Page 7
- `docs/clickhouse/SETUP.md` — operator runbook
- `docs/implementation_notes/M19-dashboard-page-7.md`

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
- TD-M14-A (pipeline_builder): DEFERRED
- TD-B (static equity), TD-C (end-of-sample vol): DEFERRED
- MLflow portfolio logging: DEFERRED to F-track

**Tags on main after M19:** `M19-complete`, `phase-3-complete` (commit 429b5c5)

---

## F-Track — React + FastAPI Frontend (Next Workstream)

**Goal:** Replace Streamlit with a typed React + FastAPI research workstation.
**Prerequisite:** Phase 3 complete (done). All `src/` analytics frozen as API surface.
**Modules:** F0–F15

**Key architecture decisions (from FRONTEND_ARCHITECTURE.md and FRONTEND_TDRs.md):**
- FastAPI is a serialization shell only — no business logic in route handlers
- Type chain: `types.py → Pydantic → OpenAPI → openapi-typescript` (CI diff enforcement)
- IC Gate: backtest launch gated on SignalEvaluation in UI with logged override
- Caching: `staleTime: Infinity` on run artifacts (derived from ADR-009 immutability)
- State partitioning: TanStack Query (server) / URL (navigation) / Zustand (workspace) / component (ephemeral)

| Module Group | Scope | Modules |
|---|---|---|
| Phase F0 | FastAPI shell + contracts | F0 |
| Phase F1 | Scaffold, tokens, design system | F1–F3 |
| Phase F2 | Market + Asset + Workbench + Backtest | F4–F8 |
| Phase F3 | Commodity Intelligence UI | F9–F11 |
| Phase F4 | Portfolio UI + scale pass | F12–F15 |

---

## Development Checklist Before Starting Each Module

Before implementing any module:

- [ ] Re-read the relevant layer section in `ARCHITECTURE.md`
- [ ] Re-read the ADRs that apply to this module
- [ ] Confirm layer contracts for this module's inputs and outputs in `src/core/types.py`
- [ ] Write tests first (TDD) or immediately after the first working implementation
- [ ] Update `ARCHITECTURE.md` if implementation reveals a deviation from the design
- [ ] Log any unexpected decisions in `docs/implementation_notes/`
- [ ] FixedNotionalSizer constructor uses `notional_usd=` (not `notional=`)
- [ ] TermStructureRegime uses `str, Enum` with explicit `__str__` returning `self.value`
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

F-Track:
Phase 3 complete (backend frozen)
    └── F0  (FastAPI shell)
            └── F1–F3  (Scaffold + Design System)
                    └── F4–F8  (Market → Workbench → Backtest → Explorer)
                            └── F9–F11  (Commodity Intelligence UI)
                                    └── F12–F15  (Portfolio UI + Scale)
```

No module should be started until its dependency is complete and its tests pass.
