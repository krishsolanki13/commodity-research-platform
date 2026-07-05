# Module 13 Implementation Notes

## Dashboard Page 6 — Futures Curve (Phase 2 Final Module)

**Branch:** module/M13-dashboard-page-6

**Completed:** 2026-07-06

**Phase:** 2 (FINAL MODULE)

### Files Created

- `dashboard/components/curve_chart.py`
- `dashboard/pages/6_futures_curve.py`
- `docs/implementation_notes/M13-dashboard-page-6.md`

### Files Modified

- `src/backtesting/run_manager.py` (pre-M13 housekeeping — MLFLOW_ALLOW_FILE_STORE fix)
- `launch_dashboard.ps1` (pre-M13 housekeeping — MLFLOW_ALLOW_FILE_STORE export)
- `launch_dashboard.sh` (pre-M13 housekeeping — MLFLOW_ALLOW_FILE_STORE export)

### Deviations from Specification

- Transfer package `curve_chart.py` imported `CAUTION` and `GRID` from `_theme.py`
  but neither was referenced in the file body. Stripped before copy-paste to prevent
  ruff F401 violations. Confirmed with tech lead before implementation.
- Transfer package `6_futures_curve.py` imported `CAUTION`, `NEGATIVE`, `POSITIVE`,
  `SLATE` from `_theme.py` but none were referenced in the page file directly
  (they are used inside `curve_chart.py`). Stripped before copy-paste. Confirmed
  with tech lead before implementation.
- Ruff auto-reformatted both files on first `ruff format` run. Changes included in
  respective commits. Pre-commit hooks passed.
- PowerShell requires `;` instead of `&&` for command chaining. No code impact.
- Automated validation steps requiring `plotly` invoked via `.venv\Scripts\python.exe`
  (system Python 3.14 does not have project dependencies). Consistent with all
  prior modules.

### Architectural Assumptions Discovered

- `TermStructureAnalyzer.analyze_series()` accepts optional `continuous_closes`
  keyword argument — confirmed by tech lead against Module 10 implementation.
- `TermStructureSnapshot` has `observation_date: date` field — confirmed by tech
  lead. Used as x-axis in history charts.
- `FuturesCurveBuilder._loader.list_contracts(asset)` private attribute access
  in the Data Quality expander is a known fragility per Section 11 risk register.
  If `FuturesCurveBuilder` internal attribute name changes, the expander breaks.

### Technical Debt Introduced

- `builder._loader.list_contracts(asset)` in Section 5 of Page 6 accesses a
  private attribute on `FuturesCurveBuilder`. Acceptable for research transparency
  in a dashboard context per transfer package Section 8 Constraint 9, but fragile
  if Module 8 internals change in Phase 3.

### Open Questions for Tech Lead

- None.

### Test Count

- 186 passing (unchanged — no new tests per ADR-008 dashboard pages policy).

### Manual Verification Results

All 17 manual checklist items passed on Gold data with dark theme dashboard.
