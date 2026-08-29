# Screen Specifications
## Commodity Systematic Research Platform

**Version:** 4.0
**Status:** Active — platform complete. All screens delivered and E2E verified (114/3/0).
**Scope:** Authoritative specification for every screen in the frontend. Layouts assume the standard tier (1440–2100px); ultrawide and laptop adaptations follow the global rules in `FRONTEND_ARCHITECTURE.md` §13 unless a screen notes otherwise. Component names reference `DESIGN_SYSTEM.md` §8. All data comes through the API endpoints in `FRONTEND_ARCHITECTURE.md` §9.2 — no screen computes anything.

Every screen specifies: purpose (the research question it answers), layout, user goals, components, interactions, datasets, and its loading / empty / error / edge-case behavior. Global defaults from `DESIGN_SYSTEM.md` §9 apply wherever a screen does not override them.

Shared shell on every screen: `SidebarNav` (left) · `TopBar` · `ContextBar` (where declared) · `ComparisonTray` (when basket non-empty) · `CommandPalette` (⌘K).

---

## S1 — Market Overview  `/market`

**Research question:** *What is the commodity universe doing, and where should I look next?*

**Purpose:** Entry point and daily orientation screen. Summarizes the full universe (6 assets today, dozens later) with enough per-asset context to pick a research target. Consumes Layer 0 only.

**Layout**

```
┌ Title: Market overview          [range: 1M ▾]  [Reload data ↺] ┐
├──────────────────────────────────────────────────────────────────┤
│ MetricGrid (universe summary, 4 cols)                            │
│  ASSETS TRACKED · LAST RELOAD · FLAGGED ANOMALIES · RUNS TOTAL  │
├──────────────────────────────────────────────────────────────────┤
│ UniverseGrid (full width, virtualized)                           │
│  asset | last | 1d% | 1w% | 1m% | realized vol | 20d sparkline   │
│        | volume | data health ● | updated                        │
├──────────────────────────────────────────────────────────────────┤
│ Panel: Return comparison        │ Panel: Volatility snapshot     │
│ (normalized line chart, range-  │ (bar chart, 63d realized vol   │
│  selected window, all assets)   │  per asset, tone-neutral)      │
└──────────────────────────────────────────────────────────────────┘
```

**User goals:** scan the universe in <10s; spot movers/regime shifts; confirm data freshness; jump into an asset.

**Components:** `MetricGrid`, `UniverseGrid`, `ChartFrame` + multi-series line (normalized to 0% at window start, series palette), bar chart, range preset control (writes `?range=`).

**Interactions:** row click → `/market/:asset`; row hover prefetches the asset summary; chart legend chip toggles series; "Open in Workbench" row action (context-carrying); ⌘K reachable as "Market overview".

**Datasets:** `GET /api/assets`, `GET /api/assets/{a}/summary` (batched by the API into one universe payload), `GET /api/data/status` (health dots — returns `last_ingestion: null` from backend; LAST RELOAD is frontend-derived and persists in localStorage after `POST /api/system/ingest` completes).

**Reload data button (F18):** Button renamed from "Re-ingest all" to "Reload data". Tooltip explains: reads from local Parquet files only — does not download from Yahoo Finance. Fresh data requires running `acquire_data.py` manually. On click: fires `POST /api/system/ingest` with `{ asset: null }`, shows "Ingesting..." loading state, invalidates dataStatus + assets queries on success.

**UniverseGrid (F18):** Implemented as plain HTML `<table>` not DataGrid (TDR-011). Uses `w-full table-fixed` with explicit column widths.

**States:**
- *Loading:* metric-grid skeleton + 6-row table skeleton + chart skeletons.
- *Empty (no ingested data):* full-screen `EmptyState`: "No market data yet. Ingest the universe to begin." → primary action "Open Data Manager". This is the first-run experience; it must be unmissable.
- *Error:* universe payload failure → screen-level `ErrorState` with retry (nothing else renders without it); per-panel errors for the two charts stay panel-scoped.
- *Edge cases:* partially ingested universe renders available assets and gray "not ingested" rows with per-row ingest action; stale data (>3 business days old) shows warn-toned updated timestamps; an asset whose validation flagged anomalies shows a warn health dot linking to Data Manager filtered to that asset.

---

## S2 — Asset Detail  `/market/:asset`

**Research question:** *What does this market look like, and is its data trustworthy for research?*

**Purpose:** Deep view of one asset: full price history, contract metadata, data-quality evidence. The launchpad into the Workbench. Consumes Layer 0 (+ regime badge from Layer 5 in P2).

**Layout**

```
Breadcrumb: Market / Gold
┌ GOLD · GC=F · COMEX · USD/troy oz     [RegimeBadge P2]           ┐
│ ContextBar: [asset: gold] [range: 2015-01-01 → 2026-07-06]       │
├──────────────────────────────────────────────────────────────────┤
│ MetricGrid (6): LAST · 1M% · 1Y% · REALIZED VOL 63D · AVG VOLUME │
│                 · BARS AVAILABLE                                  │
├──────────────────────────────────────────────────────────────────┤
│ ValidationRibbon (only if flags exist in range)                  │
├──────────────────────────────────────────────────────────────────┤
│ PriceChart (candle/line toggle, volume pane, dataZoom, ~60vh)    │
│   overlay picker: quick EMA/SMA presets (display-only re-request │
│   of Layer 1 compute — indicators come from the API, not the UI) │
├───────────────────────────────┬──────────────────────────────────┤
│ Panel: Return distribution    │ Panel: Contract metadata          │
│ (ReturnHistogram, daily logs) │ multiplier · tick size/value ·    │
│                               │ exchange · unit  (assets.yaml)    │
├───────────────────────────────┴──────────────────────────────────┤
│ Panel: Recent runs on this asset (RunTable, compact, 5 rows)     │
│                                    [→ all runs for gold]         │
└──────────────────────────────────────────────────────────────────┘
Primary action (top right): [Open in Workbench →]  carries context
```

**User goals:** judge the market's character (trend, vol, gaps); verify data quality before spending research time; carry the asset into research.

**Datasets:** `GET /api/assets/{a}/ohlcv?from&to&downsample=view`, `/summary`, `/api/system/data-status?asset=`, `POST /api/features/compute` (overlay presets), `GET /api/runs?asset=`.

**Interactions:** date-range edits update URL + refetch; zoom-in past the downsample threshold refetches the window at full resolution; histogram brush selects a return band and highlights those dates on the price chart (connected crosshair group); "Open in Workbench →" → `/research?asset=gold` — ResearchWorkbench reads `?asset=` on mount and pre-selects the asset.

**Critical (F18):** `AssetDetail.tsx` must NOT have a `useEffect` cleanup that deletes URL params on unmount. This was the root cause of "Open in Workbench" never working (the cleanup fired after navigation and deleted `?asset=` from the Workbench URL). The cleanup function has been permanently removed.

**Recent runs table (F18):** Plain HTML `<table>` (not DataGrid). Shows last 5 runs for this asset. "→ All runs for {asset}" navigates to `/runs?asset={asset}` (pre-filters Run Explorer).

**States:**
- *Loading:* metrics first, chart skeleton with ghost axes, panels after.
- *Empty:* asset known but not ingested → `EmptyState` "Gold has not been ingested" + ingest action inline.
- *Error:* OHLCV failure → chart-panel `ErrorState`; metadata panel still renders (different endpoint). Unknown asset slug → designed 404 → Market Overview.
- *Edge cases:* ranges spanning suspected roll gaps render honest line breaks (null policy); OI column absent (per backend assumption 4) is simply not shown rather than shown empty; very short histories (<63 bars) suppress the realized-vol metric with an em-dash + tooltip "insufficient bars (63 required)".

---

## S3 — Research Workbench  `/research`

**Research question:** *Does this signal contain predictive information on this asset?*

**Purpose:** The core screen of the platform: build a feature set, generate a raw signal, evaluate it (IC/ICIR/decay/turnover), and pass — or fail — the IC Gate. Implements backend workflow steps 2–4 and ADR-007's gatekeeping rule as interface. Consumes Layers 0, 1, 2.

**Layout** (F18: uniform grid-cols-2 workflow layout — TDR-015)

```
┌────────────────────────────┬───────────────────────────────────────┐
│ CONFIG (left, scrollable)  │ EVIDENCE CANVAS (right)               │
│                            │                                       │
│ Asset selector             │ RegimeContextChip (term structure)    │
│ Date range (1Y/3Y/5Y/MAX)  │                                       │
│ Strategy picker + params   │ SignalOverlayChart:                   │
│ Indicator picker           │   Price pane (candlestick)            │
│ [selected chips]           │   Signal pane (amber line)            │
│                            │   ■ Long ■ Short band legend          │
│ [Evaluate signal]          │   Position shown as markArea bands    │
│  · hides when fresh        │   (Long=green 8%, Short=red 8%)       │
│  · blurs when stale        │                                       │
│                            │ ICDecayChart {1,2,5,10,20 bars}       │
│                            │ IC · ICIR · TURNOVER · EVAL WINDOW    │
│                            │ FeatureSpecTable (plain HTML table)   │
├────────────────────────────┴───────────────────────────────────────┤
│ ICGateStrip — verdict, IC/ICIR hero values, threshold text        │
│ MEANINGFUL SIGNAL → [Configure backtest →]  (?evaluation=JSON)   │
│ WEAK SIGNAL → [Configure backtest →] with caution note           │
│ SIGNAL LIKELY NOISE → "Backtest without evaluation" (?evalOverride=1) │
└────────────────────────────────────────────────────────────────────┘
```

**User goals:** iterate feature/param combinations rapidly; see whether the signal is noise before spending a backtest; understand *where* predictiveness lives (horizon decay); carry a validated configuration into the Strategy Builder.

**Components:** `IndicatorPicker` (catalog-driven, scales to hundreds of indicators), `StrategyPicker` + `ParamForm` (schema-driven), `SignalOverlayChart`, `ICRollingChart`, `ICDecayChart`, `MetricGrid`, `TurnoverChart`, `FeatureSpecTable`, `ICGateStrip`.

**Interactions (F18 updated):**
- **Evaluate button behavior:** Button *hides* when the current config hash matches the last evaluation (fresh state — no re-eval needed). Button shows with a "Results may be stale" overlay/blur when config changes post-evaluation.
- Config changes mark the canvas *stale* rather than clearing it — the researcher sees prior evidence while deciding whether to re-evaluate.
- "Evaluate signal" runs compute → generate → evaluate as one chained mutation. Results are cached by param hash, so revisiting a tried configuration is instant.
- **IC Gate URL contract (F17):**
  - PATH A: `|IC| ≥ 0.02` → "Configure backtest →" navigates to `/backtest/new?asset=...&strategy=...&params=...&evaluation=JSON.stringify(result)`. Evaluation is persisted with the run artifact.
  - PATH B: "Backtest without evaluation — will be recorded" → navigates to `/backtest/new?asset=...&strategy=...&params=...&evalOverride=1`. Run artifact records `signal_evaluation: null`.
- **RegimeContextChip** (above evidence canvas): shows current term structure regime for selected asset (e.g., "Term structure: BACKWARDATION −4.36%/yr").
- **SignalOverlayChart:** two panes — price (candlestick) and signal (amber line). Position state shown as markArea bands on signal pane (not separate pane — TDR-013). DataZoom covers both panes simultaneously.
- Full configuration serializes to URL — a Workbench state is a shareable link.
- **ICRollingChart:** wired in FEP Inc3 (`useRollingIC` hook). Shows live rolling IC data after evaluation completes. Requires `GET /api/signals/rolling-ic?asset=&strategy=&params=&window=63` which was shipped in EM6. The placeholder from F5 is removed.
- **FeatureSpecTable:** plain HTML `<table>` (not DataGrid).

**FEP layout change (Research Workbench):**
- Pre-evaluate: grid-cols-2 (left: config rail; right: "Evaluate signal" amber button)
- Post-evaluate: full-width results, "← Modify signal" button top-left
- Blur overlay on param change: REMOVED. Previous results stay fully visible; Evaluate button is the re-evaluation trigger.
- Asset or strategy change → resets to config view (pre-evaluate state)
- Param-only change → does NOT reset (researcher can tweak and re-evaluate without losing layout)

**Signal window guidance (confirmed E2E + backend):**

| Strategy | Minimum window | Reason |
|---|---|---|
| EMA Crossover (EMA-200) | 3Y+ | 200-bar warmup; only ~16 valid bars on 1Y |
| Donchian Breakout | 3Y+ | IC ≈ 0.014 noise on 1Y (196 valid bars) |
| COT Positioning | 3Y+ | ~52 weekly bars on 1Y insufficient for rolling percentile |
| EIA Inventory | 3Y+ | Seasonal average needs 5-year history for stable z-scores |
| Carry / Gold | Any | Gold is structurally in contango → flat signal → IC null. Correct institutional finding. Carry is meaningful for energy/agricultural commodities with regime-switching term structure. |
| Momentum, RSI Reversion | 1Y | Fast signals; no warmup issue |

Near-zero or null IC on a 1-year window is **correct expected behavior** for slow-moving indicators and alternative data signals — not a bug. The 1-year default is appropriate for fast signals only.

**States:**
- *Loading (initial):* config rail loads from catalog; canvas shows an instructional `EmptyState`: "Assemble features and a signal, then evaluate. Evaluation must precede backtesting." — doctrine stated on first contact.
- *Empty (no evaluation yet):* canvas placeholder as above; ICGateStrip renders locked state.
- *Error:* evaluation-chain failure reports the failing stage inline in the config rail ("Signal generation failed: momentum_20 not in feature frame") with the API error detail; canvas keeps prior results dimmed.
- *Edge cases:* warmup NaNs (EMA-200 on short ranges) → API validation error surfaced as a range warning "range provides 180 bars; ema_200 needs 200+"; evaluation window shorter than the 63-bar rolling IC window suppresses ICIR with an explanatory em-dash; near-zero-variance RawSignal (degenerate params) → warn note "signal is nearly constant; IC undefined/unstable".

---

## S4 — Strategy Builder  `/backtest/new`

**Research question:** *Under exactly what assumptions am I about to test this signal?*

**Purpose:** Compose and launch a backtest: strategy + params, asset + range, costs, sizing, capital — every assumption explicit before execution, mirroring `params.json`. Consumes Layers 0–3.

**Layout**

```
ContextBar: [asset ▾] [range ▾]
┌───────────────────────────────┬──────────────────────────────────┐
│ CONFIGURATION (form column)   │ RUN PREVIEW (sticky summary)     │
│                               │                                  │
│ 1 Signal                      │  gold · ema_crossover            │
│   StrategyPicker              │  50/200 · thresh 0.0             │
│   ParamForm (schema-driven)   │  2015-01-01 → 2026-07-06         │
│   Evaluation status chip:     │  2,890 bars                      │
│   [IC 0.061 · strong ✓]  or   │  ─────────────────────────────   │
│   [no evaluation — flagged]   │  fixed notional $100,000         │
│                               │  commission $5.00 / trade        │
│ 2 Data                        │  slippage 1 tick ($10.00)        │
│   AssetSelector · DateRange   │  initial capital $1,000,000      │
│                               │  ─────────────────────────────   │
│ 3 Execution assumptions       │  timing: Close[t] → Open[t+1]    │
│   costs (commission,          │  (fixed — ADR-002) ⓘ            │
│   slippage ticks) · sizing    │                                  │
│   (fixed notional P1;         │  [Launch backtest]               │
│   vol-scaled section P2) ·    │                                  │
│   initial capital             │                                  │
└───────────────────────────────┴──────────────────────────────────┘
```

**User goals:** launch with zero ambiguity about assumptions; reuse prior configurations; understand fixed conventions (timing rule shown as immutable fact, not an option).

**Components:** `StrategyPicker` (renders as individual strategy **buttons**, not a combobox/dropdown — confirmed by E2E `clickStrategyButton()` via `getByRole('button', { name })`), `ParamForm`, `AssetSelector`, `DateRangePicker`, `NumberInput` (mono, unit slots), evaluation status chip, sticky preview `Panel`, primary `Button` with pending state.

**IC Gate — Launch button is always visible (never disabled):** The Launch Backtest button renders in all three IC Gate states. The gate is an information card, not a hard block:
- PATH A (`?evaluation=JSON`): card shows IC/ICIR chip — "Signal evaluated: IC X.XXX · ICIR X.XXX"
- PATH B (`?evalOverride=1`): card shows override warning — recorded in run metadata as `signal_evaluation: null`
- Direct navigation (no URL eval params): card shows "No evaluation found — Evaluate in Research Workbench first"

In all three states the Launch button is present and functional. The IC Gate is doctrine surfaced as UI — it informs and records, it does not block.

**Layout (F18):** grid-cols-2 (TDR-015). Left column: scrollable config (StrategyPicker, AssetSelector, ParamForm, BacktestConfig). Right column: fixed (Signal Evaluation card, Launch Backtest amber button full-width). Left column scrolls independently; right is sticky.

**IC Gate evaluation card (right column):**
- PATH A (`?evaluation=JSON`): shows IC/ICIR chip + "Signal evaluated: IC X.XXX · ICIR X.XXX" — evaluation will be persisted with run
- PATH B (`?evalOverride=1`): shows "This backtest will launch without a signal evaluation. The override will be recorded in run metadata."
- Direct navigation (no evaluation URL param): shows "No evaluation found — Evaluate in Research Workbench first" + "Back to Workbench →" link

**Interactions (F18 updated):** arriving from the Workbench via "Configure backtest →" pre-fills `?asset=`, `?strategy=`, `?params=`, `?evaluation=JSON`. Arriving via "Backtest without evaluation" pre-fills same but `?evalOverride=1`. Direct navigation shows selectors without evaluation. Launch fires `POST /api/backtest/run` → poll status → navigate to `/runs/{artifactId}` (`poll_` prefix stripped). The run artifact records `signal_evaluation` from the evaluation JSON (PATH A) or `null` (PATH B/direct).

**Datasets:** `GET /api/strategies` (schemas + defaults from strategies.yaml), `GET /api/system/config` (cost/sizing/capital defaults), evaluation by reference, `GET /api/runs/{fromRun}` when cloning.

**States:**
- *Loading:* form skeleton; preview populates as fields resolve.
- *Empty:* fresh arrival without context → defaults from config with a hint chip "Tip: evaluate in the Workbench first" linking back; the launch path without evaluation stays available but flagged (the gate is doctrine-with-override, not a hard wall — matching the backend's `Optional[SignalEvaluation]`).
- *Error:* Zod client validation inline per field; API `field_errors` map back onto fields; launch failure (e.g., asset not ingested) → in-place error above the button with the remedy link.
- *Edge cases:* range with insufficient warmup bars for the strategy's slowest indicator → blocking field error with the exact bar math; duplicate of an existing run's exact params → non-blocking notice "identical to run 20260701_… → view instead"; capital/notional inconsistencies (notional > capital) → warning, not block (leverage is legitimate in futures).

---

## S5 — Run Explorer  `/runs`

**Research question:** *What have I already tried, and what worked?*

**Purpose:** The experiment memory. Every run ever executed, searchable and comparable. Consumes RunRegistry (Layer 3) + headline metrics (Layer 4).

**Layout**

```
┌ Title: Runs (247)          [search q]  [strategy ▾] [asset ▾]    ┐
│                            [status ▾]  [sort: Sharpe ▾] [⬇ CSV]  │
├──────────────────────────────────────────────────────────────────┤
│ RunTable (full width, virtualized, selection column)             │
│ ☐ | status | run_id | strategy | asset | span | Sharpe | maxDD  │
│   | totRet | IC band | trades | executed_at                      │
├──────────────────────────────────────────────────────────────────┤
│ ComparisonTray (docked): [3 selected]  [Compare →] [Clear]       │
└──────────────────────────────────────────────────────────────────┘
```

**User goals:** find prior work fast; rank by any metric; assemble comparison sets; prune failed/junk runs.

**Interactions:** all filters/sort/search in URL; row click → Run Detail (hover prefetch); checkbox → comparison basket (`c` on focused row); row overflow menu: Compare · Re-run with changes · Delete (confirm dialog: "Run artifacts are immutable and deletion is permanent"); grouping by strategy or asset via toolbar toggle (collapsible group headers with per-group best-Sharpe summary).

**Datasets:** `GET /api/runs?...` (registry metadata + metrics.json headline fields).

**States:**
- *Loading:* table skeleton; filter chips render immediately from URL.
- *Empty (no runs):* `EmptyState`: "No runs yet. Evaluate a signal in the Workbench, then launch your first backtest." → Workbench action.
- *Empty (filtered):* "No runs match these filters" + clear-filters action.
- *Error:* screen-level `ErrorState` (registry list is the screen).
- *Edge cases:* `failed` runs render with crit badge and remain clickable (failure detail lives on Run Detail); `running` rows live-update status via the status poll; runs pre-dating a metrics schema addition render missing metrics as em-dashes, never zeros.

---

## S6 — Run Detail  `/runs/:runId?tab=`

**Research question:** *How did this strategy behave, and can I trust and reproduce the result?*

**Purpose:** The complete record of one backtest across five tabs. Consumes Layers 3 + 4 artifacts (immutable → cached forever).

**Header (all tabs, F17 redesign):**

```
← Run Explorer                                          🗑  Compare →
[complete]  GOLD · ema_crossover · 2010-01-04 → 2026-07-02
            20260724_162655_ema_crossover_gold  📋
```

- Single-line primary: status badge + `ASSET · strategy · from → to`
- Second line: clean artifact run ID in `font-mono text-xs text-text-secondary` + clipboard icon (copies artifact ID to clipboard)
- poll\_ prefix is stripped from displayed ID (`runId.replace(/^poll_/, '')`)
- "← Run Explorer" back link above the header
- Trash (🗑) and Compare (→) actions top-right

**Tabs: Overview | Signal Quality | Validation | Trades | Artifacts** (URL: `?tab=`) ← Validation tab added FEP Inc3

Note: `BacktestMetadata` records `git_sha` (8-char SHA), `dirty_flag` (bool), and `package_versions` (dict). Artifacts tab displays all three for reproducibility.

**Tab: Overview** — KPI row: SHARPE (3dp), SORTINO, CALMAR, MAX DD, TOTAL RETURN, CAGR; secondary row: WIN RATE, PROFIT FACTOR, AVG TRADE (N bars), TURNOVER, AVG WIN, AVG LOSS, LARGEST WIN, LARGEST LOSS. `EquityCurveChart` with auto-scaling equity curve (min:'dataMin') and attached drawdown pane. Hover shows BOTH equity value AND drawdown % with colored dots. Baseline markLine labeled with `fmt.compactUsd()`. Rolling Performance 63-day chart (Rolling Sharpe + Rolling Drawdown dual-axis). `ReturnDistribution` histogram. Contract Specs panel.

**Tab: Signal Quality** — IC band shown as inline chip beside IC value (not standalone banner). IC / ICIR / TURNOVER metrics. ICDecayChart {1,2,5,10,20 bars} with staggered threshold labels. `ICRollingChart` wired via `useRollingIC` (FEP Inc3 — endpoint EM6). Only populated for PATH A runs. PATH B/direct: "No signal evaluation recorded — Launch from Research Workbench to record IC quality here."

**Tab: Validation (FEP — EM5)** — Walk-forward validation of the same (asset, strategy, parameters) as the run. Layout: grid-cols-2 pre-launch (pre-populated asset/strategy/params from run metadata, editable n_splits/embargo_bars) → full-width results post-launch. `ValidationLaunchRequest` has no `run_id` — launched independently with the same parameters. On complete: `WalkForwardChart` (IS vs OOS Sharpe per fold) + `ValidationSummaryTable` (IS/OOS metrics with color-coded OOS column).

**Tab: Trades** — direction filter: All / Long / Short (server-side `?direction=long/short`). Force Closed toggle (`?force_closed=true`). Each filter combo cached independently at `staleTime: Infinity`. Trade KPI row updates when filter changes. `TradeTable` (plain HTML `<table>`): #, DIRECTION, ENTRY, EXIT, DURATION (N bars), ENTRY PX, EXIT PX, GROSS P&L, COST, NET P&L, RETURN.

**Tab: Artifacts** — Provenance: git SHA + package versions. Run Parameters: full JSON of `params.json`. Signal Evaluation: null (PATH B) or IC/ICIR/decay data (PATH A).

**Datasets:** `GET /api/runs/{runId}`, `GET /api/runs/{runId}/series`, `GET /api/runs/{runId}/trades?direction=&force_closed=` (staleTime: Infinity per filter combo).

**States:**
- *Loading:* header from list-cache instantly (prefetch), tab panels hydrate independently.
- *Running:* status panel replaces tabs — elapsed time, staged progress, live status poll; tabs appear as artifacts land.
- *Failed:* header crit badge; body renders exception summary + parameter snapshot + "Re-run with changes" (failures are research information — `FRONTEND_ARCHITECTURE.md` §11).
- *Error/edge:* unknown run → designed 404 → Run Explorer; partially written artifacts (crash mid-save) render available tabs and per-tab `ErrorState` for missing ones; deleted-while-viewing → toast + redirect to Explorer.

---

## S7 — Run Comparison  `/runs/compare?ids=`

**Research question:** *Which configuration is better, and where do they differ?*

**Purpose:** Side-by-side judgment of 2–4 runs (parameter sweeps, cross-asset checks, before/after iterations). Consumes Layers 3, 4 via the compare endpoint.

**Layout**

```
┌ Comparing 3 runs                    [+ add run] [swap baseline ▾]┐
│ chips: [A ema 50/200 gold ×] [B ema 20/100 gold ×] [C … ×]       │
├──────────────────────────────────────────────────────────────────┤
│ EquityCurveChart — overlaid, normalized to % of initial capital, │
│ series palette A=amber first; shared crosshair                   │
├──────────────────────────────────────────────────────────────────┤
│ MetricDeltaTable: metric rows × run columns; best-per-row        │
│ highlighted; Δ vs baseline column                                 │
├───────────────────────────────┬──────────────────────────────────┤
│ Rolling Sharpe overlay        │ Drawdown overlay (inverted)      │
├───────────────────────────────┴──────────────────────────────────┤
│ Parameter diff panel: only fields that differ, per run, mono     │
└──────────────────────────────────────────────────────────────────┘
```

**User goals:** pick a winner defensibly; see *when* one run outperformed (regime dependence); confirm exactly which parameters changed.

**Interactions:** `?ids=` is the source of truth (basket seeds it); baseline swap re-anchors the Δ column; "+ add run" opens a palette-style run search; chip removal updates URL; legend hover isolates a series across all three charts simultaneously.

**Datasets:** `POST /api/runs/compare {ids}` (aligned series + metric matrix), individual run caches reused for the diff panel.

**States:**
- *Loading:* chips + table skeleton; charts after (aligned payload is the slow call).
- *Empty:* 0–1 ids → `EmptyState` "Select at least two runs to compare" → Run Explorer.
- *Error:* one invalid id → that chip renders in error tone with remove action, comparison proceeds with the valid rest.
- *Edge cases:* non-overlapping date ranges → comparison restricted to the intersection with an explicit notice ("comparing 2018-03-01 → 2024-11-30, the common window"); mixed assets compare in normalized % terms only, with a note that Phase-1 fixed-notional PnL is not risk-comparable across assets (surfacing the ADR-005 caveat where it matters); a failed run in the set renders its column with em-dashes.

---

## S8 — Data Manager  `/system/data`

**Research question:** *Is my research data complete, current, and clean?*

**Purpose:** Ingestion control and validation evidence — the UI face of Layer 0's data-quality discipline.

**Layout:** asset status table (asset · bars · span · last ingested · flags count · [Re-ingest]) over a validation log grid (timestamp · asset · date · violation type · detail), filterable by asset/type; log rows link to the offending date range on Asset Detail.

**Interactions:** per-asset and ingest-all mutations with staged progress rows (fetch → validate → normalize → store, mirroring the Layer-0 pipeline); completion invalidates OHLCV/summary caches.

**States:** first-run empty state is the platform's true entry ("Ingest the universe to begin"); ingest failure renders per-asset inline with the DataValidationError detail; concurrent ingest of the same asset disabled while running. Edge: raw file present but validation-rejected → asset shows crit health with "view violations".

---

## S9 — Configuration  `/system/config`

**Purpose:** Read-only, secret-free view of the merged `config.yaml` / `assets.yaml` / `strategies.yaml` the API is running with — the "what assumptions govern this platform" reference. Structured mono tree per file, copyable, with source-file labels. Edits happen in the repo, not the UI (immutability of the config path is stated on-screen). States: trivial; API error → screen `ErrorState`.

---

## S10 — Commodity Intelligence  `/intelligence`  *(Phase 2 — F9–F11 complete)*

**Research question:** *What is this market's term structure telling me?*

**Purpose:** Term-structure workstation on contract-level data (Layer 5): curve shape, regime, basis, roll yield. Never mixes with continuous-series research (ADR-001 boundary preserved: this module never links into Strategy Builder with contract data).

**Layout (F18: grid-cols-2 config → View Curve → full-width results — TDR-015):**

```
Config state (half-half):
┌──────────────────────────────┬───────────────────────────────────┐
│ ASSET selector               │ [View Curve →] (amber, full width)│
│ CONTRACTS (2–6 dropdown)     │                                   │
│ HISTORY: [1Y] [3Y] [5Y] [MAX]│                                   │
└──────────────────────────────┴───────────────────────────────────┘

Results state (full-width, after View Curve click):
[← Change config]    [Compare assets →]
Observation date: [Latest] [dd-mm-yyyy input] (clicking exits Latest mode)
KPI row: REGIME · FRONT PRICE · SLOPE %/yr · ROLL YIELD %/yr · BASIS
Forward Curve chart (bar + amber line, category x-axis with contract tickers)
Term Structure History chart:
  - top pane: Slope %/yr over time (regime markArea bands: amber=Contango, green=Backwardation)
  - bottom pane: Roll Yield %/yr over time
  - trigger:'axis' tooltip shows BOTH values for same date
  - 1Y/3Y/5Y/MAX buttons above this chart change the date range shown
  - Legend: Contango | Backwardation
Contract Inventory table (plain HTML): TICKER · SETTLE · DTD · DATA DATE
```

**Key behaviors (F17/F18 confirmed):**
- History period (1Y/3Y/5Y/MAX) changes the Term Structure History chart date range ONLY — does NOT change the KPI row (which always shows the observation date snapshot)
- Observation date scrubber: "Latest" reloads current curve; clicking date input exits Latest mode and triggers historical snapshot fetch
- "Compare assets →" → `/intelligence/compare?assets={asset}&n_contracts={n}`
- Forward Curve chart: y-axis starts at 0.00, shows contract tickers on x-axis
- Sparse curves (<4 contracts) show warning: "Limited contract coverage — Slope and roll-yield analytics require at least 4 contracts"

**Datasets:** `GET /api/curves/available`, `GET /api/curves/{asset}/snapshot?n_contracts=N&observation_date=`, `GET /api/curves/{asset}/history?from_date=&to_date=&n_contracts=N`

---

## S10a — Curve Comparison  `/intelligence/compare`  *(Phase 2 — F11 complete)*

**Research question:** *How do these commodities' term structures compare?*

**Layout:** Left panel: asset checklist (max 4; 5th disabled when 4 selected) + contracts dropdown. Right: Normalized Forward Curves chart (value x-axis = days to delivery, y-axis = % from front contract price, zero reference dashed line) + Regime Comparison table (ASSET / REGIME badge / FRONT PRICE / SLOPE / ROLL YIELD).

**Datasets:** `GET /api/curves/{asset}/snapshot` in parallel for each selected asset via `useQueries` (staleTime: 5m).

---

## S11 — Portfolio Analytics  `/portfolio`  *(Phase 3 — F12–F15 complete)*

**Research question:** *How do my strategies behave as a book?*

**Purpose:** Multi-asset portfolio backtest across all 6 commodity assets using `MultiAssetRunner` (Layer 3) + `PortfolioPerformanceEngine` (Layer 4).

**Layout (F18: grid-cols-2 — TDR-015):**

```
Config state:
┌──────────────────────────────┬────────────────────────────────────┐
│ PORTFOLIO CONFIGURATION      │ [Launch Portfolio Backtest]        │
│                              │ (amber, full width)                │
│ Date range (1Y/3Y/5Y/MAX)    │                                    │
│ From/To date inputs          │ Running... 18s                     │
│ (default: 2015-01-01 →today) │ "Runs all 6 assets with {strategy} │
│ Strategy dropdown            │  strategy. ~30-60s typical."       │
│ Fixed Notional / Vol Scaled  │                                    │
│ Initial Capital (per asset)  │                                    │
│ "Running on all 6 assets ·   │                                    │
│  Total: $6.00M"              │                                    │
└──────────────────────────────┴────────────────────────────────────┘

Results (below config after completion, or via run selector):
Portfolio Analytics header:
  [▸] 20260724_170138_portfolio_ema_crossover  📋     [🗑 Delete run] [+ New run]
  SHARPE (3dp) · MAX DD · TOTAL RETURN · CAGR · PORTFOLIO VOL

Portfolio Equity Curve:
  Auto-scales around $6M baseline; drawdown pane attached below labeled "Drawdown"
  Hover shows BOTH equity value AND drawdown % with colored dots
  "Inner-join alignment: 2010-01-04 → 2026-07-02 · 4116 trading days" note below

Asset P&L Attribution (plain HTML table):
  ASSET · P&L (USD) · P&L (%)
  Source: absolute_pnl_by_asset ONLY (never asset_contributions)

Per-Asset Sharpe Ratio (horizontal bar chart, min:null, green=positive/red=negative)

Strategy Realized Vol:
  Per-asset %/yr + portfolio %/yr
  Label: "Strategy P&L volatility — not commodity price volatility"

Per-Asset Performance ▼ (collapsible):
  6-row table: Sharpe / Max DD / Return / Win Rate / Trades
  "View →" links → /runs/{assetRunId} (requires asset_run_ids in PortfolioAssetsResponse)

Regime Attribution (FEP EM8 — after Per-Asset Performance, before Risk):
  "Compute Regime Attribution" opt-in button (AD-FEP-001)
  After click: asset dropdown (populated from asset_run_ids), RegimeBreakdownChart
  "Portfolio Combined" is first option (value: __portfolio__) → uses compute-portfolio endpoint
  Shows Sharpe + Total Return per regime (Contango/Backwardation/Flat)
  Coverage summary chips below chart
  If asset_run_ids absent (pre-EM3 run): graceful empty state
  Per-asset dropdown label: "Gold — Flat" (AssetDisplayName + dominant regime)

Risk section:
  Risk Metrics KPI row: VAR 95% · VAR 99% · ES 99% · DIVERSIFICATION
  "Historical simulation VaR — realized strategy P&L over 252 days. Positive values = loss magnitudes."
  ContributionToRiskChart (horizontal bar): asset_contribution_to_vol_pct per asset
  Per-Asset VaR 99% (horizontal bar chart, all red, min:0)
  Notional Exposure: GROSS NOTIONAL · NET NOTIONAL
  Kupiec backtesting validation row: DAYS TESTED · EXCEPTIONS 99% · EXCEPTION RATE · KUPIEC p-VALUE · CALIBRATION

Correlation section:
  Strategy Return Correlations (CorrelationHeatmapChart 6×6, VisualMap -1 to +1)
  Avg Correlation · Most correlated pair · Least correlated pair
  Rolling Correlations — Top 5 Pairs (63-day / 126-day toggle in title bar chip)
  Shows top 5 pairs by absolute correlation with colored lines
  Hover: date + all 5 pair values formatted to 3dp with colored dots
```

**Confirmed section order (E2E verified):** KPI row → Portfolio Equity Curve → Asset P&L Attribution → Per-Asset Sharpe → Strategy Realized Vol → Per-Asset Performance (collapsible) → Regime Attribution → Risk section → Correlation section.

**Backend type notes:**
- `absolute_pnl_by_asset` is ALWAYS displayed — `asset_contributions` is numerically unstable near zero and is NEVER shown in the UI
- Portfolio equity baseline = `initial_capital_total` ($6M for 6 assets × $1M each)
- All 7 portfolio artifacts persist to disk (EM3 closed E6) — `/equity`, `/risk`, `/correlation`, `/summary`, `/assets`, `/positions`, `/regime_attribution` all survive server restart. The pre-EM3 graceful degradation message is no longer rendered.
- Rolling correlation lookup: always `min(a,b), max(a,b)` alphabetically (upper-triangle only from API)

**Run selector (header):** Recent runs from `GET /api/portfolio/runs`. Shows clean strategy name (poll\_ prefix stripped) + colored total_return %. Auto-selects first run on initial load when `?run_id=` not in URL.

**Datasets:** All portfolio endpoints per the API inventory in FRONTEND_ARCHITECTURE.md §9.2.

## S11a — Risk  `/portfolio/risk`  *(Phase 3 — backend complete)*

**Backend type (concrete):** `RiskReport`. Key fields:
- `portfolio_var_95/99`: positive USD loss magnitude (historical simulation, 252-day lookback default)
- `portfolio_var_95/99_pct`: fraction of `initial_capital_total`
- `portfolio_es_95/99`: Expected Shortfall (CVaR) — always ≥ VaR at same confidence
- `asset_var_95/99`: per-asset dict
- `avg_gross/net_notional_by_asset`: mean |position| / signed position over active trading days
- `total_avg_gross_notional`: sum across all assets
- `portfolio_diversification_benefit`: sum(asset_var_99) / portfolio_var_99 — confirmed 2.23× on real data

**Real data numbers:** VaR95 $31,948 (0.53%), VaR99 $44,490 (0.74%), ES99 $99,095, total avg gross notional $600,000 (6 × $100K).

**Display notes:** All VaR/ES are **positive USD loss magnitudes** (not negative). Label as "Daily VaR (99%): $44,490" not "−$44,490". VaR is backward-looking (realized strategy P&L history), not forward-looking — label "Historical VaR (252-day)". Confidence-level toggle in `?confidence=` URL param. NaN when < 20 observations — render em-dash with tooltip.

Historical VaR (95/99) and ES on the composed portfolio, gross/net notional exposure by asset (USD notional, not contract count — the backtester already works in USD), exposure-over-time chart. Empty/edge states inherit S11's composition dependency.

## S11b — Cross-Asset Analytics  `/portfolio/cross-asset?window=`  *(Phase 3 — backend complete)*

**Backend type (concrete):** `CorrelationReport`. Key fields:
- `correlation_matrix`: full symmetric nested dict `[asset_a][asset_b]` — all pairs including diagonal (1.0)
- `rolling_correlations_63/126`: **upper-triangle only** (`a < b` alphabetically). API must symmetrize before returning (the backend stores only upper triangle to save memory — TD-M17-A). Always look up as `a, b = min(x,y), max(x,y)`.
- `realized_vol_by_asset`: **strategy P&L volatility** (2–8%/yr for EMA 50/200), NOT commodity price vol (15–60%/yr). Label explicitly as "Strategy Realized Vol (%/yr)" — never "Asset Volatility".
- `avg_pairwise_correlation`, `most/least_correlated_pair`: tuple (asset_a, asset_b, value), alphabetically ordered

**Real data numbers:** Gold-Silver corr 0.65, WTI-Brent corr 0.62 (strategy returns — lower than price correlations due to frequent flat periods; rolling 63-day WTI-Brent reaches 0.84–0.96 at end of sample confirming structural relationship). avg_pairwise 0.12.

**Important framing note for UI copy:** "These are strategy return correlations (P&L / initial capital), not commodity price return correlations. Strategies with frequent flat periods show lower static correlation than the underlying commodity prices. Rolling correlation charts show the structural relationship more clearly." — this note appears in the header or as a tooltip on the heatmap.

`CorrelationHeatmap` (63/126d window toggle in `?window=`) over universe returns; cell click → pair drill-down panel (rolling correlation line + dual normalized price chart); strategy vol table ("Strategy Realized Vol (%/yr)" column header, explicit). Edge: assets with insufficient overlap render gray cells with tooltips "insufficient overlap for rolling window", not zeros.

---

---

## S11c — Data Manager  `/system`  *(rebuilt FEP EM10+EM13)*

**Research question:** *Is my research data complete, current, and clean?*

**Purpose (FEP rebuild):** Asset-level data quality control. Three sections per asset: QC report, COT positioning (where available), EIA inventory (where available). Grid-cols-2 pre-selection / full-width post-selection (TDR-015 + TDR-019 pattern).

**Layout (FEP):**
```
Asset selector (dropdown, URL: ?asset=)
─ QC Report ─────────────────────────────────────────────────────
  data_health badge (ok=green/warn=amber/crit=red) · bar_count · date range
  zero_volume_days · ohlc_violations · large_gap_flags
  anomalies list (if any)
  Note when ohlc_violations > 0: "Yahoo Finance VWAP settlement prices legally
  fall outside intraday High/Low (ADR-001 §3.1.4, strict_ohlc=False)"
─ COT Positioning ───────────────────────────────────────────────
  COTPositioningChart (net speculative + percentile rank)
  OR EmptyState for Brent: "No COT data available for Brent — COT reports cover
  CME-listed contracts only. Brent crude trades on ICE London."
─ EIA Inventory ─────────────────────────────────────────────────
  EIAInventoryChart (inventory surprise z-score over time)
  OR EmptyState for non-crude: text from EIADataResponse.message
```

**Asset constraints:**
- COT data: available for Gold, Silver, Copper, WTI, Natural Gas. NOT Brent (ICE London, not CFTC).
- EIA data: available for WTI and Brent only (petroleum inventory). All other assets: `available: false`.
- Empty states use `data.message` from API response body — not hardcoded frontend strings.

**Datasets:** `GET /api/system/data/qc?asset=`, `GET /api/system/data/cot?asset=`, `GET /api/system/data/eia?asset=`. All `staleTime: 10 minutes`.

---

## S-FEP-1 — Sweep Explorer  `/sweeps`  *(FEP EM9)*

**Research question:** *What does the performance landscape look like across this strategy's parameter space?*

**Purpose:** Systematic parameter sweep. Configure parameter grid, launch async sweep, view results table and parallel coordinates chart.

**Layout (grid-cols-2 pre-launch, full-width post-results — TDR-019):**
```
Pre-launch:
┌────────────────────────────┬───────────────────────────────────────┐
│ Left: param grid builder   │ Right: [Launch Sweep] (amber, full)   │
│  Asset selector            │                                       │
│  Strategy picker           │ Recent sweeps list (from useSweeps)   │
│  Per-param text inputs     │ (click to load results)               │
│  "enter comma-separated"   │                                       │
└────────────────────────────┴───────────────────────────────────────┘

Post-launch/select (full-width):
[← New sweep]
SweepResultsTable (sortable: Sharpe/Return/MaxDD; best-Sharpe row highlighted)
ParallelCoordinatesChart (lines per run, colored by Sharpe via VisualMap loss→gray→gain)
```

**Param grid builder:** One text input per parameter in the strategy's param schema. Comma-separated values. Validation: ≥2 values per param, all must parse as numbers, integers for int-type params. Inline error on invalid. On launch: `POST /api/sweeps` with `{ asset, strategy_name, param_grid }`.

**Progress display:** "Running sweep… (N combinations)" — n_complete is completion-only (TD-FEP-SWEEP-PROGRESS). If live n_complete > 0 (future): shows "N / M complete" automatically.

**Async polling:** mirrors backtest pattern — `useSweepStatus` polls every 2s; `useSweepResults` fetches on complete (`staleTime: Infinity`).

**Sweep history:** persisted in Zustand `sweepHistory` store (localStorage key: `commodity-research-sweep-history`, max 10).

**Datasets:** `POST /api/sweeps`, `GET /api/sweeps/{id}/status`, `GET /api/sweeps/{id}/results?sort_by=&sort_dir=`, `GET /api/sweeps`.

---

## S-FEP-2 — Curve PCA  `/intelligence/pca`  *(FEP EM11)*

**Research question:** *What are the dominant modes of term structure variation for this commodity?*

**Purpose:** Principal component analysis of the forward curve. Identifies Level (PC1), Slope (PC2), and Curvature (PC3) factors from historical contract price movements.

**Layout (grid-cols-2 pre-submit, full-width post-results — TDR-019):**
```
Pre-submit:
┌────────────────────────┬─────────────────────────────────────────┐
│ Asset selector         │ [View PCA] (amber, full width)          │
│ n_components (2-3)     │                                         │
│ n_contracts (3-6)      │                                         │
│ Date range (optional)  │                                         │
└────────────────────────┴─────────────────────────────────────────┘

Post-submit (full-width):
[← Change config]
ScreePlot: amber bars (EVR per PC) + info-blue line (cumulative EVR, dual y-axis)
PCLoadingsChart: horizontal grouped bars per PC showing contract loadings
PCTimeSeriesChart: multi-line factor values over time (fmtDate on x-axis)
```

**Gold PCA note:** Gold PC1≈100% because its term structure is near-constant over the available data window. This is **correct behavior** — render the scree plot faithfully without special-case code or warnings. WTI and Natural Gas show meaningful 3-factor decompositions.

**Datasets:** `GET /api/intelligence/pca?asset=&n_components=&n_contracts=&from_date=&to_date=` (`staleTime: 10 minutes`).

---

## S12 — Global states

- **Not Found (`*`):** designed 404, mono glyph, links to Market Overview and Run Explorer.
- **API unreachable:** full-screen `ApiUnreachable` with retry and the local-dev hint (`make dev`); health dot in TopBar goes crit everywhere else.
- **Command palette:** available on every screen; Actions section is context-aware.
- **RouteErrorBoundary:** all 16 routes have `errorElement={<RouteErrorBoundary />}`. Any unhandled ECharts error or null data crash shows a recoverable "Something went wrong" UI with Reload link — never a full app crash.

---

## E2E Verification Summary

All 13 screens are E2E verified. Final suite: **114 passed / 3 skipped / 0 failed** (117 total including @slow).

**3 permanent skips:**
- Run Detail a11y — requires live run ID, API-dependent data
- Run Explorer a11y — same
- Sweep row → Run Detail — by design, no `/runs/{id}` artifacts created by sweeps

**Run Explorer pagination:** `GET /api/runs` returns `{ runs, total, page, page_size }`. Prev/Next controls with "Showing 1–50 of N runs" display. Sort params wired server-side via SQLite ORDER BY. Load time: 0.45s (was 30s — SQLite index fix).
