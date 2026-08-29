# Design System
## Commodity Systematic Research Platform

**Version:** 4.0
**Status:** Active — platform complete. 406 vitest + 114 E2E + 429 backend. All TD items closed.
**Scope:** This document is the complete visual and component reference for the frontend. It merges the design system and the component library into one source of truth (the components *are* the design system's concrete expression; separating them duplicated every table/chart/form rule).

Sections 1–7 define the visual language and tokens. Section 8 is the component library (props, responsibilities, states, accessibility). Section 9 defines system-wide state patterns (loading/empty/error). Section 10 covers interaction and accessibility rules.

---

## 1. Visual Language

**Direction:** a modern institutional research terminal. The reference band is Bloomberg Terminal (density, dark surfaces, monospaced numerics, keyboard-first) executed with contemporary craft (real typographic hierarchy, deliberate whitespace, consistent components) — closer to an internal Jane Street/Citadel tool than to either Bloomberg's 1990s chrome or a consumer fintech dashboard.

Principles:

1. **Numbers are the interface.** Every numeric value renders in the mono data face with tabular figures, right-aligned in tables, consistently signed and colored. Text explains; numbers decide.
2. **Dark-first, low-glare.** Graphite surfaces (never pure black — pure black halos on charts and fatigues over a trading day), restrained contrast steps, color reserved for meaning.
3. **Color is semantics, not decoration.** Green/red mean directional PnL and long/short — nothing else. Amber is the single interaction accent. IC quality has its own fixed band colors. If a color appears, it is telling the researcher something.
4. **Density with air.** Compact rows and tight metric grids, but panel gutters and section spacing stay generous so density never becomes clutter.
5. **The signature element: the IC Gate.** A full-width verdict strip in the Research Workbench that renders the platform's core doctrine — *evaluate before you backtest* — as interface. It is the one place the design raises its voice (band color, large mono IC value, explicit verdict text, and the gated "Configure backtest" action). Everything else stays quiet so the gate reads as doctrine, not decoration.

Anti-patterns (prohibited): gradients as decoration, glassmorphism, glow effects, decorative illustration, motion that does not mark a state change, more than one accent hue, pure-black backgrounds, low-contrast gray-on-gray text below AA.

---

## 2. Design Tokens

All tokens are CSS custom properties in `styles/tokens.css`; Tailwind consumes them. Components never use raw hex/px values. Semantic tokens reference primitive tokens; components reference **semantic tokens only**.

### 2.1 Color — primitives (dark theme, default)

```css
/* Surfaces — graphite ramp (cool, slightly blue-shifted) */
--gray-950: #0E1116;   /* app background */
--gray-900: #141922;   /* panel background */
--gray-850: #1A202B;   /* raised panel / table header / hover */
--gray-800: #222A37;   /* borders strong, active row */
--gray-700: #2E3948;   /* borders emphasis, input borders */
--gray-500: #5B6878;   /* disabled text, tertiary */
--gray-400: #7C8A9C;   /* secondary text, axis labels */
--gray-200: #C3CDD9;   /* primary text on dark */
--gray-050: #EEF2F6;   /* headings, emphasized values */

/* Accent — terminal amber (single interaction hue) */
--amber-500: #E8A33D;  /* primary actions, focus, selection, active nav */
--amber-600: #C8862B;  /* hover/pressed */
--amber-300: #F2C376;  /* subtle accents on dark */
--amber-900a: rgba(232,163,61,0.12);  /* selection fills */

/* Directional (PnL / long-short) — tuned for dark bg */
--gain-500: #3FB68B;   /* up / long / winning */
--gain-900a: rgba(63,182,139,0.12);
--loss-500: #E05D5D;   /* down / short / losing */
--loss-900a: rgba(224,93,93,0.12);

/* Status */
--info-500: #4E9CDB;   /* running, informational */
--warn-500: #D9A03C;   /* validation flags, degraded */
--crit-500: #E05D5D;   /* failure (shares loss hue deliberately) */
--ok-500:   #3FB68B;   /* complete, healthy */

/* IC quality band (fixed platform-wide, from ARCHITECTURE.md §10 thresholds) */
--ic-noise: #7C8A9C;       /* |IC| < 0.02  — gray: no information */
--ic-weak:  #D9A03C;       /* 0.02–0.05    — amber: investigate  */
--ic-strong:#3FB68B;       /* ≥ 0.05       — green: proceed      */
```

Light theme swaps the surface/text ramp (paper `#F7F8FA`, ink `#1B2430`) and darkens directional hues one step for contrast; semantic token names are identical, so the theme is a class toggle. Dark is default and the design target; light exists for documentation/screenshots and daylight preference.

### 2.2 Color — semantic tokens

```css
--bg-app: var(--gray-950);        --text-primary:  var(--gray-200);
--bg-panel: var(--gray-900);      --text-emphasis: var(--gray-050);
--bg-raised: var(--gray-850);     --text-secondary:var(--gray-400);
--bg-hover: var(--gray-850);      --text-disabled: var(--gray-500);
--bg-selected: var(--amber-900a); --text-accent:   var(--amber-500);
--border-default: var(--gray-800);--text-gain: var(--gain-500);
--border-strong: var(--gray-700); --text-loss: var(--loss-500);
--focus-ring: var(--amber-500);
```

Helper functions (in `lib/tone.ts`) are the only sanctioned way to color data: `tone.pnl(value)`, `tone.direction(±1)`, `tone.ic(value)` (band thresholds above), `tone.status(runStatus)`.

**Regime color semantics (confirmed F9, implemented F9–FEP — never change):**
- CONTANGO → `text-warn` (amber / `--warn-500`) — roll cost to long roll yield
- BACKWARDATION → `text-gain` (green / `--gain-500`) — roll yield benefit to longs
- FLAT → `text-text-secondary` (gray / `--gray-400`)

Note: Earlier documentation referenced `tone.regime(contango) → loss/red`. This was never implemented. Amber/warn for Contango is the confirmed platform standard, corrected in Inc8 of the FEP module.

### 2.3 Typography

| Role | Face | Notes |
|---|---|---|
| UI text | **Inter** (variable) | labels, body, nav, buttons; `font-feature-settings: "cv05","ss01"` for the open digits variant in headings |
| Data / numerics | **JetBrains Mono** | *every* numeric value, run IDs, tickers, code, params; always `font-variant-numeric: tabular-nums`; slashed zero on |
| Display | Inter Tight, weight 600 | page titles and the IC Gate verdict only — restraint keeps it meaningful |

Type scale (rem, 1.0 = 16px base; compact density multiplies sizes ×0.9375):

| Token | Size / line | Use |
|---|---|---|
| `--type-xs` | 11 / 16 | table meta, axis labels, badges |
| `--type-sm` | 12.5 / 18 | table cells, dense UI, captions |
| `--type-md` | 14 / 20 | default body, inputs, buttons |
| `--type-lg` | 16 / 24 | panel titles, tab labels |
| `--type-xl` | 20 / 28 | page titles |
| `--type-metric` | 22 / 28 mono 500 | MetricStat values |
| `--type-metric-lg` | 32 / 36 mono 500 | hero metrics (IC Gate value, headline Sharpe) |

Numeric formatting rules (implemented in `lib/fmt.ts`, no exceptions):
- Prices: decimals from asset `tick_size` (gold 2dp, copper 4dp, natgas 3dp).
- Percent: `+1.24%` / `−0.87%` — explicit sign, true minus (U+2212), colored via `tone.pnl`.
- USD: `$1.24M`, `$182.4k` compact in grids; full `$1,240,000` in detail views and tooltips.
- Metrics: Sharpe/Sortino/Calmar 2dp; IC/ICIR 3dp; drawdown as signed percent (always negative-toned).
- Dates: `2026-07-06` everywhere (ISO, sortable, unambiguous); times UTC with `Z`.
- `fmt.pct(value, precision?)` — unsigned percentage (e.g., `8.0%`). Added FEP Inc1. Used for vol contribution, exception rates, coverage fractions.
- `fmt.dec(value, precision?)` — decimal to N places (e.g., `3.82`). Added FEP Inc1. Used for Sharpe, IC, PSR, DSR values where sign is context-dependent.
- No inline `.toFixed()` in JSX for user-facing values — always use `fmt.*` functions.

### 2.4 Spacing, grid, radius, elevation

- **Spacing:** 4px base scale — `--space-1..12` = 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. Compact density: table row height 32px, comfortable 40px; input height 32/36px.
- **Layout grid:** app shell = fixed left rail (232px, collapses to 56px) + fluid content with `max-width: none` (workstations use the whole monitor). Content composes from a 12-column grid with 16px gutters; panels snap to column spans defined per screen in `SCREEN_SPECIFICATIONS.md`.
- **Radius:** `--radius-sm: 3px` (inputs, badges), `--radius-md: 6px` (panels, cards), `--radius-lg: 10px` (dialogs). No pill shapes except status badges.
- **Elevation:** dark UIs elevate by *surface lightness*, not shadow. Levels: app (`--bg-app`) → panel (`--bg-panel`, 1px `--border-default`) → raised (`--bg-raised`) → overlay (raised + `0 8px 24px rgba(0,0,0,0.45)` + border-strong). Shadows appear only on overlays (menus, dialogs, palette).

### 2.5 Motion

`--dur-fast: 120ms`, `--dur-base: 160ms`; easing `cubic-bezier(0.2, 0, 0, 1)`. Inventory is closed (TDR-009): opacity/transform on overlays and drawers, skeleton shimmer, ECharts-native series transitions. `prefers-reduced-motion` disables all of it globally.

### 2.6 Iconography

**Lucide** icons exclusively, 16px in dense contexts / 18px in nav, `stroke-width: 1.75`, colored `--text-secondary` (accent only when active). Icons always pair with a label or `aria-label`; no icon-only actions except in the collapsed rail (tooltipped). Domain glyph conventions fixed platform-wide: ▲/▼ triangles for direction, `TrendingUp` runs, `FlaskConical` research, `Layers` features, `Gauge` performance, `GitCompare` comparison, `Database` data manager.

---

## 3. Chart Standards

All charts render inside `<ChartFrame>` (§8.4) on the shared ECharts theme generated from tokens.

Global rules:
- Background transparent (panel provides surface); gridlines `--gray-800` at 60% opacity, horizontal only unless the chart is time-dense; axis text `--type-xs` `--text-secondary`.
- **Crosshair everywhere:** dashed `--gray-500` cross with axis-pointer labels in mono. Charts on the same screen sharing a time axis are group-connected (hover synchronizes) — non-negotiable for price+signal, equity+drawdown pairs.
- Tooltips: raised surface, mono values, ISO date header, series swatches; max 6 series rows then "+n more".
- Zoom: horizontal `dataZoom` (drag + wheel) on all time series; a slim range brush appears only on charts > 2 years; double-click resets.
- Series palette for non-semantic multi-series (comparison overlays): `#E8A33D, #4E9CDB, #3FB68B, #B48EDE, #D9A03C, #6FB8C9` — starts with accent amber for "the current run", then perceptually distinct hues; never reuses pure gain/loss hues for arbitrary series.
- Null policy: gaps render as gaps (line breaks), never interpolated — honest about missing bars and roll artifacts.

Per-chart conventions:

| Chart | Convention |
|---|---|
| **Candlestick** | gain/loss hues for up/down bodies, hollow-up optional setting; volume sub-pane 18% height, bars tinted by day direction at 50% opacity; indicator overlays (EMA/SMA) from the series palette with legend chips; roll-gap dates (P2, once identified) marked with a subtle vertical dashed rule + tooltip note; **price Y-axis: `min: null` (ECharts auto-scale — never force `min: 0`; the WTI 2020-04-20 negative price event (−$37.63) is genuine historical data that must render correctly)**; volume Y-axis: `min: 0` |
| **Equity curve** | single line `--amber-500`; drawdown shown as an attached 25%-height under-pane, filled `--loss-900a` with `--loss-500` line, inverted axis (0 at top) so depth reads downward; initial-capital baseline as dotted rule |
| **Rolling Sharpe / vol** | line + zero/threshold reference rules (dotted `--gray-500`); 63d solid, 126d dashed of the same hue — window is a dash-pattern, not a new color |
| **IC bar (rolling IC)** | bars colored by `tone.ic` band per bar; band threshold rules at ±0.02/±0.05 labeled at right margin |
| **IC decay** | line+point over horizons {1,2,5,10,20}; x-axis categorical, log-flavored spacing; points colored by band |
| **Signal overlay** | price pane + aligned RawSignal pane (line, zero rule) + PositionSignal pane (step series, filled `--gain-900a` above zero / `--loss-900a` below) — three connected panes, one crosshair |
| **Histogram / distribution** | daily-return or trade-PnL histograms: bars `--gray-700`, negative-side bars tinted loss at 40%; mean/median rules |
| **Correlation heatmap (P3)** | diverging loss→gray-850→gain scale pinned to [−1, 1]; cell value labels in mono at ≥ 48px cells, hidden below |
| **Futures curve (P2)** | x = expiry, y = price; today's curve solid amber, historical snapshot ghosts `--gray-500` at decreasing opacity; contango/backwardation region annotation via `tone.regime` |

Export: every ChartFrame offers PNG export (2× pixel ratio, current theme) via the frame toolbar.

---

## 4. Table Standards

One `<DataGrid>` (§8.5). Rules:
- Header row `--bg-raised`, sticky, `--type-xs` uppercase tracking-wide labels; sortable columns show a slim triangle on hover/active only.
- Numeric columns right-aligned mono; text left; badges/status center. Column alignment is declared in the column def, never ad hoc.
- Row height by density token; zebra striping **off** (density + hover highlight suffices; stripes add noise at 32px rows); hover `--bg-hover`; selected `--bg-selected` + 2px left accent bar.
- Row click = primary navigation (opens the entity); explicit checkbox column appears only in selection contexts (comparison basket).
- Filters live in a toolbar above the grid (search input + typed filter chips), never inside header cells.
- Virtualize > 200 rows; server pagination for trade logs (page size 100, mono `1–100 of 2,431` counter).
- Every grid exports CSV of the *filtered* view from the toolbar.

---

## 5. Forms and Inputs

- Labels above inputs, `--type-sm` `--text-secondary`; required marked by absence of "(optional)" suffix, not asterisks.
- Inputs 32px (compact), `--bg-app` fill, `--border-strong` border, amber focus ring (2px outer). Numeric param inputs are mono with unit suffix slots (`bars`, `%`, `USD`) and native stepper suppressed in favor of styled steppers.
- Validation: inline message under field in `--crit-500` `--type-xs`, border shifts to crit; validate on blur + on submit, never on first keystroke.
- `<ParamForm>` (§8.7) renders any param schema; group order follows the schema; defaults shown as placeholder ghost text with a "reset to default" affordance per field.
- Selects/comboboxes are Radix-based, searchable when > 8 options (AssetSelector always searchable).

---

## 6. Status and Metric Language

- **Run status badges:** `queued` gray, `running` info (with 6px pulsing dot — the one permitted ambient animation, reduced-motion-safe), `complete` ok, `failed` crit. Badge = dot + label, radius-full, `--type-xs` mono.
- **MetricStat** blocks: label above (`--type-xs` secondary, uppercase), value in `--type-metric` mono, optional delta chip below (`tone.pnl` colored, signed). Drawdown values always render loss-toned even as headline metrics.
- **IC Gate verdict strip:** full-width band; left edge 3px in band color; contents: verdict label ("SIGNAL LIKELY NOISE" / "WEAK — INVESTIGATE" / "MEANINGFUL — BACKTEST WARRANTED"), IC and ICIR in `--type-metric-lg`, threshold context line, and the gated action. The only component allowed a tinted background fill (`band color @ 8%`).
- **Warning ribbons** (data validation flags): `--warn-500` left bar on `--bg-raised`, dismiss-per-session, always link to the evidence (Data Manager).

---

## 7. Voice and Microcopy

Sentence case everywhere except table headers and MetricStat labels (uppercase xs). Buttons name the action's result: "Launch backtest", "Compare 3 runs", "Re-ingest gold". Empty states instruct: *"No runs yet. Evaluate a signal in the Workbench, then launch your first backtest."* Errors state fact + remedy, no apology: *"Run not found. It may have been deleted. → Open Run Explorer."* Numbers are never rounded in copy in ways that contradict on-screen values. The interface uses the platform's own vocabulary exactly (RawSignal, IC, run, FeatureSpec) — researchers are the audience; do not paraphrase the domain.

---

## 8. Component Library

Layer key: **F1** primitive (no domain knowledge) · **F2** domain component (props-in, pixels-out; never fetches) · **Shell** app chrome. F3 features and F4 screens are specified in `SCREEN_SPECIFICATIONS.md`.

### 8.1 Shell components

**`AppShell`** — grid of SidebarNav / TopBar / ContextBar / content outlet / ComparisonTray. Owns density and theme classes from workspace store.

**`SidebarNav`** — Props: `items: NavItem[] {id, label, icon, route, phase?, disabled?}`. Renders module groups; phase-gated items disabled with phase tag tooltip ("Phase 2 — Commodity Intelligence"). Collapse toggle persists. Active item = amber text + 2px left bar. Keyboard: full arrow-key traversal; `[` toggles collapse.

**`TopBar`** — app title, global search / ⌘K affordance, theme + density toggles, API-health dot (polls `/api/health`; turns crit with tooltip when unreachable).

**`ContextBar`** — Props: `context: {asset?, dateRange?, signal?}; editable: boolean; onChange`. Persistent strip rendering the research context as removable chips; screens declare which fields they consume. Editing a chip opens the corresponding selector inline. Deep-linked URLs override and then update it.

**`CommandPalette`** (⌘K) — Props: `providers: PaletteProvider[]` (screens register searchable entities: assets, runs, screens, actions). Sections: Navigate / Assets / Runs / Actions. Fuzzy match; recent-first; actions can carry context ("New backtest: gold · ema_crossover").

**`ComparisonTray`** — docked bottom-right pill showing basket count with run-ID chips on hover; actions: Compare (→ `/runs/compare?ids=`), Clear. Hidden when empty. A11y: `aria-live="polite"` announces additions.

### 8.2 F1 primitives (shadcn/Radix base, token-restyled)

`Button` (variants: primary amber / secondary outline / ghost / danger; sizes sm 28 · md 32; `loading` prop renders inline spinner and disables), `IconButton`, `Input`, `NumberInput` (mono, unit slot, steppers), `Select`, `Combobox` (searchable), `Checkbox`, `Switch`, `Tabs` (underline style, amber active bar; router-bound variant syncs `?tab=`), `Dialog`, `Drawer` (right, 480px, used for row detail), `DropdownMenu`, `Tooltip` (500ms delay, raised surface), `Toast` (bottom-right, max 3, action slot), `Badge`, `Kbd`, `Separator`, `Skeleton`, `Panel` (`title, actions?, children, padding?` — the universal container: `--bg-panel`, border, radius-md, title row with action slot), `Popover`, `Command` (palette base). All primitives: visible focus ring, full keyboard operability, ARIA per Radix defaults.

### 8.3 Metric and status components (F2)

**`MetricStat`** — Props: `label; value: number; format: FmtKind; delta?; deltaFormat?; tone?: 'auto'|'neutral'; size?: 'md'|'lg'; hint?` (tooltip with definition — every metric carries its formula from the backend spec, e.g. Sharpe hover shows `mean(daily_return)/std(daily_return)·√252`). Renders per §6.

**`MetricGrid`** — Props: `metrics: MetricStatProps[]; columns?: 3|4|6`. Responsive metric wall with consistent gutters; skeleton variant built in.

**`RunStatusBadge`** — Props: `status: 'queued'|'running'|'complete'|'failed'`. Per §6.

**`ICBandBadge`** — Props: `ic: number`. Small band-colored chip (`0.061 · strong`) used in tables.

**`ICGateStrip`** — Props: `evaluation: SignalEvaluation | null; onConfigureBacktest; onOverride; loading?`. The signature component (§6). Null evaluation renders the locked state: "Evaluate this signal to unlock backtesting" + disabled action + explicit override link ("Backtest without evaluation — will be recorded"). Emits `override` so the launch mutation flags `signal_evaluation: null` deliberately.

**`ValidationRibbon`** — Props: `flags: DataFlag[]; onView`. Per §6.

**`RegimeBadge`** (P2) — Props: `regime: 'contango'|'backwardation'|'flat'; slope?`.

### 8.4 Chart components (F2 — all compose `ChartFrame`)

**`ChartFrame`** — Props: `title?; height; loading?; error?: ApiError; empty?: {message, action?}; toolbar?: ToolbarAction[]; syncGroup?: string; onRetry?; children(theme, ref)`. Provides the panel chrome, skeleton (ghost axes + shimmer), empty/error states, PNG export, zoom-reset, fullscreen dialog, and ECharts group-connection. Every chart below accepts `ChartFrame` passthrough props plus:

| Component | Key props | Notes |
|---|---|---|
| `PriceChart` | `ohlcv: ColumnarSeries; overlays?: {spec: FeatureSpec, values}[]; markers?: DateMarker[]; volume?: boolean; style: 'candle'\|'line'` | overlay legend chips toggle series; engine-agnostic contract (TDR-004A) |
| `EquityCurveChart` | `equity: Series; drawdown?: Series; baseline?: number; compare?: NamedSeries[]` | attached drawdown pane; comparison mode normalizes to % of initial capital |
| `RollingMetricChart` | `series: NamedSeries[]; reference?: number[]; dashByWindow?: boolean` | Sharpe/vol/drawdown rolling views |
| `ICRollingChart` | `ic: Series; window: number` | banded bars + threshold rules |
| `ICDecayChart` | `decay: Record<horizon, number>` | |
| `SignalOverlayChart` | `ohlcv; raw: Series; position: Series` | two synced panes (price + signal); position state shown as markArea bands on signal pane — see §11.3 |
| `ReturnHistogram` | `values: number[]; bins?; markers?: ('mean'\|'median')[]` | |
| `TurnoverChart` | `position: Series` | step + turnover annotation |
| `FuturesCurveChart` (P2) | `snapshots: CurveSnapshot[]; highlightDate` | ghosted history |
| `CorrelationHeatmap` (P3) | `matrix; labels; window` | click cell → pair drill-down callback |
| `Sparkline` | `values; tone?` | SVG renderer, 80×24, used in grid cells |

### 8.5 Data components (F2 + F18)

**Table infrastructure — two types (TDR-011):**

#### `DataGrid<T>` — TanStack Table + virtualization
**Used ONLY for Run Explorer** (`/runs`). Props: `columns: ColumnDef<T>[]; data: T[] | ServerPage<T>; getRowId; onRowClick?; selection?: {ids, onChange}; toolbar?: {search?, filters?: FilterDef[], export?}; virtualized?; density?; sortState/onSort; emptyState; loading`. A11y: `role="grid"`, arrow-key cell navigation, Enter = row click, Space = toggle selection.

**Critical constraint:** DataGrid uses `display:block` on tbody — this prevents width inheritance from flow context. Column widths must be set explicitly on `th`/`td`. Do NOT add new DataGrid instances for other tables.

#### Plain HTML `<table>` — all other tables
**Reference implementation:** `src/components/data/PortfolioAssetTable.tsx`. Required pattern:

```tsx
<div className="overflow-hidden rounded border border-border-default">
  <table className="w-full table-fixed border-collapse text-sm">
    <thead className="bg-bg-raised">
      <tr>
        <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary w-[...]">COLUMN</th>
      </tr>
    </thead>
    <tbody>
      {rows.map(row => (
        <tr key={row.id} className="border-t border-border-default hover:bg-bg-hover">
          <td className="px-3 py-2 text-sm text-text-primary">{value}</td>
        </tr>
      ))}
    </tbody>
  </table>
</div>
```

**Files using plain table pattern (F18):** `UniverseGrid`, `ContractInventoryPanel`, `AssetRunsPanel`, `TradeTable`, `FeatureSpecTable`, `MetricDeltaTable`, `RegimeComparisonTable`, `PortfolioAssetTable`.

**Domain table specs:**
- **`UniverseGrid`** — asset, last price (2dp), 1d/1w/1m% (tone.pnl), realized vol, volume sparkline (20d), data-health dot, last-updated. Row → Asset Detail.
- **`RunTable`** (DataGrid) — status badge, run_id (mono), strategy, asset, date span, Sharpe, max DD, total return, IC (`ICBandBadge`), trades, executed_at. Selection column feeds ComparisonTray. Row → Run Detail.
- **`TradeTable`** — direction, entry/exit dates, entry/exit prices, duration (bars), gross PnL, cost, net PnL, return%. Server-side direction filter via `?direction=long/short&force_closed=true`.
- **`FeatureSpecTable`** — indicator, params (mono JSON), column_name, computed_at. Used in Workbench + Run Detail Artifacts.
- **`MetricDeltaTable`** (comparison) — metric rows × run columns (`ASSET · strategy` format); delta vs. baseline run; best-value highlighted.

### 8.6 Input components (F2)

**`AssetSelector`** — Props: `value; onChange; multiple?`. Searchable combobox listing universe with exchange + last price; keyboard-first; scales to dozens of assets (TDR/scalability requirement).

**`DateRangePicker`** — Props: `value: {from, to}; onChange; presets?: ('1Y'|'3Y'|'5Y'|'MAX'|…)[]; bounds` (from data availability). Mono ISO display; presets as segmented buttons.

**`ParamForm`** — Props: `schema: ParamSchema[]; values; onChange; onSubmit?; errors?; layout?: 'grid'|'stack'`. Schema-driven renderer (TDR-008): number/int/enum/bool field kinds, min/max, defaults, unit suffixes, per-field reset, Zod validation generated from schema.

**`IndicatorPicker`** — Props: `catalog: IndicatorMeta[]; selected: FeatureSpec[]; onChange`. Category-grouped searchable list; selecting opens its ParamForm inline; selected specs render as removable chips showing the resolved column name (`ema_50`) — the naming convention made visible.

**`StrategyPicker`** — Props: `strategies: StrategyMeta[]; value; onChange`. Cards with one-line description + default params preview.

### 8.7 State components (F2)

**`EmptyState`** — Props: `icon?; title; body; action?: {label, onClick|href}`. **`ErrorState`** — Props: `error: ApiError; onRetry?; compact?` (panel-inline vs. full). **`LoadingSkeleton`** variants: `metric-grid`, `chart`, `table(rows)`, `form`. **`NotFound`**, **`ApiUnreachable`** (full-screen, retry + troubleshooting hint pointing at `make dev`).

---

## 9. System State Patterns

Every screen specifies all four states in `SCREEN_SPECIFICATIONS.md`; the defaults are:

| State | Pattern |
|---|---|
| **Loading** | layout-mirroring skeletons per panel; numbers before charts before tables; `keepPreviousData` on filter changes (grids dim to 60% + inline spinner instead of emptying) |
| **Empty (no data yet)** | instructive EmptyState pointing to the *previous workflow stage* (no runs → Workbench; no data → Data Manager ingest) |
| **Empty (filters exclude all)** | distinct copy: "No runs match these filters" + one-click clear |
| **Error** | panel-scoped ErrorState; siblings unaffected; retry always offered; failed runs are rendered entities, not errors (see `FRONTEND_ARCHITECTURE.md` §11) |

---

## 10. Interaction and Accessibility

**Keyboard model:** ⌘K palette; `g` then `m/r/b/u` go-to-module chords; `[` collapse nav; `j/k` row traversal in focused grids; `Enter` open; `c` add focused run to comparison; `Esc` closes overlays innermost-first; `?` opens the shortcut sheet. All shortcuts suppressed while inputs are focused.

**Focus:** amber 2px ring on every interactive element, never removed; focus trapped in dialogs; palette and drawers return focus to their invoker.

**Accessibility floor (WCAG 2.1 AA):** text contrast ≥ 4.5:1 on all surfaces (the token ramp is chosen to guarantee this — `--text-secondary` on `--bg-panel` = 4.6:1); color never the sole carrier of meaning (direction always pairs glyph + sign; IC band always pairs label; status always pairs text); charts expose `aria-label` summaries ("Equity curve, gold EMA crossover, +18.2% over 2,514 bars, max drawdown −9.1%") and every chart's data is reachable via a table elsewhere on screen or via CSV export; `prefers-reduced-motion` honored globally; hit targets ≥ 24px even in compact density.

**Selection and copy:** run IDs, tickers, param values, and metric values are click-to-copy with toast confirmation — researchers paste these into notes constantly; treat copyability as a feature.

**Persistence of preferences:** theme, density, nav collapse, column visibility per grid, and last research context persist in the workspace store; URLs always win over remembered context.

---

## 11. ECharts Patterns (F16–F18)

### 11.1 CSS Variable Rule (CRITICAL)

**Never pass CSS `var(--)` strings as ECharts color values.** ECharts resolves colors through its own canvas renderer — `var(--text-loss)` silently falls back to `#000000`. All ECharts colors must use the `resolveCssVar()` helper from `lib/chart-theme.ts`:

```typescript
// Call inside component function body (not at module level — must run after CSS loads):
const gainColor = resolveCssVar('--bg-gain-fill', '#166534')
const lossColor = resolveCssVar('--bg-loss-fill', '#7f1d1d')

// For rgba opacity (use toRgba(), not +1F hex suffix — source may already be rgba()):
const longBand = toRgba(resolveCssVar('--bg-gain-fill', '#166534'), 0.08)
```

CSS var strings (`var(--)`) are correct in Tailwind class names applied to DOM elements. Only ECharts canvas colors need the `resolveCssVar()` treatment.

### 11.2 Tooltip Pattern — Colored Dots (Required)

All custom ECharts tooltip formatters MUST include `params.marker` to produce the colored dot beside each series entry:

```typescript
tooltip: {
  trigger: 'axis',
  formatter: (params: CallbackDataParams[]) => {
    const date = fmtDate(params[0]?.axisValue ?? params[0]?.value[0])
    return [date, ...params.map(p =>
      `${p.marker}${p.seriesName}: ${Number(p.value[1]).toFixed(3)}`
    )].join('<br/>')
  }
}
```

`p.marker` generates the colored HTML circle ECharts produces per series. Omitting it removes colored dots from hover cards.

**Exception:** OHLCV dimensions (O/H/L/C/Volume) in candlestick tooltips do not get markers — ECharts only generates markers for named series, not OHLC dimensions.

### 11.3 axisPointer Label (Required)

Prevent raw epoch millisecond values appearing in the blue crosshair label on x-axis hover:

```typescript
xAxis: {
  type: 'category',
  axisLabel: { formatter: (v: string | number) => fmtDate(v) },
  axisPointer: { label: { formatter: (p: { value: string | number }) => fmtDate(p.value) } }
}
```

Without `axisPointer.label.formatter`, the hovering crosshair shows `1262563200000` on the axis in a blue box.

### 11.4 DataZoom Positioning

DataZoom slider is positioned independently of grid `bottom` margin to prevent overlap with date labels:

```typescript
// Grid bottom — only for date axis labels:
{ bottom: 28 }   // ~25px for date labels

// DataZoom slider — absolute at container bottom, independent of grid:
{ type: 'slider', xAxisIndex: [0, 1, 2], bottom: 4, height: 18 }
```

### 11.6 Confirmed Canonical Patterns (E2E verified)

These three patterns were confirmed correct across all 11 chart components delivered in FEP and all prior chart components:

1. **`import { echarts } from '@/lib/echarts-setup'`** — never from `'echarts'` or `'echarts/core'` directly. `echarts-setup.ts` re-exports the core instance after `use([...])`. `ParallelChart` and `ParallelComponent` were added in FEP Inc6 for `ParallelCoordinatesChart`.

2. **`globalThis.addEventListener('resize', handleResize)`** — never `window`. Confirmed by F14 D11 ruling. Active ESLint check enforces this in chart files.

3. **`resolveCssVar('--token', '#hexFallback')`** — called inside component function body, never at module level. Hex fallback is required (ESLint override for `src/components/charts/**` to allow hex literals in this context).

**ECharts bundle size warning (accepted, not a build error):** Vite build produces: `chunk "echarts_charts" (1,234 kB) exceeds 500 kB. Consider using dynamic imports.` This is expected — the full ECharts bundle is required for `ParallelChart` (Sweep Explorer). The research platform loads once per session on a desktop machine. Performance concern at this scale is render time, not load time. The warning should be documented and ignored in CI — it is not a build failure.

Binary Long/Flat/Short position state is shown as **background shading bands on the signal pane only** — not as a separate pane and not on the price pane.

**Institutional rationale:** Price charts stay clean — Short red bands clash with red bearish candlesticks, creating analytical ambiguity. Signal pane context is unambiguous: amber signal line on faint green/red background.

```typescript
// Long bands — faint green at 8% opacity on signal pane markArea:
itemStyle: { color: toRgba(resolveCssVar('--bg-gain-fill', '#166534'), 0.08) }

// Short bands — faint red at 8% opacity:
itemStyle: { color: toRgba(resolveCssVar('--bg-loss-fill', '#7f1d1d'), 0.08) }
```

**Legend:** `■ Long  ■ Short` inline in chart title bar (right side) using ChartFrame `actions` prop.

**Index alignment:** `position.index` starts later than `ohlcv.index` due to signal warmup period (e.g., EMA 200 = 200 bars before valid signal). Bands use string matching against the signal pane category axis — applied to signal pane only where `raw.index` guarantees a match.

---

## 12. Workflow Page Layout Pattern (F18)

All four workflow pages (Research Workbench, Strategy Builder, Futures Curve, Portfolio Analytics) share a uniform two-column layout:

```
<div className="grid grid-cols-2 gap-4 h-full">
  <div className="overflow-y-auto">      {/* Left: scrollable config */}
    <Panel title="Configuration">
      {/* form fields, selectors, params */}
    </Panel>
  </div>
  <div className="overflow-hidden">      {/* Right: fixed action */}
    <Panel>
      <Button variant="amber" className="w-full">Launch / Evaluate / View</Button>
      {/* results render below after action */}
    </Panel>
  </div>
</div>
```

- `grid-cols-2` for genuine 50/50 split at any viewport (not fixed `w-96`)
- Left column scrolls independently
- Right column fixed with full-width amber action button
- Results appear below the button after the action completes

---

## 13. URL State Semantics (`useUrlState`)

```typescript
// null  = explicit delete — removes the param from URL:
setUrlState({ run_id: null })      // → URL: /portfolio (no run_id param)

// undefined = no-op — preserves existing URL param:
setUrlState({ run_id: undefined }) // → URL unchanged

// string = set value:
setUrlState({ run_id: '20260722_...' }) // → URL: ?run_id=20260722_...
```

This distinction is enforced in all callers as of F18: `CompareConfigPanel`, `CurveDateControl`, `PortfolioAnalytics`. Using `undefined` when intending to clear a param is a silent bug — always use `null` to clear.

---

## 14. Key Confirmed API Field Names (F16)

These differ from what the initial transfer packages assumed. These are the actual API field names:

| Context | Wrong assumption | Actual field |
|---|---|---|
| Run strategy name | `strategy_name` | `strategy` |
| Trade open date | `open_date` | `entry_date` |
| Trade close date | `close_date` | `exit_date` |
| Trade P&L | `pnl` | `net_pnl` |
| Trade duration | `duration` | `duration_bars` |
| Assets endpoint | `/api/market/universe` | `/api/assets` |

---

---

## 15. FEP New Components and Patterns (FEP-complete)

### 15.1 New Chart Components (FEP)

All 11 new chart components follow the exact same pattern as `CorrelationHeatmapChart.tsx` — `useRef + useEffect + echarts.init + globalThis.addEventListener + dispose`. No exceptions.

| Component | File | Purpose |
|---|---|---|
| `ContributionToRiskChart` | `components/charts/ContributionToRiskChart.tsx` | Horizontal bar — `asset_contribution_to_vol_pct` per asset |
| `WalkForwardChart` | `components/charts/WalkForwardChart.tsx` | Grouped bar — IS (amber) vs OOS (info-blue) Sharpe per fold |
| `RegimeBreakdownChart` | `components/charts/RegimeBreakdownChart.tsx` | Grouped bar per regime; colors follow regime semantics |
| `ParallelCoordinatesChart` | `components/charts/ParallelCoordinatesChart.tsx` | ECharts `parallel` type; VisualMap loss→gray→gain by Sharpe |
| `ScreePlot` | `components/charts/ScreePlot.tsx` | Bar (EVR) + line overlay (cumulative EVR), dual y-axis |
| `PCLoadingsChart` | `components/charts/PCLoadingsChart.tsx` | Horizontal grouped bars per PC, one series per PC |
| `PCTimeSeriesChart` | `components/charts/PCTimeSeriesChart.tsx` | Multi-line factor series; `fmtDate` on x-axis |
| `COTPositioningChart` | `components/charts/COTPositioningChart.tsx` | Net speculative (amber) + pct rank (info-blue area); 80th/20th percentile lines |
| `EIAInventoryChart` | `components/charts/EIAInventoryChart.tsx` | Colored bars by sign (gain=draw, loss=build); ±1σ threshold lines |

**ParallelChart registration:** `ParallelChart` and `ParallelComponent` must be registered in `echarts-setup.ts` before `ParallelCoordinatesChart` can render. This was added in FEP Inc6.

### 15.2 New Table Components (FEP)

Follow TDR-011 exactly — same pattern as `PortfolioAssetTable.tsx`.

| Component | File | Purpose |
|---|---|---|
| `ValidationSummaryTable` | `features/runs/ValidationSummaryTable.tsx` | IS vs OOS metrics; OOS column color-coded by ratio |
| `SweepResultsTable` | `features/sweeps/SweepResultsTable.tsx` | Sortable sweep results; best-Sharpe row highlighted |

### 15.3 Tooltip Dark Theme (AD-FEP-006)

All Radix `TooltipContent` uses the platform dark terminal style, applied once in `src/ui/tooltip.tsx`:
```tsx
className="z-50 overflow-hidden rounded border border-border-default bg-bg-raised text-text-primary px-2.5 py-1.5 text-xs font-mono shadow-md animate-in fade-in-0 zoom-in-95 ..."
```
This applies platform-wide. The path is `@/ui/tooltip` — NOT `@/components/ui/tooltip`.

**Accessibility requirement:** `aria-label` on `<span>` elements requires `role="img"`. Health-dot spans in `UniverseGrid` use `role="img" aria-label="..."`. Plain HTML `<select>` elements require `aria-label` when not paired with a visible `<label>`. Combobox triggers (`<button role="combobox">`) require `aria-label`.

### 15.4 Regime Attribution Pattern (AD-FEP-001)

`PortfolioRegimePanel` uses opt-in button rather than auto-fetch:

```tsx
const [shouldFetch, setShouldFetch] = useState(false)
const { data } = useRegimeAttribution(
  shouldFetch ? selectedAssetRunId : null, 4
)
// Default: "Compute Regime Attribution" button shown
// After click: setShouldFetch(true), data loads, RegimeBreakdownChart renders
```

**Rationale:** Single-worker Uvicorn saturates under 30–90s synchronous regime computation. Opt-in is the Bloomberg-standard pattern for computationally expensive exploratory analytics. `useRegimeAttributionParallel.ts` is preserved for when TD-FEP-REGIME-ASYNC ships (one import swap).

### 15.5 SweepHistory Store

```typescript
// src/stores/sweepHistory.ts
// Zustand persist — localStorage key: 'commodity-research-sweep-history'
// Stores recent sweep IDs (up to 10)
```

### 15.7 fmt.price Thousands Separator (TD-fmt-thousands — closed)

`fmt.price(value, asset)` now uses `Intl.NumberFormat('en-US')` internally. Signature unchanged. ASSET_DECIMALS lookup preserved. MINUS (U+2212) for negatives preserved.

```typescript
// Before: "4078.70"
// After:  "4,078.70"
fmt.price(4078.70, 'gold')  // → "4,078.70"
fmt.price(60.425, 'silver') // → "60.425" (no change — under 1000)
```

### 15.8 RouteErrorBoundary on All 16 Routes

`RouteErrorBoundary` added to all 16 routes in `routes.tsx` as `errorElement`. Any future unhandled chart error (e.g. ECharts receiving null data) shows a recoverable UI instead of crashing the full app. Created `src/components/layout/RouteErrorBoundary.tsx`.

**Root cause that triggered this:** Clicking the Research Workbench sidebar icon while already on `/research` with evaluation results caused `TypeError: Cannot read properties of null (reading 'value')` in ECharts `WhiskerBoxCommonMixin2`. Same-route navigation stripped query params → `asset`/`strategy` emptied for one frame → chart received null OHLCV data → candlestick array of `[null, null, ...]` → ECharts crash.

**Fix:** Null guard at top of `SignalOverlayChart` and `PriceChart` `useEffect` before any `chart.setOption()` call. Null entries filtered from candlestick data array. Commit `0d06bfd`.

```typescript
// src/lib/retry.ts
// Wraps portfolio result hooks to handle 1-3s persistence race after status → complete
export async function fetchWithRaceRetry<T>(
  fn: () => Promise<T>,
  maxAttempts = 4,
  delays = [1000, 3000, 6000, 10000]
): Promise<T>
```

Applied to all 5 portfolio result hooks: `usePortfolioSummary`, `usePortfolioEquity`, `usePortfolioRisk`, `usePortfolioCorrelation`, `usePortfolioAssets`.

---

*Last updated: Platform complete — E2E suite 114/3/0, all TD items closed (2026-08-27)*
