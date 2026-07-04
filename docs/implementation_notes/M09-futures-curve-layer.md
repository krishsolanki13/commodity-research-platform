# Module 9 Implementation Notes

## Futures Curve Layer (Phase 2, Layer 5)

**Branch:** module/M09-futures-curve-layer

**Phase:** 2

### Deviations from Specification

1. **Test count: 17, not 15.** The transfer package stated "15 tests total" but
  Section 7.3 contained 17 test functions. The discrepancy was a counting error
   in the spec — the final section (available_assets + empty curve edge cases,
   2 tests) was omitted from the header count. All 17 tests are correct and
   intentional. Baseline on module exit: 145 tests (128 + 17).
2. **Ruff: I001 import-sort on initial check.** Resolved by re-running
  `ruff check --fix`. No structural issue.

### Architectural Assumptions Discovered

None.

### Technical Debt Introduced

None.

### Open Questions for Tech Lead

None.

### End-to-End Gate Results

`
Assets with contract data: ['gold']
Gold forward curve at 2026-07-05:
  n_points:         6
  front_price:      4174.60
  back_price:       4248.40
  is_contango:      True
  is_backwardation: False
  slope:            0.482352 USD/day
  tickers:          ['GCN26', 'GCQ26', 'GCU26', 'GCV26', 'GCX26', 'GCZ26']
Historical snapshots: 3
  2026-01-01: 3 points
  2026-04-01: 3 points
  2026-07-01: 3 points
Module 9 end-to-end gate: PASSED
`
