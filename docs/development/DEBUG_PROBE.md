# Debug Probe Utility

## Overview

The `debug_probe` module provides a lightweight utility for instrumenting data processing pipelines. It allows you to "x-ray" DataFrames at various steps without refactoring your codebase.

## Features

- **Basic Statistics**: Rows, columns, null counts, duplicate detection
- **Amount Tracking**: Sum values from amount/value columns
- **Date Range**: Track min/max dates in your data
- **Unique Key Counts**: Count unique values in key columns
- **Logging**: Append JSON-formatted logs to `probes.log`
- **Snapshots**: Optional CSV snapshots of DataFrames
- **Financial Data Support**: Handles NaN and Infinity values in JSON serialization

## Installation

The module is part of the SOXauto core package. No additional installation is required.

## Quick Start

```python
from src.core.debug_probe import probe_df
import pandas as pd

# Create sample data
df = pd.DataFrame({
    "customer_id": [1, 2, 3],
    "amount": [100, 200, 300],
    "posting_date": ["2024-01-01", "2024-02-01", "2024-03-01"]
})

# Basic probe
probe = probe_df(df, "after_load", "/tmp/probes")
print(f"Rows: {probe.rows}, Nulls: {probe.nulls_total}")

# Probe with amount tracking
probe = probe_df(df, "with_amounts", "/tmp/probes", amount_col="amount")
print(f"Total amount: {probe.amount_sum}")

# Full featured probe with snapshot
probe = probe_df(
    df, 
    "complete", 
    "/tmp/probes",
    amount_col="amount",
    date_col="posting_date",
    key_cols=["customer_id"],
    snapshot=True
)
```

## API Reference

### `DFProbe` Dataclass

A dataclass that holds all probe statistics.

**Fields:**
- `name` (str): Identifier for this probe point
- `rows` (int): Number of rows
- `cols` (int): Number of columns
- `nulls_total` (int): Total null values across all columns
- `duplicated_rows` (int): Number of duplicate rows
- `amount_sum` (float | None): Sum of amount column (if specified)
- `amount_col` (str | None): Name of amount column (if specified)
- `min_date` (str | None): Minimum date value (if specified)
- `max_date` (str | None): Maximum date value (if specified)
- `unique_keys` (dict[str, int] | None): Unique value counts for key columns

### `probe_df()` Function

Probe a DataFrame and collect statistics.

**Parameters:**
- `df` (pd.DataFrame): The DataFrame to probe
- `name` (str): Identifier for this probe point
- `out_dir` (str | Path): Directory for logs and snapshots
- `amount_col` (str | None): Column name for amount summation
- `date_col` (str | None): Column name for date range
- `key_cols` (list[str] | None): Columns to count unique values
- `snapshot` (bool): If True, save CSV snapshot (default: False)
- `snapshot_cols` (list[str] | None): Columns to include in snapshot (default: all)

**Returns:**
- `DFProbe`: Object containing all statistics

**Error Handling:**
- Missing columns are handled gracefully with warnings logged
- Non-numeric amount columns are skipped with warnings
- Invalid dates are coerced to NaT and excluded from min/max calculation

## Output Files

### probes.log

JSON-formatted log file with one entry per probe:

```json
{"timestamp": "2024-12-17T11:37:43.123456Z", "probe": {"name": "test", "rows": 100, "cols": 5, ...}}
```

### Snapshot Files

CSV files named `snapshot_{name}_{timestamp}.csv` containing DataFrame data.

## Usage Examples

### Example 1: Basic Pipeline Instrumentation

```python
# At various points in your pipeline
df = load_data()
probe_df(df, "01_after_load", "/tmp/probes")

df = apply_filters(df)
probe_df(df, "02_after_filters", "/tmp/probes")

df = calculate_balances(df)
probe_df(df, "03_final", "/tmp/probes", amount_col="balance")
```

### Example 2: Reconciliation Workflow

```python
# Track reconciliation progress
df_ipe = extract_ipe_data()
probe_df(df_ipe, "ipe_extracted", "/tmp/reconciliation", 
         amount_col="amount", snapshot=True)

df_gl = extract_gl_data()
probe_df(df_gl, "gl_extracted", "/tmp/reconciliation",
         amount_col="amount")

df_merged = merge_data(df_ipe, df_gl)
probe_df(df_merged, "merged_data", "/tmp/reconciliation",
         amount_col="amount",
         key_cols=["account", "period"])
```

### Example 3: Data Quality Monitoring

```python
# Monitor data quality
df = load_suspicious_data()
probe = probe_df(df, "quality_check", "/tmp/probes",
                 amount_col="amount",
                 date_col="posting_date",
                 key_cols=["customer_id", "document_no"])

# Check for issues
if probe.nulls_total > 0:
    print(f"Warning: {probe.nulls_total} null values found")

if probe.duplicated_rows > 0:
    print(f"Warning: {probe.duplicated_rows} duplicate rows found")
```

## Integration with Existing Code

The debug probe is designed to be non-invasive. You can add probes to existing code without refactoring:

```python
# Before
df = process_data(df)

# After (just add one line)
df = process_data(df)
probe_df(df, "after_process", "/tmp/probes")  # Add this line
```

## Handling Financial Data

The probe utility automatically handles special float values (NaN, Infinity, -Infinity) that commonly occur in financial data:

- **NaN values**: Converted to `null` in JSON output
- **Infinity values**: Converted to `null` in JSON output
- **-Infinity values**: Converted to `null` in JSON output

This ensures JSON serialization never fails when logging financial reconciliation data.

```python
import pandas as pd
import numpy as np

# DataFrame with special values
df = pd.DataFrame({
    "account": ["A", "B", "C"],
    "amount": [100.0, float('nan'), float('inf')]
})

# This will log successfully, converting NaN/Inf to null in JSON
probe = probe_df(df, "financial_data", "/tmp/probes", amount_col="amount")
```

## Performance Considerations

- Probes are lightweight and add minimal overhead
- File I/O is done synchronously (consider using sparingly in production)
- Snapshots can be large for big DataFrames (use `snapshot_cols` to limit size)

## Troubleshooting

### No output files created

Check that:
1. The output directory has write permissions
2. The function completed without errors
3. Check the logs for any error messages

### Missing statistics

Check that:
1. Column names are spelled correctly
2. Columns exist in the DataFrame
3. Check warnings in the logs for missing columns

### Snapshot files too large

Use the `snapshot_cols` parameter to include only necessary columns:

```python
probe_df(df, "large_df", "/tmp/probes", 
         snapshot=True,
         snapshot_cols=["id", "amount", "date"])
```

## Testing

Run the test suite:

```bash
pytest tests/test_debug_probe.py -v
```

Run the demonstration script:

```bash
python3 scripts/demo_debug_probe.py
```

## See Also

- `src/core/quality_checker.py` - Data quality validation framework
- `src/core/evidence/manager.py` - Digital evidence generation
- `src/core/logging_config.py` - Centralized logging configuration
