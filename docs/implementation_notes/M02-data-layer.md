# Module 2 Implementation Notes

## Data Layer (Layer 0)

**Branch:** module/M02-data-layer

**Completed:** 2025-06-28

### Deviations from Specification

1. `datetime.date` attrs not JSON-serializable for Parquet — `ParquetStore.write()` converts `data_start` and `data_end` to ISO strings before writing. `read()` re-populates from index as `date` objects. No impact on layer contract.

2. Ruff UP045 modernised `Optional[X]` to `X | None` across all files.

3. Ruff B905 added `strict=False` to `zip()` calls in [validator.py](http://validator.py).

4. Ruff E741 renamed ambiguous loop variable `l` to `low_val` in [validator.py](http://validator.py).

5. `collections.abc.Callable` import added to [validator.py](http://validator.py) for mypy compliance.

6. Pre-commit ruff-format reformatted [store.py](http://store.py) and test_data_[loader.py](http://loader.py) on first commit attempt — re-staged and recommitted both.

### Architectural Assumptions Discovered

1. `DataFrame.attrs` are silently lost through Parquet round-trips — confirmed and mitigated in `ParquetStore.read()` by explicit re-population.

2. End-to-end pipeline verification requires a raw CSV in `data/raw/continuous/` — tests correctly use `tmp_path` redirection; no real raw data file needed for the test suite.

### Technical Debt Introduced

None.

### Open Questions for Tech Lead

None.
