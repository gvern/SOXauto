# audit_merge Function - Quick Reference

## Purpose

Detect Cartesian products (exploding joins) **before** merging DataFrames to prevent financial discrepancies.

## Quick Start

```python
from src.utils.merge_utils import audit_merge

# Before merging
result = audit_merge(
    left=ipe_df,
    right=gl_df,
    on='customer_id',
    name='reconciliation',
    out_dir='./audit_output'
)

# Check for problems
if result['has_duplicates']:
    print(f"⚠️ WARNING: Found {result['left_duplicates']} left duplicates")
    print(f"Review: {result.get('left_dup_keys_file')}")
else:
    # Safe to merge
    merged = ipe_df.merge(gl_df, on='customer_id')
```

## When to Use

✅ **Use audit_merge before:**
- Reconciling IPE data with GL actuals
- Joining transactions with categorization rules
- Combining data from multiple sources
- Any financial data merge operation

⚠️ **Critical for detecting:**
- Duplicate customer/transaction IDs
- Many-to-many relationships
- Data quality issues in source systems
- Potential amount duplication

## Files & Documentation

| File | Purpose |
|------|---------|
| `src/utils/merge_utils.py` | Core implementation |
| `tests/test_merge_utils.py` | Full test suite (16 tests) |
| `tests/test_audit_merge_smoke.py` | Quick smoke test |
| `scripts/validate_audit_merge.py` | Validation with 4 scenarios |
| `scripts/audit_merge_examples.py` | 5 production examples |
| `docs/development/MERGE_AUDIT_GUIDE.md` | Complete documentation |
| `IMPLEMENTATION_AUDIT_MERGE.md` | Implementation summary |

## Run Tests

```bash
# Full test suite
pytest tests/test_merge_utils.py -v

# Quick smoke test
python tests/test_audit_merge_smoke.py

# Validation scenarios
python scripts/validate_audit_merge.py

# See examples
python scripts/audit_merge_examples.py
```

## Output

Creates in `out_dir`:
1. `merge_audit.log` - Detailed audit log
2. `<name>.left_dup_keys.csv` - Left DataFrame duplicates (if found)
3. `<name>.right_dup_keys.csv` - Right DataFrame duplicates (if found)

## Return Value

```python
{
    'left_duplicates': 15,        # Count of duplicate rows
    'right_duplicates': 0,
    'has_duplicates': True,       # Quick flag
    'left_dup_keys_file': '...'   # CSV path (if created)
}
```

## Common Scenarios

### Scenario 1: Clean Data ✓
```python
# One-to-one relationship
left:  [C001, C002, C003]
right: [C001, C002, C003]
Result: No duplicates → Safe to merge
```

### Scenario 2: Data Quality Issue ⚠️
```python
# Duplicate in IPE extract
left:  [C001, C001, C002]  # C001 appears twice!
right: [C001, C002]
Result: Left duplicates → Investigate source system
```

### Scenario 3: Cartesian Product 🚨
```python
# Both sides have duplicates
left:  [C001, C001, C002]  # C001 appears twice
right: [C001, C001, C002]  # C001 appears twice
Result: Both duplicates → Merge will EXPLODE (2×2=4 rows for C001)
```

## Integration Example

```python
def safe_reconciliation(ipe, gl, key):
    # Audit first
    audit = audit_merge(ipe, gl, on=key, name='recon', out_dir='./audits')
    
    # Decide based on results
    if audit['has_duplicates']:
        logger.warning(f"Duplicates found: {audit}")
        # Send alert, halt process, etc.
        return None
    
    # Proceed safely
    return ipe.merge(gl, on=key)
```

## See Also

- **Full Documentation**: `docs/development/MERGE_AUDIT_GUIDE.md`
- **Implementation Details**: `IMPLEMENTATION_AUDIT_MERGE.md`
- **Issue**: Feature request for audit_merge (Labels: debug, utils, priority-high)

---

**For SOX compliance**, this audit trail should be included in the digital evidence package.
