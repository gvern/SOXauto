# Pandas Utilities - Data Type Casting

## Overview

The `pandas_utils` module provides centralized, tested utilities for normalizing numeric data types across the SOXauto reconciliation and bridge analysis pipelines.

**Location**: `src/utils/pandas_utils.py`

**Purpose**: Handle inconsistent numeric data from CSV uploads, SQL extractions, and fixtures by providing:
- Safe string-to-float coercion with comma/space stripping
- Configurable NaN filling (default: 0.0 for Amount aggregations)
- Pattern-based amount column detection
- Type validation for required columns

## The Problem

Across the reconciliation workflow, numeric "Amount" fields arrive from various sources with inconsistent dtypes:

| Source | Data Type Issues |
|--------|-----------------|
| CSV Uploads | Strings with commas: `"1,234.56"` |
| SQL Extractions | Mixed object/str, NaNs, NULL values |
| Fixtures | Inconsistent dtypes across test files |

Without standardization, these issues cause:
- ❌ Fragile calculations (TypeError on `.sum()`, `.groupby()`)
- ❌ Silent failures (NaNs propagate through calculations)
- ❌ CSV/SQL interoperability problems

## The Solution

Three core functions for explicit, testable dtype normalization:

### 1. `coerce_numeric_series()`

**Purpose**: Coerce a single Series to numeric (float64) dtype.

**Signature**:
```python
def coerce_numeric_series(
    s: pd.Series,
    *,
    fillna: Optional[float] = None,
) -> pd.Series
```

**Features**:
- Strips commas: `"1,234.56"` → `1234.56`
- Strips spaces: `" 1 234.56 "` → `1234.56`
- Handles empty strings: `""` → `NaN` (then optional fillna)
- Safe coercion: Invalid values → `NaN`
- Efficient passthrough for already-numeric data

**Example**:
```python
from src.utils.pandas_utils import coerce_numeric_series

# Messy CSV data
amounts = pd.Series(['1,234.56', '2,000', '', None, '3,456.78'])

# Clean it up
clean_amounts = coerce_numeric_series(amounts, fillna=0.0)

# Now safe for calculations
total = clean_amounts.sum()  # 6,691.34
```

### 2. `cast_amount_columns()`

**Purpose**: Cast multiple amount columns in a DataFrame.

**Signature**:
```python
def cast_amount_columns(
    df: pd.DataFrame,
    *,
    columns: Optional[List[str]] = None,
    pattern: Optional[str] = None,
    fillna: float = 0.0,
    inplace: bool = False,
) -> pd.DataFrame
```

**Features**:
- **Auto-detection**: Finds columns matching pattern (default: `r'amount'` case-insensitive)
- **Explicit list**: Specify exact columns to cast
- **Safe defaults**: Won't accidentally cast IDs, dates, or other non-numeric fields
- **Copy-by-default**: Returns new DataFrame unless `inplace=True`

**Example - Auto-detection**:
```python
from src.utils.pandas_utils import cast_amount_columns

df = pd.DataFrame({
    'Amount': ['1,234.56', '2,000'],
    'Amount_USD': ['100.5', '200'],
    'amount_lcy': ['50', '75'],
    'Customer_ID': ['C001', 'C002'],  # Won't be touched
})

# Auto-detect and cast all amount columns
df_clean = cast_amount_columns(df, fillna=0.0)

# Amount, Amount_USD, amount_lcy → float64
# Customer_ID → object (unchanged)
```

**Example - Explicit columns**:
```python
# Specify exact columns
df_clean = cast_amount_columns(
    df,
    columns=['Balance', 'Total_Amount'],
    fillna=0.0
)
```

**Example - Custom pattern**:
```python
# Match "total" in any column name
df_clean = cast_amount_columns(
    df,
    pattern=r'total',
    fillna=0.0
)
```

### 3. `ensure_required_numeric()`

**Purpose**: Validate required columns exist, coerce to numeric, and fill NaNs.

**Signature**:
```python
def ensure_required_numeric(
    df: pd.DataFrame,
    required: List[str],
    *,
    fillna: float = 0.0,
) -> pd.DataFrame
```

**Features**:
- **Strict validation**: Raises `ValueError` if any required column is missing
- **Always returns copy**: Never modifies original DataFrame
- **Use for critical columns**: Where missing data would cause errors

**Example**:
```python
from src.utils.pandas_utils import ensure_required_numeric

# Validate and clean critical columns
df_clean = ensure_required_numeric(
    df,
    required=['Amount', 'Balance'],
    fillna=0.0
)

# If 'Balance' is missing → ValueError
```

## Usage in Reconciliation Pipeline

### Summary Builder (`src/core/reconciliation/summary_builder.py`)

**Before** (manual casting, fragile):
```python
def _calculate_actuals(self):
    if amount_col:
        return float(cr_04_df[amount_col].sum())  # May fail on strings
```

**After** (robust):
```python
from src.utils.pandas_utils import coerce_numeric_series

def _calculate_actuals(self):
    if amount_col:
        amount_series = coerce_numeric_series(cr_04_df[amount_col], fillna=0.0)
        return float(amount_series.sum())  # Always works
```

### VTC Bridge (`src/bridges/calculations/vtc.py`)

**Before**:
```python
adjustment_amount = proof_df[amount_col].sum()  # May fail on mixed types
```

**After**:
```python
from src.utils.pandas_utils import coerce_numeric_series

source_vouchers_df[amount_col] = coerce_numeric_series(
    source_vouchers_df[amount_col], fillna=0.0
)
adjustment_amount = proof_df[amount_col].sum()  # Guaranteed to work
```

### Timing Bridge (`src/bridges/calculations/timing.py`)

**Before**:
```python
jdash_agg = df_jdash.groupby("voucher_id")["jdash_amount_used"].sum()
# May propagate NaNs through aggregation
```

**After**:
```python
from src.utils.pandas_utils import coerce_numeric_series

jdash_agg["Jdash_Amount_Used"] = coerce_numeric_series(
    jdash_agg["Jdash_Amount_Used"], fillna=0.0
)
# NaNs handled explicitly
```

## Best Practices

### When to use each function

| Function | Use Case |
|----------|----------|
| `coerce_numeric_series()` | Single column cleanup (most flexible) |
| `cast_amount_columns()` | Multiple columns, auto-detection, optional columns |
| `ensure_required_numeric()` | Critical columns, validation required |

### Recommended patterns

#### 1. Extract-Transform-Aggregate

```python
from src.utils.pandas_utils import cast_amount_columns

# 1. Load data (may be messy)
df = load_from_csv('data.csv')

# 2. Clean amount columns EARLY
df = cast_amount_columns(df, fillna=0.0)

# 3. Now safe to aggregate
totals = df.groupby('Category')['Amount'].sum()
```

#### 2. Validation for Critical Paths

```python
from src.utils.pandas_utils import ensure_required_numeric

# Validate before reconciliation calculations
df = ensure_required_numeric(
    df,
    required=['Amount', 'Balance'],
    fillna=0.0
)

# Now guaranteed to have numeric columns
variance = df['Amount'].sum() - df['Balance'].sum()
```

#### 3. Defensive Programming

```python
from src.utils.pandas_utils import coerce_numeric_series

# Don't trust input data types
if 'Amount' in df.columns:
    df['Amount'] = coerce_numeric_series(df['Amount'], fillna=0.0)
```

## Testing

### Unit Tests

**Location**: `tests/test_pandas_utils.py`

Covers:
- ✅ String to float conversion
- ✅ Comma handling (`"1,234.56"`)
- ✅ NaN/empty string handling
- ✅ fillna behavior
- ✅ Mixed dtype scenarios
- ✅ Negative amounts
- ✅ Already-float passthrough
- ✅ Scientific notation
- ✅ Edge cases (very large/small numbers, zero)

### Integration Tests

**Location**: `tests/test_pandas_utils_integration.py`

Covers:
- ✅ CSV-like data with edge cases
- ✅ SQL extraction scenarios with NULLs
- ✅ Multi-company extractions
- ✅ Numeric operations stability (groupby, sum, variance)
- ✅ Pivot tables, merges
- ✅ Reconciliation pipeline scenarios
- ✅ Performance with 10,000+ rows

### Pipeline Integration Tests

**Locations**:
- `tests/reconciliation/test_summary_builder.py`
- `tests/test_timing_bridge.py`

Verifies that refactored modules correctly handle:
- ✅ String amounts with commas
- ✅ NaN and empty strings
- ✅ Mixed numeric and string data
- ✅ CSV upload edge cases

### Running Tests

```bash
# Run all pandas_utils tests
pytest tests/test_pandas_utils.py -v
pytest tests/test_pandas_utils_integration.py -v

# Run integration with reconciliation pipeline
pytest tests/reconciliation/test_summary_builder.py -v
pytest tests/test_timing_bridge.py -v

# Full test suite
pytest tests/ -v
```

## Performance Considerations

### Efficient for Already-Clean Data

The utilities detect already-numeric data and short-circuit expensive operations:

```python
# Already float64 → fast passthrough
s = pd.Series([100.5, 200.0], dtype='float64')
result = coerce_numeric_series(s)  # O(1) dtype check + optional fillna
```

### Safe for Large DataFrames

- Works efficiently with 10,000+ rows (tested)
- Pattern matching on column names (not data) → O(n_columns), not O(n_rows)
- fillna is vectorized pandas operation

## Migration Guide

### Step 1: Identify Amount Calculations

Search for patterns like:
- `.sum()` on potentially non-numeric columns
- `float(df[col].sum())` with no prior casting
- `.groupby()` aggregations on amount fields
- Direct arithmetic on DataFrame columns

### Step 2: Add Imports

```python
from src.utils.pandas_utils import (
    coerce_numeric_series,
    cast_amount_columns,
    ensure_required_numeric,
)
```

### Step 3: Insert Casting Before Calculations

**Pattern 1** - Single column:
```python
# Before calculation
df[amount_col] = coerce_numeric_series(df[amount_col], fillna=0.0)
total = df[amount_col].sum()
```

**Pattern 2** - Multiple columns:
```python
# Early in function
df = cast_amount_columns(df, fillna=0.0)
# Now all amount columns are clean
```

**Pattern 3** - Required columns:
```python
# At function entry
df = ensure_required_numeric(df, required=['Amount', 'Balance'], fillna=0.0)
# Guaranteed to have these columns as float64
```

### Step 4: Update Tests

Add tests for messy data scenarios:
```python
def test_with_comma_separated_amounts(self):
    df = pd.DataFrame({'Amount': ['1,234.56', '2,000']})
    result = your_function(df)
    assert result == expected_value
```

## Troubleshooting

### Issue: "Columns not found in DataFrame"

**Cause**: Using `cast_amount_columns()` with explicit columns list, but column names don't match.

**Solution**: 
1. Check column names: `df.columns`
2. Use pattern matching instead: `cast_amount_columns(df, pattern=r'amount')`
3. Or handle column name variants in calling code

### Issue: "Required columns missing from DataFrame"

**Cause**: Using `ensure_required_numeric()` but required column doesn't exist.

**Solution**:
1. This is intentional - function is strict for critical columns
2. Either add column to DataFrame before calling
3. Or use `cast_amount_columns()` for optional columns

### Issue: Warning "Pattern matched zero columns"

**Cause**: Pattern doesn't match any column names.

**Solution**:
1. Check pattern regex: `cast_amount_columns(df, pattern=r'amount')`
2. Or explicitly list columns: `cast_amount_columns(df, columns=['Amount'])`
3. Warning is informational - no error raised

## Related Documentation

- [Testing Guide](TESTING_GUIDE.md) - General testing practices
- [Reconciliation Flow](RECONCILIATION_FLOW.md) - Where casting fits in pipeline
- [Date Utils](DATE_UTILS.md) - Similar utility module for date handling

## References

- **Issue**: GitHub Issue tracking this implementation
- **PR**: Pull request with full implementation
- **Google Sheet**: Line 3.03 (PHASE 3: RECONCILIATION → Normalization → Data Type Casting)

---

**Last Updated**: 2026-01-08  
**Author**: SOXauto Development Team
