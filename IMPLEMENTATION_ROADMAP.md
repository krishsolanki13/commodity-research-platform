# Implementation Roadmap
## Commodity Systematic Research Platform

**Purpose:** Defines the exact module development sequence for Phase 1 implementation. Designed for Cursor-based incremental development. Each module has explicit dependencies, prerequisites, and expected test coverage.

**Principle:** Build one vertical slice end-to-end before expanding horizontally. The first slice should be: Gold data → EMA Crossover signal → backtest → performance report.

---

## Phase 1 — Research MVP

### Module 1: Repository Initialization

**Purpose:** Establish the repository skeleton, configuration, and shared infrastructure before any business logic is written.

**Dependencies:** None.

**Deliverables:**
- Folder structure as defined in ARCHITECTURE.md
- `config.yaml`, `assets.yaml`, `strategies.yaml` (complete, no placeholders)
- `.env.example` (template, no real values)
- `pyproject.toml` with all Phase 1 dependencies
- `ARCHITECTURE.md` (this file)
- `docs/adr/ADRs.md`
- `src/core/config.py` — config loader (reads and validates all YAML files, raises on missing keys)
- `src/core/types.py` — all Phase 1 type definitions (NormalizedOHLCV attrs, FeatureSpec, RawSignal, PositionSignal, SignalEvaluation, TradeRecord, BacktestResult, BacktestMetadata, PerformanceReport as dataclass stubs — no logic)
- `src/core/registry.py` — abstract base classes: `DataSource`, `Indicator`, `SignalGenerator`, `BacktestEngine`, `PositionSizer`
- `src/core/logging_config.py` — logging setup (reads log level + path from config)
- `tests/conftest.py` — shared fixtures: synthetic Gold OHLCV DataFrame (252 bars), loaded config
- `tests/fixtures/gold_sample.csv` — synthetic OHLCV data file (252 rows)

**Testing requirements:**
- `test_config.py`: config loads without error; missing required keys raise `ConfigError`
- `test_types.py`: all dataclasses instantiate with expected fields

**Gate:** All abstract base classes defined. Config loading confirmed working. No implementation code written yet.

---

### Module 2: Data Layer (Layer 0)

**Purpose:** Ingestion, validation, normalization, and Parquet storage for continuous futures series.

**Dependencies:** Module 1 complete.

**Architectural prerequisites:**
- `DataSource` abstract base class defined in `src/core/registry.py` (Module 1 deliverable)
- Paths configured in `config.yaml`
- `NormalizedOHLCV` type defined in `src/core/types.py`

**Implementation order within module:**
1. `src/data/sources/base.py` — `ContinuousDataSource` abstract subclass (extends `DataSource` from `src/core/registry.py`; adds continuous-series-specific contract)
2. `src/data/sources/csv.py` — `LocalCSVSource` implementation (reads from `data/raw/continuous/`)
3. `src/data/validator.py` — OHLCV consistency checks, gap detection, anomaly flagging
4. `src/data/normalizer.py` — dtype enforcement, column renaming, DatetimeIndex normalization
5. `src/data/store.py` — `ParquetStore.write()` and `ParquetStore.read()`
6. `src/data/loader.py` — orchestrates Source → Validator → Normalizer → Store pipeline

**Expected deliverables:**
- `DataLoader.load(asset="gold")` returns a clean NormalizedOHLCV DataFrame from Parquet
- Validation errors are logged with asset, date, and violation type
- Raw CSV files remain unmodified after ingestion

**Testing requirements:**
- `tests/test_data_validation.py`:
  - OHLC consistency violation detected and raises `DataValidationError`
  - Gap detection identifies missing trading days
  - Anomalous prices (negative close, zero volume) are flagged
- `tests/test_data_loader.py`:
  - Loader returns DataFrame with correct dtypes and index
  - Loader is idempotent (running twice produces same Parquet)

**Gate:** `DataLoader.load("gold")` works on the sample CSV fixture. Parquet file written to `data/processed/continuous/gold.parquet`. All validation tests pass.

---

### Module 3: Feature Engineering Layer (Layer 1)

**Purpose:** Indicator computation, FeaturePipeline, FeatureFrame, FeatureSpec.

**Dependencies:** Module 2 complete.

**Implementation order:**
1. `src/research/base.py` — `Indicator` ABC with `compute(df)` and `column_name` property
2. `src/research/feature_frame.py` — `FeatureFrame` wrapper and `FeatureSpec` dataclass
3. `src/research/moving_averages.py` — `SMA`, `EMA` implementations
4. `src/research/oscillators.py` — `RSI`, `RVGI` implementations
5. `src/research/momentum.py` — `Momentum` implementation
6. `src/research/pipeline.py` — `FeaturePipeline.compute(ohlcv, specs)` → FeatureFrame + List[FeatureSpec]

**Column naming convention (enforced by Indicator base class):**
- `EMA(period=50)` → column `ema_50`
- `RSI(period=14)` → column `rsi_14`
- `Momentum(lookback=20)` → column `momentum_20`

**Expected deliverables:**
- `FeaturePipeline.compute(ohlcv, [EMA(50), EMA(200), RSI(14)])` returns FeatureFrame with `feature_frame.data` containing columns `[open, high, low, close, volume, ema_50, ema_200, rsi_14]`
- `FeatureSpec` list accompanies FeatureFrame and is accessible via `feature_frame.feature_specs`

**Testing requirements:**
- `tests/test_indicators.py`:
  - SMA(5) of known series returns mathematically correct values
  - EMA(10) matches expected exponential decay behavior
  - RSI(14) produces values in [0, 100]
  - RVGI(10) produces values (basic sanity check)
  - Momentum(20) = close[t] / close[t-20] - 1
  - Each indicator column is correctly named per convention
  - NaN values appear only in the warmup period (first `period` bars); use EMA(50) to test warmup boundary — EMA(50) produces first non-NaN at bar 50, all prior bars are NaN
  - EMA(200) is tested for correct long-window computation on the 252-bar fixture (not warmup boundary, which would require a separate 200+ bar subset)
- `tests/test_pipeline.py`:
  - FeaturePipeline with multiple indicators returns all expected columns
  - FeatureSpec list matches indicators passed to pipeline

**Gate:** Pipeline computes EMA(50), EMA(200), RSI(14), and Momentum(20) on Gold OHLCV. All indicator unit tests pass.

---

### Module 4: Signal Research Layer (Layer 2)

**Purpose:** Signal generation, IC/ICIR evaluation, signal decay analysis, PositionSignal construction.

**Dependencies:** Module 3 complete.

**Implementation order:**
1. `src/signal/base.py` — `SignalGenerator` ABC with `generate(feature_frame)` → RawSignal
2. `src/signal/evaluation.py` — `SignalEvaluator`: IC, ICIR, decay at multiple horizons, turnover
3. `src/signal/trend.py` — `EMACrossoverSignal`, `MomentumSignal`
4. `src/signal/reversion.py` — `RSIReversionSignal`
5. `src/signal/breakout.py` — `DonchianBreakoutSignal`
6. `src/signal/position.py` — `PositionSignalConstructor.build(raw_signal, threshold)` → PositionSignal

**Critical constraint:** All signal generators must be validated for look-ahead bias. The RawSignal at index t must be computable from information available at or before Close[t].

**Expected deliverables:**
- `EMACrossoverSignal.generate(feature_frame)` returns RawSignal using EMA spread
- `SignalEvaluator.evaluate(raw_signal, ohlcv)` returns IC, ICIR, and decay dict
- `PositionSignalConstructor.build(raw_signal)` returns {+1, 0, -1} series

**Testing requirements:**
- `tests/test_signal_evaluation.py`:
  - IC of a perfect signal (signal = future return) ≈ 1.0
  - IC of a random signal ≈ 0.0 (with tolerance)
  - ICIR computed correctly from rolling IC series
  - Signal decay array has correct shape (length = number of horizons)
- `tests/test_signals.py`:
  - EMA Crossover signal is +1 when fast EMA > slow EMA, -1 when fast < slow
  - No look-ahead: signal value at t does not use price from t+1
  - PositionSignal has values only in {-1, 0, +1}

**Gate:** EMACrossover RawSignal generated for Gold. IC computed and non-zero for EMA signal. PositionSignal aligns correctly to FeatureFrame index.

---

### Module 5: Backtesting Engine (Layer 3)

**Purpose:** Vectorized backtester, cost model, position sizer, trade log, equity curve, run management.

**Dependencies:** Module 4 complete.

**Implementation order:**
1. `src/backtesting/costs.py` — `CostModel(commission_per_trade, slippage_ticks)` → cost in USD per trade
2. `src/backtesting/sizing.py` — `FixedNotionalSizer(notional_usd)` implementing `PositionSizer`
3. `src/backtesting/trade_log.py` — `TradeRecord` serialization, `TradeLog` (list of TradeRecord)
4. `src/backtesting/engine.py` — `VectorizedBacktester.run(position_signal, ohlcv)` → BacktestResult
5. `src/backtesting/run_manager.py` — `RunManager`: assign run_id, serialize BacktestResult to `data/runs/{run_id}/`

**Execution logic in VectorizedBacktester:**
```
for t in range(1, len(ohlcv)):
    execution_price = ohlcv["open"][t]        # Open[t+1] relative to signal at Close[t]
    signal = position_signal[t-1]             # Signal generated at Close[t-1]
    # apply cost model and sizing to generate trade record
```

**Expected deliverables:**
- `VectorizedBacktester.run(position_signal, ohlcv)` returns BacktestResult with trades, equity_curve, pnl_series
- `RunManager.save(backtest_result)` writes params.json, trades.parquet, equity_curve.parquet, pnl_series.parquet, positions.parquet to `data/runs/{run_id}/`
- `metrics.json` is NOT written in Module 5. It is written by Module 6 after PerformanceReport is computed.

**Trade boundary detection spec (implement in `src/backtesting/trade_log.py`):**

A trade is defined as a continuous period during which the PositionSignal holds the same non-zero direction. The following rules are applied to the PositionSignal series to detect trade boundaries:

- A trade **opens** when PositionSignal changes from 0 to +1 or 0 to -1. Entry price = Open[t+1].
- A trade **closes** when PositionSignal changes from ±1 to 0. Exit price = Open[t+1].
- A **direction reversal** (+1 to -1, or -1 to +1 with no flat bar) is treated as two trades: the existing trade closes at Open[t+1] and a new trade in the opposite direction opens at the same Open[t+1]. Two transaction costs are applied.
- Any position open at the final bar is **force-closed** at Close[T] (the last available close price). This trade is recorded with `exit_date = last_date` and flagged in TradeRecord metadata.

**PnL calculation per trade:**
```
gross_pnl = direction * (exit_price - entry_price) * size_notional / entry_price
transaction_cost = cost_model.compute(size_notional, asset_metadata)
net_pnl = gross_pnl - transaction_cost
```

**Testing requirements:**
- `tests/test_backtester.py`:
  - A signal that is always long on a rising price series produces positive net PnL
  - A signal that is always flat produces zero PnL
  - Transaction costs reduce gross PnL by expected amount
  - Equity curve is monotonically increasing for a perfect signal (synthetic test)
  - No look-ahead: backtester shift is verified by inspecting entry prices
  - Run artifacts are written to disk and loadable
- Edge cases:
  - All-flat signal (no trades)
  - Signal that changes every bar (maximum turnover)
  - Signal over a period with a known price gap (roll date simulation)

**Gate:** Full backtest of EMA Crossover on Gold completes. Run artifacts written to `data/runs/`. Trade log contains plausible entries. Equity curve shape matches expected behavior.

---

### Module 6: Performance Layer (Layer 4)

**Purpose:** Compute all performance metrics from BacktestResult. Assemble PerformanceReport.

**Dependencies:** Module 5 complete.

**Implementation order:**
1. `src/performance/metrics.py` — all scalar metrics (see list below)
2. `src/performance/rolling.py` — rolling Sharpe, rolling volatility, rolling drawdown
3. `src/performance/report.py` — `PerformanceEngine.compute(backtest_result)` → PerformanceReport
4. Extend `src/backtesting/run_manager.py` — add `RunManager.save_metrics(run_id, report)` → writes `metrics.json` to existing run directory

**Scalar metrics to implement:**
- `initial_capital`: from `backtest_result.metadata.initial_capital_usd`
- `total_return`: `(equity_curve[-1] - initial_capital) / initial_capital`
- `daily_return[t]`: `pnl_series[t] / equity_curve[t-1]` (return on capital, not on notional)
- `cagr`: `(1 + total_return)^(252/n_bars) - 1`
- `sharpe`: `mean(daily_return) / std(daily_return) * sqrt(252)`
- `sortino`: `mean(daily_return) / std(negative_daily_returns only) * sqrt(252)`
- `calmar`: `cagr / abs(max_drawdown)`
- `max_drawdown`: max peak-to-trough decline in equity_curve as a fraction
- `avg_drawdown`: mean of all drawdown periods
- `win_rate`: `n_winning_trades / n_total_trades`
- `profit_factor`: `sum(winning_net_pnl) / abs(sum(losing_net_pnl))`
- `avg_trade_duration_bars`: `mean(TradeRecord.duration_bars)`
- `turnover`: `mean(abs(position_signal.diff()))` — average daily position change

**Testing requirements:**
- `tests/test_performance.py`:
  - Sharpe ratio of constant positive returns ≈ expected value
  - Sharpe ratio of zero returns = 0
  - Max drawdown of monotonically increasing equity curve = 0
  - Max drawdown computed correctly on known synthetic series
  - Calmar = cagr / max_drawdown
  - Win rate of 10 wins and 10 losses = 0.5
  - All metrics are finite numbers (no NaN, no inf) for valid BacktestResult

**Gate:** PerformanceReport computed from Gold EMA Crossover BacktestResult. All metrics are finite and within expected ranges. Test suite passes.

---

### Module 7: Dashboard (Layer 8) — Phase 1 Pages

**Purpose:** Streamlit dashboard implementing pages 1–5.

**Dependencies:** Modules 1–6 complete. Full end-to-end pipeline operational.

**Implementation order:**
1. `dashboard/components/price_chart.py`
2. `dashboard/components/equity_curve_chart.py`
3. `dashboard/components/metrics_table.py`
4. `dashboard/components/signal_chart.py`
5. `dashboard/app.py` — page router
6. `dashboard/pages/1_market_overview.py`
7. `dashboard/pages/2_research_workbench.py`
8. `dashboard/pages/3_strategy_builder.py`
9. `dashboard/pages/4_backtest_results.py`
10. `dashboard/pages/5_performance_analysis.py`

**Rules for all dashboard pages:**
- No computation in page files. Call `src/` functions only.
- Cache expensive function calls with `@st.cache_data`.
- Use `st.session_state` for user input persistence across rerenders.

**Testing requirements:**
- No unit tests for dashboard pages (Streamlit testing is integration-level)
- Smoke test: `streamlit run dashboard/app.py` launches without errors
- Manual verification checklist for each page

**Gate:** All 5 pages render without errors for Gold EMA Crossover. IC chart visible on Research Workbench. Trade log table visible on Backtest Results. Sharpe and drawdown metrics visible on Performance Analysis.

---

## Phase 2 — Commodity Intelligence (Sequence)

Phase 2 begins after Phase 1 is complete and all tests pass. Implement in order:

1. **Module 8: Contract Data Layer** — `ContractDataSource`, contract-level Parquet ingestion
2. **Module 9: Futures Curve Layer** — `FuturesCurveBuilder`, term structure snapshot
3. **Module 10: Term Structure Analytics** — contango/backwardation slope, basis, roll yield, regime flag
4. **Module 11: Volatility-Scaled Sizing** — `VolatilityScaledSizer` in Layer 3
5. **Module 12: MLflow Integration** — MLflow logging in `RunManager`
6. **Module 13: Dashboard Page 6** — Commodity Intelligence page

---

## Phase 3 — Portfolio Analytics (Sequence)

Phase 3 begins after Phase 2 is complete. Implement in order:

1. **Module 14: Multi-Asset Runner** — `MultiAssetRunner` producing portfolio equity curve
2. **Module 15: Portfolio Performance** — portfolio-level Sharpe, drawdown, correlation
3. **Module 16: Risk Analytics** — VaR, ES, exposure (notional-aware via assets.yaml)
4. **Module 17: Cross-Asset Analytics** — correlation matrix, rolling correlations
5. **Module 18: ClickHouse Integration** — `ClickHouseStore`, data migration scripts
6. **Module 19: Dashboard Page 7** — Cross-Asset Analytics page

---

## Development Checklist Before Starting Each Module

Before implementing any module:

- [ ] Re-read the relevant layer section in `ARCHITECTURE.md`
- [ ] Re-read the ADRs that apply to this module
- [ ] Confirm layer contracts for this module's inputs and outputs in `src/core/types.py`
- [ ] Write tests first (TDD) or immediately after the first working implementation
- [ ] Update `ARCHITECTURE.md` if implementation reveals a deviation from the design
- [ ] Log any unexpected decisions in the `docs/` folder as implementation notes

---

## Dependency Graph Summary

```
Module 1 (Init)
    └── Module 2 (Data Layer)
            └── Module 3 (Feature Engineering)
                    └── Module 4 (Signal Research)
                            └── Module 5 (Backtesting Engine)
                                    └── Module 6 (Performance)
                                            └── Module 7 (Dashboard Pages 1-5)
                                                        │
                                                        ▼
                                              Phase 2 begins here
```

No module should be started until its dependency is complete and its tests pass.
