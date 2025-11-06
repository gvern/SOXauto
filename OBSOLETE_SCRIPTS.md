# Obsolete Scripts - Deletion Proposal

## Overview

With the migration to Temporal.io workflow orchestration, several script-based orchestration files have become obsolete. This document proposes their deletion and provides migration guidance.

## Scripts Proposed for Deletion

### 1. `scripts/generate_customer_accounts.py`

**Status**: ❌ **OBSOLETE**

**Reason**: This script's functionality has been replaced by the Temporal activity `execute_ipe_query_activity("IPE_07")` in `src/orchestrators/cpg1_activities.py`.

**Migration Path**:
- The workflow automatically executes IPE_07 queries as part of the C-PG-1 reconciliation workflow
- Evidence generation is handled by the IPERunner within the activity
- All validation logic is preserved

**Before** (old script):
```bash
python scripts/generate_customer_accounts.py
```

**After** (Temporal workflow):
```python
# Automatically executed as part of workflow
ipe_07_result = await workflow.execute_activity(
    execute_ipe_query_activity,
    args=["IPE_07", cutoff_date],
    ...
)
```

---

### 2. `scripts/generate_collection_accounts.py`

**Status**: ❌ **OBSOLETE**

**Reason**: This script's functionality has been replaced by the Temporal activity `execute_ipe_query_activity("IPE_31")` in `src/orchestrators/cpg1_activities.py`.

**Migration Path**:
- The workflow automatically executes IPE_31 queries as part of the C-PG-1 reconciliation workflow
- Evidence generation is handled by the IPERunner within the activity
- All validation logic is preserved

**Before** (old script):
```bash
python scripts/generate_collection_accounts.py
```

**After** (Temporal workflow):
```python
# Automatically executed as part of workflow
ipe_31_result = await workflow.execute_activity(
    execute_ipe_query_activity,
    args=["IPE_31", cutoff_date],
    ...
)
```

---

### 3. `scripts/generate_other_ar.py`

**Status**: ❌ **OBSOLETE**

**Reason**: This script's functionality has been replaced by multiple Temporal activities that execute IPE_10 (Customer Prepayments) and IPE_08 (Voucher Liabilities) queries.

**Migration Path**:
- The workflow automatically executes IPE_10 and IPE_08 queries as part of the C-PG-1 reconciliation workflow
- Each IPE is executed as a separate activity for better observability and retry logic
- Evidence generation is handled by the IPERunner within each activity

**Before** (old script):
```bash
python scripts/generate_other_ar.py
```

**After** (Temporal workflow):
```python
# Automatically executed as part of workflow
ipe_10_result = await workflow.execute_activity(
    execute_ipe_query_activity,
    args=["IPE_10", cutoff_date],
    ...
)

ipe_08_result = await workflow.execute_activity(
    execute_ipe_query_activity,
    args=["IPE_08", cutoff_date],
    ...
)
```

---

### 4. `scripts/classify_bridges.py`

**Status**: ❌ **OBSOLETE**

**Reason**: This script's functionality has been replaced by the Temporal activity `classify_bridges_activity()` in `src/orchestrators/cpg1_activities.py`.

**Migration Path**:
- The workflow automatically applies bridge classification as part of the C-PG-1 reconciliation workflow
- Classification rules are loaded from the same catalog (`src/bridges/catalog.py`)
- Results are saved as evidence within the workflow

**Before** (old script):
```bash
python scripts/classify_bridges.py
```

**After** (Temporal workflow):
```python
# Automatically executed as part of workflow
classified_result = await workflow.execute_activity(
    classify_bridges_activity,
    args=[ipe_31_result["data"], None],
    ...
)
```

---

## Verification Checklist

Before deleting these scripts, verify:

- ✅ All tests pass (including `test_temporal_setup.py`)
- ✅ Temporal workflow successfully executes all steps
- ✅ Evidence generation works correctly
- ✅ All classification rules are applied correctly
- ✅ No other scripts or tools depend on these files
- ✅ Documentation has been updated to reflect new workflow

## Deletion Instructions

Once verification is complete, delete these files:

```bash
# Delete obsolete scripts
git rm scripts/generate_customer_accounts.py
git rm scripts/generate_collection_accounts.py
git rm scripts/generate_other_ar.py
git rm scripts/classify_bridges.py

# Commit the deletion
git commit -m "Remove obsolete script-based orchestration files

These scripts have been replaced by Temporal.io workflow orchestration:
- generate_customer_accounts.py → execute_ipe_query_activity('IPE_07')
- generate_collection_accounts.py → execute_ipe_query_activity('IPE_31')
- generate_other_ar.py → execute_ipe_query_activity('IPE_10', 'IPE_08')
- classify_bridges.py → classify_bridges_activity()

See src/orchestrators/README.md for migration details."
```

## Rollback Plan

If issues are discovered after deletion:

1. **Short-term**: Restore files from git history
   ```bash
   git checkout <commit-before-deletion> -- scripts/generate_customer_accounts.py
   ```

2. **Long-term**: Fix the Temporal workflow implementation to address the issue

## Benefits of Deletion

1. **Reduced Maintenance**: Fewer files to maintain
2. **Clearer Architecture**: Single source of truth for orchestration logic
3. **Better Error Handling**: Temporal provides automatic retries and error recovery
4. **Improved Observability**: Temporal UI shows execution status
5. **No Duplication**: Eliminates duplicate code paths

## Related Files to Keep

These files should **NOT** be deleted as they are still used:

- ✅ `scripts/run_full_reconciliation.py` - Now the Temporal workflow starter
- ✅ `scripts/check_mssql_connection.py` - Still useful for testing DB connectivity
- ✅ `scripts/validate_ipe_config.py` - Still useful for validating IPE configurations
- ✅ `scripts/run_demo.py` - Demo script, not part of production workflow
- ✅ `scripts/database_ingestion.py` - Separate utility script
- ✅ `scripts/run_sql_from_catalog.py` - Separate utility script

## Timeline

Recommended deletion timeline:

1. **Week 1**: Complete migration and testing
2. **Week 2**: Run production workflows using Temporal
3. **Week 3**: Monitor for issues
4. **Week 4**: Delete obsolete scripts if no issues found

## Questions?

For questions about this proposal or the migration:
1. Review `src/orchestrators/README.md`
2. Check Temporal UI for workflow execution details
3. Contact the development team
