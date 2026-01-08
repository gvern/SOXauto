# Date Normalization Utilities

**Module**: `src/utils/date_utils.py`  
**Created**: 2026-01-08  
**Purpose**: Centralized date parsing and normalization for consistent behavior across the codebase

---

## Overview

The date_utils module provides a single, tested API for date parsing and normalization, eliminating ad-hoc `pd.to_datetime()` and `datetime.strptime()` patterns that led to inconsistent behavior.

### Problem Solved

Before centralization:
- ❌ Inconsistent timezone/normalization behavior
- ❌ Duplicated date parsing logic across modules
- ❌ Custom month-end calculations with potential bugs
- ❌ Multiple validation patterns (regex + strptime)

After centralization:
- ✅ Single source of truth for date operations
- ✅ Consistent midnight normalization
- ✅ Correct leap year handling
- ✅ Strict YYYY-MM-DD validation
- ✅ Comprehensive test coverage

---

## Public API

### Core Functions

#### `parse_date(value, *, tz=None) -> pd.Timestamp`
Parse various date inputs (str, date, datetime, pd.Timestamp) to pd.Timestamp.

```python
from src.utils.date_utils import parse_date

# From string
ts = parse_date("2024-10-31")
# Timestamp('2024-10-31 00:00:00')

# From date object
from datetime import date
ts = parse_date(date(2024, 10, 31))

# With timezone
ts = parse_date("2024-10-31", tz="UTC")
```

#### `normalize_date(value, *, tz=None) -> pd.Timestamp`
Parse and normalize to midnight (00:00:00). **Use this for cutoff dates.**

```python
from src.utils.date_utils import normalize_date

# Strips time component
cutoff = normalize_date("2024-10-31 14:30:00")
# Timestamp('2024-10-31 00:00:00')
```

#### `month_start(value) -> pd.Timestamp`
Get first day of month.

```python
from src.utils.date_utils import month_start

start = month_start("2024-10-15")
# Timestamp('2024-10-01 00:00:00')
```

#### `month_end(value) -> pd.Timestamp`
Get last day of month (handles leap years).

```python
from src.utils.date_utils import month_end

# Leap year
end = month_end("2024-02-10")
# Timestamp('2024-02-29 00:00:00')

# Non-leap year
end = month_end("2023-02-10")
# Timestamp('2023-02-28 00:00:00')
```

#### `validate_yyyy_mm_dd(value: str) -> None`
Strict YYYY-MM-DD validation. **Use for input validation.**

```python
from src.utils.date_utils import validate_yyyy_mm_dd

# Valid - no exception
validate_yyyy_mm_dd("2024-10-31")

# Invalid format - raises ValueError
validate_yyyy_mm_dd("2024/10/31")  # Wrong separator

# Invalid date - raises ValueError
validate_yyyy_mm_dd("2024-02-30")  # Doesn't exist
```

#### `format_yyyy_mm_dd(value) -> str`
Format any date type to YYYY-MM-DD string.

```python
from src.utils.date_utils import format_yyyy_mm_dd

formatted = format_yyyy_mm_dd(date(2024, 10, 31))
# '2024-10-31'
```

---

## Refactored Modules

The following modules now use the centralized date utilities:

### 1. `src/bridges/calculations/timing.py`

**Before:**
```python
cutoff_dt = pd.to_datetime(cutoff_date).normalize()
```

**After:**
```python
from src.utils.date_utils import normalize_date
cutoff_dt = normalize_date(cutoff_date)
```

### 2. `src/bridges/calculations/vtc.py`

**Before:**
```python
cutoff_dt = pd.to_datetime(cutoff_date)
month_start = cutoff_dt.replace(day=1)
if cutoff_dt.month == 12:
    month_end = cutoff_dt.replace(year=cutoff_dt.year + 1, month=1, day=1) - pd.Timedelta(days=1)
else:
    month_end = cutoff_dt.replace(month=cutoff_dt.month + 1, day=1) - pd.Timedelta(days=1)
```

**After:**
```python
from src.utils.date_utils import normalize_date, month_start, month_end
cutoff_dt = normalize_date(cutoff_date)
month_start_dt = month_start(cutoff_dt)
month_end_dt = month_end(cutoff_dt)
```

### 3. `src/core/reconciliation/run_reconciliation.py`

**Before:**
```python
try:
    datetime.strptime(params['cutoff_date'], '%Y-%m-%d')
except ValueError:
    errors.append("'cutoff_date' must be in YYYY-MM-DD format")
```

**After:**
```python
from src.utils.date_utils import validate_yyyy_mm_dd
try:
    validate_yyyy_mm_dd(params['cutoff_date'])
except ValueError as e:
    errors.append(f"Invalid cutoff_date: {e}")
```

### 4. `src/core/runners/mssql_runner.py`

**Before:**
```python
import re
if not re.match(r'^\d{4}-\d{2}-\d{2}$', cutoff_date):
    raise ValueError(f"Invalid cutoff_date format: {cutoff_date}. Expected YYYY-MM-DD")
try:
    datetime.strptime(cutoff_date, '%Y-%m-%d')
except ValueError as e:
    raise ValueError(f"Invalid cutoff_date value: {cutoff_date}. {e}")
```

**After:**
```python
from src.utils.date_utils import validate_yyyy_mm_dd
try:
    validate_yyyy_mm_dd(cutoff_date)
except ValueError as e:
    raise ValueError(f"Invalid cutoff_date: {e}")
```

### 5. `src/frontend/app.py`

**Before:**
```python
params = {
    "cutoff_date": cutoff_date.strftime("%Y-%m-%d"),
    "year_end": cutoff_date.strftime("%Y-%m-%d"),
}
```

**After:**
```python
from src.utils.date_utils import format_yyyy_mm_dd
params = {
    "cutoff_date": format_yyyy_mm_dd(cutoff_date),
    "year_end": format_yyyy_mm_dd(cutoff_date),
}
```

---

## Testing

### Unit Tests
Location: `tests/test_date_utils.py`

Coverage:
- ✅ Parsing various input formats
- ✅ Normalization to midnight
- ✅ Month start/end calculations
- ✅ Leap year handling (Feb 29)
- ✅ All 12 months
- ✅ Year boundaries
- ✅ Invalid format detection
- ✅ Invalid date detection
- ✅ Timezone handling (optional)

Run tests:
```bash
pytest tests/test_date_utils.py -v
```

### Integration Tests
Location: `tests/test_date_utils_integration.py`

Coverage:
- ✅ Timing bridge uses normalize_date correctly
- ✅ VTC bridge uses month_start/month_end correctly
- ✅ Reconciliation uses validate_yyyy_mm_dd correctly
- ✅ Cross-module consistency

Run tests:
```bash
pytest tests/test_date_utils_integration.py -v
```

---

## Design Principles

### 1. Timezone-Naive by Default
All functions return timezone-naive timestamps unless `tz` parameter is explicitly provided.

**Rationale**: Most SOX reconciliations use cutoff dates without timezones. Explicit opt-in for timezone-aware timestamps prevents confusion.

### 2. Fail Loudly
All functions raise clear exceptions for invalid inputs. No silent coercion.

**Rationale**: Date errors in financial reconciliation can lead to incorrect results. Better to fail fast with clear error messages.

### 3. Normalization Always Returns Midnight
`normalize_date()` always returns 00:00:00 time component.

**Rationale**: Consistent comparison behavior across modules. No ambiguity about whether a date includes time.

### 4. Month End Handles All Edge Cases
Uses pandas `MonthEnd` offset for correct leap year and month length handling.

**Rationale**: Manual calculations are error-prone. Pandas has robust, tested logic.

---

## Common Use Cases

### Cutoff Date Validation
```python
from src.utils.date_utils import validate_yyyy_mm_dd

def process_reconciliation(cutoff_date: str):
    # Validate input
    validate_yyyy_mm_dd(cutoff_date)
    
    # Now safe to use
    # ...
```

### Reconciliation Month Window
```python
from src.utils.date_utils import normalize_date, month_start, month_end

cutoff_date = "2024-09-30"

cutoff_dt = normalize_date(cutoff_date)
start = month_start(cutoff_dt)
end = month_end(cutoff_dt)

# Filter data
df_filtered = df[
    (df['date'] >= start) & 
    (df['date'] <= end)
]
```

### Rolling 1-Year Window
```python
from src.utils.date_utils import normalize_date
import pandas as pd

cutoff_date = "2025-09-30"
cutoff_dt = normalize_date(cutoff_date)

# Start from 1st of next month, minus 1 year
next_month_first = (cutoff_dt.replace(day=1) + pd.DateOffset(months=1))
start_dt = next_month_first - pd.DateOffset(years=1)

# Window: 2024-10-01 to 2025-09-30
```

---

## Best Practices

### DO ✅

```python
# Use normalize_date for cutoff dates
cutoff = normalize_date(params['cutoff_date'])

# Use validate_yyyy_mm_dd for input validation
validate_yyyy_mm_dd(user_input)

# Use month_start/month_end instead of manual calculation
start = month_start(cutoff)
end = month_end(cutoff)

# Use format_yyyy_mm_dd for consistent output
formatted = format_yyyy_mm_dd(some_date)
```

### DON'T ❌

```python
# Don't use pd.to_datetime directly
cutoff = pd.to_datetime(cutoff_date).normalize()  # ❌

# Don't use datetime.strptime for validation
datetime.strptime(cutoff_date, '%Y-%m-%d')  # ❌

# Don't calculate month boundaries manually
month_end = cutoff.replace(month=cutoff.month + 1, day=1) - pd.Timedelta(days=1)  # ❌

# Don't use .strftime() directly
formatted = some_date.strftime('%Y-%m-%d')  # ❌
```

---

## Migration Notes

If you're updating existing code:

1. **Add import**: `from src.utils.date_utils import normalize_date, validate_yyyy_mm_dd, ...`
2. **Replace patterns**: See "Refactored Modules" section above for examples
3. **Run tests**: Verify behavior hasn't changed
4. **Remove old code**: Delete duplicated validation/normalization logic

---

## Future Enhancements

Potential additions (not currently needed):

- `parse_date_range()` - Parse date ranges like "2024-01 to 2024-03"
- `business_days_between()` - Calculate business days between dates
- `fiscal_year_start()` / `fiscal_year_end()` - Fiscal year calculations
- `quarter_start()` / `quarter_end()` - Quarter boundary calculations

Add these only if multiple modules need them. Keep the module focused.

---

## Troubleshooting

### Error: "Date string does not match YYYY-MM-DD format"
**Cause**: Using wrong separator (e.g., `/` instead of `-`) or wrong format (e.g., `DD-MM-YYYY`)

**Fix**: Use strict `YYYY-MM-DD` format: `"2024-10-31"`

### Error: "Invalid date value"
**Cause**: Date doesn't exist (e.g., `2024-02-30`, `2023-02-29`)

**Fix**: Check month has enough days, verify leap year for Feb 29

### Error: "Unsupported date type"
**Cause**: Passing unsupported type (e.g., integer, float)

**Fix**: Convert to string, date, datetime, or pd.Timestamp first

---

## References

- **Implementation**: `src/utils/date_utils.py`
- **Unit Tests**: `tests/test_date_utils.py`
- **Integration Tests**: `tests/test_date_utils_integration.py`
- **Issue**: GitHub Issue #XX (Add centralized date normalization utilities)

---

**Maintained By**: SOXauto Development Team  
**Last Updated**: 2026-01-08  
**Status**: ✅ Active - Production Ready
