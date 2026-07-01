# Module 5 Implementation Notes
## Backtesting Engine (Layer 3)

**Branch:** module/M05-backtesting-engine
**Completed:** 2026-07-01

### Deviations from Specification

- **CostModel slippage model:** Slippage is charged once per `TradeRecord` execution (`commission + slippage_ticks x tick_value`), not as two separate per-side fills. This avoids double-charging the flat commission while still satisfying the test contract (15.0 for commission=5, slippage=1, tick_value=10). Documented in `costs.py` for Phase 2 revisit.
- **RunManager scope:** ADR-009 separate RunManager (assign/save) and RunRegistry (list/load/compare/delete) responsibilities are consolidated into a single `RunManager` class per Module 5 Transfer Package Section 8.
- **`initial_capital_usd`:** Bound as a `VectorizedBacktester` constructor parameter (default 1,000,000.0), not a `config.yaml` key — no such key exists in the frozen Module 1 schema.
- **`signal_evaluation`:** `BacktestResult.signal_evaluation` is always `None`; Module 6 orchestration attaches evaluation results.
- **`metrics.json`:** Not written by `RunManager.save()` — deferred to Module 6.

### Architectural Assumptions Discovered

- **ADR-002 execution lag:** `held_position[t] = position_signal.shift(1, fill_value=0)`. Entry and normal exit fills occur at `Open[t+1]` relative to the signal transition bar; force-close at final bar uses `Close` on the last bar.
- **PnL decomposition telescoping:** Daily `pnl_series` is built from mark-to-market close prices with transaction cost on the entry day; cumulative sum equals sum of trade `net_pnl` (verified in end-to-end gate to < 1e-6).
- **Direction reversal:** A direct +1 to -1 transition produces two adjacent constant-position runs, yielding two `TradeRecord`s with coincident exit/entry dates and separate costs — no special-case logic required.
- **Phase 1 sizing:** `FixedNotionalSizer` returns a constant USD notional from `config.sizing.fixed_notional_usd`; contract count is derived from notional and entry price.

### Technical Debt Introduced

- **Single-call cost model:** Entry and exit slippage are not modeled as separate fills; revisit for Phase 2 execution realism.
- **`compare_runs`:** Implemented on `RunManager` but not covered by Module 5 tests; relies on `load_run` round-trip correctness.
- **Git commit hash:** `_get_git_commit_hash()` uses a subprocess call with a broad exception fallback to `"unknown"` — acceptable for metadata but not hardened for non-git environments.

### Open Questions for Tech Lead

- Should Phase 2 split slippage into per-side fills while keeping commission flat per trade, or per fill?
- Should `compare_runs` be promoted to a first-class API with dedicated tests in Module 6?
- Should `initial_capital_usd` be added to `config.yaml` in a future schema revision?
