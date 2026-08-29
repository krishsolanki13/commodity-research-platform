# Frontend Technology Decision Records
## Commodity Systematic Research Platform

**Format:** Mirrors `docs/adr/ADRs.md`. Each TDR documents one frontend technology or architecture decision with context, alternatives, trade-offs, and migration path.
**Status values:** Proposed | Accepted | Superseded | Deprecated

---

## TDR-001 — React + Vite + TypeScript SPA

**Status:** Accepted
**Supersedes:** Backend ADR-008 (Streamlit) as the presentation technology. ADR-008's architectural rule — presentation layer performs no computation — is retained and restated in `FRONTEND_ARCHITECTURE.md` §2.

### Context

The platform's dashboard was originally specified as Streamlit (ADR-008), which was the right Phase-1 call for a single-developer Python-only stack. The project's goals have expanded: the frontend is itself a portfolio artifact and must demonstrate the interaction quality, information density, and architectural discipline of an institutional research workstation. Streamlit's rerun-the-script execution model, limited layout control, and coarse interactivity cap all three.

### Decision

Build a client-side single-page application: **React 18, Vite, TypeScript (strict mode)**.

- **React** — the dominant framework for institutional internal tools; the ecosystem the rest of the stack (TanStack, Radix/shadcn, ECharts wrappers) targets first; component model maps cleanly onto the F1–F4 layer architecture; maximal hiring-signal value for trading-technology roles.
- **Vite** — sub-second dev server and HMR keep the Cursor implementation loop tight; trivial config; first-class TypeScript and code-splitting; no framework lock-in.
- **TypeScript strict** — the frontend consumes generated contracts mirroring `src/core/types.py` (TDR-010); strict typing makes contract drift a compile error, the same guarantee layer contracts give the backend.

### Alternatives Considered

**Option A: Keep Streamlit.** Rejected. Cannot deliver keyboard-driven workflows, URL-addressable state, panel-level loading, virtualized grids, or a real design system. Its rerun model fights the caching strategy rather than enabling it. Streamlit remains legitimate for `notebooks/`-adjacent throwaway exploration.

**Option B: Dash (Plotly).** Rejected. Better than Streamlit for layout, but callbacks-over-HTTP interactivity is sluggish for dense workstations, and the component ecosystem is far thinner. Also keeps the UI in Python, forfeiting the portfolio value of a typed frontend.

**Option C: Next.js.** Rejected — see TDR-006. SSR/RSC solve public-web problems (SEO, first-paint on slow networks) this internal localhost tool does not have, at the cost of server complexity and a second runtime concern.

**Option D: Svelte/SvelteKit or SolidJS.** Rejected. Technically excellent, but ecosystem depth (grid, charts, headless UI) and industry-alignment for quant-dev roles favor React. The performance edge of fine-grained reactivity is not the bottleneck here; chart rendering is.

### Consequences

Positive: full control of density/layout/keyboard UX; typed end-to-end contracts; industry-standard stack for the target audience. Negative: introduces a Node toolchain and a second language to a previously Python-only repo; requires an HTTP API (TDR-002); higher upfront cost than Streamlit (accepted — the frontend is a first-class deliverable, not an afterthought).

### Future Migration Path

None anticipated at the framework level. If the platform ever becomes multi-user/public, add auth at the API and consider SSR then — the F0–F4 layering keeps that a deployment change, not a rewrite.

---

## TDR-002 — FastAPI Serialization Shell as the HTTP Boundary

**Status:** Accepted

### Context

`src/` is a Python library with no network surface; Streamlit consumed it in-process. A browser frontend requires HTTP. The risk is that an API layer becomes a second home for business logic, violating the platform's single-source-of-computation rule.

### Decision

A thin **FastAPI** service (`api/`) whose route handlers do exactly three things: parse/validate the request, call one `src/` function, serialize the result. **No computation in route handlers** — the API-layer restatement of the "no computation in dashboard code" rule.

- Pydantic response models are constructed 1:1 from the dataclasses in `src/core/types.py`.
- Time series serialize columnar (`{index: [], columns: {}}`), with API-side downsampling for chart payloads (a display transform, hence permitted here).
- `POST /api/backtests` is async: returns `run_id` immediately; a background task (FastAPI `BackgroundTasks` in Phase 1) executes the pipeline; the client polls `/status`.

### Alternatives Considered

**Option A: Flask.** Rejected. No native Pydantic integration or automatic OpenAPI, which TDR-010 depends on.

**Option B: Django REST Framework.** Rejected. ORM-centric heavyweight for a filesystem/Parquet-backed read API.

**Option C: WebSockets/SSE for run status from day one.** Deferred. Vectorized backtests complete in seconds; 1s polling is indistinguishable UX at Phase 1 scale. SSE is the documented upgrade when Phase 3 multi-asset runs lengthen execution.

**Option D: GraphQL.** Rejected. The read patterns are fixed and screen-shaped; REST endpoints map 1:1 to layer outputs. GraphQL's flexibility buys nothing and costs schema/tooling overhead.

### Consequences

Positive: `src/` remains the only computation home; FastAPI's OpenAPI output powers type generation; async pattern established before Phase 3 needs it. Negative: one more process to run locally (mitigated: a single `make dev` starts API + Vite); background tasks are in-process (a crashed API loses a queued run — acceptable for a local research tool; a task queue is the Phase 3+ path if ever needed).

### Future Migration Path

Phase 3: SSE for run progress; optional job persistence. Multi-user later: auth middleware at this layer only.

---

## TDR-003 — Tailwind CSS + shadcn/ui on a Design-Token Foundation

**Status:** Accepted

### Context

The workstation needs a disciplined, dense, themeable (dark-first) visual system, buildable by one developer with AI assistance, without accumulating a bespoke CSS architecture.

### Decision

- **Design tokens as CSS custom properties** (`styles/tokens.css`) are the source of truth for color, spacing, type, radius, elevation (full spec in `DESIGN_SYSTEM.md`). Tailwind is configured to consume tokens; raw hex/px values in components are prohibited.
- **Tailwind CSS** for all layout/utility styling — colocated, greppable, no specificity wars, and the idiom Cursor/Claude generate most reliably.
- **shadcn/ui** (Radix primitives, vendored source) for interaction-heavy primitives: dialog, dropdown, tabs, popover, command palette, toast, tooltip. Vendored code means components are restyled to the token system rather than fought — critical because default shadcn aesthetics read consumer-SaaS, not terminal.

### Alternatives Considered

**Option A: Component library (MUI/Ant/Mantine).** Rejected. Fast start, but institutional density and terminal aesthetics require overriding these libraries everywhere; the override layer becomes the real (unowned) design system. Ant's data-grid strength is replaced by TanStack Table (TDR-007).

**Option B: CSS Modules / vanilla-extract, no utility framework.** Rejected. More ceremony per component for one developer; no accessibility-hardened primitives included.

**Option C: Bloomberg-style fully bespoke CSS.** Rejected. Radix's keyboard/focus/ARIA behavior is months of work to replicate correctly; accessibility is a stated quality floor.

### Consequences

Positive: theme = token file; dark/light and density modes are variable swaps; primitives accessible by default. Negative: shadcn components are owned code to maintain (accepted — that ownership is exactly what allows the terminal restyling); Tailwind class strings need lint discipline (`prettier-plugin-tailwindcss` enforced).

### Future Migration Path

Tokens are framework-agnostic; if the styling approach ever changes, tokens survive.

---

## TDR-004 — Apache ECharts as the Single Charting Engine

**Status:** Accepted

### Context

The platform's chart inventory spans candlesticks with overlays, equity/drawdown curves, rolling metrics, IC bars and decay curves, histograms, scatter, correlation heatmaps (P3), and futures curves (P2) — dense, interactive, synchronized-crosshair financial charts over up to ~15 years of daily bars. Splitting this across multiple libraries fragments theming, tooltips, and interaction behavior.

### Decision

**Apache ECharts** for every chart, wrapped once (`<ChartFrame>` + `useChartTheme()`), with tree-shaken per-chart imports. Canvas renderer for series-heavy charts, SVG where crispness matters at small size (sparklines).

Rationale: it is the only single library that natively covers the full inventory (candlestick, heatmap, custom series) with institutional-grade interaction (dataZoom, connected crosshairs via `group`/`connect`, brush selection) and canvas performance on 10k+ points; theming is a JSON object that maps directly from design tokens.

### Alternatives Considered

**Option A: TradingView Lightweight Charts for price + ECharts for the rest.** Seriously evaluated — LW Charts' candlestick pan/zoom feel is best-in-class. Rejected for Phase 1: two theming systems, two tooltip behaviors, and no synchronized crosshair across libraries. Documented as a Phase 2+ candidate if price-chart interaction becomes the bottleneck; `<PriceChart>`'s props contract is engine-agnostic to keep that swap contained.

**Option B: D3 directly.** Rejected as primary. Unmatched control, weeks-per-chart cost. Retained as the escape hatch for any genuinely custom visualization (e.g., a bespoke term-structure ribbon) via ECharts custom series or a scoped D3 component.

**Option C: Recharts/Visx/Nivo.** Rejected. SVG-first performance ceilings on long daily series; no serious candlestick/heatmap support (Recharts, Nivo); Visx is a D3 toolkit with D3's cost.

**Option D: Plotly.js.** Rejected. Bundle weight, dated default aesthetics requiring heavy override, weaker fine-grained interaction control.

### Consequences

Positive: one theme, one tooltip/crosshair behavior, one wrapper to test; covers Phases 1–3 without new dependencies. Negative: ECharts option objects are verbose (mitigated by per-chart-type option builders in `components/charts/`); bundle weight demands disciplined tree-shaken imports (enforced in CI budget).

---

## TDR-005 — State Partitioning: TanStack Query + URL State + Zustand

**Status:** Accepted

### Context

Research UIs die by state entanglement: server data copied into global stores goes stale; filter state trapped in components makes screens unshareable. The backend's immutability guarantees (run artifacts never change; processed data changes only on re-ingest) permit an unusually aggressive and simple model.

### Decision

Four state classes, four homes (detail in `FRONTEND_ARCHITECTURE.md` §8):

1. **TanStack Query** owns all server state and is the only cache. Immutable artifacts get `staleTime: Infinity`. Deterministic computations (features/evaluations) are cached by canonical param-hash keys.
2. **URL search params** own anything that defines "what am I looking at" — typed via a Zod-validated `useUrlState` hook.
3. **Zustand** owns cross-screen workspace state only: research context defaults, comparison basket, theme/density, nav collapse. Persisted to localStorage.
4. **Component state / React Hook Form** own ephemeral interaction.

Hard rule: server-derived data is never copied into Zustand.

### Alternatives Considered

**Option A: Redux Toolkit (+ RTK Query).** Rejected. Global-store discipline and boilerplate solve coordination problems this app doesn't have; RTK Query is capable but TanStack Query's staleness/prefetch/keepPreviousData ergonomics fit the read-heavy immutable workload better.

**Option B: SWR.** Rejected. Fine for simple reads; weaker mutation lifecycle, invalidation targeting, and devtools than TanStack Query — all load-bearing here (run launch → invalidate list → prefetch detail).

**Option C: React Context for workspace state.** Rejected. Context re-render behavior is wrong for frequently-read workspace values; Zustand selectors are precise and store logic is testable outside React.

**Option D: Everything in URL.** Rejected. Comparison baskets and preferences pollute URLs and exceed practical length; URL is for view identity, not preferences.

### Consequences

Positive: every screen shareable/restorable by URL; near-zero refetch waste; state bugs localized by class. Negative: developers must route each new piece of state to the right home — the decision table in `FRONTEND_ARCHITECTURE.md` §8 is the enforcement artifact, checked in code review.

---

## TDR-006 — React Router (Library Mode), Client-Side SPA, No SSR

**Status:** Accepted

### Context

The app is a localhost-deployed internal tool. Routing needs: typed-ish URL state, lazy module chunks, nested layouts (app shell → module → tabs), and zero server rendering concerns.

### Decision

**React Router v7 in library mode**, with data fetching owned entirely by TanStack Query (router loaders are not used, avoiding a second data-fetching idiom). Routes lazy-load per module group. No SSR framework.

### Alternatives Considered

**Option A: TanStack Router.** Seriously evaluated — first-class typed search params are exactly the `useUrlState` need. Rejected (narrowly) for Phase 1: React Router's ubiquity maximizes AI-assisted implementation reliability and reviewer familiarity; the typed-params gap is closed by the small Zod `useUrlState` hook. Documented as the strongest future alternative; the hook API is designed so a TanStack Router migration would be mechanical.

**Option B: Next.js App Router.** Rejected (see TDR-001-C). Server components complicate the "Query owns all data" model for zero benefit on localhost.

**Option C: Hash routing / no router.** Rejected. Deep-linkable research state is a core requirement.

### Consequences

Positive: one data-fetching idiom; minimal router surface; simple static deployment (Vite build served by FastAPI or any static server). Negative: search-param typing is hand-rolled via Zod (small, tested, contained in one hook).

---

## TDR-007 — TanStack Table + Row Virtualization for All Data Grids

**Status:** Accepted — **partially superseded by TDR-011** for non-virtualized tables (F18)

### Context

Trade logs (thousands of rows), the run registry (hundreds growing to thousands), and the universe grid all need sorting, filtering, sticky headers, column visibility, grouping (P3), and CSV export — with terminal-grade density that off-the-shelf grids resist.

### Decision

One `<DataGrid>` component built on **TanStack Table** (headless) + **TanStack Virtual** for any table that can exceed 200 rows. Domain tables are column definitions + `fmt`/`tone` formatters only. Server-side pagination for trade logs; client-side operation elsewhere at Phase 1 scale.

### Alternatives Considered

**Option A: AG Grid Community.** Seriously evaluated — the institutional-finance incumbent, and naming it is itself interview-defensible. Rejected: the features that make AG Grid the desk standard (pivoting, range selection, Excel export) are Enterprise-licensed; Community delivers a large bundle and a fight-the-theme styling model for features TanStack covers. Documented as the drop-in if Phase 3 grouping/pivot needs outgrow headless — `<DataGrid>`'s props contract is deliberately AG-compatible in shape.

**Option B: Plain `<table>` + hand-rolled sort.** Rejected. Re-implements column visibility/filter/virtualization badly by the third table.

**Option C: Glide Data Grid.** Rejected. Canvas grid excellent at 100k+ rows, but custom-cell rendering (badges, sparklines, links) is where this UI lives, and DOM cells are far cheaper to build and test at our row counts.

### Consequences

Positive: total styling control at terminal density; one grid to test; column defs are trivially reviewable. Negative: features like column-drag and range selection are build-on-demand (deferred until a workflow needs them).

**F18 amendment:** DataGrid's `display:block` tbody prevents width inheritance in flow context — all non-virtualized tables render as blank rows or collapse to minimum width. Decision: DataGrid is now used **only** for Run Explorer (the one table that genuinely needs virtualization). All other tables use plain HTML `<table>` per TDR-011. The `DataGrid` component remains in the codebase for the Run Explorer use case; AG Grid Community remains the documented future upgrade path if pivot/grouping needs emerge.

---

## TDR-008 — React Hook Form + Zod, Schema-Driven Parameter Forms

**Status:** Accepted

### Context

Strategy Builder must render parameter forms for every strategy in `strategies.yaml`, and the Workbench must render parameter inputs for every indicator in the registry — today 4 strategies and 5 indicators, tomorrow dozens/hundreds. Hand-building a form per strategy guarantees drift.

### Decision

- The API exposes param **schemas** (name, type, default, min/max, description) derived from strategy/indicator definitions.
- A single `<ParamForm>` renders any schema via typed field components; **React Hook Form** manages state/performance (uncontrolled inputs, no re-render storms in dense forms); **Zod** validates client-side, mirroring API-side Pydantic validation.
- Adding a strategy/indicator to the backend adds it to the UI with zero frontend code.

### Alternatives Considered

**Option A: Formik.** Rejected — maintenance-dormant, controlled-input re-render cost.
**Option B: Hand-written forms per strategy.** Rejected — the scalability requirement is explicit.
**Option C: JSON-Schema form generators (RJSF).** Rejected — generated markup fights the design system; our schema is narrow enough that a small bespoke renderer is cheaper than fighting a general one.

### Consequences

Positive: strategy/indicator growth is backend-only work; validation duplicated by generation, not by hand. Negative: the param-schema endpoint becomes a real contract to maintain (it would be needed regardless).

---

## TDR-009 — No Animation Library; CSS Transitions Only

**Status:** Accepted

### Context

Framer Motion was on the candidate list. The design philosophy states animation exists only where it improves usability.

### Decision

No animation library. The complete motion inventory: 120–160ms opacity/transform transitions on panels, menus, and drawers; skeleton shimmer; chart transitions handled natively by ECharts; `prefers-reduced-motion` respected globally. All achievable in CSS via tokenized durations/easings.

### Alternatives Considered

**Framer Motion.** Rejected. ~30KB+ and a physics-animation API whose expressive range this interface must deliberately not use. A workstation used all day rewards stillness; motion should mark state change, not decorate it. Revisit only if a specific interaction (e.g., animated run-comparison reordering) demonstrably needs orchestration CSS cannot express.

### Consequences

Positive: smaller bundle, calmer interface, one less dependency. Negative: none identified at this scope.

---

## TDR-010 — OpenAPI-Generated TypeScript Contracts

**Status:** Accepted

### Context

The backend's discipline rests on `src/core/types.py` as the single source of truth. A hand-written TypeScript mirror would silently drift.

### Decision

`types.py → Pydantic models (api/models.py) → OpenAPI → openapi-typescript → src/api/schema.d.ts`. Generation runs in the dev loop (`make types`) and CI fails on uncommitted diff. `schema.d.ts` is never hand-edited; the typed API client and all query hooks consume it.

### Alternatives Considered

**Option A: Hand-written types.** Rejected — guaranteed drift; contract violations become runtime bugs instead of compile errors.
**Option B: Full-client generators (Orval, openapi-generator).** Rejected for Phase 1 — generated clients impose their own fetch/query conventions; `openapi-typescript` generates types only, leaving the thin hand-written client (~100 lines) under our control. Orval noted as a Phase 3 option if endpoint count grows large.
**Option C: tRPC-style end-to-end typing.** Not applicable across a Python/TypeScript boundary; OpenAPI is the interoperable equivalent.

### Consequences

Positive: `types.py` remains the platform-wide single source of truth, now spanning both languages; contract changes are compile-visible in the frontend within seconds. Negative: generation step in the toolchain (one make target; CI-enforced).

---

## TDR-011 — Plain HTML `<table>` for All Non-Virtualized Tables

**Status:** Accepted (F18)
**Supersedes:** TDR-007 for all tables except Run Explorer

### Context

F16 Inc3 attempted to fix table width issues by adding `w-full` to DataGrid wrapper divs. F17 and F17-hotfix attempted multiple further fixes. After three modules the tables still did not span full container width. F18 identified the root cause: `DataGrid` uses `display:block` on its `<tbody>` (required for TanStack Virtual's absolute row positioning). This breaks standard CSS width inheritance — the `<tbody>` does not receive width from its parent, so all cells collapse to minimum content width.

### Decision

All tables that do not require row virtualization use a plain HTML `<table>` with `className="w-full table-fixed border-collapse"`, wrapped in `<div className="overflow-hidden rounded border border-border-default">`. `DataGrid` is retained only for Run Explorer (`/runs`), which is the one table that can have 100+ rows and benefits from virtualization.

Reference implementation: `src/components/data/PortfolioAssetTable.tsx`

Files migrated in F18: `UniverseGrid`, `ContractInventoryPanel`, `AssetRunsPanel`, `TradeTable`, `FeatureSpecTable`, `MetricDeltaTable`, `RegimeComparisonTable`.

### Alternatives Considered

**Continue patching DataGrid:** Rejected after three module attempts. The `display:block` constraint is fundamental to virtualization — it cannot be overridden without breaking virtual scroll.

**AG Grid Community:** Rejected for the same reasons as TDR-007. Not the right tool for 6-row fixed tables.

### Consequences

Positive: tables span full container width universally; simpler implementation; easier to test. Negative: server-side pagination, column visibility, and CSV export must be hand-built per table if needed (not currently required for any affected tables). The `DataGrid` remains the pattern for future large-dataset tables.

---

## TDR-012 — ECharts CSS Variable Resolution via `resolveCssVar()`

**Status:** Accepted (F16 Inc1)

### Context

F16 visual verification found the correlation heatmap rendering entirely black. Browser console showed: `[ECharts] 'var(--text-loss)' is an illegal color, fallback to '#000000'`. The chart theme was passing CSS custom property strings directly to ECharts as color values.

### Decision

ECharts processes colors through its own canvas renderer — CSS `var(--)` strings are not browser-resolved CSS, they are raw strings that ECharts cannot interpret. All ECharts color values must use the `resolveCssVar()` helper from `lib/chart-theme.ts`, called inside the component function body (after CSS is loaded):

```typescript
function resolveCssVar(name: string, fallback = '#888888'): string {
  if (typeof document === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}
```

CSS `var(--)` strings remain correct in Tailwind class names applied to DOM elements — only ECharts canvas colors need resolution.

### Consequences

Positive: ECharts colors match the design system; heatmap and all chart colors render correctly. Negative: one extra call per component initialization (negligible).

**ECharts bundle size (accepted):** Vite build produces a warning that the ECharts chunk exceeds the 500 kB hint. This is expected and accepted — a consequence of the single-chart-engine decision (TDR-004). The full ECharts bundle is required for the parallel coordinates chart type (added in FEP Inc6 for Sweep Explorer). No tree-shaking workaround is pursued: the research platform loads once per session on a desktop machine, and the performance budget concern (§14 of FRONTEND_ARCHITECTURE.md) is render time, not load time. The warning is not a build error and should not be treated as one.

---

## TDR-013 — Position State as markArea Bands (Not Separate Pane)

**Status:** Accepted (F18)

### Context

`SignalOverlayChart` originally rendered three synced ECharts panes: price (candlestick), signal (line), and position (bar showing Long=+1, Flat=0, Short=−1). After 8+ implementation attempts across F17 and F18, the gap between the signal and position panes could not be closed — ECharts renders axis labels outside grid boundaries, consuming ~10–12px of inter-pane space regardless of axis config (`containLabel`, `showMinLabel`, `min/max` adjustments all failed to close both gaps simultaneously).

### Decision

Remove the position pane (`grid[2]`) entirely. Replace with `markArea` background bands on the signal pane:
- Long periods: faint green (rgba of `--bg-gain-fill` at 8% opacity)
- Short periods: faint red (rgba of `--bg-loss-fill` at 8% opacity)
- Applied to signal pane only (not price pane)

**Institutional rationale:** Price charts stay clean — Short red bands clash with red bearish candlesticks, creating analytical ambiguity. Position context on the signal pane is unambiguous. Background shading for binary Long/Flat/Short is the standard pattern in Bloomberg backtesting views and most institutional research platforms.

**Legend:** `■ Long  ■ Short` inline in chart title bar (right side).

**Index alignment:** `position.index` starts later than `ohlcv.index` due to signal warmup period. Band boundaries use string matching against the signal pane category axis (`raw.index`) only — guaranteed to match.

### Consequences

Positive: no inter-pane gaps; cleaner visual; institutionally standard pattern; eliminates 80+ lines of grid/axis config. Negative: per-bar position detail not visible (only period start/end shown as bands); TD-F18-A: price pane bands deferred due to index alignment complexity.

---

## TDR-014 — useUrlState: null=Delete, undefined=Preserve

**Status:** Accepted (F18)

### Context

Multiple screens had bugs where URL params were unintentionally cleared or preserved. The root cause was that `setUrlState({ key: undefined })` was being called with `undefined` when the intent was "do nothing" — but the hook was treating `undefined` as "clear this param".

### Decision

Formalize the semantics:
- `null` = explicit delete — removes the param from the URL
- `undefined` = no-op — preserves the existing URL param value unchanged

```typescript
setUrlState({ run_id: null })      // → removes ?run_id= from URL
setUrlState({ run_id: undefined }) // → URL unchanged
setUrlState({ run_id: '...' })     // → sets ?run_id=...
```

All callers updated: `CompareConfigPanel`, `CurveDateControl`, `PortfolioAnalytics` (×2).

### Consequences

Positive: eliminates class of silent URL state bugs. Negative: any new caller must be aware of the null/undefined distinction — using `undefined` to clear a param is now a documentable bug, not just inconsistent behavior.

---

## TDR-015 — Uniform Workflow Page Layout: grid-cols-2

**Status:** Accepted (F18)

### Context

Research Workbench, Strategy Builder, Futures Curve, and Portfolio Analytics each had different layout patterns — some used fixed `w-96` sidebars, some used full-width stacked layouts. Visual verification showed they looked inconsistent and some compressed main content when the sidebar was open.

### Decision

All four workflow pages share a uniform layout:

```tsx
<div className="grid grid-cols-2 gap-4 h-full">
  <div className="overflow-y-auto">    {/* Left: scrollable config */}
    <Panel>...</Panel>
  </div>
  <div className="overflow-hidden">   {/* Right: fixed action */}
    <Panel>
      <Button className="w-full">Action</Button>
      {/* results */}
    </Panel>
  </div>
</div>
```

`grid-cols-2` for genuine 50/50 split at any viewport (not fixed `w-96`). Left column scrolls independently. Right column fixed. Action button always full-width amber.

### Consequences

Positive: visual consistency across all workflow screens; config always left, action always right; predictable for researcher switching screens. Negative: 50/50 may not be optimal for all content densities (a narrower config rail might be better on ultrawide — deferred).

---

## TDR-016 (AD-FEP-001) — Regime Panel: Opt-In Button

**Status:** Accepted (FEP)

### Context

`PortfolioRegimePanel` initially auto-fetched regime attribution for all assets on mount using `useQueries` (6 simultaneous requests). Each request runs full term structure classification across ~4,100 bars synchronously — 30–90 seconds each. In single-worker Uvicorn, 6 concurrent requests saturate the server completely, blocking all other API calls (Strategy Builder asset list, Research Workbench signal evaluation, health checks) for 3–9 minutes.

### Decision

`PortfolioRegimePanel` does not auto-fetch on mount. The researcher explicitly clicks "Compute Regime Attribution" to trigger a single asset request. Asset switching within the session is instant (cached, `staleTime: Infinity`).

`useRegimeAttributionParallel.ts` is preserved in the codebase with a documentation comment explaining `TD-FEP-REGIME-ASYNC`. When `POST /api/regime-attribution/compute` (async job) ships, the frontend change is a single import swap.

### Institutional Rationale

Bloomberg standard: computationally expensive exploratory analytics are behind an explicit user action, not auto-loaded. Regime attribution is exploratory — not a primary KPI — so the opt-in gate matches its role in the research workflow.

### Migration Path

Backend ships `POST /api/regime-attribution/compute → { job_id }` → `GET /api/regime-attribution/{job_id}/status` → `GET /api/regime-attribution/{job_id}/result`. Frontend replaces `useRegimeAttribution` import with `useRegimeAttributionAsync` in `PortfolioRegimePanel.tsx`. Zero other changes.

---

## TDR-017 (AD-FEP-002) — TDR-011 Confirmed for All FEP Tables

**Status:** Accepted (FEP)

### Decision

TDR-011 (plain HTML `<table>`) confirmed for all new FEP tables. `ValidationSummaryTable` and `SweepResultsTable` both use the `PortfolioAssetTable.tsx` reference pattern exactly.

---

## TDR-018 (AD-FEP-003) — Contango=Amber/Warn Confirmed; DESIGN_SYSTEM Corrected

**Status:** Accepted (FEP)

### Context

`DESIGN_SYSTEM.md §2.2` previously contained a stale entry: `tone.regime(contango) → loss/red` (documented as "defensible because contango costs the long roll yield"). This was never implemented. The actual implementation since F9 has always used amber/warn for Contango.

### Decision

The regime color mapping is:
- CONTANGO → `--warn-500` (amber)
- BACKWARDATION → `--gain-500` (green)
- FLAT → `--gray-400` (gray)

`DESIGN_SYSTEM.md §2.2` corrected in FEP Inc8. Any future developer referencing the doc will see the correct mapping.

---

## TDR-019 (AD-FEP-004) — TDR-015 Extended: All Workflow Screens

**Status:** Accepted (FEP)

### Decision

TDR-015 extended to cover all workflow screens added in FEP. The grid-cols-2 pre-action / full-width post-action pattern now applies to:
- Research Workbench (FEP: full-width post-evaluate, "← Modify signal" back button)
- Strategy Builder (F18)
- Futures Curve (F18)
- Portfolio Analytics (F18)
- Validation Tab in Run Detail (FEP)
- Sweep Explorer (FEP)
- Curve PCA (FEP)
- Data Manager (FEP)

---

## TDR-020 (AD-FEP-005) — TDR-012 Confirmed for All FEP Charts

**Status:** Accepted (FEP)

### Decision

TDR-012 (`resolveCssVar()` for all ECharts colors) confirmed for all 9 new FEP chart components. ESLint `no-restricted-syntax` override added in `frontend/.eslintrc.cjs` for `src/components/charts/**` — hex literals in `resolveCssVar()` fallback arguments are the correct pattern and must not be flagged.

---

## TDR-021 (AD-FEP-006) — All Radix TooltipContent: Dark Platform Theme

**Status:** Accepted (FEP)

### Context

All Radix `TooltipContent` rendered with white background and gray text (Radix defaults), inconsistent with the platform's dark terminal aesthetic.

### Decision

`src/ui/tooltip.tsx` updated once — applies platform-wide:
```tsx
className="z-50 overflow-hidden rounded border border-border-default bg-bg-raised text-text-primary px-2.5 py-1.5 text-xs font-mono shadow-md ..."
```

Import path is `@/ui/tooltip` — NOT `@/components/ui/tooltip`. This distinction matters and has burned implementors before.

### Consequences

All tooltips across the platform (regime Info icon, WTI-Brent Spread disabled tooltip, Kupiec null tooltip, validation info) now consistently dark. Any new tooltip added anywhere inherits the correct style automatically.

---

## TDR-022 (AD-FEP-007) — Sweep n_complete: Completion-Only by Design

**Status:** Accepted (FEP)

### Decision

`GET /api/sweeps/{sweep_id}/status` populates `n_complete` only when the sweep reaches `complete` status — not updated per combination during execution. Frontend displays "Running sweep… (N combinations)" without a progress fraction during execution. When the sweep completes, `n_complete` equals `n_combinations`.

Backend can add real-time `n_complete` updates later (`TD-FEP-SWEEP-PROGRESS` — ~30 minute backend task). Frontend already handles live `n_complete > 0` values and will display "14 / 27" automatically when the field is populated. Zero frontend changes needed.

---

## TDR-023 (AD-FEP-008) — fetchWithRaceRetry for Portfolio Result Hooks

**Status:** Accepted (FEP)

### Context

Portfolio run status transitions to `complete` before artifact persistence finishes (~1–3 seconds). Frontend navigating immediately to results sees 404 from `/summary`, `/equity`, `/risk`, `/correlation`, `/assets`.

### Decision

`src/lib/retry.ts` implements `fetchWithRaceRetry<T>(fn, maxAttempts=4, delays=[1000,3000,6000,10000])`. Applied to all 5 portfolio result hooks with `retry: false` on the TanStack Query config (manual retry, not TanStack's built-in exponential backoff).

### Migration Path

Backend ships `persisting` intermediate status (set before disk writes, flip to `complete` after all 7 artifacts confirmed written). Frontend polling hooks already handle any non-`complete`/`failed` status by continuing to poll — zero frontend changes needed when backend fix ships. `fetchWithRaceRetry` can be removed or left harmless.

Tracked as `TD-FEP-PORTFOLIO-RACE` in the backend enhancement register.

---

## TDR-024 — RouteErrorBoundary on All 16 Routes

**Status:** Accepted (post-FEP, commit 0d06bfd)

### Context

Clicking the Research Workbench sidebar icon while already on `/research` with evaluation results caused a full app crash: `TypeError: Cannot read properties of null (reading 'value') at WhiskerBoxCommonMixin2.getInitialData`. Same-route navigation stripped query params → `asset`/`strategy` emptied → chart received null OHLCV data → `[null, null, ...]` candlestick array → ECharts crash. No error boundary existed to catch it — the entire app crashed.

### Decision

1. Add null guard at top of `SignalOverlayChart` and `PriceChart` `useEffect` — `setOption` never called with null or empty data.
2. Filter null entries from candlestick data array before passing to ECharts.
3. Add `errorElement: <RouteErrorBoundary />` to ALL 16 routes in `routes.tsx`.

`RouteErrorBoundary` shows the error message and a "Reload" link — recoverable, not a full app crash. Created `src/components/layout/RouteErrorBoundary.tsx`.

### Consequences

Positive: any future unhandled chart error shows recoverable UI. Negative: none. The error boundary is a safety net — it does not change normal behavior.

---

## TDR-025 — IC State: TanStack Query Cache (Not Zustand)

**Status:** Confirmed (E2E suite discovery)

### Context

Early architecture documentation and some component comments stated that IC evaluation state (IC value, ICIR, decay data) was stored in Zustand. E2E testing confirmed this is incorrect.

### Confirmed Behavior

IC evaluation state lives entirely in **TanStack Query cache**, keyed by (asset, strategy, params hash). There is no Zustand store for evaluation results. The cache:
- Survives component re-renders and same-page navigation ✓
- Dies on full page navigation (`page.goto()`, hard refresh) ✓
- After reload: Research Workbench shows "No evaluation found" — **correct behavior, not a regression** ✓

### Consequences

Any spec, comment, or documentation referencing "Zustand for IC state" is incorrect and should be updated. The IC Gate URL contract (PATH A: `?evaluation=JSON.stringify(result)`) exists precisely because TanStack Query cache is ephemeral — evaluation results must be serialized to URL to survive page transitions to Strategy Builder.
