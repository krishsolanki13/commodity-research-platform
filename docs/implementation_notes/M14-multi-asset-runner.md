# Module 14 Implementation Notes
## Multi-Asset Runner (Phase 3, Module 1)

**Branch:** module/M14-multi-asset-runner
**Phase:** 3

### Deviations from Specification
- `executed_at` field in `MultiAssetBacktestResult` annotated as
  `datetime.datetime` (not `datetime`) in `types.py` because `datetime`
  is imported as a module in that file. mypy requires the fully-qualified
  form. No functional impact.
- Pre-commit hook (ruff-format) reformatted `tests/test_multi_asset.py`
  after initial commit, requiring a re-stage. Environmental only.

### Technical Debt Introduced
- TD-M14-A: `_build_pipeline_components()` in `MultiAssetRunner` duplicates
  the strategy->pipeline mapping from `dashboard/pages/3_strategy_builder.py`.
  Both files must be updated when a new strategy is added.
  Mitigation: extract to `src/backtesting/pipeline_builder.py` in a future module.

### Open Questions for Tech Lead
None.

### End-to-End Gate Results
MultiAssetRunner: gold IC=0.0123 below 0.02 threshold ? signal noise level; proceeding (research transparency per ADR-010)
MultiAssetRunner: silver IC=-0.0065 below 0.02 threshold ? signal noise level; proceeding (research transparency per ADR-010)
MultiAssetRunner: copper IC=-0.0155 below 0.02 threshold ? signal noise level; proceeding (research transparency per ADR-010)
C:\Users\krish\AppData\Roaming\Python\Python314\site-packages\pandas\core\arraylike.py:399: RuntimeWarning: invalid value encountered in log
  result = getattr(ufunc, method)(*inputs, **kwargs)
MultiAssetRunner: brent IC=-0.0127 below 0.02 threshold ? signal noise level; proceeding (research transparency per ADR-010)
MultiAssetRunner: natural_gas IC=-0.0180 below 0.02 threshold ? signal noise level; proceeding (research transparency per ADR-010)
Portfolio run ID:          20260708_170118_portfolio_ema_crossover
Assets successful:         6/6
Skipped:                   none
Total trades (all assets): 166

  gold             19 trades  IC=0.0123
  silver           23 trades  IC=-0.0065
  copper           29 trades  IC=-0.0155
  wti              29 trades  IC=-0.0367
  brent            35 trades  IC=-0.0127
  natural_gas      31 trades  IC=-0.0180

Portfolio equity start:  6,000,000
Portfolio equity end:    6,074,759
Portfolio return:        1.25%
Portfolio trading days:  4116
Portfolio == sum of per-asset (max diff 0.00e+00): VERIFIED

Module 14 end-to-end gate: PASSED
