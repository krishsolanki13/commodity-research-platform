# Commodity Systematic Research Platform

![CI](https://github.com/krishsolanki13/commodity-research-platform/actions/workflows/ci.yml/badge.svg)

An institutional-style quantitative research infrastructure for commodity futures markets. Built to demonstrate and practice the systematic research workflow used by professional commodity trading teams: data normalization → feature engineering → signal evaluation → backtesting → performance attribution.

---

## Why This Architecture Exists

Most quantitative project backtests share the same structural weakness: they evaluate signal quality through the backtest itself. A trend-following signal that happens to be long during a multi-year commodity bull run produces a strong backtest Sharpe. Whether that Sharpe reflects genuine edge or regime coincidence is invisible.

This platform follows the institutional approach: **signal evaluation (IC analysis) is a precondition for backtesting, not a diagnostic run after it.** Before a backtest is executed, the signal's predictive content is evaluated via Information Coefficient (IC), IC Information Ratio (ICIR), and signal decay across multiple forecast horizons. Only signals with demonstrated IC proceed to backtesting. A signal with IC near zero is flagged as noise before any capital is simulated.

This is ADR-007, and it governs the entire research workflow.

---

## Architecture
Layer 0  │  Data Infrastructure
│  DataLoader · ContinuousDataSource · OHLCVValidator · OHLCVNormalizer · ParquetStore
│  Immutable raw CSVs → Validated, normalized Parquet → Analyst queries
│
Layer 1  │  Feature Engineering
│  FeaturePipeline · Indicator ABCs · SMA · EMA · RSI · RVGI · Momentum
│  NormalizedOHLCV → FeatureFrame (named, tracked indicator columns)
│
Layer 2  │  Signal Research
│  SignalGenerator · SignalEvaluator (IC/ICIR/decay) · PositionSignalConstructor
│  FeatureFrame → RawSignal → [IC gate] → PositionSignal {-1, 0, +1}
│
Layer 3  │  Backtesting Engine
│  VectorizedBacktester · CostModel · FixedNotionalSizer · TradeLog · RunManager
│  PositionSignal → BacktestResult (trades, equity curve, PnL, run artifacts)
│
Layer 4  │  Performance and Attribution
│  PerformanceEngine · scalar metrics · rolling metrics · signal attribution
│  BacktestResult → PerformanceReport (Sharpe, Sortino, Calmar, IC linkage)
│
Layer 8  │  Dashboard (Streamlit)
│  5-page research interface · pure presentation · composes Layers 0–4

---

## Research Workflow
Load data           DataLoader.load("gold") → NormalizedOHLCV (Parquet, validated)
Build features      FeaturePipeline([EMA(50), EMA(200)]).compute(ohlcv) → FeatureFrame
Generate signal     EMACrossoverSignal.generate(feature_frame) → RawSignal
Evaluate signal  ←  SignalEvaluator.evaluate(raw_signal, ohlcv) → IC, ICIR, decay
[IC gate]           |IC| < 0.02 → noise. 0.02-0.05 → weak. ≥ 0.05 → proceed.
Build position      PositionSignalConstructor.build(raw_signal) → PositionSignal
Run backtest        VectorizedBacktester.run(position_signal, ohlcv) → BacktestResult
Compute metrics     PerformanceEngine.compute(backtest_result) → PerformanceReport
Persist run         RunManager.save(result) · RunManager.save_metrics(id, report)

Step 4 is not optional. It runs before Step 6. This is the architectural commitment that separates systematic research infrastructure from a backtesting script.

---

## Phase 1 Deliverables

**Data layer:** Six commodity assets (Gold, Silver, Copper, WTI, Brent, Natural Gas) sourced from Yahoo Finance continuous series (`auto_adjust=False`). Validated, normalized, and persisted to Parquet. Not back-adjusted — roll gaps acknowledged per ADR-001.

**Feature engineering:** SMA, EMA, RSI, RVGI, Momentum with parameter-aware column naming (`ema_50`, `rsi_14`, `momentum_20`). Every feature column tracked via `FeatureSpec` for research reproducibility.

**Signal research:** IC evaluation against 1-bar forward log returns. ICIR from rolling 63-bar window. Signal decay at horizons {1, 2, 5, 10, 20 bars}. Four Phase 1 signals: EMA Crossover, Momentum, RSI Reversion, Donchian Breakout.

**Backtesting:** Vectorized engine with Close[t]→Open[t+1] execution per ADR-002. Commission ($5/trade) + slippage (1 tick) cost model. Fixed notional sizing ($100K per signal). Full run artifact persistence.

**Performance attribution:** Sharpe, Sortino, Calmar, max drawdown, win rate, profit factor. Rolling Sharpe (63-bar, 126-bar), rolling drawdown. Signal IC metrics linked to PerformanceReport.

**Dashboard:** Five-page Streamlit research interface. Market Overview → Research Workbench (IC analysis) → Strategy Builder (full pipeline) → Backtest Results → Performance Analysis.

**Test coverage:** 107 pytest tests. mypy clean. ruff clean.

---

## Quick Start

**Prerequisites:** Python 3.11+, git

```bash
# 1. Clone and install
git clone https://github.com/krishsolanki13/commodity-research-platform.git
cd commodity-research-platform
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -e ".[dev]"

# 2. Acquire commodity data
python scripts/acquire_data.py

# 3. Launch the dashboard
# Windows
.\launch_dashboard.ps1
# Mac/Linux
./launch_dashboard.sh
```

The dashboard will be available at `http://localhost:8501`.

**Minimum data (for quick evaluation):**
```bash
cp tests/fixtures/gold_sample.csv data/raw/continuous/gold.csv
```
This uses the 252-bar synthetic Gold fixture. Real data provides more meaningful IC values and trade counts.

---

## Architectural Decisions

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-001 | Continuous series for research, contract series for term structure | Yahoo Finance provides undocumented roll methodology; treated as opaque stream for signal research |
| ADR-002 | Signal at Close[t], execution at Open[t+1] | Eliminates look-ahead bias; reflects realistic end-of-day signal computation |
| ADR-003 | Vectorized backtesting engine | Research velocity priority in Phase 1; `BacktestEngine` interface supports future event-driven engine |
| ADR-004 | Parquet in Phase 1, ClickHouse in Phase 3 | File-based approach is the correct Phase 1 approximation of institutional time-series database |
| ADR-005 | Fixed notional sizing in Phase 1 | Explicit limitation: does not equalize risk across assets; Phase 2 adds volatility-scaled sizing |
| ADR-006 | FeatureFrame as typed Python class, not plain DataFrame | Enforces named feature tracking; prevents anonymous column aliasing in research workflows |
| ADR-007 | IC evaluation precedes backtesting | Core architectural commitment: a positive IC is a precondition for backtest justification |
| ADR-008 | Dashboard as pure presentation layer | No computation in dashboard code; all analytics through `src/` function calls |
| ADR-009 | File-based run tracking in Phase 1, MLflow in Phase 2 | Run artifacts are immutable once written; every backtest produces an auditable record |

---

## Phase Roadmap

**Phase 1 (complete):** Research MVP — single-asset backtesting, IC evaluation, five-page dashboard

**Phase 2 (planned):** Commodity intelligence — contract-level data, futures curve construction, term structure analytics (contango, backwardation, roll yield, basis), volatility-scaled position sizing, MLflow integration

**Phase 3 (planned):** Portfolio analytics — multi-asset portfolio backtesting, cross-sectional IC, ClickHouse integration, portfolio optimization

---

## Testing

```bash
pytest tests/ -v
# 107 tests · mypy clean · ruff 0.4.0 clean

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Data Architecture Note

The platform stores commodity futures data locally rather than calling the Yahoo Finance API on each request. This is a deliberate architectural decision:

- **Reproducibility:** Every backtest run uses an identical frozen dataset. API responses change as new bars arrive and historical data is occasionally revised.
- **Research velocity:** Loading from Parquet is 50–100× faster than an API round-trip, which matters when iterating over signals and parameters.
- **Vendor isolation:** The `DataSource` abstraction allows swapping Yahoo Finance for Bloomberg, Refinitiv, or an internal feed without touching signal or backtest code.

The local file approach in Phase 1 is the correct approximation of how institutional systematic research teams use internal time-series databases. Phase 3's ClickHouse integration brings this to production scale.
