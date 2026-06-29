# Module 3 Implementation Notes
## Feature Engineering (Layer 1)

**Branch:** module/M03-feature-engineering
**Completed:** 2026-06-29

### Deviations from Specification
None.

### Architectural Assumptions Discovered
- `FeatureFrame` lives in `src/research/feature_frame.py` and must not be imported into `src/core/types.py` to avoid a circular dependency with `FeatureSpec` (documented in ADR-006 and `types.py`).
- `FeaturePipeline.compute()` copies the input OHLCV DataFrame before applying indicators; indicators run sequentially and each output column is appended before the next indicator runs.
- `Indicator.parameters` is a concrete `@property` on the ABC in `registry.py`; each concrete indicator overrides it for `FeatureSpec` serialization.
- `FeatureSpec.indicator_name` is derived from `type(indicator).__name__.lower()` (e.g. `EMA` -> `"ema"`).

### Technical Debt Introduced
None.

### Open Questions for Tech Lead
None.
