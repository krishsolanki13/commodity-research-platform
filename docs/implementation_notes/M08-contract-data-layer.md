# Module 8 Implementation Notes
## Contract Data Layer (Phase 2, Layer 0 Extension)

**Branch:** module/M08-contract-data-layer
**Completed:** 2026-07-04
**Phase:** 2 — first module

### Files Created
- `scripts/acquire_contract_data.py`
- `src/data/sources/futures_contract.py`
- `src/data/contract_store.py`
- `src/data/contract_loader.py`
- `tests/test_contract_data.py`
- `docs/implementation_notes/M08-contract-data-layer.md`

### Files Modified
- `config/config.yaml` — contracts_raw and contracts_processed paths added
- `config/assets.yaml` — contract_root and exchange_suffix added to all 6 assets
- `src/core/types.py` — ContractMetadata dataclass added
- `src/data/sources/futures_contract.py` — available_assets() added (fix)
- `tests/test_contract_data.py` — Parquet roundtrip assertion relaxed (fix)

### Classes Implemented
- `ContractMetadata` (src/core/types.py — dataclass)
- `FuturesContractSource` (src/data/sources/futures_contract.py — concrete DataSource)
- `ContractStore` (src/data/contract_store.py — abstract)
- `ContractParquetStore` (src/data/contract_store.py — concrete)
- `ContractDataLoader` (src/data/contract_loader.py — concrete)

### Functions Implemented
- `parse_contract_ticker()` (src/data/sources/futures_contract.py)
- `build_ticker()` (scripts/acquire_contract_data.py)
- `build_yfinance_ticker()` (scripts/acquire_contract_data.py)
- `generate_contract_tickers()` (scripts/acquire_contract_data.py)

### Test Results
- 21 new tests in tests/test_contract_data.py
- 128 total tests passing

### Deviations from Specification
1. available_assets() was missing from FuturesContractSource — added as fix commit.
2. Parquet roundtrip drops DatetimeIndex frequency — assertion relaxed to compare values only.
3. Test count is 21 (not 20 as stated in spec) — ContractDataLoader has 5 tests, spec count was wrong.
4. exchange_suffix field added to assets.yaml alongside contract_root per tech lead amendment.
5. yf.Ticker().history() used instead of yf.download() per tech lead amendment — timezone stripped before CSV write.

### Technical Debt Introduced
- pandas UserWarning: DataFrame.attrs with date objects are not JSON-serializable
  and do not round-trip through Parquet. attrs are not part of the NormalizedOHLCV
  contract so this has no functional consequence.

### Real Data Notes
Acquisition summary (gold, 2-year lookback, 43 tickers attempted):
```
gold: 20/43 contracts downloaded (0 skipped, 23 no data)
```
20 contracts returned OK; 23 returned no data (delisted or unavailable on yfinance).

End-to-end gate output:
```
Available Gold contracts: 20
  GCZ25: 2025-12
  GCN26: 2026-07
  GCQ26: 2026-08
  GCU26: 2026-09
  GCV26: 2026-10
Loaded GCZ25: 1510 bars
Columns: ['open', 'high', 'low', 'close', 'volume', 'open_interest']
Index type: DatetimeIndex
Close range: [1570.50, 4529.10]
Forward curve: 3 contracts
  GCN26: 352 bars
  GCQ26: 444 bars
  GCU26: 352 bars
Module 8 end-to-end gate: PASSED
```

### Open Questions for Tech Lead
None.
