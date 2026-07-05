# Module 10 Implementation Notes
## Term Structure Analytics (Phase 2, Layer 5 completion)

**Branch:** module/M10-term-structure-analytics
**Completed:** 2026-07-05
**Phase:** 2

### Deviations from Specification

None.

### Architectural Assumptions Discovered

- `continuous_close` is always passed into `analyze()` / `analyze_series()` as a parameter; the analyzer never calls `DataLoader` directly. This preserves ADR-001 separation between the Phase 1 continuous pipeline and the Phase 2 contract pipeline.
- Basis is computed as a pseudo-basis (`continuous_close - front_price`) using the Yahoo Finance continuous series as a spot proxy. Roll methodology artifacts in the continuous series are an accepted Phase 2 limitation.
- Regime classification uses a single configurable threshold (`DEFAULT_REGIME_THRESHOLD = 0.005`, i.e. 0.5%/year) applied uniformly across assets. Noisier commodities (e.g. Natural Gas) may require per-asset tuning in Phase 3.
- `TermStructureRegime` inherits from `str` (with `# noqa: UP042`) for JSON serialization and plain-string comparison compatibility on Python 3.11.

### Technical Debt Introduced

- Pseudo-basis does not reflect true physical market basis; documented in `compute_basis()` docstring but not surfaced to dashboard consumers yet.
- `regime_threshold` is a constructor parameter with a global default; no per-asset configuration in `config/` yet.

### Open Questions for Tech Lead

- Should `regime_threshold` be moved into per-asset config (e.g. `config/assets/gold.yaml`) before Phase 3 signal conditioning?
- Is the 0.5%/year flat-band threshold appropriate for all six assets, or should Natural Gas and WTI have wider bands?

### End-to-End Gate Results

```
Gold forward curve at 2026-07-05:
  n_points:   6
  front:      4174.60
  back:       4248.40
  tickers:    ['GCN26', 'GCQ26', 'GCU26', 'GCV26', 'GCX26', 'GCZ26']
Continuous close (Gold): 4078.70

--- TermStructureSnapshot ---
Regime:                  contango
Annualized slope pct:    4.3306%
Roll yield (annualized): -3.5710%
Basis:                   -95.9001
Basis pct:               -0.023512
n_contracts:             6
raw_slope (USD/day):     0.482352

Historical term structure analysis: 3 snapshots
  2026-01-01: contango       slope=1.11%
  2026-04-01: contango       slope=1.78%
  2026-07-01: contango       slope=4.10%
ValueError on length mismatch: OK (continuous_closes length (2) must match curves length (3))

Module 10 end-to-end gate: PASSED
```

Key observations:
- Gold term structure regime: contango
- Annualized slope: 4.3306%
- Roll yield (annualized): -3.5710%
- Basis: -95.9001
