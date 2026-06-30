# Module 4 Implementation Notes
## Signal Research (Layer 2)

**Branch:** module/M04-signal-research
**Completed:** 2026-06-30

### Deviations from Specification

- `PositionSignalConstructor` was implemented in increment 2 rather than increment 3, because `test_position_signal_values_restricted` required it before the reversion/breakout increment.
- `RSIReversionSignal` accepts `oversold_threshold` and `overbought_threshold` constructor parameters, but `generate()` uses the symmetric formula `-(RSI - 50) / 50` only; threshold levels are not yet applied to the raw signal.

### Architectural Assumptions Discovered

- `DonchianBreakoutSignal` reads raw OHLCV columns (`high`, `low`, `close`) directly from `FeatureFrame.data` and does not require pre-computed indicator columns; an empty `FeaturePipeline([])` is sufficient.
- `SignalEvaluator` turnover is computed via inline sign discretization (`> 0` -> long, `< 0` -> short) rather than delegating to `PositionSignalConstructor`; this keeps evaluation independent of position-threshold configuration.
- IC and ICIR use 1-bar forward log returns (`log(close[t+1] / close[t])`); decay horizons are fixed at `{1, 2, 5, 10, 20}` via `SignalEvaluator.HORIZONS`.
- `DonchianBreakoutSignal` applies `shift(1)` on rolling channel bounds to satisfy the no-look-ahead constraint (ADR-002).

### Technical Debt Introduced

- `RSIReversionSignal` oversold/overbought threshold parameters are stored but unused in signal generation.
- KeyError on missing required columns is implemented in all signal generators but not covered by dedicated unit tests.

### Open Questions for Tech Lead

- Should `RSIReversionSignal.generate()` incorporate the oversold/overbought thresholds (e.g., stronger signal beyond 30/70), or should those parameters be removed until needed?
- Should `SignalEvaluator` turnover delegate to `PositionSignalConstructor` for consistency with the backtest path, or remain decoupled?
