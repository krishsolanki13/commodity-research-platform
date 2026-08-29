# Frontend Architecture
## Commodity Systematic Research Platform

**Version:** 4.0
**Status:** Platform complete. F-track + FEP + EM14 + E2E suite. 406 vitest + 114 E2E (3 skipped by design) + 429 backend. All TD items closed. mypy enforced in CI. Zero open items.
**Audience:** Frontend developers, quantitative researchers, architecture reviewers
**Companion documents:** `FRONTEND_TDRs.md`, `DESIGN_SYSTEM.md`, `SCREEN_SPECIFICATIONS.md`, `FRONTEND_IMPLEMENTATION_ROADMAP.md`

> **Supersession note:** This document supersedes backend **ADR-008 (Streamlit Dashboard Architecture)**. ADR-008's core architectural rule — *the presentation layer performs no data manipulation; all computation lives in `src/`* — is preserved and strengthened here. Only the presentation technology changes. ADR-008 should be marked `Superseded by FRONTEND_TDR-001` in `docs/adr/ADRs.md`.

---

## Table of Contents

1. [Frontend Goals](#1-frontend-goals)
2. [Design Philosophy](#2-design-philosophy)
3. [User Personas and Workflows](#3-user-personas-and-workflows)
4. [Information Architecture](#4-information-architecture)
5. [Navigation and Routing](#5-navigation-and-routing)
6. [Frontend Layer Model](#6-frontend-layer-model)
7. [Component Architecture](#7-component-architecture)
8. [State Management Strategy](#8-state-management-strategy)
9. [API Integration Strategy](#9-api-integration-strategy)
10. [Caching Strategy](#10-caching-strategy)
11. [Error Handling](#11-error-handling)
12. [Loading Strategy](#12-loading-strategy)
13. [Responsiveness and Display Targets](#13-responsiveness-and-display-targets)
14. [Performance Budgets](#14-performance-budgets)
15. [Scalability and Future Evolution](#15-scalability-and-future-evolution)
16. [Repository Structure](#16-repository-structure)
17. [TDR Index](#17-tdr-index)

---

## 1. Frontend Goals

The frontend is an **internal quantitative research workstation**, not a dashboard. Its purpose is to let a researcher execute the platform's canonical research loop — data → features → signal → IC evaluation → backtest → performance → comparison — faster and with fewer errors than a notebook, while making the platform's institutional discipline (signal evaluation before backtesting, immutable run artifacts, explicit contracts) *visible in the interface itself*.

Concrete goals:

1. **Workflow completion, not page viewing.** Every screen answers a research question and leads to the next step of the research loop. Navigation between workflow stages carries context (asset, date range, run) so the researcher never re-enters state.
2. **Information density with hierarchy.** A researcher should see prices, signal quality, and performance for the full universe without scrolling hunts, but the eye must always know where to land first.
3. **Reproducibility surfaced.** Run IDs, parameter snapshots, git hashes, and FeatureSpecs are first-class UI citizens, not buried metadata.
4. **Architectural discipline mirrored.** The frontend enforces the same rule as ADR-007: the UI *gates* backtest launch behind signal evaluation. The interface teaches the workflow.
5. **A full-trading-day tool.** Dark-first, low-glare, keyboard-driven, fast. No animation that does not communicate state.
6. **Phase-scalable.** The IA, routing, and component contracts absorb Phase 2 (Commodity Intelligence) and Phase 3 (Portfolio/Risk/Cross-Asset) without redesign.

Non-goals: mobile support, marketing polish, multi-user auth (out of backend scope), real-time streaming data.

---

## 2. Design Philosophy

**Bloomberg discipline, modern execution.** The visual and interaction language sits between a terminal (density, monospaced numerics, keyboard control, dark surfaces) and a modern internal tool (clear typography, deliberate whitespace, consistent components). Full visual specification is in `DESIGN_SYSTEM.md`.

Operating principles:

- **Presentation-only frontend.** The frontend never computes indicators, signals, PnL, or metrics. It renders what Layers 0–7 produce, requested through the API layer. Client-side computation is limited to *display transforms*: formatting, sorting, filtering, series downsampling for rendering, and chart coordinate math. If a number appears on screen, it was computed in `src/`. This is the frontend restatement of ADR-008's rule and of the backend rule "no computation in page files."
- **URL is the primary state container.** Any screen a researcher is looking at must be shareable and restorable from its URL (asset, date range, selected run(s), active tab, comparison set). Local state is used only for ephemeral interaction (open menus, hover, in-progress form input).
- **Read-heavy, write-rare.** The only mutations are: trigger data ingestion, trigger a backtest run, delete a run. Everything else is a read of immutable artifacts. The caching strategy (§10) exploits this aggressively.
- **Progressive disclosure.** Universe → asset → signal → run → trade. Each level summarizes the level below and links into it. Detail is one click away, never on the first screen.
- **Empty, loading, and error states are designed, not defaulted.** A new install with no runs is the first thing a reviewer will see; it must direct the user to the workflow, not show a blank grid.

---

## 3. User Personas and Workflows

### 3.1 Personas

| Persona | Primary screens | What they optimize for |
|---|---|---|
| **Quant Researcher** (primary) | Research Workbench, Run Detail, Run Comparison | Signal quality judgment speed; parameter iteration loop time |
| **Quant Developer** | Run Detail (artifacts tab), System | Reproducibility, artifact inspection, config verification |
| **Systematic Trader / PM** | Market Overview, Run Comparison, Portfolio (P3) | Cross-strategy and cross-asset judgment; drawdown and risk framing |
| **Risk Analyst** (P3) | Portfolio Analytics, Risk views | Exposure, VaR/ES, correlation regimes |

A single developer plays all roles today; the IA still separates them so Phase 3 requires no restructuring.

### 3.2 The canonical research loop (drives the entire IA)

```
 MARKET DISCOVERY          RESEARCH                    EXECUTION                 ANALYSIS
┌─────────────────┐  ┌──────────────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
│ Market Overview │→ │ Research Workbench       │→ │ Strategy Builder │→ │ Run Detail          │
│ Asset Detail    │  │  features → raw signal   │  │  params → launch │  │  trades/perf/signal │
└─────────────────┘  │  → IC / ICIR / decay     │  └──────────────────┘  │ Run Comparison      │
                     │  [IC GATE]               │        ▲               └─────────────────────┘
                     └──────────────────────────┘        │                          │
                              │  evaluation passes ──────┘                          ▼
                              │                                          ┌─────────────────────┐
                              └──── evaluation fails → iterate           │ Run Explorer        │
                                                                         │ (experiment memory) │
                                                                         └─────────────────────┘
Phase 2 adds:  Commodity Intelligence (term structure) — feeds Research context
Phase 3 adds:  Portfolio Analytics, Cross-Asset, Risk — consume Run Explorer output
```

The **IC Gate** is the interface's signature mechanism: the Strategy Builder's launch action is visually and functionally gated on a `SignalEvaluation` for the current signal/asset combination, with an explicit, logged override ("Backtest anyway — evaluation skipped" → `signal_evaluation = None` in `BacktestResult`, exactly as the backend contract allows). The UI enforces institutional practice by default and records deviation, mirroring ADR-007.

### 3.3 Workflow-to-screen mapping

| Workflow step (backend §10) | Screen | API surface consumed |
|---|---|---|
| 1. Load asset data | Market Overview / Asset Detail | Layer 0 |
| 2. Build feature frame | Research Workbench — Features panel | Layer 1 |
| 3. Generate raw signal | Research Workbench — Signal panel | Layer 2 |
| 4. Evaluate signal quality | Research Workbench — Evaluation panel (IC Gate) | Layer 2 |
| 5–6. Position signal + backtest | Strategy Builder | Layers 2, 3 |
| 7. Compute performance | Run Detail — Performance tab | Layer 4 |
| 8. Store / recall runs | Run Explorer, Run Comparison | Layer 3 (RunRegistry), 4 |
| Term structure (P2) | Commodity Intelligence | Layer 5 |
| Portfolio / risk / correlation (P3) | Portfolio Analytics, Cross-Asset | Layers 6, 7 |

---

## 4. Information Architecture

### 4.1 Module hierarchy

```
Workstation
├── Market                          Phase 1
│   ├── Market Overview             (universe grid: 6 assets → dozens)
│   └── Asset Detail                (/market/:asset)
├── Research                        Phase 1
│   └── Research Workbench          (/research?asset=&signal=…)
│       ├── Features panel
│       ├── Signal panel
│       └── Evaluation panel (IC Gate)
├── Backtest                        Phase 1
│   └── Strategy Builder            (/backtest/new)
├── Runs                            Phase 1
│   ├── Run Explorer                (/runs)
│   ├── Run Detail                  (/runs/:runId)
│   │   ├── Overview tab
│   │   ├── Trades tab
│   │   ├── Performance tab
│   │   ├── Signal Quality tab
│   │   └── Artifacts tab
│   └── Run Comparison              (/runs/compare?ids=a,b,c)
├── Intelligence                    Phase 2
│   └── Commodity Intelligence      (/intelligence/:asset)
├── Portfolio                       Phase 3
│   ├── Portfolio Analytics         (/portfolio)
│   ├── Risk                        (/portfolio/risk)
│   └── Cross-Asset                 (/portfolio/cross-asset)
└── System                          Phase 1
    ├── Data Manager                (/system/data — ingestion status, validation log)
    └── Configuration               (/system/config — read-only view of YAML configs)
```

### 4.2 Navigation tiers

- **Primary navigation** — fixed left rail, one entry per module group above (Market, Research, Backtest, Runs, Intelligence, Portfolio, System). Icons + labels; collapses to icon-only. Phase-gated entries render disabled with a phase tag rather than hidden, advertising the roadmap.
- **Secondary navigation** — contextual within a module: tabs inside Run Detail; panel switcher inside Research Workbench; sub-pages under Portfolio.
- **Global Context Bar** — a persistent horizontal strip under the top bar holding the **research context**: selected asset, date range, and (when applicable) selected signal/strategy. Screens that are context-aware (Asset Detail, Workbench, Strategy Builder, Intelligence) read and write this context; screens that are not (Run Explorer) ignore it. Context is serialized into URLs.
- **Command palette (⌘K)** — jump to any asset, run, or screen; execute "New backtest with current context"; search runs by strategy/asset/date. This is the terminal-style power path and the primary discoverability mechanism as the universe grows.
- **Breadcrumb strategy** — breadcrumbs appear only on entity detail screens (`Runs / 20260706_142233_ema_crossover_gold / Trades`, `Market / Gold`). Top-level screens show a title, not a one-crumb breadcrumb. Breadcrumb segments are links carrying context.

### 4.3 User journeys (reference set)

1. **New signal idea:** Market Overview → notices copper trend → Asset Detail → "Open in Workbench" (context carries asset) → add EMA(20)/EMA(100) features → EMACrossover signal → IC = 0.061, ICIR 0.7 → gate opens → "Configure backtest" → Strategy Builder pre-filled → launch → redirected to Run Detail on completion.
2. **Parameter iteration:** Run Detail of a mediocre run → "Re-run with changes" → Strategy Builder pre-filled from `params.json` → adjust threshold → launch → Run Comparison auto-suggested between parent and child run.
3. **Weekly review:** Run Explorer → filter `strategy=ema_crossover`, sort by Sharpe → select 4 → Compare → overlaid equity curves + metric delta table → open weakest run's Trades tab → inspect losing streak dates → cross-link to Asset Detail at that date range.
4. **Data hygiene:** System / Data Manager → validation log shows OHLC violation flagged in natural gas ingestion → inspect offending rows → re-ingest.

---

## 5. Navigation and Routing

### 5.1 Route table (all phases — FEP-complete)

| Route | Screen | URL state |
|---|---|---|
| `/` | redirect → `/market` | — |
| `/market` | Market Overview | `?range=` |
| `/market/:asset` | Asset Detail | `?from=&to=&indicators=` |
| `/research` | Research Workbench | `?asset=&strategy=&params=&evaluation=&evalOverride=` |
| `/backtest/new` | Strategy Builder | `?asset=&strategy=&params=&evaluation=&evalOverride=` |
| `/runs` | Run Explorer | `?strategy=&asset=&sort=&q=` |
| `/runs/compare` | Run Comparison | `?ids=` ← must be registered BEFORE `/runs/:runId` |
| `/runs/:runId` | Run Detail | `?tab=` (tabs: overview, signal-quality, validation, trades, artifacts) |
| `/intelligence` | Futures Curve | `?asset=&n_contracts=&lookback=&observation_date=` |
| `/intelligence/compare` | Curve Comparison | `?assets=&n_contracts=` |
| `/intelligence/pca` | Curve PCA | `?asset=&n_components=&n_contracts=&from_date=&to_date=` (FEP) |
| `/sweeps` | Sweep Explorer | `?sweep_id=&sort_by=&sort_dir=` (FEP) |
| `/portfolio` | Portfolio Analytics | `?run_id=` |
| `/system` | Data Manager | `?asset=` (FEP — asset selector drives QC/COT/EIA panels) |
| `*` | Not Found | — |

**Critical routing rule:** `/runs/compare` must be registered before `/runs/:runId` in the route table. If `:runId` appears first, navigating to `/runs/compare` will try to load a run with ID `"compare"` and 404.

**IC Gate URL contract (F17):**
- PATH A (Configure backtest → from meaningful/weak IC): `?evaluation=JSON.stringify(EvaluationResult)` — evaluation is persisted with the run
- PATH B (Backtest without evaluation / override): `?evalOverride=1` — run records `signal_evaluation: null`, override flag recorded in artifacts

### 5.2 Routing rules

- React Router in library (data-less) mode; TanStack Query owns all data fetching (see TDR-006). Routes are lazy-loaded per module group for code-splitting.
- All filter/tab/selection state that survives a refresh lives in search params via a typed `useUrlState` hook (Zod-validated parse, silent fallback to defaults on invalid params).
- Navigation between workflow stages uses **context-carrying links**: `Open in Workbench`, `Configure backtest`, `Re-run with changes`, `Compare with…` construct URLs from current context rather than relying on hidden state.
- Unsaved-form guard on Strategy Builder only (the single screen with meaningful transient input).

---

## 6. Frontend Layer Model

Mirrors the backend's strict downward dependency rule.

```
┌────────────────────────────────────────────────────────────────┐
│ F4 — SCREENS (routes/pages)                                    │
│ Compose features; own layout and URL state. No fetch logic,    │
│ no business rules beyond composition.                          │
├────────────────────────────────────────────────────────────────┤
│ F3 — FEATURES (workflow units)                                 │
│ e.g. run-comparison, ic-evaluation, strategy-form, universe-   │
│ grid. Own their queries/mutations and feature-local state.     │
├────────────────────────────────────────────────────────────────┤
│ F2 — DOMAIN COMPONENTS (research-specific, reusable)           │
│ PriceChart, EquityCurveChart, ICDecayChart, MetricGrid,        │
│ TradeTable, RunStatusBadge… Pure props-in, pixels-out.         │
├────────────────────────────────────────────────────────────────┤
│ F1 — UI PRIMITIVES (design system)                             │
│ Button, Table, Tabs, Panel, Input, Toast… (shadcn/ui base +    │
│ tokens). No domain knowledge.                                  │
├────────────────────────────────────────────────────────────────┤
│ F0 — API CLIENT & TYPES                                        │
│ Generated TypeScript types from OpenAPI; typed fetch wrapper;  │
│ query-key factory; serialization of backend contracts.         │
└────────────────────────────────────────────────────────────────┘
Dependency rule: a layer imports only from layers below it.
F2 components never fetch. F1 never imports domain types.
```

The TypeScript types in F0 are the frontend mirror of `src/core/types.py`: `NormalizedOHLCV` (as a columnar series payload), `FeatureSpec`, `SignalEvaluation`, `TradeRecord`, `BacktestResult` (metadata + series references), `PerformanceReport`. They are **generated, not hand-written** (see §9.4), so contract drift between Python and TypeScript is mechanically impossible.

---

## 7. Component Architecture

Full component-by-component specification (props, states, accessibility) is in `DESIGN_SYSTEM.md` §8. Architectural rules:

1. **Container/presentational split at the F3/F2 boundary.** Features fetch and orchestrate; domain components render. Every F2 component is testable with a fixture object and renderable in isolation.
2. **Charts are wrappers around one engine.** All charts are thin configuration wrappers over Apache ECharts (TDR-004) sharing a `useChartTheme()` hook that maps design tokens → ECharts theme, and a common `<ChartFrame>` that provides title, toolbar (zoom reset, PNG export, fullscreen), loading skeleton, and empty/error states. No screen instantiates ECharts directly.
3. **Tables are one component.** A single `<DataGrid>` built on TanStack Table provides sorting, filtering, column visibility, sticky headers, virtualized rows, and CSV export. Domain tables (TradeTable, RunTable, UniverseGrid) are column definitions + formatters, not new table implementations.
4. **Formatting is centralized.** `fmt.price(v, asset)`, `fmt.pct(v)`, `fmt.usd(v)`, `fmt.metric(name, v)`, `fmt.date(v)` in one module, asset-aware via `assets.yaml` metadata (tick size drives decimal places). No inline `toFixed` anywhere.
5. **Semantic color is data-driven, never hardcoded.** Long/short, gain/loss, IC-quality banding, and regime colors come from token-mapped helpers (`tone.pnl(v)`, `tone.ic(v)`), keeping the meaning of color consistent platform-wide.

---

## 8. State Management Strategy

Four state classes, four homes — chosen to keep each kind of state in the simplest tool that owns it (TDR-005):

| State class | Examples | Home |
|---|---|---|
| **Server state** | OHLCV, feature frames, evaluations, runs, reports | TanStack Query cache (the only cache) |
| **URL state** | asset, date range, run ids, tab, filters, sort | Search params via `useUrlState` (Zod-typed) |
| **Workspace state** | research context defaults, sidebar collapsed, density mode, theme, comparison basket | Zustand store, persisted to `localStorage` |
| **Ephemeral UI state** | open menu, hover, form draft | Component state / React Hook Form |

Rules:

- Nothing server-derived is ever copied into Zustand. Derived data is computed in selectors/memos from Query cache results.
- URL beats workspace: if a link specifies `?asset=copper`, it overrides the remembered context, then updates it.
- The **comparison basket** (runs selected for comparison across screens) lives in Zustand (`comparisonBasket`, persisted to localStorage key `commodity-research-comparison-basket`, max 8 runs) and renders as a docked tray.
- **Portfolio run history** is served by `GET /api/portfolio/runs` — not localStorage (F16 Inc6 removed the Zustand store workaround).
- **Sweep history** lives in Zustand (`sweepHistory`, persisted to localStorage key `commodity-research-sweep-history`, max 10 sweep IDs). Added FEP Inc6.
- **LAST RELOAD timestamp** persists in localStorage after "Reload data" button fires successfully. Frontend-derived (backend returns `last_ingestion: null` — see TD-FEP-PORTFOLIO-RACE).
- **IC evaluation state** is held in **TanStack Query cache** — not Zustand. The evaluation result (IC value, ICIR, decay data) is cached by the query key derived from (asset, strategy, params). Cache dies on full page navigation (`page.goto()`). After reload, the Research Workbench correctly shows "No evaluation found" — this is correct behavior per TDR-006. Any component comment or spec referencing "Zustand for IC state" is incorrect.
- **Backtest launch** is a Query mutation whose completion invalidates the runs list and navigates to the new Run Detail (`poll_` prefix stripped from URL: `runId.replace(/^poll_/, '')`).

**useUrlState semantics (F18 — critical):**
- `null` = explicit delete: removes the param from the URL
- `undefined` = no-op: preserves existing URL param value
- Using `undefined` to clear a param is a silent bug. All callers confirmed: `CompareConfigPanel`, `CurveDateControl`, `PortfolioAnalytics`.

**AssetDetail → ResearchWorkbench navigation (F18 root cause fix):**
`AssetDetail.tsx` must NOT have a `useEffect` cleanup function that calls `setSearchParams` or deletes URL params on unmount. This was the root cause of the "Open in Workbench" feature never working — the cleanup fired after navigation and deleted `?asset=` from the new screen's URL.

---

## 9. API Integration Strategy

### 9.1 The missing HTTP boundary

The backend has no API today — `src/` is a Python library and Streamlit imported it in-process. A React frontend requires an HTTP boundary. **Decision:** introduce a thin **FastAPI service** (`api/`) that only *exposes* existing `src/` functions. It contains zero business logic — the frontend equivalent of the "no computation in dashboard code" rule applies to the API layer too: no computation in route handlers beyond serialization. This is Module F0 in the roadmap and TDR-002. It preserves every backend ADR: `src/` remains the sole computation home; the API is a serialization shell; the frontend is a presentation shell.

### 9.2 Endpoint surface (Phase 1)

```
GET  /api/assets                                → universe + assets.yaml metadata
GET  /api/assets/{asset}/ohlcv?from&to&downsample → NormalizedOHLCV (columnar JSON)
GET  /api/assets/{asset}/summary                → last price, returns, vol summary (Layer 0/4 helpers)
POST /api/features/compute                      → {asset, specs[]} → FeatureFrame columns + FeatureSpec[]
POST /api/signals/generate                      → {asset, signal, params, features} → RawSignal series
POST /api/signals/evaluate                      → SignalEvaluation (IC, ICIR, decay, turnover)
GET  /api/indicators                            → indicator catalog (name, params schema, category, column_name convention) — drives IndicatorPicker; adding an indicator to the backend registry automatically surfaces it here
GET  /api/strategies                            → strategies.yaml defaults + param schemas
POST /api/backtests                             → launch run; returns {run_id, status}
GET  /api/backtests/{run_id}/status             → queued|running|complete|failed (+error)
GET  /api/runs?strategy&asset&sort&q            → run registry list (metadata + headline metrics)
GET  /api/runs/{run_id}                         → params.json + metrics.json + metadata
GET  /api/runs/{run_id}/series/{name}           → equity_curve | pnl | positions (columnar)
GET  /api/runs/{run_id}/trades?page             → TradeRecord page
POST /api/runs/compare                          → {ids[]} → aligned series + metric matrix
DELETE /api/runs/{run_id}                       → RunRegistry.delete_run
GET  /api/system/data-status                    → per-asset ingestion + validation log
POST /api/system/ingest                         → trigger DataLoader.load(asset)
GET  /api/system/config                         → merged, secret-free config view
```

Phase 2 added `/api/curve/{asset}?date`, `/api/term-structure/{asset}` (Layer 5) — delivered F9–F11. Phase 3 portfolio surface delivered F12–F15 and extended through FEP + EM14.

**Async job pattern — all five job types confirmed working:**

All compute-heavy operations follow the same pattern: `POST` → `{job_id, status: "queued"}` → poll `GET /{job_id}/status` → `GET /{job_id}/result`. No synchronous endpoint blocks the server.

| Job type | Launch endpoint | Status | Result |
|---|---|---|---|
| Backtest | `POST /api/backtests` | `/api/backtests/{id}/status` | `/api/runs/{id}` |
| Portfolio run | `POST /api/portfolio/run` | `/api/portfolio/{id}/status` | `/api/portfolio/{id}/summary` etc. |
| Walk-forward validation | `POST /api/validation/run` | `/api/validation/{id}/status` | `/api/validation/{id}/report` |
| Parameter sweep | `POST /api/sweeps` | `/api/sweeps/{id}/status` | `/api/sweeps/{id}/results` |
| Regime attribution (per-asset) | `POST /api/regime-attribution/compute` | `/api/regime-attribution/{id}/status` | `/api/regime-attribution/{id}/result` |
| Regime attribution (portfolio) | `POST /api/regime-attribution/compute-portfolio` | same status endpoint | `/api/regime-attribution/{id}/portfolio-result` |

**Run list pagination (TD-RUN-EXPLORER-PERF — closed):** `GET /api/runs` queries a SQLite index (`data/runs/index.db`) rather than reading individual `metrics.json` files. Response includes `{ runs: RunListItem[], total: number, page: number, page_size: number }`. Default page size: 50, sorted `executed_at DESC`. Run Explorer handles Prev/Next pagination and displays "Showing 1–50 of N runs". Load time: 0.45s regardless of run count (was 30s with 925 runs before the index).

**Phase 3 endpoints (backend M14–M19 complete — available now):**

```
POST /api/portfolio/run                         → trigger MultiAssetRunner across all/selected assets;
                                                  returns {run_id, status}; async (same pattern as backtests)
GET  /api/portfolio/{run_id}/status             → queued|running|complete|failed (+error)
GET  /api/portfolio/{run_id}/summary            → PortfolioPerformanceReport
                                                  (portfolio_metrics, asset_contributions,
                                                   absolute_pnl_by_asset, portfolio_date_range,
                                                   per_asset_reports headlines, initial_capital_total)
GET  /api/portfolio/{run_id}/risk               → RiskReport
                                                  (portfolio_var_95/99, portfolio_es_95/99,
                                                   portfolio_var_95/99_pct, asset_var_95/99,
                                                   avg_gross/net_notional_by_asset,
                                                   total_avg_gross_notional, diversification_benefit)
GET  /api/portfolio/{run_id}/correlation        → CorrelationReport
                                                  (correlation_matrix, rolling_correlations_63/126,
                                                   realized_vol_by_asset, portfolio_realized_vol,
                                                   avg_pairwise_correlation, most/least_correlated_pair)
GET  /api/portfolio/{run_id}/equity             → portfolio_equity_curve + portfolio_pnl_series (columnar)
GET  /api/portfolio/{run_id}/assets             → assets: string[], asset_metrics: Record<string, Record<string, float|null>>, asset_run_ids: Record<string, string|null>
GET  /api/portfolio/runs                        → list of recent portfolio runs (run_id, strategy, total_return, executed_at)
DELETE /api/portfolio/{run_id}                  → cleanup portfolio run artifacts
```

**poll\_ prefix handling (F16):** All backtest and portfolio status endpoints return the `run_id` exactly as passed in — the `poll_` prefix is NOT stripped by the backend. Frontend must strip it before navigation and display:
```typescript
const artifactId = runId.replace(/^poll_/, '')
navigate(`/runs/${artifactId}`)  // or /portfolio?run_id=...
```

**Portfolio artifact persistence (EM3 — closed E6):** All 7 portfolio artifacts (`portfolio_summary.json`, `portfolio_equity.parquet`, `portfolio_pnl.parquet`, `portfolio_risk.json`, `portfolio_correlation.json`, `portfolio_positions.parquet`, `portfolio_regime_attribution.json`) persist to disk. The pre-EM3 note about in-memory-only equity/risk/correlation endpoints is **stale and incorrect** — all endpoints survive server restart. The frontend graceful degradation message ("Detailed analytics unavailable — re-run to restore") was removed in EM3 and is no longer rendered.

**Key Phase 3 type notes for API consumers:**
- `absolute_pnl_by_asset` (always-stable USD attribution) is preferred over `asset_contributions` (fractional, unstable when |total_pnl/capital| < 1%). S11 displays absolute PnL by default; fractional only when denominator is large enough.
- Rolling correlation lookup uses upper-triangle only: `rolling_correlations_63[a][b]` exists only when `a < b` alphabetically. Always look up as `min(x,y), max(x,y)`. The API should symmetrize this before returning to avoid client-side complexity.
- `realized_vol_by_asset` values (2–8%/yr for EMA 50/200) are **strategy P&L vols**, not commodity price vols (15–60%/yr). Label as "Strategy Realized Vol" not "Asset Volatility".
- `portfolio_diversification_benefit = sum(asset_var_99) / portfolio_var_99`. Values > 1.0 indicate diversification is reducing portfolio risk. Real-data confirmed: 2.23× for EMA 50/200 across 6 assets.

The surface grows by module, never by redesign.

### 9.3 Payload conventions

- **Time series are columnar**, not row-of-objects: `{index: number[] (epoch ms), columns: {close: number[], …}}`. This is 3–5× smaller, decodes straight into typed arrays, and maps naturally from DataFrames.
- **Server-side downsampling** for chart payloads: OHLCV beyond ~3,000 bars is LTTB/OHLC-bucket downsampled by the API for overview charts; detail zoom refetches the window at full resolution. Downsampling is a display transform, so it is legitimately API-side per the presentation rule.
- **Long-running work is async.** All five compute-heavy operation types (backtest, portfolio run, walk-forward validation, parameter sweep, regime attribution) follow the same pattern: `POST` returns `{job_id}` immediately; client polls `/status` at 2s while `status !== 'complete' && status !== 'failed'`. Polling stops when complete or failed; `staleTime: Infinity` on result queries (immutable once written). No SSE upgrade was built — polling remains correct at current scale.
- Errors follow one envelope: `{error: {code, message, detail?, field_errors?}}` with correct HTTP semantics (400 validation, 404 unknown run or asset, 500 with `run_id`/log reference). **The evaluation gate is enforced client-side by `ICGateStrip`, not by the API.** The backend accepts a backtest launch with `signal_evaluation: null` — that is the deliberate override path, recorded in run metadata. There is no 409 for a missing evaluation; the API never enforces the doctrine, only the UI does.

### 9.4 Type generation

FastAPI emits OpenAPI; `openapi-typescript` generates `src/api/schema.d.ts` in CI and in the dev loop. Pydantic models in the API layer are constructed from the dataclasses in `src/core/types.py`, making that file the single source of truth end-to-end: `types.py → Pydantic → OpenAPI → TypeScript`. A contract change is one edit and two generated artifacts.

---

## 10. Caching Strategy

Cache aggressiveness follows data mutability, which the backend guarantees:

| Data | Mutability (backend rule) | Query config |
|---|---|---|
| Run artifacts (`/runs/{id}/**`) | **Immutable once written** | `staleTime: Infinity`, `gcTime: 1h` — never refetched |
| Run list | Append/delete only | `staleTime: 30s`, invalidated by launch/delete mutations |
| OHLCV / summaries | Changes only on re-ingestion | `staleTime: 5m`, invalidated by ingest mutation |
| Features / signals / evaluations | Deterministic function of (asset, params) | keyed by canonicalized param hash; `staleTime: Infinity` per key |
| Config / strategies / assets | Static per session | `staleTime: Infinity` |
| Backtest status | Live | polled while `running`, then removed |

Additional mechanics: a central **query-key factory** (`qk.run(id)`, `qk.ohlcv(asset, range)`) prevents key drift; hover-**prefetch** on run rows and asset rows makes detail screens feel instant; Run Comparison reuses per-run caches before requesting the aligned comparison payload. No custom cache layer exists outside TanStack Query.

---

## 11. Error Handling

Three tiers, all designed states (visual spec in `DESIGN_SYSTEM.md` §9):

1. **Field/validation errors** — Strategy Builder and Workbench forms validate with Zod client-side before submission; API `field_errors` map back onto form fields via React Hook Form. The launch button is disabled with a reason, never silently.
2. **Panel-scoped data errors** — every F3 feature is wrapped in an error boundary + query error state rendering an inline `<ErrorState>` (what failed, the API error code, a Retry action). One failed chart never blanks a screen; sibling panels keep rendering.
3. **Screen/app errors** — route-level boundary with "return to Market Overview"; unknown run id renders a designed 404 with a link to Run Explorer; API-unreachable renders a full-screen connection state with retry, since nothing works without the API.

Domain-specific handling: a **failed backtest run** is a first-class object — the Run Detail screen for a failed run shows status `failed`, the captured exception summary, and the parameter snapshot, with a "Re-run with changes" path (failures are research information, not dead ends). **Data validation flags** from Layer 0 surface as a non-blocking warning ribbon on Asset Detail/Workbench ("3 anomalies flagged in this range → view in Data Manager"), keeping the backend's data-quality discipline visible where research happens.

Mutations use toasts only for confirmation of async completion ("Run 20260706_… complete — View"); errors render in place, never only as a toast.

---

## 12. Loading Strategy

- **Skeletons mirror final layout** (chart frame skeleton, table row skeletons, metric-grid skeletons) — no spinners on primary surfaces; spinners are reserved for button-level pending states.
- **Progressive hydration per panel.** Screens render their shell immediately; each panel resolves independently (Suspense per feature). Metric numbers appear before charts; charts before tables.
- **Perceived-speed tools:** hover prefetch (§10), `keepPreviousData` on filter/sort changes so grids never flash empty, optimistic add-to-comparison-basket, and route-level code splitting so first paint isn't taxed by ECharts until a chart screen loads.
- **Backtest launch feedback:** launch → button pending → redirect to Run Detail in `running` state (live status panel with elapsed time) → panels hydrate as artifacts land. The researcher watches the run become a result on the screen where they'll analyze it.

---

## 13. Responsiveness and Display Targets

Desktop-first with three deliberate breakpoints, not fluid mobile-style responsiveness:

| Tier | Width | Behavior |
|---|---|---|
| **Ultrawide** | ≥ 2100px | Multi-panel layouts widen to 3-column; comparison shows 4 runs side-by-side; charts gain horizontal room, not new content |
| **Standard (primary)** | 1440–2100px | Canonical layouts as specified in `SCREEN_SPECIFICATIONS.md` |
| **Laptop (supported)** | 1160–1440px | Left rail auto-collapses to icons; side panels become drawers; density stays compact |

Below 1160px the app renders a "designed for desktop research" notice. Mobile is explicitly out of scope. Density modes (compact default / comfortable) are a user setting orthogonal to breakpoints.

---

## 14. Performance Budgets

| Budget | Target |
|---|---|
| First contentful paint (dev machine, local API) | < 1.0s |
| Route transition (code-split chunk) | < 300ms |
| Chart render, 3k downsampled bars | < 150ms |
| Table interaction (sort/filter, 10k virtualized rows) | < 50ms |
| Initial JS (gzipped, before chart chunk) | < 250KB |

Enforcement: bundle analysis in CI; ECharts loaded per-chart-type via tree-shaken imports; virtualization mandatory for any table that can exceed 200 rows (trade logs will).

---

## 15. Scalability and Future Evolution

**Universe growth (6 → dozens of assets):** Market Overview is a virtualized grid with search/sector grouping from day one, not six cards. Asset selection everywhere is the searchable `AssetSelector`, not a dropdown of six.

**Indicator growth (5 → hundreds):** the Workbench feature panel is driven by an indicator catalog endpoint (name, params schema, category) — adding an indicator to the backend registry makes it appear in the UI with a generated param form. No frontend change per indicator.

**Phase 2 (Commodity Intelligence):** new module group + routes; new chart components (`FuturesCurveChart`, `TermStructureRibbon`); a regime badge added to Asset Detail and the Context Bar. Volatility-scaled sizing appears as a new sizing section in Strategy Builder driven by the strategies/config schema. MLflow arrival changes nothing user-facing (RunRegistry API stays canonical), with an optional deep link "Open in MLflow" per run.

**Phase 3 (Portfolio) — backend complete, UI next:** Portfolio module activates (F12–F15); Run Comparison generalizes into portfolio aggregation views; `CorrelationHeatmap` and exposure components land. The comparison basket becomes the seed for portfolio composition — an IA decision made now so Phase 3 feels like a continuation. The backend already delivers: `MultiAssetRunner`, `PortfolioPerformanceEngine`, `RiskEngine` (historical VaR/ES), `CorrelationEngine` (pairwise matrix, rolling correlations), `ClickHouseStore` (24,862 rows migrated), and Dashboard Page 7 (7-section Streamlit reference). The React F12–F15 modules build on concrete API contracts, not speculative types.

**Beyond:** multi-user (auth at the API layer, no frontend restructure), additional asset classes (asset metadata already drives formatting/multipliers), live pipelines (SSE replaces polling behind the same query hooks).

---

## 16. Repository Structure

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json                  # strict: true
├── package.json
├── src/
│   ├── main.tsx
│   ├── app/
│   │   ├── App.tsx                # providers: Query, Router, Theme, Toast
│   │   ├── routes.tsx             # route table, lazy imports
│   │   └── shell/                 # AppShell, SidebarNav, TopBar, ContextBar, CommandPalette
│   ├── api/                       # F0
│   │   ├── schema.d.ts            # GENERATED from OpenAPI — never edited
│   │   ├── client.ts              # typed fetch wrapper + error envelope parsing
│   │   ├── queryKeys.ts           # query-key factory
│   │   └── hooks/                 # useOhlcv, useRun, useRuns, useEvaluation, useLaunchBacktest…
│   ├── ui/                        # F1 — primitives (shadcn/ui + tokens)
│   ├── components/                # F2 — domain components
│   │   ├── charts/                # ChartFrame, PriceChart, EquityCurveChart, ICDecayChart…
│   │   ├── data/                  # DataGrid, MetricGrid, MetricStat, RunStatusBadge…
│   │   └── inputs/                # AssetSelector, DateRangePicker, ParamField…
│   ├── features/                  # F3 — workflow units
│   │   ├── market/  research/  backtest/  runs/  system/
│   │   ├── intelligence/          # Phase 2
│   │   └── portfolio/             # Phase 3
│   ├── screens/                   # F4 — route components
│   ├── stores/                    # Zustand: workspace.ts, comparisonBasket.ts, sweepHistory.ts (FEP)
│   ├── lib/                       # fmt.ts, tone.ts, useUrlState.ts, downsample-view.ts, retry.ts (FEP)
│   └── styles/                    # tokens.css, globals.css
└── tests/                         # vitest + testing-library; playwright smoke
api/                               # FastAPI serialization shell (Module F0)
├── main.py  routers/  models.py   # Pydantic mirrors of src/core/types.py
└── tests/
```

Rules: `schema.d.ts` is generated only; `ui/` never imports from `components/` or above; `components/` never fetches; screens never call `client.ts` directly (only F3 hooks); all colors/spacing via tokens.

---

## 17. TDR Index

| TDR | Title | Status |
|---|---|---|
| TDR-001 | React + Vite + TypeScript SPA (supersedes ADR-008's Streamlit choice) | Accepted |
| TDR-002 | FastAPI serialization shell as the HTTP boundary | Accepted |
| TDR-003 | Tailwind CSS + shadcn/ui on a design-token foundation | Accepted |
| TDR-004 | Apache ECharts as the single charting engine | Accepted |
| TDR-005 | TanStack Query + URL state + Zustand (state partitioning) | Accepted |
| TDR-006 | React Router (library mode), client-side SPA, no SSR framework | Accepted |
| TDR-007 | TanStack Table + virtualization for all data grids | Partially superseded by TDR-011 |
| TDR-008 | React Hook Form + Zod, schema-driven parameter forms | Accepted |
| TDR-009 | No animation library; CSS transitions only | Accepted |
| TDR-010 | OpenAPI-generated TypeScript contracts | Accepted |
| TDR-011 | Plain HTML `<table>` for all non-virtualized tables | Accepted (F18) |
| TDR-012 | ECharts CSS variable resolution via resolveCssVar() | Accepted (F16) |
| TDR-013 | Position state as markArea bands (not separate pane) | Accepted (F18) |
| TDR-014 | useUrlState: null=delete, undefined=preserve | Accepted (F18) |
| TDR-015 | Uniform workflow page layout: grid-cols-2 | Accepted (F18) |
| TDR-016 (AD-FEP-001) | Regime panel: opt-in button — no auto-fetch on mount | Accepted (FEP) |
| TDR-017 (AD-FEP-002) | TDR-011 confirmed for all FEP tables | Accepted (FEP) |
| TDR-018 (AD-FEP-003) | Contango=amber/warn, Backwardation=green/gain — DESIGN_SYSTEM corrected | Accepted (FEP) |
| TDR-019 (AD-FEP-004) | TDR-015 extended — all workflow screens grid-cols-2 | Accepted (FEP) |
| TDR-020 (AD-FEP-005) | TDR-012 confirmed — resolveCssVar() everywhere in FEP charts | Accepted (FEP) |
| TDR-021 (AD-FEP-006) | All Radix TooltipContent: dark platform theme in shared tooltip.tsx | Accepted (FEP) |
| TDR-022 (AD-FEP-007) | Sweep n_complete: completion-only by design | Accepted (FEP) |
| TDR-023 (AD-FEP-008) | fetchWithRaceRetry on all 5 portfolio result hooks | Accepted (FEP — removed EM14) |
| TDR-024 | RouteErrorBoundary on all 16 routes — no chart crash takes down full app | Accepted (post-FEP) |
| TDR-025 | IC state: TanStack Query cache, not Zustand — dies on page.goto() by design | Confirmed (E2E) |

Full records in `FRONTEND_TDRs.md`.
