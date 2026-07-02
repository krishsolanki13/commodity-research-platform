# Module 7 Implementation Notes
## Dashboard — Pages 1–5 (Layer 8)

**Branch:** module/M07-dashboard
**Completed:** 2026-07-02
**Phase 1 status:** This module completes Phase 1.

### Deviations from Specification
None.

### Architectural Assumptions Discovered
- Pages 4 and 5 read `backtest_result`, `performance_report`, `last_run_asset`, and `last_run_strategy` from `st.session_state`, populated by Page 3 (Strategy Builder) on successful pipeline run.
- Page 1 computes simple 1D/1W/1M return percentages inline via pandas for the universe summary table (display-only aggregation; no numpy, no src/ math).
- `report.initial_capital_usd` is used as the authoritative initial-capital display source on Pages 4 and 5 (per Module 6 deviation 1).

### Technical Debt Introduced
- Broad `except Exception` handlers on data-load paths (pages 1–3) with `# noqa: BLE001` to gracefully handle missing CSV files.
- Page 1 return calculations are not centralized in a shared dashboard utility.

### Open Questions for Tech Lead
None.

### Data Setup Required for Dashboard
To run the dashboard locally:
  cp tests/fixtures/gold_sample.csv data/raw/continuous/gold.csv
  streamlit run dashboard/app.py
