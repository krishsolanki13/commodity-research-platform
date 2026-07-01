# Module 6 Implementation Notes
## Performance and Attribution (Layer 4)

**Branch:** module/M06-performance-layer
**Completed:** 2026-07-01

### Deviations from Specification
- initial_capital added as 16th key in scalar_metrics (convenience duplicate
  of PerformanceReport.initial_capital_usd). Module 7 should use
  report.initial_capital_usd as the authoritative source.
- _rolling_sharpe uses simplified form (result[roll_std < 1e-10] = 0.0)
  instead of the original fillna(0.0).where() pattern from the transfer
  package. Simpler and equally correct.
- tests/test_performance.py contains 21 tests (not 20 as spec'd) — tests
  16 and 17 from the original numbering were both preserved.

### Architectural Assumptions Confirmed
- BacktestResult is a non-frozen dataclass — signal_evaluation is directly
  settable (confirmed from Module 1 types.py).
- RunManager.save() writes exactly 5 files and does NOT write metrics.json
  (confirmed from Module 5).
- json and Path already imported in run_manager.py — no new imports needed.

### Technical Debt Introduced
None.

### Open Questions for Tech Lead
None.
