# Implementation Summary: Company Subfolder Fixture Loading

## Overview

This implementation adds support for organizing test fixtures into company-specific subfolders, enabling cleaner separation of test data for different entities (EC_NG, JD_GH, etc.) while maintaining backward compatibility with the existing single-folder structure.

## Problem Statement

Previously, all fixture files were stored in a single `tests/fixtures/` directory:
```
tests/fixtures/
├── fixture_IPE_07.csv
├── fixture_IPE_08.csv
├── fixture_CR_03.csv
└── fixture_JDASH.csv
```

This made it difficult to:
1. Test multiple companies with different datasets
2. Organize company-specific vs shared reference data
3. Maintain separate fixture sets for different entities

## Solution

Implemented a two-tier fixture lookup system that supports company subfolders:

```
tests/fixtures/
├── EC_NG/                    # Nigeria-specific
│   ├── fixture_IPE_07.csv
│   ├── fixture_IPE_08.csv
│   └── fixture_JDASH.csv
├── JD_GH/                    # Ghana-specific
│   ├── fixture_IPE_07.csv
│   └── fixture_JDASH.csv
└── fixture_CR_05.csv         # Shared FX rates
```

## Implementation Details

### 1. ExtractionPipeline (src/core/extraction_pipeline.py)

**Modified Method**: `_load_fixture(item_id: str) -> pd.DataFrame`

**Logic**:
1. **Priority 1**: Try `tests/fixtures/{company}/fixture_{item_id}.csv`
2. **Priority 2**: Fallback to `tests/fixtures/fixture_{item_id}.csv`
3. **Priority 3**: Return empty DataFrame

**Key Code**:
```python
# Priority 1: Try company-specific subfolder
if self.country_code:
    company_fixture_path = os.path.join(
        REPO_ROOT, "tests", "fixtures", self.country_code, f"fixture_{item_id}.csv"
    )
    if os.path.exists(company_fixture_path):
        return pd.read_csv(company_fixture_path, low_memory=False)

# Priority 2: Fallback to root fixtures directory
root_fixture_path = os.path.join(
    REPO_ROOT, "tests", "fixtures", f"fixture_{item_id}.csv"
)
if os.path.exists(root_fixture_path):
    return pd.read_csv(root_fixture_path, low_memory=False)

# Priority 3: Not found
return pd.DataFrame()
```

### 2. JDASH Loader (src/core/jdash_loader.py)

**Modified Function**: `load_jdash_data(source, fixture_fallback, company)`

**Changes**:
- Added `company: Optional[str] = None` parameter
- Implemented same two-tier lookup as ExtractionPipeline
- Maintains backward compatibility (company parameter is optional)

**Key Code**:
```python
# Priority 1: Try company-specific subfolder
if company:
    company_fixture_path = os.path.join(REPO_ROOT, "tests", "fixtures", company, "fixture_JDASH.csv")
    if os.path.exists(company_fixture_path):
        df = pd.read_csv(company_fixture_path, low_memory=False)
        return _normalize_jdash_columns(df), f"Local Fixture ({company})"

# Priority 2: Fallback to root fixtures directory
root_fixture_path = os.path.join(REPO_ROOT, "tests", "fixtures", "fixture_JDASH.csv")
if os.path.exists(root_fixture_path):
    df = pd.read_csv(root_fixture_path, low_memory=False)
    return _normalize_jdash_columns(df), "Local Fixture"
```

## How It Works

### Scenario 1: Running with Company Parameter

```bash
python scripts/run_headless_test.py --company EC_NG --cutoff-date 2025-09-30
```

**Flow**:
1. System extracts `country_code = "EC_NG"` from `--company EC_NG`
2. For each IPE (e.g., IPE_07):
   - First looks in: `tests/fixtures/EC_NG/fixture_IPE_07.csv` ✅
   - If not found, tries: `tests/fixtures/fixture_IPE_07.csv`
   - If still not found: returns empty DataFrame
3. For shared files (e.g., CR_05):
   - First looks in: `tests/fixtures/EC_NG/fixture_CR_05.csv` (not found)
   - Then tries: `tests/fixtures/fixture_CR_05.csv` ✅ (found - shared file)

### Scenario 2: Backward Compatibility (No Subfolders)

```bash
python scripts/run_headless_test.py --company EC_NG --cutoff-date 2025-09-30
```

If no company subfolders exist:
- System tries: `tests/fixtures/EC_NG/fixture_IPE_07.csv` (not found)
- Fallback to: `tests/fixtures/fixture_IPE_07.csv` ✅ (found)
- **Result**: Works exactly as before!

## Testing

Created comprehensive test suite: `tests/test_fixture_subfolder_loading.py`

**Test Coverage**:
1. ✅ Loading from company subfolder when available
2. ✅ Fallback to root fixtures when company file not found
3. ✅ Empty DataFrame when file not found in either location
4. ✅ Preference for company subfolder over root
5. ✅ JDASH loader with company parameter
6. ✅ JDASH fallback behavior
7. ✅ JDASH preference for company over root

**Run Tests**:
```bash
pytest tests/test_fixture_subfolder_loading.py -v
```

## Documentation

### Created:
1. **tests/FIXTURE_SETUP_GUIDE.md** - Complete setup instructions with examples
2. **Updated tests/fixtures_README.md** - Directory structure and loading priority
3. **Updated .gitignore** - Allow README files in fixtures directories

### Key Documentation Sections:
- Directory structure diagram
- Setup instructions
- Usage examples
- Troubleshooting guide
- Security notes

## Benefits

### 1. Better Organization
- Separate test data by company/entity
- Clear distinction between company-specific and shared files

### 2. Multi-Entity Testing
- Easy to test EC_NG, JD_GH, EC_KE with different datasets
- No file naming conflicts

### 3. Maintainability
- Shared reference files (FX rates) in one place
- Company-specific overrides when needed

### 4. Backward Compatibility
- Zero breaking changes
- Works with existing single-folder structure
- Gradual migration path

## Migration Path

### For Existing Users:
**Option 1**: Do nothing - system still works with existing structure

**Option 2**: Organize by company:
```bash
# Create company directories
mkdir -p tests/fixtures/EC_NG
mkdir -p tests/fixtures/JD_GH

# Move company-specific files
mv tests/fixtures/fixture_IPE_07.csv tests/fixtures/EC_NG/
mv tests/fixtures/fixture_IPE_08.csv tests/fixtures/EC_NG/

# Keep shared files in root
# tests/fixtures/fixture_CR_05.csv stays in root
```

## Acceptance Criteria - Status

✅ **Path Resolution**: When engine receives `--company EC_NG`, it defines fixture_dir as `tests/fixtures/EC_NG/`

✅ **Fallback Logic**: If file not found in company subfolder, checks root `tests/fixtures/`

✅ **JDash Loading**: JDash loader looks in `tests/fixtures/{company}/fixture_JDASH.csv` first

✅ **Backward Compatible**: Works with existing single-folder structure

✅ **Error Handling**: Returns empty DataFrame (not FileNotFoundError) when file missing

## Technical Notes

### Country Code Extraction
- From params: `id_companies_active = "('EC_NG')"` → `country_code = "EC_NG"`
- Handles quotes and parentheses: `.strip("()'")`

### File Naming Convention
- Pattern: `fixture_{ITEM_ID}.csv`
- Examples: `fixture_IPE_07.csv`, `fixture_JDASH.csv`, `fixture_CR_05.csv`

### Logging
- Logs which path was used (company subfolder vs root)
- Helps debugging fixture loading issues
- Example: `"Loading fixture for IPE_07 from company subfolder: tests/fixtures/EC_NG/fixture_IPE_07.csv"`

## Performance Impact

**Negligible**: 
- Two `os.path.exists()` checks at most per fixture
- No performance degradation for existing single-folder setup
- Minimal overhead for subfolder lookups

## Security

- Fixtures remain gitignored (no sensitive data in repo)
- Only README files allowed in fixtures directories
- Maintains existing security posture

## Future Enhancements

Potential improvements:
1. Auto-create fixture directories on first run
2. Fixture validation tool to check completeness
3. Fixture generation script from live database
4. Multiple fallback levels (company → region → global)

## Conclusion

This implementation successfully adds company subfolder support for fixture loading while maintaining 100% backward compatibility. The system now supports both organizational structures:

**New (Organized)**:
```
tests/fixtures/EC_NG/fixture_IPE_07.csv
tests/fixtures/fixture_CR_05.csv
```

**Old (Flat)**:
```
tests/fixtures/fixture_IPE_07.csv
tests/fixtures/fixture_CR_05.csv
```

Both work seamlessly without any code changes required by users.
