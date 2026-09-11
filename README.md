# Commodity Systematic Research Platform

An institutional-style quantitative research platform for systematic commodity futures trading — a single-seat research workstation built to production discipline.

![CI](https://github.com/krishsolanki13/commodity-research-platform/actions/workflows/ci.yml/badge.svg) ![Python](https://img.shields.io/badge/Python-3.11-blue) ![mypy](https://img.shields.io/badge/mypy-strict-blue) ![License: MIT](https://img.shields.io/badge/License-MIT-yellow)

**6 commodity markets · 16 years of daily data · 9 architectural layers · 987 tests (443 backend · 427 frontend · 117 E2E) · 14 ADRs**

## What This Is

A complete systematic research environment covering the full institutional research loop:

```
data → features → signals → IC evaluation → backtesting → performance
     → term structure → portfolio risk → cross-asset analytics → validation
```

A **research tool, not a trading system** — no live orders, no execution. The output is research: signal quality scores, backtest reports, term-structure analytics, portfolio risk metrics, and out-of-sample validation results. Every result is reproducible from immutable run artifacts.

**Core design principle:** signal evaluation precedes backtesting. Every signal is scored on information coefficient (IC), ICIR, IC decay across 5 horizons, and turnover before any P&L is simulated. The platform separates "does this signal contain information?" from "did the backtest go up?" — the distinction that defines institutional research discipline.

**Honest finding:** after walk-forward validation and Deflated Sharpe Ratio correction against the platform's own logged trial count, none of the eight signals in this platform's library — tested individually and as a diversified six-asset portfolio — clears statistical significance. See Findings below.

## What's Inside


| Module                             | What it does                                                                                                                                                             |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Market Overview / Asset Detail** | Live universe grid across 6 commodities, built to scale to dozens without redesign.                                                                                      |
| **Research Workbench**             | Feature → signal → IC/ICIR evaluation — the doctrine the rest of the platform enforces: nothing gets backtested without first proving it contains information.           |
| **Strategy Builder**               | Parameterized launch. Doctrine, not force: launching without evaluation is possible, but the override is permanently logged in the run's metadata.                       |
| **Run Explorer**                   | Full experiment memory — every run ever executed, searchable, sortable, sub-second lookup even at 900+ runs.                                                             |
| **Run Detail**                     | Five-tab record per run — performance, signal quality, walk-forward validation, trades, and full reproducibility artifacts (git SHA, dirty-tree flag, package versions). |
| **Run Comparison**                 | Up to 8 runs overlaid — equity curves, a metric-delta table, parameter diffs.                                                                                            |
| **Sweep Explorer**                 | Parameter-grid search with a parallel-coordinates view of the performance landscape across all parameter combinations. Results stored as immutable sweep artifacts.      |
| **Curve PCA**                      | Level/Slope/Curvature factor decomposition — Gold: PC1 ≈ 100% on its genuinely computable window (398 dates, ~19 months — no earlier 4-contract Gold curve exists); not a multi-year finding as originally framed. WTI and Natural Gas are two-factor, not three (PC3 is negligible in both, ~1% and ~0.2% respectively) — neither curve is one-dimensional, and the slope factor (PC2) is economically meaningful (11–28% of variance). |
| **Term Structure / Futures Curve** | Regime classification, roll yield, multi-contract curve comparison (up to 4 assets side by side).                                                                        |
| **Portfolio Analytics**            | 6-asset book performance, 2.22× diversification benefit (confirmed via canonical run `20260910_095142_portfolio_ema_crossover`), Kupiec-calibrated VaR, and regime-conditional attribution computed per-asset and portfolio-wide. |
| **Data Manager**                   | Per-asset data-quality report, CFTC/EIA data where it exists, honest empty states where it doesn't.                                                                      |


*(A second, more technical route-by-route table — with URLs, for anyone about to actually run the app — appears later, under "The Research Workstation." This one is deliberately the quick version.)*

## Universe


| Asset           | Exchange | Symbol | Coverage                   |
| --------------- | -------- | ------ | -------------------------- |
| **Gold**        | COMEX    | `GC=F` | 2010–present (~4,150–4,190 bars) |
| **Silver**      | COMEX    | `SI=F` | 2010–present (~4,150–4,190 bars) |
| **Copper**      | COMEX    | `HG=F` | 2010–present (~4,150–4,190 bars) |
| **WTI Crude**   | NYMEX    | `CL=F` | 2010–present (~4,150–4,190 bars) |
| **Brent Crude** | ICE      | `BZ=F` | 2010–present (~4,150–4,190 bars) |
| **Natural Gas** | NYMEX    | `NG=F` | 2010–present (~4,150–4,190 bars) |


Daily bars, continuous and individual contract series. Includes the April 2020 WTI negative-price event (−$37.63) — handled, not filtered.

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
- **Deflated Sharpe Ratio** — computed against the platform's own MLflow trial count; selection bias is priced into every reported number (Bailey & López de Prado)
- **Kupiec calibration backtesting** — the risk model proves its exception rate matches its stated confidence level (p = 0.7680 on the platform's canonical 6-asset portfolio run — well-calibrated)
- **Point-in-time correctness** — position-sizing volatility estimates are strictly rolling; a look-ahead bias was found and fixed in the rolling estimator, then locked with golden-master regression tests



## Signal Library


| Signal                | Type             | Key data dependency              |
| --------------------- | ---------------- | -------------------------------- |
| **EMA Crossover**     | Trend            | Price features                   |
| **Momentum**          | Trend            | Price features                   |
| **RSI Reversion**     | Mean-reversion   | Price features                   |
| **Donchian Breakout** | Breakout         | Price features                   |
| **Carry**             | Risk premium     | FuturesCurve roll yield          |
| **WTI–Brent Spread**  | Statistical arb  | Cointegration (ADF p≈0.0025 on full-sample re-verification, 2010–2026) |
| **COT Positioning**   | Alternative data | CFTC Managed Money positions     |
| **EIA Inventory**     | Alternative data | EIA petroleum inventory surprise |


All eight signals were evaluated under identical cost and validation assumptions, individually and as a diversified portfolio.

## Findings

Every signal in the platform — four technical baselines and four commodity-specific and alternative-data signals — was tested individually through a parameter sweep corrected for selection bias via the Deflated Sharpe Ratio (Bailey & López de Prado, 2014; significance cutoff DSR ≥ 0.95), and then tested again as a diversified six-asset portfolio under both fixed-notional and volatility-scaled position sizing. Nothing survived at statistical significance under any of the tests.

Only after reaching that conclusion did I check the literature to understand why — and found the answer had been documented for years. Koijen, Moskowitz, Pedersen & Vrugt's *Carry* (2018) and Moskowitz, Ooi & Pedersen's *Time Series Momentum* (2012) both find real, well-documented premia — but only when tested cross-sectionally across dozens of instruments over decades, not on six correlated commodities over a handful of years. The risk engine still measured genuine diversification benefit (up to 2.22× on VaR, confirmed via canonical run `20260910_095142_portfolio_ema_crossover`) — the tools work; the honest conclusion is that this universe is too narrow for a statistically significant edge.

Finding a strategy that looks good in a single backtest is cheap — almost any sufficiently-searched parameter space produces something before correction. What's rare is building the infrastructure to catch that in your own results, not just describe it in someone else's — and then actually using it, including on the finding I most wanted to keep.

## Commodity-Native Analytics

Forward curves are built from individual contract data — a separate dataset that never touches the backtesting pipeline:

- **Forward curve construction** — up to 12 contracts per asset per observation date
- **Term-structure regime classification** — contango / backwardation / flat via annualized slope
- **Roll yield and basis** — annualized, with the continuous-contract basis correctly labelled as pseudo-basis
- **Curve PCA** — Level / Slope / Curvature factor decomposition; Gold: PC1 ≈ 100% on its genuinely computable window (398 dates, ~19 months — no earlier 4-contract Gold curve exists); not a multi-year finding as originally framed. WTI and Natural Gas are two-factor, not three (PC3 is negligible in both, ~1% and ~0.2% respectively) — neither curve is one-dimensional, and the slope factor (PC2) is economically meaningful (11–28% of variance).



## Selected Results


| Metric                         | Value                                                   |
| ------------------------------ | ------------------------------------------------------- |
| **Portfolio 99% daily VaR**    | $44,490 (0.74% of capital)                              |
| **Portfolio 99% ES**           | $99,095                                                 |
| **Diversification benefit**    | 2.22× (Σ per-asset VaR₉₉ / portfolio VaR₉₉; confirmed via canonical run `20260910_095142_portfolio_ema_crossover`) |
| **Kupiec calibration p-value** | 0.7680 on the platform's canonical 6-asset portfolio run (well-calibrated) |
| **Gold–Silver strategy corr**  | 0.65                                                    |
| **WTI–Brent strategy corr**    | 0.63 (0.6294 on the canonical run — rounds to 0.63, not the previously published 0.62) |
| **All 8 signals**              | No signal clears DSR ≥ 0.95 significance — see Findings |

*(All portfolio-level figures above from canonical run `20260910_095142_portfolio_ema_crossover`, git_sha `8f1dd26e`.)*




## Portfolio Risk Analytics

Across the 6-asset universe:

- **Historical-simulation VaR and Expected Shortfall** (95/99%) — no parametric assumption
- **Kupiec Likelihood Ratio test** — VaR model calibration backtesting; p < 0.05 signals miscalibration
- **Contribution-to-risk decomposition** — per-asset marginal vol contribution, sums to 1.0
- **Rolling cross-asset correlations** — 63-day and 126-day windows
- **Regime-conditional attribution** — Sharpe, return, and drawdown conditioned on term-structure regime (contango / backwardation / flat), per-asset and portfolio-level



## The Research Workstation

The engine is exposed through a typed full-stack layer, validated end-to-end by 117 Playwright tests:

- **IC Gate** — the interface enforces the research doctrine. Backtest launch is gated on signal evaluation; overrides are permanently recorded in run metadata (`signal_evaluation: null`). Not a hard block — doctrine-with-override, logged either way.
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

`scripts/reproduce_run.py` re-executes any completed run by ID, hashes the resulting equity curve, and compares against the original artifact — exit 0 = match, 1 = mismatch, 2 = error. A closed reproducibility loop, not a documentation promise.

All experiments additionally tracked in MLflow (`data/mlruns/`) with programmatic trial-count queries feeding the Deflated Sharpe correction.

## Storage

**Parquet is canonical.** ClickHouse (Docker, 24.3) is available behind the same `DataStore` abstraction via a one-line config switch:

```yaml
storage:
  backend: "parquet"      # default
  # backend: "clickhouse" # opt-in after: docker compose up -d
```

24,862 rows at time of ClickHouse verification (current total is closer to ~25,100 across all six assets after subsequent data refreshes); Parquet vs ClickHouse numerical equivalence confirmed at rtol 1e-6. At this data volume, ClickHouse is a migration-path demonstration — the abstraction is the point, not the necessity.

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
pytest -m "not slow"                    # 423 passed (fast suite, ~6-7 min)
pytest                                  # 443 passed (full suite, ~40 min)

# Streamlit reference dashboard
streamlit run dashboard/app.py          # localhost:8501

# React research workstation
make dev                                # FastAPI :8000 + Vite :5173
cd frontend && npm test -- --run        # 427 passed
npx playwright test                     # 117 passed

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
| **Backend fast** | `pytest -m "not slow"`  | 423   | Excludes Hypothesis property tests               |
| **Backend full** | `pytest`                | 443   | Includes property-based invariants               |
| **Frontend**     | `npm test -- --run`     | 427   | Vitest, runs in ~3 min                           |
| **E2E standard** | `npm run test:e2e`      | 110   | Excludes @slow (validation, portfolio regime)    |
| **E2E full**     | `npm run test:e2e:full` | 117   | All tests including ~8 min portfolio computation |


CI enforces **mypy strict** (0 errors, 68 source files) and **ruff** on every push.

## Documentation


| Document                            | Location                                           | Contents                                                           |
| ----------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------ |
| **Architecture**                    | `ARCHITECTURE.md`                                  | System design, layer contracts, 9-layer diagram, known limitations |
| **ADRs**                            | `docs/adr/ADRs.md`                                 | 14 Architecture Decision Records (ADR-001 through ADR-014)         |
| **Implementation Roadmap**          | `IMPLEMENTATION_ROADMAP.md`                        | Full module build log — Phase 1–3 + EM1–14 + F-Track               |
| **Frontend Implementation Roadmap** | `docs/frontend/FRONTEND_IMPLEMENTATION_ROADMAP.md` | Frontend build log — F-Track, FEP, EM14, E2E                       |
| **Frontend Architecture**           | `docs/frontend/FRONTEND_ARCHITECTURE.md`           | React/FastAPI design, state partitioning, TDR index                |
| **Frontend TDRs**                   | `docs/frontend/FRONTEND_TDRs.md`                   | 25 technical design records                                        |
| **Screen Specifications**           | `docs/frontend/SCREEN_SPECIFICATIONS.md`           | All 13 screens with component and data contracts                   |
| **Design System**                   | `docs/frontend/DESIGN_SYSTEM.md`                   | Tokens, typography, chart patterns                                 |




## Project Structure

```
commodity-research-platform/
├── src/
│   ├── core/                    Types, config, registry (all shared contracts)
│   ├── data/                    Data pipeline — loaders, validators, stores, QC
│   ├── signal/                  8 signal generators + SignalEvaluator
│   ├── backtesting/             Engine, sizing, pipeline builder, sweep runner
│   ├── performance/             PerformanceEngine, PortfolioPerformanceEngine
│   ├── analytics/               RegimeAttributionEngine
│   ├── commodity/               FuturesCurveBuilder, TermStructureAnalyzer, CurvePCAEngine
│   ├── risk/                    RiskEngine (VaR, ES, Kupiec, contribution-to-risk)
│   └── validation/              WalkForwardValidator, PSR, DSR (scipy-free)
├── api/
│   ├── main.py                  FastAPI app — startup, CORS, route registration
│   ├── models.py                All Pydantic models (30+ request/response types)
│   └── routers/                 One router per domain — backtests, runs, portfolio,
│                                signals, sweeps, validation, intelligence, regime,
│                                system
├── frontend/
│   ├── src/
│   │   ├── api/                 Generated schema.d.ts, queryKeys, client, hooks
│   │   ├── features/            Screen-scoped React components
│   │   └── lib/                 fmt.ts, chart-theme.ts, shared utilities
│   └── tests/e2e/               15 Playwright spec files + helpers.ts
├── dashboard/                   Streamlit reference dashboard (7 pages)
├── scripts/                     Data acquisition + reproduce_run.py
├── tests/                       443 backend tests + golden master fixture
├── config/                      config.yaml, assets.yaml, strategies.yaml
├── docs/
│   ├── adr/                     ADRs.md (14 records)
│   ├── clickhouse/              SETUP.md
│   ├── frontend/                5 frontend architecture documents
│   └── implementation_notes/    M01–M19 module implementation notes
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
- **No signal in the current library clears statistical significance after correction for selection bias** — see Findings for the full DSR-corrected result across individual and portfolio-level testing
- **Contract-level curve data (used by Carry) is retention-limited to a rolling window per asset, not the full 2010+ history** — an industry-standard limitation also present in professional platforms, not specific to this project's data source



## Disclaimer

*Research and educational software. Not investment advice. No live trading.*

---

*Built to understand commodity futures markets and systematic research workflows from first principles. Every design decision documented. Every result validated.*
