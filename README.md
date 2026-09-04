# Commodity Systematic Research Platform

An institutional-style quantitative research platform for systematic commodity futures trading — a single-seat research workstation built to production discipline.

![CI](https://github.com/krishsolanki13/commodity-research-platform/actions/workflows/ci.yml/badge.svg) ![Python](https://img.shields.io/badge/Python-3.11-blue) ![mypy](https://img.shields.io/badge/mypy-strict-blue) ![License: MIT](https://img.shields.io/badge/License-MIT-yellow)

**6 commodity markets · 16 years of daily data · 9 architectural layers · 949 tests (429 backend · 406 frontend · 114 E2E) · 14 ADRs**

## What This Is

A complete systematic research environment covering the full institutional research loop:

```
data → features → signals → IC evaluation → backtesting → performance
     → term structure → portfolio risk → cross-asset analytics → validation

```

A **research tool, not a trading system** — no live orders, no execution. The output is research: signal quality scores, backtest reports, term-structure analytics, portfolio risk metrics, and out-of-sample validation results. Every result is reproducible from immutable run artifacts.

**Core design principle:** signal evaluation precedes backtesting. Every signal is scored on *information coefficient (IC)*, *ICIR*, *IC decay* across 5 horizons, and *turnover* before any P&L is simulated. The platform separates "does this signal contain information?" from "did the backtest go up?" — the distinction that defines institutional research discipline.

**Honest finding:** after walk-forward validation and Deflated Sharpe Ratio correction against the platform's own logged trial count, most simple technical signals on this universe do not survive. The carry signal is the most interesting exception.

## What's Inside


| Module                             | What it does                                                                                                                                                             |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Market Overview / Asset Detail** | Live universe grid across 6 commodities, built to scale to dozens without redesign.                                                                                      |
| **Research Workbench**             | Feature → signal → IC/ICIR evaluation — the doctrine the rest of the platform enforces: nothing gets backtested without first proving it contains information.           |
| **Strategy Builder**               | Parameterized launch. Doctrine, not force: launching without evaluation is possible, but the override is permanently logged in the run's metadata.                       |
| **Run Explorer**                   | Full experiment memory — every run ever executed, searchable, sortable, sub-second lookup even at 900+ runs.                                                             |
| **Run Detail**                     | Five-tab record per run — performance, signal quality, walk-forward validation, trades, and full reproducibility artifacts (git SHA, dirty-tree flag, package versions). |
| **Run Comparison**                 | Up to 8 runs overlaid — equity curves, a metric-delta table, parameter diffs.                                                                                            |
| **Sweep Explorer**                 | Parameter-grid search with a parallel-coordinates view of the performance landscape, every trial logged for the platform's own selection-bias correction.                |
| **Curve PCA**                      | Level/Slope/Curvature factor decomposition — Gold's curve is genuinely one-dimensional (PC1 ≈ 100%); WTI and Natural Gas aren't.                                         |
| **Term Structure / Futures Curve** | Regime classification, roll yield, multi-contract curve comparison (up to 4 assets side by side).                                                                        |
| **Portfolio Analytics**            | 6-asset book performance, 2.23× diversification benefit, Kupiec-calibrated VaR, and regime-conditional attribution computed per-asset and portfolio-wide.                |
| **Data Manager**                   | Per-asset data-quality report, CFTC/EIA data where it exists, honest empty states where it doesn't.                                                                      |


*(A second, more technical route-by-route table — with URLs, for anyone about to actually run the app — appears later, under "The Research Workstation." This one is deliberately the quick version.)*

## Universe


| Asset           | Exchange | Symbol | Coverage                   |
| --------------- | -------- | ------ | -------------------------- |
| **Gold**        | COMEX    | `GC=F` | 2010–present (~4,150 bars) |
| **Silver**      | COMEX    | `SI=F` | 2010–present (~4,150 bars) |
| **Copper**      | COMEX    | `HG=F` | 2010–present (~4,150 bars) |
| **WTI Crude**   | NYMEX    | `CL=F` | 2010–present (~4,150 bars) |
| **Brent Crude** | ICE      | `BZ=F` | 2010–present (~4,150 bars) |
| **Natural Gas** | NYMEX    | `NG=F` | 2010–present (~4,150 bars) |


Daily bars, continuous and individual contract series. Includes the *April 2020 WTI negative-price event* (−$37.63) — handled, not filtered.

## Architecture

**Nine strictly layered modules** with a hard rule: each layer depends only on layers below it. Typed contracts (`src/core/types.py`) at every boundary. The rule held without violation across 33 submodules and 14 rounds of feature addition.


| Layer | Name             | Contents                                                                                                                                                                                  |
| ----- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0** | **Data**         | Ingestion, validation, normalization — Parquet / ClickHouse. Alternative data: CFTC COT positioning, EIA petroleum inventory                                                              |
| **1** | **Features**     | Indicator registry, FeaturePipeline → FeatureFrame                                                                                                                                        |
| **2** | **Signals**      | RawSignal → IC evaluation → PositionSignal. 8 signals: EMA, momentum, RSI, Donchian breakout (technical); carry, WTI–Brent spread (term-structure); COT, EIA inventory (alternative data) |
| **3** | **Backtesting**  | Vectorized engine, costs, sizing, walk-forward validation, parameter sweep runner                                                                                                         |
| **4** | **Performance**  | Sharpe/Sortino/Calmar, drawdowns, rolling metrics                                                                                                                                         |
| **5** | **Intelligence** | Futures curves, term-structure regimes, roll yield, PCA                                                                                                                                   |
| **6** | **Risk**         | Historical VaR/ES, Kupiec calibration, contribution-to-risk                                                                                                                               |
| **7** | **Cross-Asset**  | Correlation matrices, regime-conditional attribution                                                                                                                                      |
| **8** | **Presentation** | React/TypeScript workstation + Streamlit reference dashboard                                                                                                                              |


All design decisions documented in **14 Architecture Decision Records**.

## Validation — the part most backtests skip

Every headline result passes through `src/validation/` before it is reported:

- **Walk-forward out-of-sample testing** — expanding windows with embargo periods between train and test; no future data leaks into the training window
- **Newey-West Sharpe standard errors** — autocorrelation-corrected inference, not IID-assumed p-values
- **Deflated Sharpe Ratio** — computed against the platform's own MLflow trial count; selection bias is priced into every reported number (*Bailey & López de Prado*)
- **Kupiec calibration backtesting** — the risk model proves its exception rate matches its stated confidence level (p = 0.7680 on a live 2-asset portfolio — well-calibrated)
- **Point-in-time correctness** — position-sizing volatility estimates are strictly rolling; a look-ahead bias was found and fixed in the rolling estimator, then locked with golden-master regression tests

## Signal Library


| Signal                | Type             | Key data dependency              |
| --------------------- | ---------------- | -------------------------------- |
| **EMA Crossover**     | Trend            | Price features                   |
| **Momentum**          | Trend            | Price features                   |
| **RSI Reversion**     | Mean-reversion   | Price features                   |
| **Donchian Breakout** | Breakout         | Price features                   |
| **Carry**             | Risk premium     | FuturesCurve roll yield          |
| **WTI-Brent Spread**  | Statistical arb  | Cointegration (ADF p = 0.003)    |
| **COT Positioning**   | Alternative data | CFTC Managed Money positions     |
| **EIA Inventory**     | Alternative data | EIA petroleum inventory surprise |


All eight signals evaluated under identical cost and validation assumptions. The carry and alternative data signals require multi-year windows for non-noise IC — *the platform measures and documents this, not hides it.*

## Commodity-Native Analytics

Forward curves are built from individual contract data — a separate dataset that never touches the backtesting pipeline:

- **Forward curve construction** — up to 12 contracts per asset per observation date
- **Term-structure regime classification** — contango / backwardation / flat via annualized slope
- **Roll yield and basis** — annualized, with the continuous-contract basis correctly labelled as pseudo-basis
- **Curve PCA** — Level / Slope / Curvature factor decomposition; Gold: PC1 ≈ 100% (structural contango); WTI and Natural Gas: meaningful three-factor decompositions

## Selected Results


| Metric                         | Value                                                        |
| ------------------------------ | ------------------------------------------------------------ |
| **Portfolio 99% daily VaR**    | $44,490 (0.74% of capital)                                   |
| **Portfolio 99% ES**           | $99,095                                                      |
| **Diversification benefit**    | 2.23× (Σ per-asset VaR₉₉ / portfolio VaR₉₉)                  |
| **Kupiec calibration p-value** | 0.7680 (well-calibrated)                                     |
| **Gold–Silver strategy corr**  | 0.65                                                         |
| **WTI–Brent strategy corr**    | 0.62                                                         |
| **COT positioning / Gold**     | IC −0.065, ICIR −0.521 (meaningful, inverse)                 |
| **EIA inventory / WTI**        | IC −0.093, ICIR −0.462 (meaningful, inverse)                 |
| **Carry / Gold**               | IC null (structural contango → near-flat signal — *correct*) |


## Portfolio Risk Analytics

Across the 6-asset universe:

- **Historical-simulation VaR and Expected Shortfall** (95/99%) — no parametric assumption
- **Kupiec Likelihood Ratio test** — VaR model calibration backtesting; p < 0.05 signals miscalibration
- **Contribution-to-risk decomposition** — per-asset marginal vol contribution, sums to 1.0
- **Rolling cross-asset correlations** — 63-day and 126-day windows
- **Regime-conditional attribution** — Sharpe, return, and drawdown conditioned on term-structure regime (contango / backwardation / flat), per-asset and portfolio-level

## The Research Workstation

The engine is exposed through a typed full-stack layer, validated end-to-end by 114 Playwright tests:

- **IC Gate** — the interface enforces the research doctrine. Backtest launch is gated on signal evaluation; overrides are permanently recorded in run metadata (`signal_evaluation: null`). *Not a hard block* — doctrine-with-override, logged either way.
- **One contract chain** — `src/core/types.py` → Pydantic → OpenAPI → generated TypeScript. Cross-language type drift is a compile error; CI fails on schema diff.
- **Async job architecture** — every long-running computation follows the same pattern: `POST → {job_id, status: "queued"} → poll /status at 2s → GET /result`. Applied uniformly across backtest, portfolio, walk-forward validation, parameter sweep, and regime attribution (per-asset + Portfolio Combined).

**13 screens** across all platform capabilities:


| Route                   | Screen                                                                           |
| ----------------------- | -------------------------------------------------------------------------------- |
| `/market`               | Market Overview                                                                  |
| `/market/:asset`        | Asset Detail                                                                     |
| `/research`             | Research Workbench — IC evaluation, signal visualization                         |
| `/backtest/new`         | Strategy Builder — IC Gate, parameter configuration                              |
| `/runs`                 | Run Explorer — searchable, sortable, paginated                                   |
| `/runs/:runId`          | Run Detail — 5 tabs: Overview · Signal Quality · Validation · Trades · Artifacts |
| `/runs/compare`         | Run Comparison                                                                   |
| `/intelligence`         | Futures Curve                                                                    |
| `/intelligence/compare` | Curve Comparison                                                                 |
| `/intelligence/pca`     | Curve PCA — Level/Slope/Curvature decomposition                                  |
| `/sweeps`               | Sweep Explorer — parameter grid with live progress                               |
| `/portfolio`            | Portfolio Analytics — equity, attribution, regime, risk, correlation             |
| `/system`               | Data Manager — QC reports, COT/EIA data, asset health                            |


**Stack:** FastAPI · React 18 · TypeScript (strict) · TanStack Query · ECharts · Playwright

## Reproducibility

Every backtest writes an **immutable artifact set** to `data/runs/{run_id}/`:

```
params.json          complete parameter snapshot
trades.parquet       full trade log
equity_curve.parquet cumulative PnL series
pnl_series.parquet   daily PnL
positions.parquet    position size series
metrics.json         all scalar metrics (upserted into SQLite run index)

```

Portfolio runs additionally write `portfolio_summary.json` containing `asset_run_ids` and `has_regime_attribution`.

Every run also records **provenance**: `git_sha`, a `dirty_flag` (uncommitted-changes warning), and full `package_versions` for every dependency — captured automatically at execution time, visible on each run's Artifacts tab.

`scripts/reproduce_run.py` re-executes any completed run by ID, hashes the resulting equity curve, and compares against the original artifact — exit 0 = match, 1 = mismatch, 2 = error. *A closed reproducibility loop, not a documentation promise.*

All experiments additionally tracked in MLflow (`data/mlruns/`) with programmatic trial-count queries feeding the Deflated Sharpe correction.

## Storage

**Parquet is canonical.** ClickHouse (Docker, 24.3) is available behind the same `DataStore` abstraction via a one-line config switch:

```yaml
storage:
  backend: "parquet"      # default
  # backend: "clickhouse" # opt-in after: docker compose up -d

```

24,862 OHLCV rows migrated; Parquet vs ClickHouse numerical equivalence confirmed at rtol 1e-6. At this data volume, ClickHouse is a *migration-path demonstration* — the abstraction is the point, not the necessity.

A SQLite run index (`data/runs/index.db`, WAL mode) keeps `GET /api/runs` under **0.5 seconds** at 900+ accumulated runs. The index is built from `metrics.json` on startup and upserted on every new run — regenerated automatically, gitignored.

## Quickstart

```bash
# Clone and set up
git clone https://github.com/krishsolanki13/commodity-research-platform
cd commodity-research-platform
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e ".[dev]"

# Ingest market data
python scripts/acquire_data.py          # continuous futures (~25,000 bars)
python scripts/acquire_contract_data.py # individual contracts (term structure)

# Optional: alternative data (requires free EIA API key in config/local.yaml)
python scripts/acquire_cot_data.py
python scripts/acquire_eia_data.py

# Run tests
pytest -m "not slow"                    # 409 passed (fast suite, ~6-7 min)
pytest                                  # 429 passed (full suite, ~30 min)

# Streamlit reference dashboard
streamlit run dashboard/app.py          # localhost:8501

# React research workstation
make dev                                # FastAPI :8000 + Vite :5173
cd frontend && npm test -- --run        # 406 passed
npx playwright test                     # 114 passed

# Optional ClickHouse backend
docker compose up -d
python scripts/setup_clickhouse_schema.py
python scripts/migrate_to_clickhouse.py

```

EIA API key (optional, for inventory signals): register free at eia.gov/opendata, then add to `config/local.yaml`:

```yaml
eia:
  api_key: your_key_here

```

## Testing


| Suite            | Command                 | Tests | Notes                                            |
| ---------------- | ----------------------- | ----- | ------------------------------------------------ |
| **Backend fast** | `pytest -m "not slow"`  | 409   | Excludes Hypothesis property tests               |
| **Backend full** | `pytest`                | 429   | Includes property-based invariants               |
| **Frontend**     | `npm test -- --run`     | 406   | Vitest, runs in ~3 min                           |
| **E2E standard** | `npm run test:e2e`      | 111   | Excludes @slow (validation, portfolio regime)    |
| **E2E full**     | `npm run test:e2e:full` | 114   | All tests including ~8 min portfolio computation |


CI enforces **mypy strict** (0 errors, 67 source files) and **ruff** on every push.

## Documentation


| Document                   | Location                                 | Contents                                                           |
| -------------------------- | ---------------------------------------- | ------------------------------------------------------------------ |
| **Architecture**           | `ARCHITECTURE.md`                        | System design, layer contracts, 9-layer diagram, known limitations |
| **ADRs**                   | `docs/adr/ADRs.md`                       | 14 Architecture Decision Records (ADR-001 through ADR-014)         |
| **Implementation Roadmap** | `IMPLEMENTATION_ROADMAP.md`              | Full module build log — Phase 1–3 + EM1–14 + F-Track               |
| **Frontend Architecture**  | `docs/frontend/FRONTEND_ARCHITECTURE.md` | React/FastAPI design, state partitioning, TDR index                |
| **Frontend TDRs**          | `docs/frontend/FRONTEND_TDRs.md`         | 25 technical design records                                        |
| **Screen Specifications**  | `docs/frontend/SCREEN_SPECIFICATIONS.md` | All 13 screens with component and data contracts                   |
| **Design System**          | `docs/frontend/DESIGN_SYSTEM.md`         | Tokens, typography, chart patterns                                 |


## Project Structure

```
commodity-research-platform/
├── src/
│   ├── core/                    Types, config, registry (all shared contracts)
│   ├── data/                    Data pipeline — loaders, validators, stores, QC
│   ├── signal/                  8 signal generators + SignalEvaluator
│   ├── backtesting/             Engine, sizing, pipeline builder, sweep runner
│   ├── performance/             PerformanceEngine, PortfolioPerformanceEngine
│   ├── analytics/                RegimeAttributionEngine
│   ├── commodity/                FuturesCurveBuilder, TermStructureAnalyzer, CurvePCAEngine
│   ├── risk/                    RiskEngine (VaR, ES, Kupiec, contribution-to-risk)
│   └── validation/              WalkForwardValidator, PSR, DSR (scipy-free)
├── api/
│   ├── main.py                  FastAPI app — startup, CORS, route registration
│   ├── models.py                All Pydantic models (30+ request/response types)
│   └── routers/                 One router per domain — backtests, runs, portfolio,
│                                 signals, sweeps, validation, intelligence, regime,
│                                 system
├── frontend/
│   ├── src/
│   │   ├── api/                  Generated schema.d.ts, queryKeys, client, hooks
│   │   ├── features/              Screen-scoped React components
│   │   └── lib/                  fmt.ts, chart-theme.ts, shared utilities
│   └── tests/e2e/                11 Playwright spec files + helpers.ts
├── dashboard/                    Streamlit reference dashboard (7 pages)
├── scripts/                      Data acquisition + reproduce_run.py
├── tests/                        429 backend tests + golden master fixture
├── config/                       config.yaml, assets.yaml, strategies.yaml
├── docs/
│   ├── adr/                      ADRs.md (14 records)
│   ├── clickhouse/                SETUP.md
│   ├── frontend/                  5 frontend architecture documents
│   └── implementation_notes/      M01–M19 module implementation notes
├── ARCHITECTURE.md
└── IMPLEMENTATION_ROADMAP.md

```

## What's Next

The platform is **feature-complete**. What remains is external verification, not more infrastructure:

1. A written research note replicating a published commodity carry finding using the platform's walk-forward + DSR machinery — the infrastructure exists, only the write-up is missing
2. One third-party-verified result — competition placement or an accepted open-source contribution

## Limitations

- **Continuous series not back-adjusted** — Yahoo Finance roll methodology is undocumented; price discontinuities occur at roll dates
- **No margin modeling** — the backtester is not an execution simulator
- **No risk limits** — Layer 6 computes and calibrates VaR; nothing enforces a constraint from it
- **No dependency pinning** — `pyproject.toml` uses version ranges, not a lockfile
- **Alternative data signals require multi-year windows** — COT and EIA produce noise-band IC on 1-year windows by design (insufficient weekly history for stable percentile ranks and seasonal averages)

## Disclaimer

*Research and educational software. Not investment advice. No live trading.*

---

*Built to understand commodity futures markets and systematic research workflows from first principles. Every design decision documented. Every result validated.*
