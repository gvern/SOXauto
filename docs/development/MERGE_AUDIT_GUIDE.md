# Merge Audit Utility Documentation

## Overview

The `audit_merge` function is a pre-merge validation tool designed to detect **Cartesian products** (exploding joins) before they happen. This is critical in financial reconciliation where duplicate amount lines can cause major discrepancies.

## Problem Statement

In SOX compliance work, "exploding joins" occur when merging DataFrames with many-to-many relationships. For example:

```python
# IPE data with duplicate customer entries
ipe = pd.DataFrame({
    'customer_id': [1, 1, 2],  # Customer 1 appears twice
    'amount': [500, 600, 2000]
})

# GL data  
gl = pd.DataFrame({
    'customer_id': [1, 2],
    'gl_balance': [1100, 2000]
})

# Merge without audit - DANGEROUS!
result = ipe.merge(gl, on='customer_id')
# Result has 3 rows: customer 1 appears TWICE with the same GL balance
# This duplicates the GL balance amount, causing reconciliation errors!
```

## Solution: `audit_merge`

The `audit_merge` function analyzes both DataFrames **before** merging to detect duplicates on the join keys.

## Usage

### Basic Usage

```python
from src.utils.merge_utils import audit_merge

# Before merging, audit the operation
result = audit_merge(
    left=ipe_df,
    right=gl_df,
    on='customer_id',
    name='ipe_gl_reconciliation',
    out_dir='./audit_output'
)

# Check the results
if result['has_duplicates']:
    print("⚠️ WARNING: Duplicates detected!")
    print(f"Left duplicates: {result['left_duplicates']}")
    print(f"Right duplicates: {result['right_duplicates']}")
    # Review the exported CSV files before proceeding
else:
    # Safe to merge
    merged_df = ipe_df.merge(gl_df, on='customer_id')
```

### Multiple Join Keys

```python
result = audit_merge(
    left=sales_df,
    right=inventory_df,
    on=['customer_id', 'product_id'],  # Composite key
    name='sales_inventory_join',
    out_dir='./audit_output'
)
```

### Integration in Workflow

```python
def safe_merge(left, right, on, name):
    """Wrapper function that audits before merging."""
    # Audit first
    audit_result = audit_merge(left, right, on, name, out_dir='./merge_audits')
    
    # Warn if duplicates found
    if audit_result['has_duplicates']:
        print(f"⚠️ WARNING: Merge '{name}' has duplicates!")
        print(f"  Left: {audit_result['left_duplicates']} duplicate rows")
        print(f"  Right: {audit_result['right_duplicates']} duplicate rows")
        print(f"  Check CSV files in ./merge_audits/")
    
    # Proceed with merge (with warning in place)
    return left.merge(right, on=on)

# Use it
result = safe_merge(ipe_df, gl_df, on='customer_id', name='reconciliation')
```

## Output Files

The function creates several output files in the specified `out_dir`:

### 1. `merge_audit.log`

Detailed audit log with timestamps:

```
2025-12-17 10:30:15 - merge_audit - INFO - === Merge Audit: ipe_gl_reconciliation ===
2025-12-17 10:30:15 - merge_audit - INFO - Join keys: ['customer_id']
2025-12-17 10:30:15 - merge_audit - INFO - Left DataFrame shape: (150, 5)
2025-12-17 10:30:15 - merge_audit - INFO - Right DataFrame shape: (120, 3)
2025-12-17 10:30:15 - merge_audit - INFO - Left DataFrame: 15 duplicate rows across 7 unique keys
2025-12-17 10:30:15 - merge_audit - WARNING - ⚠️ Left duplicates found! Exported to: ./audit_output/ipe_gl_reconciliation.left_dup_keys.csv
2025-12-17 10:30:15 - merge_audit - WARNING - ✗ Merge audit FAILED: Duplicates detected
```

### 2. `<name>.left_dup_keys.csv`

Full export of all rows from the left DataFrame that have duplicate keys. This lets you inspect:
- Which keys are duplicated
- How many times each appears
- What values differ between duplicates

### 3. `<name>.right_dup_keys.csv`

Same as above, but for the right DataFrame.

## Return Value

The function returns a dictionary with audit results:

```python
{
    'left_duplicates': 15,           # Number of duplicate rows in left
    'right_duplicates': 0,            # Number of duplicate rows in right
    'left_total_rows': 150,           # Total rows in left DataFrame
    'right_total_rows': 120,          # Total rows in right DataFrame
    'left_unique_dup_keys': 7,        # Number of unique keys with duplicates
    'right_unique_dup_keys': 0,       # Number of unique keys with duplicates
    'has_duplicates': True,           # Quick flag: any duplicates found?
    'left_dup_keys_file': './audit_output/ipe_gl_reconciliation.left_dup_keys.csv'  # CSV path (if created)
}
```

## Use Cases in SOXauto

### 1. IPE-to-GL Reconciliation

```python
# Before reconciling IPE data with GL
audit_merge(
    left=ipe_07_df,      # Customer balances
    right=nav_gl_df,      # GL actuals
    on='customer_id',
    name='ipe07_gl_recon',
    out_dir='./evidence/IPE_07/merge_audits'
)
```

### 2. Bridge Analysis

```python
# Before joining transactions with categorization
audit_merge(
    left=ipe_31_transactions,
    right=bridge_rules_df,
    on=['transaction_type', 'status'],
    name='bridge_classification',
    out_dir='./bridges/audits'
)
```

### 3. Multi-Source Data Validation

```python
# Before combining BOB and NAV data
audit_merge(
    left=bob_vouchers_df,    # IPE_08
    right=nav_vouchers_df,   # CR_03
    on='voucher_id',
    name='voucher_matching',
    out_dir='./reconciliation/voucher_audits'
)
```

## Best Practices

1. **Always audit before merging** financial data
2. **Review CSV files** when duplicates are detected
3. **Store audit logs** in the evidence package for SOX compliance
4. **Use descriptive names** for the `name` parameter (helps in logs)
5. **Investigate root causes** of duplicates rather than just ignoring them

## Common Duplicate Scenarios

### Scenario 1: One-to-Many Relationship (Expected)
- Left: Customer master data (1 row per customer)
- Right: Transactions (multiple rows per customer)
- Result: Right duplicates expected, left should be clean

### Scenario 2: Data Quality Issue (Unexpected)
- Left: IPE extraction has duplicate customer entries
- Right: GL has one entry per customer
- Result: Left duplicates indicate data quality problem in source system

### Scenario 3: Cartesian Product (Dangerous!)
- Left: Multiple transactions per customer
- Right: Multiple GL entries per customer
- Result: Both have duplicates on `customer_id` → merge will explode!

## Technical Details

- **Duplicate Detection**: Uses `pandas.DataFrame.duplicated()` with `keep=False` to identify all duplicate rows
- **Performance**: O(n log n) for sorting/grouping; efficient even for large datasets
- **Memory**: Creates copies only of duplicate rows for export, not entire DataFrames
- **Thread Safety**: Each audit creates its own log handlers to avoid conflicts

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest tests/test_merge_utils.py -v

# Run specific test
pytest tests/test_merge_utils.py::TestAuditMerge::test_cartesian_risk -v

# Quick validation script
python scripts/validate_audit_merge.py
```

## See Also

- Issue #[number]: Feature request for audit_merge
- `src/bridges/classifier.py`: Example usage in bridge classification
- `docs/development/DATA_QUALITY.md`: Data quality guidelines
