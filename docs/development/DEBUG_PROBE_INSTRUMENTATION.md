# Debug Probe Instrumentation

## Overview

The reconciliation engine (`src/core/reconciliation/run_reconciliation.py`) has been instrumented with debug probes to trace data flow during the "September 2025 NG" reconciliation run.

## Debug Output Location

All debug output is written to: `outputs/_debug_sep2025_ng/`

This directory contains:
- `probe_log.txt` - Main probe log file with checkpoint summaries
- `merge_audit_log.txt` - Merge audit log file with join analysis
- `*_sample.csv` - Sample data files (first 100 rows) from each checkpoint

## Probe Utilities

### `probe_df(df, checkpoint_name, debug_dir, metrics=None)`

Captures a snapshot of a DataFrame at a specific checkpoint in the data flow.

**What it logs:**
- Row count
- Column count
- Column names
- Memory usage
- Optional metrics (sum, mean, unique count for specified columns)

**Example:**
```python
probe_df(nav_df, "NAV_raw_load", metrics=["Amount"])
```

### `audit_merge(left_df, right_df, on, merge_name, debug_dir, how='inner')`

Analyzes a merge operation before it happens.

**What it logs:**
- Key uniqueness on both sides
- Duplicate key detection
- Null key detection
- Expected match rate
- Potential data loss from merge

**Example:**
```python
audit_merge(jdash_df, ipe_df, on=['OrderId'], 
            merge_name="Timing_Diff_Merge", how="inner")
```

## Instrumentation Points

The following checkpoints have been instrumented in `run_reconciliation.py`:

### Phase 1: Extraction
1. **NAV Raw Load (CR_03)** - After loading CR_03 data
   - Checkpoint: `NAV_raw_load_CR03`
   - Metrics: `Amount`

2. **JDash Load** - After loading JDASH data
   - Checkpoint: `JDash_load`
   - Metrics: `OrderedAmount`, `OrderId`

3. **IPE_08 Load** - After loading IPE_08 data
   - Checkpoint: `IPE08_load`
   - Metrics: `TotalAmountUsed`, `VoucherId`

### Phase 2: Preprocessing
4. **NAV Preprocessing** - After GL 18412 filter on CR_03
   - Checkpoint: `NAV_preprocessing_GL18412`
   - Metrics: `Amount`

5. **IPE_08 Scope Filtering** - After filtering for Non-Marketing vouchers
   - Checkpoint: `IPE08_scope_filtered`
   - Metrics: `TotalAmountUsed`

### Phase 3: Categorization
6. **NAV Categorization** - After applying bridge categorization to CR_03
   - Checkpoint: `NAV_categorization_with_bridge`
   - Metrics: `Amount`

### Phase 4: Bridge Analysis
7. **Before VTC Merge** - Audit merge keys before VTC adjustment calculation
   - Merge Audit: `VTC_adjustment_merge`
   - Keys: `[Voucher No_]` or `VoucherId`

8. **Before Timing Diff Merge** - Audit merge keys before timing difference calculation
   - Merge Audit: `Timing_diff_JDash_IPE08_merge`
   - Keys: `OrderId` or `VoucherId`

9. **After Timing Diff Bridge** - After calculating timing difference bridge
   - Checkpoint: `Timing_diff_bridge_result`
   - Metrics: `OrderedAmount` (if available)

## Important Notes

### No Business Logic Changes
⚠️ **The debug probes do NOT modify the business logic.** They only:
- Read DataFrames
- Write log files
- Create sample CSV files

The actual reconciliation calculations remain unchanged.

### Conditional Probing
Probes are only executed when:
- The DataFrame exists in the data store
- The DataFrame is not None
- The DataFrame is not empty

This ensures probes don't interfere with the reconciliation flow.

### Performance Impact
Debug probes have minimal performance impact:
- Lightweight metrics calculation
- Sample-based CSV output (max 100 rows)
- Append-only log writing

## Usage Example

```python
from src.core.reconciliation.run_reconciliation import run_reconciliation

params = {
    'cutoff_date': '2025-09-30',
    'id_companies_active': "('EC_NG')",
}

# Run reconciliation with debug probes active
result = run_reconciliation(params)

# Check debug logs
# outputs/_debug_sep2025_ng/probe_log.txt
# outputs/_debug_sep2025_ng/merge_audit_log.txt
```

## Disabling Probes (Future)

To disable probes in the future, you can:

1. **Remove the probe calls** - Delete the probe_df and audit_merge lines
2. **Comment them out** - Add # before each probe call
3. **Add a flag** - Add a `debug_mode` parameter to control probe execution

## Files Modified

1. `src/utils/debug_probes.py` (NEW) - Probe utility functions
2. `src/core/reconciliation/run_reconciliation.py` (MODIFIED) - Added probe calls
3. `.gitignore` (MODIFIED) - Exclude `outputs/` directory
4. `tests/test_debug_probes.py` (NEW) - Unit tests for probe utilities
5. `tests/test_debug_probe_instrumentation.py` (NEW) - Integration tests for instrumentation

## Testing

Run tests to validate probe functionality:

```bash
# Test probe utilities
pytest tests/test_debug_probes.py -v

# Test instrumentation
pytest tests/test_debug_probe_instrumentation.py -v

# Test reconciliation still works
pytest tests/reconciliation/test_run_reconciliation.py -v
```

## Support

For questions or issues with debug probes, see:
- Probe utility code: `src/utils/debug_probes.py`
- Instrumentation code: `src/core/reconciliation/run_reconciliation.py`
- Test examples: `tests/test_debug_probes.py`
