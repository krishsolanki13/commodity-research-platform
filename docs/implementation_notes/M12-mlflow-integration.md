---
# Module 12 Implementation Notes
## MLflow Integration (Phase 2, Layer 3 extension)

**Branch:** module/M12-mlflow-integration
**Completed:** 2026-07-05
**Phase:** 2

### What Was Built

MLflow logging added to `RunManager.save_metrics()` via a new private method
`_try_log_to_mlflow()`. Each backtest run now produces both file-based artifacts
(canonical, always written) and an MLflow run (best-effort, non-fatal on failure).

Files created:
- `tests/test_mlflow_integration.py` — 10 tests
- `docs/implementation_notes/M12-mlflow-integration.md` — this file

Files modified:
- `config/config.yaml` — mlflow section added
- `src/core/config.py` — mlflow_tracking_uri and mlflow_experiment_prefix properties
- `src/backtesting/run_manager.py` — _try_log_to_mlflow() method + _sanitize_mlflow_key() function
- `pyproject.toml` — mlflow>=2.0 dependency

Functions implemented:
- `RunManager._try_log_to_mlflow()` — private method, non-fatal MLflow logging
- `_sanitize_mlflow_key()` — module-level free function, sanitizes MLflow parameter keys

### Deviations from Specification

1. **MLflow 3.14 requires MLFLOW_ALLOW_FILE_STORE=true** — MLflow 3.x places the
   filesystem tracking backend in maintenance mode and blocks it by default. The env var
   re-enables it. Set via autouse pytest fixture in test_mlflow_integration.py and via
   os.environ in end-to-end gate scripts. Not required in config.yaml (set at runtime).

2. **Config internal attribute is self._config** — The inspection step in Increment 1
   revealed that cfg.data only holds the data: section dict. A self._config attribute
   storing the full parsed YAML was added to Config.__init__/load() to support the new
   properties. The tmp_config fixture overrides cfg._config["mlflow"]["tracking_uri"]
   directly for test URI isolation.

3. **isinstance(v, int | float) instead of isinstance(v, (int, float))** — Ruff UP038
   (pre-commit) required the union syntax. Functionally equivalent.

4. **PerformanceReport import added to test file** — Return type annotation on
   _run_full_pipeline() required explicit import from src.core.types. Caught by ruff F821
   during pre-commit; added before commit.

5. **mlflow installed for Python 3.11** — Project uses Python 3.11.4 for tests;
   mlflow was initially only available on 3.14 interpreter. Installed for 3.11 to run suite.

### Technical Debt

None introduced. Dual-write architecture (file-first, MLflow best-effort) is the
intended design per ADR-009.

### Open Questions for Tech Lead

None. ADR-009 Phase 2 commitment fully satisfied.

### End-to-End Gate Results

```
2026/07/05 22:11:55 INFO mlflow.tracking.fluent: Experiment with name 'commodity_research_gold' does not exist. Creating a new experiment.
Tracking URI:      file:./data/mlruns
Experiment prefix: commodity_research
Run ID: 20260705_164155_ema_crossover_gold
Sharpe: 0.3006

MLflow experiment: commodity_research_gold
MLflow run name:   20260705_164155_ema_crossover_gold
Logged params:     ['asset', 'data_end', 'data_source', 'data_start', 'initial_capital', 'param_fast_period', 'param_slow_period', 'signal_name', 'strategy_name']
Logged metrics:    ['avg_drawdown', 'avg_loss', 'avg_trade_duration_bars', 'avg_win', 'cagr', 'calmar', 'initial_capital', 'largest_loss', 'largest_win', 'max_drawdown', 'profit_factor', 'sharpe', 'sortino', 'total_return', 'turnover', 'win_rate']
file_run_id tag:   20260705_164155_ema_crossover_gold

Module 12 end-to-end gate: PASSED

To view in browser: mlflow ui --backend-store-uri file:./data/mlruns
```
