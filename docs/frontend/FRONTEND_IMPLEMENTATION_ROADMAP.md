# Frontend Implementation Roadmap
## Commodity Systematic Research Platform

**Purpose:** Defines the exact module development sequence for the frontend, in the same format and discipline as the backend `IMPLEMENTATION_ROADMAP.md`. Designed for Cursor-based incremental development with Claude. Each module has explicit dependencies, deliverables, testing requirements, and a gate.

**STATUS: F-TRACK COMPLETE (F0–F18)**

All modules F0–F18 are merged to `main` and tagged. Final state:
- **354 vitest** (97 files) — 0 failures
- **33 Playwright E2E** (27 pass + 1 graceful CI skip per design + 5 conditional on live data)
- **332 backend pytest** — 0 failures
- TypeScript strict: clean. ESLint: 0 warnings. Prettier: clean. Build: exits 0.
- All 10 screens delivered and verified across Steps 1–12 manual review.

**Post-F-track tags:** `F18-complete`, `ftrack-complete`, `F4-complete` (Phase F4 portfolio complete)

**Git history (rebased):** 297 total commits. 9 semantic commits since F15-complete representing all post-F-track work (F16–F18 + backend patches).

**Open technical debt (backend owner unless noted):**
| ID | Item | Owner |
|---|---|---|
| TD-F18-D | FuturesCurve period selector (fixed in F18 final hotfix) | ✓ CLOSED |
| TD-F18-A | Price pane markArea bands (index alignment) | Frontend — deferred |
| TD-F18-B | ohlcv/raw/position index arrays not guaranteed identical | Backend contract |
| E6 | /equity /risk /correlation in-memory only | Backend |
| ICRollingChart | Awaiting /api/signals/rolling-ic endpoint | Backend |
| CarrySignal | Awaiting backend CarrySignal class | Backend |
| TD-fmt-thousands | fmt.price no thousands separator | Frontend |
| TD-LastIngestion | Backend returns null for last_ingestion | Backend |

**Principle (mirrors the backend):** Build one vertical slice end-to-end before expanding horizontally. The first user-visible slice is: **Market Overview → Asset Detail for Gold**, followed immediately by the core research slice: **Workbench evaluation → backtest launch → Run Detail**.

**Prerequisite (all met):** Backend M01–M19 complete (phase-3-complete tag). F-track F0–F18 complete (ftrack-complete tag).

---

## Phase F1 — Research Workstation MVP

### Module F0: API Serialization Shell  *(backend-side prerequisite)*

**Purpose:** Introduce the HTTP boundary (TDR-002). FastAPI service exposing existing `src/` functions with zero business logic in handlers.

**Dependencies:** Backend Phase 1 (M01–M07) and Phase 2 (M08–M13) complete. The API shell exposes both phases' `src/` functions from day one — the Phase F2 UI modules (F9–F11) extend the existing shell, they do not require a rebuild.

**Deliverables:**
- `api/main.py` — app factory, CORS (localhost dev), `/api/health`
- `api/models.py` — Pydantic models mirroring `src/core/types.py` 1:1 (constructed from the dataclasses; no parallel definitions), columnar-series response model
- `api/routers/` — `assets.py`, `features.py`, `signals.py`, `backtests.py`, `runs.py`, `system.py` implementing the full endpoint surface in `FRONTEND_ARCHITECTURE.md` §9.2; `signals.py` additionally includes `GET /api/indicators` (indicator catalog — name, params schema, category, column_name convention — derived from the `Indicator` registry in `src/core/registry.py`; adding an indicator to the backend registry surfaces it automatically in the UI's `IndicatorPicker` with no frontend code change)
- Server-side view downsampling utility (display transform; lives in `api/`, not `src/`)
- Background-task backtest execution + `/status` polling endpoint
- Error envelope (`{error: {code, message, detail, field_errors}}`) with the HTTP semantics defined in §9.3
- `make dev` target: API + (later) Vite dev server
- OpenAPI schema emitted at `/openapi.json`

**Testing requirements (`api/tests/`):**
- Every router: happy path returns the documented shape; unknown asset/run → 404 envelope
- Handlers contain no computation: contract test asserting each handler calls exactly the intended `src/` function (spy-based)
- Columnar serialization round-trips a fixture DataFrame losslessly (index ms epochs, NaN → null)
- Backtest lifecycle: POST → run_id, status transitions queued→running→complete, artifacts readable via the runs endpoints; failure path captures exception into run status
- Downsampler preserves OHLC bucket extremes on a known fixture

**Gate:** `curl` walk of the full research loop (ohlcv → compute → generate → evaluate → backtest → run detail) succeeds against the Gold fixture. OpenAPI validates.

---

### Module F1: Frontend Scaffold, Tokens, and Contracts

**Purpose:** Repository skeleton, design tokens, generated types — the frontend's Module 1.

**Dependencies:** F0 complete (OpenAPI available).

**Deliverables:**
- `frontend/` scaffold per `FRONTEND_ARCHITECTURE.md` §16: Vite + React 18 + TypeScript strict; ESLint + Prettier (+ Tailwind class sorting); Vitest + Testing Library; Playwright configured
- `styles/tokens.css` — complete token set from `DESIGN_SYSTEM.md` §2 (dark + light), density variables; Tailwind config consuming tokens; Inter + JetBrains Mono loaded, `tabular-nums` defaults on data classes
- `make types` → `src/api/schema.d.ts` via openapi-typescript; CI fails on uncommitted diff (TDR-010)
- `src/api/client.ts` (typed fetch + error-envelope parsing), `queryKeys.ts` factory, Query client with the §10 cache defaults
- `lib/fmt.ts`, `lib/tone.ts`, `lib/useUrlState.ts` (Zod-typed search params)
- Route table with lazy module chunks; placeholder screens rendering titles

**Testing requirements:**
- `fmt` unit tests: asset-aware price decimals from tick size, signed percents with true minus, compact USD
- `tone` band tests: IC thresholds at boundaries (0.02, 0.05), pnl sign mapping
- `useUrlState`: parse/serialize round-trip, invalid-param fallback to defaults
- `client`: error envelope → typed `ApiError`; 404/400/500 discrimination

**Gate:** app boots, routes render placeholders, `make types` clean, all lib tests pass, token file is the only place hex values exist (lint rule active).

---

### Module F2: Design System Primitives and Shell

**Purpose:** F1-layer primitives (shadcn vendored + token-restyled) and the app shell.

**Dependencies:** F1 complete.

**Implementation order:** primitives (`Button`, `Input`, `NumberInput`, `Select`, `Combobox`, `Tabs`, `Dialog`, `Drawer`, `Tooltip`, `Toast`, `Badge`, `Panel`, `Skeleton`, `Command`) → shell (`AppShell`, `SidebarNav` with phase-gated items, `TopBar` with health dot, `ContextBar`, `CommandPalette` skeleton with Navigate provider, `ComparisonTray` stub) → state components (`EmptyState`, `ErrorState`, `LoadingSkeleton` variants, `NotFound`, `ApiUnreachable`) → workspace Zustand store (theme, density, nav collapse, context) with persistence.

**Testing requirements:**
- Interaction tests: Tabs URL-sync variant writes `?tab=`; Dialog/Drawer focus trap + Esc + focus return; palette opens on ⌘K and navigates
- Token compliance: visual smoke via Playwright screenshot of a primitives gallery route (dark + light + both densities)
- Workspace store: persistence round-trip; URL-overrides-context rule
- Axe accessibility pass on the gallery route (AA)

**Gate:** shell navigable by keyboard alone; gallery route renders every primitive in all states; a11y scan clean.

---

### Module F3: Chart and Grid Engines

**Purpose:** The two heaviest shared components: `ChartFrame` + ECharts theme, and `DataGrid`.

**Dependencies:** F2 complete.

**Deliverables:**
- `useChartTheme()` mapping tokens → ECharts theme; `ChartFrame` (skeleton/empty/error, toolbar: zoom reset, PNG export, fullscreen; `syncGroup` crosshair connection); tree-shaken ECharts registration per chart type
- First chart set: `PriceChart` (candle/line, volume pane, overlays, markers), `EquityCurveChart` (drawdown under-pane, baseline, compare mode), `Sparkline`
- `DataGrid<T>` on TanStack Table + Virtual per `DESIGN_SYSTEM.md` §4: controlled sort (URL-syncable), toolbar search/filters, column visibility, sticky header, selection, CSV export of filtered view, server-page mode
- `MetricStat`, `MetricGrid`, `RunStatusBadge`, `ICBandBadge`

**Testing requirements:**
- ChartFrame: renders each of the four states; export produces a PNG blob; sync group connects two instances (event-level test)
- PriceChart fixture render: correct candle tones, gap (null) produces a break not interpolation
- DataGrid: sort/filter/visibility behavior; virtualization active >200 rows (row-count assertion); selection controlled; CSV matches filtered view; keyboard j/k/Enter
- MetricStat: formatting + tone delegation (drawdown always loss-toned)

**Gate:** demo route renders a 3k-bar candle chart <150ms (perf assertion in Playwright trace) and a 10k-row virtualized grid with smooth sort. Bundle check: ECharts confined to chart chunks.

---

### Module F4: Market Module (first vertical slice)

**Purpose:** Screens S1 (Market Overview) and S2 (Asset Detail) end-to-end against the live API.

**Dependencies:** F3 complete.

**Deliverables:** query hooks (`useAssets`, `useAssetSummary`, `useOhlcv` with downsample/window logic, `useDataStatus`); `UniverseGrid`; `ReturnHistogram`; `ValidationRibbon`; `AssetSelector`, `DateRangePicker`; both screens with all specified states; hover prefetch; context-carrying "Open in Workbench" link (target lands in F5).

**Testing requirements:** hook tests with MSW-mocked API (cache config: summary staleTime, ingest invalidation); screen tests for the four states of each screen incl. first-run empty → Data Manager pointer; histogram-brush → chart highlight interaction; Playwright: load overview → click gold → zoom chart → verify full-res refetch.

**Gate:** the S1→S2 journey works against real ingested Gold data; first-run empty state verified on a clean `data/` directory.

---

### Module F5: Research Workbench

**Purpose:** Screen S3 — the platform's core — including the IC Gate.

**Dependencies:** F4 complete.

**Deliverables:** indicator catalog + strategy schema hooks; `IndicatorPicker`, `StrategyPicker`, `ParamForm` (schema-driven renderer + generated Zod validation — TDR-008); chained evaluate mutation (compute → generate → evaluate) with staged progress and param-hash cache keys; `SignalOverlayChart`, `ICRollingChart`, `ICDecayChart`, `TurnoverChart`, `FeatureSpecTable`; `ICGateStrip` with locked/banded/override states; stale-canvas dimming; full URL serialization of workbench state.

**Testing requirements:**
- ParamForm: renders every field kind from a schema fixture; min/max validation; reset-to-default; error mapping from API `field_errors`
- Gate logic: null → locked; band selection at threshold boundaries; override emits the flagged launch intent
- Evaluation chain: stage-failure surfaces the failing stage; identical params hit cache (no network — MSW call-count assertion)
- Missing-dependency rule: signal requiring absent feature disables Evaluate with the actionable message
- URL round-trip restores an identical workbench configuration

**Gate:** EMA-crossover-on-Gold evaluation reproduces the backend's IC numbers on screen; gate opens; "Configure backtest" carries full context. Doctrine states (locked, override-recorded) demoed.

---

### Module F6: Backtest Launch and Run Detail

**Purpose:** Screens S4 (Strategy Builder) and S6 (Run Detail, all five tabs) — closing the research loop.

**Dependencies:** F5 complete.

**Deliverables:** Strategy Builder with sticky preview, `?fromRun=` cloning + field-diff chips, unsaved guard, launch mutation (invalidate runs list, prefetch new run, redirect); Run Detail header + tabs; `TradeTable` (server-paginated) + trade drawer; `RollingMetricChart`; Performance tab metric wall; Signal-quality tab incl. the skipped-evaluation warn state; Artifacts tab (params tree, FeatureSpecs, artifact list + downloads, git hash); running-state live panel; failed-run rendering.

**Testing requirements:** launch lifecycle (pending → redirect → running poll → tabs hydrate — MSW-scripted status sequence); clone diff chips; insufficient-warmup blocking validation with exact bar math; TradeTable pagination + force-closed flag; immutable-run caching (revisit produces zero refetches); failed-run body renders exception + re-run path; 404 run.

**Gate:** full loop on live stack: Workbench → gate → Builder → launch → watch run complete → inspect all five tabs. Run artifacts on disk match every number shown (spot-check protocol documented in the module summary).

---

### Module F7: Run Explorer and Comparison

**Purpose:** Screens S5 and S7 — experiment memory and judgment.

**Dependencies:** F6 complete.

**Deliverables:** `RunTable` with URL-synced filters/sort/search and grouping toggle; comparison basket store + `ComparisonTray` + `c` shortcut; delete mutation with confirm; `/runs/compare`: compare hook, overlaid normalized equity, `MetricDeltaTable` with baseline swap, rolling overlays, parameter-diff panel; palette Run provider + context actions ("Compare with…", "Re-run with changes").

**Testing requirements:** filter/sort URL round-trips; basket persistence + `?ids=` seeding; baseline swap re-anchors deltas; intersection-window logic for non-overlapping runs (notice rendered); invalid id → error chip, comparison proceeds; mixed-asset normalized-only mode with the ADR-005 caveat note; delete invalidates list and evicts run cache.

**Gate:** three real parameter-sweep runs compared; best-per-row highlighting and param diff verified against `params.json` files.

---

### Module F8: System Module and Hardening

**Purpose:** Screens S8/S9, keyboard model, and release-quality hardening. Completes Phase F1.

**Dependencies:** F7 complete.

**Deliverables:** Data Manager (status table, staged ingest progress, validation log with Asset Detail cross-links); Configuration screen; full keyboard chord set + `?` shortcut sheet; light theme QA; laptop-tier (1160–1440) and ultrawide adaptations; error-boundary sweep (route + panel level); performance-budget CI (bundle size, chart render trace); Playwright end-to-end suite covering journeys J1–J4 from `FRONTEND_ARCHITECTURE.md` §4.3; axe pass on every screen.

**Testing requirements:** as embedded above, plus: API-unreachable full-screen state (kill API mid-session in Playwright); ingest completion invalidates market caches; reduced-motion snapshot.

**Gate — Phase F1 done:** all four reference journeys pass headless; budgets green; a11y clean; a new machine reaches first backtest from `make dev` + empty `data/` guided entirely by empty states.

---

## Phase F2 — Commodity Intelligence UI (Delivered — F9–F11)

Backend Phase 2 API surface (`/api/curve`, `/api/term-structure`) was available. All three modules shipped.

1. **Module F9: Term-Structure Components** — `FuturesCurveChart`, `RegimeBadge`, regime timeline strip, basis/roll-yield charts. ✓
2. **Module F10: Commodity Intelligence Screen (S10)** — route + hooks, FuturesCurve grid-cols-2 config → "View Curve" → full-width results. RegimeBadge added to Asset Detail header. ADR-001 boundary respected — no contract data enters Strategy Builder. ✓
3. **Module F11: Curve Comparison + PCA** — `/intelligence/compare` and `/intelligence/pca` screens delivered. Gold PC1≈100% confirmed correct behavior (near-constant term structure). ✓

---

## Phase F3 — Portfolio UI (Delivered — F12–F15 + FEP + EM14)

Backend Phase 3 was complete when frontend implementation began. All API contracts were concrete.

**Real data numbers (EMA 50/200, all 6 assets):**
- Portfolio return: +1.25% over 4,116 trading days
- Portfolio Sharpe: 0.0018 (near breakeven — EMA 50/200 trend strategy in this universe)
- Max drawdown: −7.37%, Portfolio vol: 2.54%/yr
- VaR99: $44,490 (0.74% of $6M capital), ES99: $99,095
- Diversification benefit: 2.23× (sum of asset VaR99 / portfolio VaR99)
- Gold-Silver corr: 0.65, WTI-Brent corr: 0.62 (strategy returns, not price returns)

1. **Module F12: Portfolio Composition (S11)** — date range picker (1Y/3Y/5Y/MAX), strategy selector, launch `POST /api/portfolio/run`, poll status, portfolio equity curve, per-asset P&L from `absolute_pnl_by_asset`. ✓

2. **Module F13: Risk Panel** — `GET /api/portfolio/{id}/risk` → VaR/ES panels, ContributionToRiskChart, Kupiec backtesting validation row. ✓

3. **Module F14: Correlation Panel** — `GET /api/portfolio/{id}/correlation` → CorrelationHeatmap, rolling correlation chart for top 5 pairs, strategy vol table labeled "Strategy Realized Vol (%/yr)". ✓

4. **Module F15: Scale Pass + Regime Attribution** — Portfolio Combined regime attribution via async job pattern (`POST /api/regime-attribution/compute-portfolio`), per-asset regime via `POST /api/regime-attribution/compute`. ✓

---

## Development Checklist Before Starting Each Module

- [ ] Re-read the relevant sections of `FRONTEND_ARCHITECTURE.md` and `DESIGN_SYSTEM.md`
- [ ] Re-read the TDRs that apply to this module
- [ ] Confirm the API contract for this module's endpoints; regenerate types (`make types`)
- [ ] Confirm each new piece of state's home against the §8 state table
- [ ] Write component/hook tests alongside the first working implementation
- [ ] Update `FRONTEND_ARCHITECTURE.md` / `DESIGN_SYSTEM.md` on any deviation; log implementation notes in `docs/implementation_notes/`
- [ ] Module summary on completion: files created/modified, tests created, open questions, technical debt, deviations (matches the backend development process)

---

## Dependency Graph Summary

```
Backend Modules 1–19 (Phase 1 + Phase 2 + Phase 3 complete — phase-3-complete tag)
    └── F0  API shell
          └── F1  scaffold · tokens · contracts
                └── F2  primitives · app shell
                      └── F3  chart + grid engines
                            └── F4  Market (S1, S2)          ← first visible slice
                                  └── F5  Workbench (S3)     ← core research slice
                                        └── F6  Builder + Run Detail (S4, S6)
                                              └── F7  Explorer + Comparison (S5, S7)
                                                    └── F8  System + hardening (S8, S9)
                                                          │
                                                          ▼
                                              Phase F2 (F9–F11)  → Phase F3 (F12–F15)
```

No module starts until its dependency's gate has passed.

---

## Post-F-Track Modules (F16–F18)

These modules are not planned deliverables — they are the UI polish, bug fix, and verification passes that ran after the F-track (F0–F15) completed.

### Module F16 — UI Polish and Bug Fix Pass

**Status:** Complete. 337 vitest + 33 Playwright. 36 issues resolved.

Key fixes: ECharts CSS var resolution (all colors via resolveCssVar), TitleComponent registration, date formatters on all chart x-axes (fmtDate), DataGrid column field names corrected (strategy/entry_date/net_pnl/duration_bars), routing fix (/runs/compare before :runId), dark dropdowns platform-wide, trade direction filters server-side, comparison tray wired, signal evaluation URL threading, portfolio graceful degradation.

**Backend actions in F16:** trades direction fix, GET /api/portfolio/runs added, signal_evaluation persistence fixed (4e178a8), poll\_ routing fixed for all 5 portfolio handlers (f4c8001, expanded to all handlers at F16).

### Module F17 + F17-Hotfix — Post-Verification Fix Pass

**Status:** Complete. 347 vitest + 33 Playwright. 25 issues + 20 additional items resolved.

Key fixes: signal chart x-axis dates, DataZoom spacing, equity+drawdown dual tooltip, run header redesign (single-line ASSET · strategy · dates + clipboard), IC gate PATH A/B URL separation, trade KPI filter stats update on filter change, clean run URLs (poll\_ stripped), history chart period selector (nullish fallback fix), dual-series history chart hover (trigger:'axis'), regime legend colors matched to markArea fill colors, signal DataZoom restored (all 3 pane xAxisIndex), equity crosshair dates.

### Module F18 — Final Platform Polish

**Status:** Complete. 354 vitest + 33 Playwright. 40+ commits → rebased to semantic history.

Key fixes:
- **Table infrastructure (ARCHITECTURAL DECISION):** Replace ALL DataGrid instances with plain HTML `<table>` EXCEPT Run Explorer. Root cause: display:block tbody in virtualized DataGrid cannot inherit width. Pattern: w-full table-fixed border-collapse + overflow-hidden rounded border wrapper. Files: UniverseGrid, ContractInventoryPanel, AssetRunsPanel, TradeTable, FeatureSpecTable, MetricDeltaTable.
- **SignalOverlayChart (most iterated file):** Position pane REMOVED after 8 attempts to close inter-grid gaps failed (ECharts hard constraint). Replaced with markArea background bands on signal pane ONLY (institutional standard). Long=rgba(--bg-gain-fill, 8%), Short=rgba(--bg-loss-fill, 8%).
- **Navigation fix:** AssetDetail.tsx cleanup function REMOVED (was deleting ?asset= from URL on unmount — root cause of "Open in Workbench" never working across all prior modules).
- **Page layout uniformity:** All workflow pages: grid-cols-2 (left config, right action button).
- **Chart fixes:** hover card colored dots (params.marker), equity+drawdown dual tooltip, axisPointer date formatters, volume series named "Volume", IC decay thresholds staggered.
- **IC gate strip:** moved to inline chip beside IC value (not separate banner row).
- **TopBar:** search bar removed (⌘K palette retained).
- **"Reload data":** Re-ingest button renamed with tooltip; LAST RELOAD persists in localStorage.
- **Portfolio run selector:** strategy_name + colored total_return %.
- **FuturesCurve:** half-half config → "View Curve" → full-width results flow.


---

## Frontend Enhancement Pass (FEP)

**Status:** Complete. 391 vitest + 37 Playwright + 424 backend tests. FEP-complete tag at 698c770. Post-FEP a11y + DataGrid fixes committed at 35733d5.

**Purpose:** Consolidated frontend delivery for backend enhancement modules EM1–EM13. All frontend work intentionally deferred to a single pass with full platform context. 8 increments, ~50 commits (excluding post-merge fixes).

### New Screens Delivered

| Screen | Route | Module |
|---|---|---|
| Sweep Explorer | `/sweeps` | EM9 |
| Curve PCA | `/intelligence/pca` | EM11 |

### Existing Screens Extended

| Screen | Addition | Module |
|---|---|---|
| Portfolio Risk | ContributionToRiskChart + Kupiec calibration row | EM4 |
| Run Detail | Validation tab (5th tab) | EM5 |
| Research Workbench | ICRollingChart wired (was placeholder F5–FEP), full-width post-evaluate layout, blur overlay removed | EM6 |
| Run Signal Quality Tab | ICRollingChart wired | EM6 |
| Portfolio Analytics | Regime Attribution section (opt-in, bottom of screen) | EM8 |
| Strategy Builder | 4 new strategy param panels + wti_brent_spread hard disable | EM7/EM12/EM13 |
| Data Manager | Complete rebuild — QC Report, COT Positioning, EIA Inventory sections | EM10/EM13 |
| SidebarNav | Sweep Explorer (SlidersHorizontal icon), Curve PCA (Network icon) | — |

### New Components (19)

**Charts (9):** `ContributionToRiskChart`, `WalkForwardChart`, `RegimeBreakdownChart`, `ParallelCoordinatesChart`, `ScreePlot`, `PCLoadingsChart`, `PCTimeSeriesChart`, `COTPositioningChart`, `EIAInventoryChart`

**Tables (2):** `ValidationSummaryTable`, `SweepResultsTable`

**Features (8):** `SweepParamGridBuilder`, `DataQCPanel`, `COTDataPanel`, `EIADataPanel`, `PortfolioRegimePanel`, `RunValidationTab`, `SweepExplorer` (screen), `CurvePCA` (screen)

### New Hooks (13)

`useValidationLaunch`, `useValidationStatus`, `useValidationReport`, `useRollingIC`, `useRegimeAttribution`, `useRegimeAttributionParallel` (preserved — not called), `useSweepLaunch`, `useSweepStatus`, `useSweepResults`, `useSweeps`, `useDataQC`, `useCurvePCA`, `useCOTData`, `useEIAData`

### Key Architecture Decisions (FEP)

- **AD-FEP-001:** Regime panel is opt-in (button). Single-worker Uvicorn saturates under 30–90s synchronous regime computation. Bloomberg standard for expensive analytics.
- **AD-FEP-006:** All Radix TooltipContent uses dark platform style applied once in `src/ui/tooltip.tsx`.
- **AD-FEP-008:** `fetchWithRaceRetry` (4 attempts: 1s/3s/6s/10s) on all 5 portfolio result hooks — handles persistence race condition between status=complete and artifact writes.
- **Regime color correction:** DESIGN_SYSTEM.md §2.2 stale entry (contango=red) corrected. Confirmed: Contango=amber/warn, Backwardation=green/gain.
- **Research Workbench layout:** Full-width post-evaluate (not grid-cols-2). "← Modify signal" returns to config. Blur/relaunch overlay removed.
- **Validation tab:** No run_id in ValidationLaunchRequest — launched with (asset, strategy_name, parameters, n_splits, embargo_bars) pre-populated from run metadata.

### Technical Debt Register (FEP + open)

| ID | Description | Owner | Status |
|---|---|---|---|
| TD-FEP-REGIME-ASYNC | POST /api/regime-attribution/compute → async job | Backend (~1 day) | `useRegimeAttributionParallel.ts` preserved, one import swap |
| TD-FEP-PORTFOLIO-RACE | Add `persisting` intermediate status to portfolio background task | Backend (~2h) | fetchWithRaceRetry workaround ships |
| TD-FEP-SWEEP-PROGRESS | Real-time n_complete during sweep execution | Backend (~30min) | Frontend handles live values, zero changes needed |
| TD-FEP-PORTFOLIO-DATERANGE | Add from_date/to_date to POST /api/portfolio/run | Backend + Frontend (~2h each) | Not started |
| TD-FEP-PORTFOLIO-RUNSELECTOR | Expand run history selector fields | Frontend (~1h after backend) | Not started |
| TD-CI-MYPY | Backend mypy in CI pipeline | Backend | No frontend dependency |
| TD-fmt-thousands | fmt.price no thousands separator ($4078.70 not $4,078.70) | Frontend | Not started |
| E6 | /equity /risk /correlation in-memory only | Backend | Graceful degradation shown |

### Post-FEP Fixes (35733d5)

Committed directly to main after merge:
- `tests/test_engine_properties.py`: Added missing `from hypothesis import given, settings, assume` + `strategies as st`
- `UniverseGrid.tsx`: Added `role="img"` to health-dot `<span aria-label>` (a11y: aria-label prohibited on span without role)
- `PortfolioConfigPanel.tsx`: Added `aria-label="Select portfolio strategy"` to Combobox trigger
- `PortfolioRegimePanel.tsx`: Added `aria-label="Select asset for regime attribution"` to plain `<select>`
- `DataGrid.tsx`: Restored `h-full` on outer wrapper (`flex h-full min-h-0 w-full flex-col`) — virtualization broken by FEP when `h-full` was removed
- `tests/e2e/intelligence.spec.ts`: Added "View Curve" click before regime badge assertion (F18 restructured FuturesCurve to require it)
- `tests/e2e/a11y.spec.ts`: Run Detail and Run Explorer a11y tests skip gracefully when API server not running (Option A pattern)

**Final baselines after all post-FEP fixes:**
- Frontend vitest: **391 passed**
- Playwright (with API): **35 passed, 2 skipped** (Run Detail/Explorer a11y — need populated run data)
- Playwright (without API): **30 passed, 7 skipped**
- Backend pytest: **424 passed**

---

## Post-FEP Fixes and EM14 Clearances

**Status:** Complete. 406 vitest + 114 E2E. All TD items closed.

### EM14 — Workaround Clearances (4df6d1, d13fad7, c67e4aa, 660216e)

| TD | Workaround Removed | How |
|---|---|---|
| TD-FEP-PORTFOLIO-RACE | `fetchWithRaceRetry` removed from all 5 portfolio result hooks; `retry.ts` deleted | Backend added `persisting` intermediate status |
| TD-FEP-REGIME-ASYNC | Opt-in button remains; `useRegimeAttributionParallel.ts` deleted; `useRegimeAttributionAsync.ts` fully wired | Backend shipped `POST /api/regime-attribution/compute` async job pattern |
| TD-FEP-SWEEP-PROGRESS | Static "N combinations" display replaced with live counter | Backend increments `n_complete` per combination |
| TD-FEP-PORTFOLIO-RUNSELECTOR | Run selector expanded to 5 columns (added Sharpe) | Frontend only |

### TD-EM8-C — Portfolio Combined Regime Attribution (660216e + verification)

`PortfolioRegimePanel` now has "Portfolio Combined" as the first option in the asset dropdown (value: `__portfolio__`). Uses `usePortfolioRegimeCompute()` → `useRegimeAttributionJobStatus()` (reused) → `usePortfolioRegimeResult()`. Job ID cached in `jobIdByAsset.current['__portfolio__']`. Switch-back restores instantly from cache. `RegimeBreakdownChart` receives identical data shape — no chart changes. `useRegimeAttributionParallel.ts` deleted.

### Bug Fixes (post-FEP)

| Bug | Fix | Commit |
|---|---|---|
| Silent evaluation failure — 6 strategies | Skip features compute when `featureSpecs.length === 0`; add `onError` handler; inline alert in WorkbenchConfigRail | dabac29 |
| Same-route navigation crash (sidebar → /research while on /research) | Null guard on SignalOverlayChart + PriceChart before `setOption`; RouteErrorBoundary on all 16 routes | 0d06bfd |
| fmt.price no thousands separator | `Intl.NumberFormat('en-US')` — signature unchanged | 2aef1bc |
| SweepParamGridBuilder param fills wiped on re-render | useEffect depends on `paramNamesKey` (joined string) not `paramNames` array | 8166470 |

### TD-FEP-PORTFOLIO-DATERANGE (4e4f553, e7f64a7, 4dcc77a)

Date range inputs added to Portfolio Configuration panel. 1Y/3Y/5Y/MAX period buttons + from/to date inputs matching Research Workbench pattern exactly. Default: 2015-01-01 → today. MAX: 2010-01-01 → today. Conditional spread in launch request. 405 vitest.

### Run Explorer Pagination + Sort (5e00dbb, backend 848ff6d, backend ORDER BY)

Backend: SQLite run index (`data/runs/index.db`). 30s → 0.45s. Response shape: `{ runs, total, page, page_size }`. Frontend: `useRuns` already expected paginated response. Added `keepPreviousData`. Existing Prev/Next UI confirmed working. "Showing 1–50 of N runs" display. Sort params now wired server-side via ORDER BY.

### E2E Suite Complete (114/3/0)

117 total tests across 13 groups covering all 13 screens, 8 strategies, IC Gate flow, all 5 async job types, cross-screen Zustand state, error states, accessibility.

**3 permanent skips (all by design):**
- Run Detail a11y — requires live run ID, API-dependent
- Run Explorer a11y — same
- Sweep row → Run Detail — sweeps produce no `/runs/{id}` artifacts (S-FEP-1)

**Key E2E architectural confirmations:**
- IC state: TanStack Query cache, not Zustand. Dies on `page.goto()`. "No evaluation found" after reload is correct behavior.
- ICGateStrip enabled only when `band !== 'noise' && band !== null`. All live strategies return noise-band on short windows — correct, not regression.
- StrategyPicker renders as buttons, not combobox. URL param navigation is canonical test pattern.
- Param form renders asynchronously after `GET /api/strategies` — requires `toBeVisible({ timeout: 10_000 })` gate.
- Tab state (`?tab=`) resets on navigation — by design per TDR-014.

### Final Technical Debt Register — All Items Closed

| ID | Status |
|---|---|
| TD-FEP-PORTFOLIO-RACE | ✓ Closed EM14 |
| TD-FEP-REGIME-ASYNC | ✓ Closed EM14 |
| TD-FEP-SWEEP-PROGRESS | ✓ Closed EM14 |
| TD-FEP-PORTFOLIO-RUNSELECTOR | ✓ Closed EM14 |
| TD-FEP-PORTFOLIO-DATERANGE | ✓ Closed |
| TD-RUN-EXPLORER-PERF | ✓ Closed |
| TD-RUN-SORT | ✓ Closed |
| TD-F18-A | ✓ Closed (will not implement — TDR-013) |
| TD-fmt-thousands | ✓ Closed |
| TD-CI-MYPY | ✓ Closed EM14 (mypy enforced on CI, 0 errors on 67 source files) |
| E6 | ✓ Closed EM3 (all 7 portfolio artifacts persist to disk) |

**Zero open items. Platform is complete.**
