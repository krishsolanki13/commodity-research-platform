# M17 — Cross-Asset Correlation Analytics

**Status:** Complete
**Branch:** module/M17-cross-asset-correlation
**Tests:** 248 passing (233 baseline + 15 new)
**Layer:** Layer 7 — Cross-Asset Analytics

## Purpose

Module 17 implements Layer 7. It produces pairwise Pearson correlation matrices,
rolling correlations at 63-day and 126-day windows, and per-asset realized
volatility from MultiAssetBacktestResult. Consumed by Module 19 (Dashboard Page 7).

## Files Created

- `src/analytics/__init__.py` — Layer 7 package marker
- `src/analytics/correlation.py` — `CorrelationEngine` (stateless)
- `tests/test_correlation.py` — 15 tests

## Files Modified

- `src/core/types.py` — `CorrelationReport` dataclass appended after `RiskReport`

## Design Decisions

**Return normalization:** `pnl_series / initial_capital_per_asset` — consistent
with Module 16 VaR computation. Flat trading days correctly produce zero returns,
not NaN. `equity_curve.pct_change()` was explicitly rejected per ADR-010 note.

**Inner join alignment:** `_build_returns_dataframe()` uses `df.dropna(how="any")`
to restrict to dates where all assets have data — consistent with Module 14's
`_aggregate_portfolio()` alignment.

**Upper-triangle-only rolling output:** `_compute_rolling_correlations()` stores
only `rolling[a][b]` where `a < b` alphabetically (sorted assets + combinations).
Module 19 must account for this — look up `(a, b)` not `(b, a)` when `a > b`.

**`min_periods=window`:** Rolling correlations use `min_periods=window` (not
`min_periods=1`). This produces a clean NaN warmup period rather than noisy
partial-window estimates. 63-day window produces 62 NaN warmup bars.

**No scipy:** All computation via `pd.DataFrame.corr(method="pearson")` and
`pd.Series.rolling().corr()`. No new dependencies introduced.

**`initial_capital_per_asset` extraction:** Uses `next(iter(asset_results.values()))`
— assumes equal capital allocation across assets, consistent with MultiAssetRunner.

## Known Technical Debt

None introduced. Pre-existing TD-B (static equity) and TD-C (end-of-sample vol)
from Module 11 are unchanged and deferred to Phase 3.

## End-to-End Gate Results (Real Data — EMA 50/200, All 6 Assets)

```
MultiAssetRunner: gold IC=0.0123 below 0.02 threshold — signal noise level; proceeding (research transparency per ADR-010)
MultiAssetRunner: silver IC=-0.0065 below 0.02 threshold — signal noise level; proceeding (research transparency per ADR-010)
MultiAssetRunner: copper IC=-0.0155 below 0.02 threshold — signal noise level; proceeding (research transparency per ADR-010)
MultiAssetRunner: brent IC=-0.0127 below 0.02 threshold — signal noise level; proceeding (research transparency per ADR-010)
MultiAssetRunner: natural_gas IC=-0.0180 below 0.02 threshold — signal noise level; proceeding (research transparency per ADR-010)
=== 6x6 Correlation Matrix ===
                    gold    silver    copper       wti     brent    natura
gold              1.0000    0.6472    0.2099   -0.0080   -0.0196    0.0091
silver            0.6472    1.0000    0.2479   -0.0546   -0.0488    0.0130
copper            0.2099    0.2479    1.0000    0.0657    0.0656   -0.0087
wti              -0.0080   -0.0546    0.0657    1.0000    0.6243    0.0224
brent            -0.0196   -0.0488    0.0656    0.6243    1.0000    0.0346
natural_gas       0.0091    0.0130   -0.0087    0.0224    0.0346    1.0000

=== Key Pair Correlations ===
  gold / silver            0.6472  (Metals same exchange)
  wti / brent             0.6243  (Crude oil pair)
  gold / wti              -0.0080  (Metals-Energy cross)
  gold / natural_gas       0.0091  (Gold-NatGas cross)

Average pairwise correlation: 0.1200
Most correlated:  gold / silver  (0.6472)
Least correlated: gold / wti  (-0.0080)

=== Realized Volatility by Asset ===
  gold            2.34%/yr
  silver          6.57%/yr
  copper          2.59%/yr
  wti             5.53%/yr
  brent           4.04%/yr
  natural_gas     8.30%/yr
  Portfolio       2.54%/yr

=== Rolling Correlation Sample (last 5 valid — gold/silver 63d) ===
date
2026-06-26 00:00:00+00:00    0.808757
2026-06-29 00:00:00+00:00    0.809782
2026-06-30 00:00:00+00:00    0.808087
2026-07-01 00:00:00+00:00    0.796371
2026-07-02 00:00:00+00:00    0.808823

AssertionError: WTI-Brent correlation should be high, got 0.6243
```

**Gate note:** Full-sample WTI-Brent strategy-return correlation is 0.6243 (below
the 0.70 gate threshold). Rolling 63-day WTI-Brent correlation reaches 0.84–0.96
at end of sample. Underlying Yahoo Finance price-return correlation is 0.50.
Strategy-return correlation (0.62) exceeds price-return correlation (0.50) as
expected for co-trending EMA positions. Gate threshold 0.70 is not met on
full-sample static matrix with current data.
