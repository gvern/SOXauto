# Evidence Package Enhancement - Implementation Summary

## Overview
This PR implements significant enhancements to the Digital Evidence Package system as requested by the audit team (João). The changes improve traceability, metadata capture, and data visibility for SOX compliance.

## Changes Implemented

### 1. System Context Tracking (NEW: `00_system_context.json`)
**Location:** `src/utils/system_utils.py`, `src/core/evidence/manager.py`

**What:** Every evidence package now includes a system context file capturing:
- `git_commit_id`: Short Git commit hash (7 characters) of the code version
- `execution_host`: Hostname of the machine running the extraction
- `python_version`: Full Python version string
- `runner_version`: "SOXauto v1.0"

**Why:** Enables complete traceability of which code version was used for each extraction, essential for audit compliance.

**Example:**
```json
{
  "git_commit_id": "a1b2c3d",
  "execution_host": "soxauto-worker-01",
  "python_version": "3.11.4 (main, Jun  7 2023, 10:13:09) [GCC 9.4.0]",
  "runner_version": "SOXauto v1.0"
}
```

### 2. Enhanced Folder Naming Convention
**Location:** `src/core/evidence/manager.py`

**What:** Evidence folders now follow the format: `{ipe_id}_{country}_{period}_{timestamp}`

**Examples:**
- `IPE_08_NG_202509_20251120_103000` (IPE 08, Nigeria, September 2025)
- `IPE_07_KE_202412_20251120_143022` (IPE 07, Kenya, December 2024)

**Fallback:** If country/period not provided, falls back to `{ipe_id}_{timestamp}`

**Why:** Makes evidence packages immediately identifiable and easier to organize by country and period. The audit team requested this for better folder organization.

### 3. Full Parameter Logging
**Location:** `src/core/runners/mssql_runner.py`

**What:** The `02_query_parameters.json` file now captures ALL SQL parameters, not just cutoff_date:
- `cutoff_date`: The cutoff date for extraction
- `gl_accounts`: GL account numbers used
- `id_companies_active`: Active company IDs
- `year`: Extraction year
- `month`: Extraction month
- Any other custom parameters passed to the runner

**Why:** Provides complete context for audit trail. Auditors need to see all parameters that influenced the query results.

**Before:**
```json
{
  "cutoff_date": "2024-05-01",
  "parameters": ["2024-05-01"]
}
```

**After:**
```json
{
  "cutoff_date": "2024-05-01",
  "parameters": ["2024-05-01"],
  "gl_accounts": "13003,13011,18350",
  "id_companies_active": "BF,CI,DZ,EG,GH,KE,MA,NG,SN,UG",
  "year": "2024",
  "month": "05"
}
```

### 4. Tail Snapshots Instead of Head
**Location:** `src/core/evidence/manager.py` (`IPEEvidenceGenerator.save_data_snapshot`)

**What:** Data snapshots now capture the LAST rows instead of the FIRST rows:
- If dataset > 1000 rows: saves `tail(1000)`
- If dataset ≤ 1000 rows: saves `tail(snapshot_rows)` (default 100)

**Why:** The audit team requested this because the most recent transactions are typically more relevant for review. Head snapshots may show old, less relevant data.

**Changes in Files:**
- `03_data_snapshot.csv`: Header now says "Snapshot Rows (TAIL): 1000"
- `04_data_summary.json`: Includes new field `"snapshot_type": "tail"`

### 5. Updated All Callers
**Locations:** 
- `scripts/run_demo.py`
- `src/orchestrators/workflow.py`
- `src/orchestrators/cpg1_activities.py`

**What:** All code that creates IPERunner instances now passes:
- `country`: Country code extracted from context
- `period`: Period in YYYYMM format (extracted from cutoff_date)
- `full_params`: Dictionary of all parameters to be logged

**Example in run_demo.py:**
```python
runner = IPERunner(
    ipe_config=ipe_config_dict, 
    secret_manager=None,
    country='NG',
    period='202511',
    full_params={
        'country_code': 'EC_NG',
        'country_name': 'Nigeria'
    }
)
```

## Test Coverage
**Location:** `tests/test_evidence_enhancements.py`

Created comprehensive test suite with 4 test classes:

1. **TestSystemUtils**: Tests git commit hash, hostname, Python version retrieval
2. **TestEvidenceManagerEnhancements**: Tests folder naming with/without country and period
3. **TestDataSnapshotEnhancements**: Tests tail snapshot logic for large and small datasets
4. **TestFullParameterLogging**: Tests that all parameters are correctly logged

All tests pass successfully and can be run with:
```bash
python3 tests/test_evidence_enhancements.py
# or
pytest tests/test_evidence_enhancements.py -v
```

## Documentation Updates
**Location:** `docs/development/evidence_documentation.md`

Updated the evidence documentation to reflect:
- New `00_system_context.json` file
- Enhanced folder naming convention
- Full parameter logging in `02_query_parameters.json`
- Tail snapshot functionality
- Examples of all new file formats

## Backward Compatibility
✅ **Fully backward compatible**
- If `country` and `period` are not provided, falls back to old naming format
- Existing code continues to work without modifications
- New parameters are optional in IPERunner constructor

## Files Modified
1. `src/utils/system_utils.py` (NEW)
2. `src/core/evidence/manager.py` (MODIFIED)
3. `src/core/runners/mssql_runner.py` (MODIFIED)
4. `scripts/run_demo.py` (MODIFIED)
5. `src/orchestrators/workflow.py` (MODIFIED)
6. `src/orchestrators/cpg1_activities.py` (MODIFIED)
7. `tests/test_evidence_enhancements.py` (NEW)
8. `docs/development/evidence_documentation.md` (MODIFIED)

## Acceptance Criteria - All Met ✅

| Requirement | Status | Implementation |
|------------|--------|----------------|
| 1. Folder naming: `{ipe_id}_{country}_{period}_{timestamp}` | ✅ | `DigitalEvidenceManager.create_evidence_package()` |
| 2. Git versioning via `00_system_context.json` | ✅ | `get_system_context()` + auto-created in evidence package |
| 3. Full parameter logging | ✅ | `IPERunner.run()` logs ALL params to `02_query_parameters.json` |
| 4. Tail snapshots (last 1000 rows) | ✅ | `IPEEvidenceGenerator.save_data_snapshot()` |
| 5. Update all callers | ✅ | Updated run_demo.py, workflow.py, cpg1_activities.py |

## Next Steps for Deployment
1. ✅ Code changes implemented and tested
2. ✅ Documentation updated
3. ✅ Tests created and passing
4. ⏳ PR ready for review
5. ⏳ Deploy to production after approval

## Notes for Reviewers
- All changes maintain backward compatibility
- New parameters are optional - existing code continues to work
- Tail snapshot logic handles both large (>1000 rows) and small datasets correctly
- Git commit hash gracefully handles cases where git is not available (returns "unknown")
- System context is captured automatically - no manual configuration needed
