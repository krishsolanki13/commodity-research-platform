---
# M15 Implementation Notes — Portfolio Performance

**Date:** 2026-07-09
**Branch:** module/M15-portfolio-performance
**Tests:** 218 passing (203 baseline + 15 new)
**Tag:** M15-complete (after merge)

## Files Created
- src/performance/portfolio.py — PortfolioPerformanceEngine
- tests/test_portfolio_performance.py — 15 tests
- docs/implementation_notes/M15-portfolio-performance.md

## Files Modified
- src/core/types.py — PortfolioPerformanceReport appended after MultiAssetBacktestResult

## Design Decisions
- _compute_asset_contributions uses dict[str, BacktestResult] (not Any) per
  Risk Register recommendation in transfer package Section 11, Risk 1.
- portfolio_date_range is a required non-optional field — surfaces inner-join
  alignment from MultiAssetRunner._aggregate_portfolio() explicitly.
- initial_capital_total denominator used for all portfolio return/vol/Sharpe
  calculations, not per-asset capital.
- No RunManager calls — persistence deferred to pre-M19 housekeeping.

## End-to-End Gate Output
```
Run ID:                   20260709_061053_portfolio_ema_crossover
Assets:                   6
Skipped:                  none
Date range:               2010-01-04 to 2026-07-02
Initial capital (total):  $6,000,000
Initial capital (per asset): $1,000,000

=== Portfolio Metrics ===
  total_return              0.0125
  cagr                      0.0008
  sharpe                    0.0018
  sortino                   0.0021
  calmar                    0.0103
  max_drawdown              -0.0737
  portfolio_vol             0.0254
  n_trading_days            4116

=== Asset Contributions ===
  gold            +2379.79%
  silver          +520.30%
  copper          +4.88%
  wti             -474.33%
  brent           +231.15%
  natural_gas     -2561.78%
  Contribution sum:      1.000000  (should be ~1.0)

=== Per-Asset Summary ===
  gold            Sharpe=0.3006  MaxDD=-6.82%  Return=+10.88%  Trades=19
  silver          Sharpe=0.0803  MaxDD=-18.31%  Return=+4.96%  Trades=23
  copper          Sharpe=0.0333  MaxDD=-7.23%  Return=+0.87%  Trades=29
  wti             Sharpe=0.0001  MaxDD=-14.97%  Return=-2.36%  Trades=29
  brent           Sharpe=0.0317  MaxDD=-11.30%  Return=+0.78%  Trades=35
  natural_gas     Sharpe=-0.0150  MaxDD=-19.01%  Return=-7.66%  Trades=31

Module 15 end-to-end gate: PASSED
```

## Technical Debt
- TD-M15-A: Portfolio run artifacts not persisted. run_id carried through
  PortfolioPerformanceReport for future RunManager integration (pre-M19).
- TD-M15-B: Portfolio MLflow logging not implemented. Deferred alongside
  persistence to pre-M19 or M19 itself.

## Deviations from Transfer Package
- Ruff reformatted both files during validation (5 auto-fixes, style only).
- Annotations use unquoted forms in types.py (consistent with existing
  dataclasses; from __future__ import annotations makes this equivalent).
- _compute_asset_contributions aligns per-asset PnL to portfolio_pnl.index
  before summing (inner-join dates); unaligned sums diverged on real 6-asset
  data where start dates differ across commodities.

## Open Questions
None.
---
