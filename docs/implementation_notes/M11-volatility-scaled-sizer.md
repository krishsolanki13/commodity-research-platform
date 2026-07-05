# Module 11 Implementation Notes
## Volatility Scaled Sizer (Phase 2, ADR-005 completion)

**Branch:** module/M11-volatility-scaled-sizer
**Completed:** 2026-07-05
**Phase:** 2

### Deviations from Specification

- Module transfer package specified `size(signal, current_equity)` as the primary `PositionSizer` method. The existing codebase uses `compute_size(signal, asset, equity)`. `VolatilityScaledSizer` implements both: `size()` holds the vol-scaling logic; `compute_size()` delegates to it (ignoring `asset`, which is already bound at backtester construction time).
- Transfer package verification scripts referenced `FixedNotionalSizer(notional=...)`; the frozen API is `notional_usd=`.

### Architectural Assumptions Discovered

- `configure(ohlcv)` pre-computes a single realized-vol estimate from the most recent `lookback_days` of the full OHLCV series. Vol is not re-estimated bar-by-bar during the simulation. This matches the Phase 2 scope (static vol estimate per run) but differs from a production rolling-vol sizer.
- `TradeLog` passes `initial_capital_usd` as the equity argument to `compute_size()`, not rolling mark-to-market equity. Position sizes are therefore constant across all trades in a run. Documented in `TradeLog.__init__` as Phase 1 compatibility; vol scaling inherits this limitation.
- `VectorizedBacktester.run()` calls `configure(ohlcv)` unconditionally before `TradeLog.build()`. `FixedNotionalSizer` inherits the ABC no-op — zero behavior change for existing backtests.
- Default `target_annual_vol=0.01` (1%/yr per asset) with `$1M` initial capital yields ~$42K notional on Gold at current realized vol (~23%/yr), vs $100K fixed notional.

### Technical Debt Introduced

- Static equity and static realized vol per run: neither updates as the portfolio grows or as volatility regimes shift mid-backtest.
- `sizing_model_params` in `BacktestMetadata` still records only `method` and `fixed_notional_usd` from config; vol-scaled runs do not persist `target_annual_vol` / `lookback_days` in metadata yet.
- No `config.yaml` key for `target_annual_vol`; sizer parameters are constructor-only.

### Open Questions for Tech Lead

- Should Phase 3 wire rolling equity into `TradeLog` before enabling dynamic vol scaling, or is static-$1M-equity acceptable for cross-asset comparison research?
- Should `target_annual_vol` move into `config/sizing.yaml` with per-asset overrides?
- Is a single end-of-sample realized vol estimate sufficient, or should `configure()` accept a date index for walk-forward vol estimation?

### End-to-End Gate Results

```
Gold: 4148 bars, 3949 signal bars

=== Fixed Notional (100K) ===
Sharpe:  0.3006
Max DD:  -6.82%
Trades:  19

=== Volatility Scaled (1% target vol) ===
Realized vol:  0.2349 (23.49%/yr)
Sharpe:        0.2900
Max DD:        -3.03%
Trades:        19

Max |position| fixed:     100,000 USD
Max |position| vol-scaled: 42,567 USD

Gold vol contribution:        0.0100 (target 0.01)
Natural Gas vol contribution: 0.0100 (target 0.01)

Module 11 end-to-end gate: PASSED
```

Key observations:
- Gold EMA crossover on 4148 bars produces 19 trades under both sizers (same signal, same trade boundaries).
- Vol-scaled max position (~$42.6K) is materially smaller than fixed $100K, reflecting Gold realized vol ~23%/yr vs 1% target contribution.
- Equal-risk property verified: Gold and Natural Gas both achieve ~1% annualized vol contribution at $1M equity with `target_annual_vol=0.01`.
- Max drawdown improves (-3.03% vs -6.82%) because smaller positions reduce dollar exposure; Sharpe is similar (0.29 vs 0.30).
