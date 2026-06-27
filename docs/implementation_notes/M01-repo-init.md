# Module 1 Implementation Notes
## Repository Initialization

**Branch:** module/M01-repo-init
**Completed:** June 26, 2026

### Deviations from Specification

1. **pyproject.toml build-backend**: Changed from
   `setuptools.backends.legacy:build` to `setuptools.build_meta`.
   The specified backend does not exist in any setuptools release.
   `pip install -e ".[dev]"` fails with the spec value. Cursor's
   correction is right; this was a prompt spec error.

2. **registry.py forward reference suppression**: Added
   `# noqa: F821, UP037` alongside `# type: ignore[name-defined]`
   on the `BacktestEngine.run` return type annotation. Both
   suppressions are required: `# type: ignore` silences mypy;
   `# noqa` silences ruff. The forward reference is intentional
   to avoid importing from types.py in registry.py.

3. **Increment 2 commit count**: logging_config.py and test_types.py
   landed in one commit instead of two separate commits due to
   parallel git operations. No history rewrite performed.

### .gitignore Correction (applied between Increments 1 and 2)

The initial `.gitignore` contained `data/` which also matched
`src/data/`. Corrected to `/data/` (anchored to repository root)
before Increment 2. The fix was committed as:
`fix(M01/inc1): anchor data/ gitignore pattern to repo root`

### Architectural Assumptions

None. Module 1 has no upstream modules and no architectural
ambiguities were encountered.

### Technical Debt

None introduced. All accepted deviations are documented above and
are non-blocking for subsequent modules.

### Open Questions for Tech Lead

None.
