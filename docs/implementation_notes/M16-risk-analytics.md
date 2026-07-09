---
# M16 Implementation Notes — Risk Analytics

**Date:** 2026-07-09
**Branch:** module/M16-risk-analytics
**Tests:** 233 passing (218 baseline + 15 new)
**Tag:** M16-complete (after merge)

## Files Created
- src/risk/__init__.py — Layer 6 package init
- src/risk/risk_engine.py — RiskEngine (historical simulation VaR/ES)
- tests/test_risk_analytics.py — 15 tests
- docs/implementation_notes/M16-risk-analytics.md

## Files Modified
- src/core/types.py — RiskReport dataclass appended after PortfolioPerformanceReport

## Design Decisions
- Historical simulation over lookback_days (default 252); no parametric normal
  assumption — appropriate for fat-tailed commodity futures returns (ADR-003).
- VaR and ES expressed as positive USD loss magnitudes: |quantile(1 − c)| and
  mean of tail losses beyond the VaR threshold, respectively.
- Minimum 20 valid PnL observations required; fewer returns NaN (not an error).
- Notional exposure averaged over active trading days only (positions != 0).
- portfolio_diversification_benefit = sum(asset_var_99) / portfolio_var_99;
  values > 1.0 indicate cross-asset diversification benefit.
- Stateless RiskEngine — lookback_days is per compute() call, not instance state.
- Consumes MultiAssetBacktestResult.portfolio_pnl_series (inner-join dates).

## End-to-End Gate Output
```
Portfolio Value at Risk (252-day historical simulation):
  VaR 95%: $31,948  (0.5325%)
  VaR 99%: $44,490  (0.7415%)
  ES  95%: $51,542
  ES  99%: $99,095
  Diversification benefit: 2.23x

Per-Asset VaR 99%:
  gold            VaR99=$11,403  avg_gross=$100,000
  silver          VaR99=$32,597  avg_gross=$100,000
  copper          VaR99=$6,484  avg_gross=$100,000
  wti             VaR99=$14,060  avg_gross=$100,000
  brent           VaR99=$16,587  avg_gross=$100,000
  natural_gas     VaR99=$17,936  avg_gross=$100,000

Total avg gross notional: $600,000

Module 16 end-to-end gate: PASSED
```

## Technical Debt
- TD-M16-A: Risk report artifacts not persisted. run_id carried through
  RiskReport for future RunManager integration (pre-M19).
- TD-M16-B: Dashboard Page 7 (risk analytics) not yet implemented — deferred
  to Module 19.

## Deviations from Transfer Package
- Ruff format reformatted 14 test files during validation (style only).
- ES fallback: when no observations fall strictly beyond the VaR quantile
  threshold, ES returns |var_threshold| rather than NaN.
- ValueError raised for empty asset_results and lookback_days < 20 (validated
  in engine; not all edge cases covered by unit tests).

## Open Questions
None.
---
