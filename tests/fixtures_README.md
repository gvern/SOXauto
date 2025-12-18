# Test Fixtures for SOXauto

This directory contains test fixture data files used by the test suite and demo scripts.

## Fixture Organization (Company Subfolders)

**NEW**: Fixtures are now organized by company/entity to support multi-entity testing.

### Directory Structure

```
tests/fixtures/
├── EC_NG/                    # Nigeria-specific fixtures
│   ├── fixture_IPE_07.csv
│   ├── fixture_IPE_08.csv
│   ├── fixture_CR_03.csv
│   └── fixture_JDASH.csv
├── JD_GH/                    # Ghana-specific fixtures
│   ├── fixture_IPE_07.csv
│   ├── fixture_IPE_08.csv
│   └── fixture_JDASH.csv
└── fixture_CR_05.csv         # Shared/reference files (FX rates, etc.)
```

### Loading Priority

When running reconciliation with `--company EC_NG`:
1. **First**: Looks for `tests/fixtures/EC_NG/fixture_{item_id}.csv`
2. **Then**: Falls back to `tests/fixtures/fixture_{item_id}.csv` (for shared files)
3. **Finally**: Returns empty DataFrame if not found in either location

**Shared files** (like FX rates) can be placed in the root `tests/fixtures/` directory
and will be accessible to all companies.

## Required Fixture Files

The following CSV fixture files are required for running tests and demos:

### 1. fixture_CR_05.csv
**Purpose:** FX Rates for currency conversion  
**Required Columns:**
- `Company_Code` (str): Company identifier (e.g., 'JD_GH', 'EC_NG')
- `Company_Name` (str): Company name (optional)
- `FX_rate` (float): Exchange rate (Local Currency / USD)
- `rate_type` (str): Rate type (e.g., 'Closing')
- `year` (int): Year of the rate
- `cod_month` (int): Month of the rate

**Sample Data:**
```csv
Company_Code,Company_Name,FX_rate,rate_type,year,cod_month
JD_GH,Jumia Ghana,15.5,Closing,2025,9
EC_NG,Jumia Nigeria,1650.0,Closing,2025,9
EC_KE,Jumia Kenya,142.0,Closing,2025,9
JM_EG,Jumia Egypt,48.9,Closing,2025,9
```

### 2. fixture_CR_03.csv
**Purpose:** NAV GL Entries for reconciliation  
**Required Columns:**
- `id_company` or `ID_COMPANY` (str): Company code
- `Amount` (float): Transaction amount
- `[Voucher No_]` (str): Voucher number
- `Chart of Accounts No_` (str): GL account number
- `Bal_ Account Type` (str): Balance account type
- `User ID` (str): User ID
- `Document Description` (str): Description
- `Document Type` (str): Document type

### 3. fixture_IPE_08.csv
**Purpose:** Voucher liabilities from BOB  
**Required Columns:**
- `ID_COMPANY` (str): Company code
- `id` (str): Voucher ID
- `business_use_formatted` or `business_use` (str): Business use type
- `Is_Valid` or `is_valid` (str): Validity status
- `is_active` (int): Active status (0 or 1)
- `remaining_amount` (float): Remaining amount
- `created_at` (datetime): Creation date
- `TotalAmountUsed` (float): Total amount used

### 4. fixture_IPE_07.csv
**Purpose:** Customer balances  
**Required Columns:**
- `id_company` (str): Company code
- `Customer No_` (str): Customer number
- `Customer Name` (str): Customer name
- `Customer Posting Group` (str): Posting group

### 5. fixture_JDASH.csv
**Purpose:** Jdash voucher usage data  
**Required Columns:**
- `Voucher Id` (str): Voucher identifier
- `Amount Used` (float): Amount used

### 6. fixture_DOC_VOUCHER_USAGE.csv
**Purpose:** Voucher usage TV extract  
**Required Columns:**
- `ID_Company` (str): Company code
- `TotalAmountUsed` (float): Total amount used

### 7. fixture_IPE_REC_ERRORS.csv (Optional)
**Purpose:** Integration errors for Task 3  
**Required Columns:**
- `Source_System` (str): Source system name
- `Amount` (float): Transaction amount
- `Integration_Status` (str): Integration status
- `Transaction_ID` (str): Transaction ID (optional)
- `ID_COMPANY` (str): Company code

## Creating Fixture Files

Fixture files are not committed to the repository due to data sensitivity (.gitignore excludes `fixtures/` and `*.csv`).

To create fixture files:

1. **From Production Data (Recommended):** Use the `fetch_live_fixtures.py` script:
   ```bash
   python scripts/fetch_live_fixtures.py --entity EC_NG
   ```
   This will extract sample data from the SQL Server queries defined in `src/core/catalog/cpg1.py` and save them to `tests/fixtures/EC_NG/`.

2. **From Demo Script:** Run `python scripts/run_demo.py` which will auto-generate minimal fixtures

3. **Manual Creation:** Create CSV files following the column structure above

### Company-Specific Fixtures

For company-specific data (IPE_07, IPE_08, CR_03, JDASH):
```bash
# Create company subfolder
mkdir -p tests/fixtures/EC_NG

# Place company-specific fixtures there
tests/fixtures/EC_NG/fixture_IPE_07.csv
tests/fixtures/EC_NG/fixture_IPE_08.csv
tests/fixtures/EC_NG/fixture_CR_03.csv
tests/fixtures/EC_NG/fixture_JDASH.csv
```

### Shared Reference Files

For shared data (FX rates, global mappings):
```bash
# Place in root fixtures directory
tests/fixtures/fixture_CR_05.csv  # FX rates for all companies
```

## File Locations

Place fixture files in entity-specific subdirectories:
- `tests/fixtures/{entity}/` - For entity-specific test data (e.g., `tests/fixtures/EC_NG/`, `tests/fixtures/JD_GH/`)
- Each entity folder should contain all required fixture files for that entity
- JDash files should be manually placed in the entity folder before running `fetch_live_fixtures.py`

## FX Conversion Testing

For testing FX conversion features, ensure `fixture_CR_05.csv` contains:
- Multiple companies with different exchange rates
- At least one company matching each test company code (JD_GH, EC_NG, EC_KE, etc.)
- Valid non-zero FX_rate values

Example minimal CR_05 fixture for testing:
```csv
Company_Code,FX_rate
JD_GH,15.5
EC_NG,1650.0
EC_KE,142.0
```

## Notes

- All CSV files should use UTF-8 encoding
- Numeric columns should not contain currency symbols
- Date columns should use ISO format (YYYY-MM-DD)
- Boolean fields use 0/1 or 'true'/'false' depending on the field

## Running Headless Tests with Company Fixtures

To run headless reconciliation using company-specific fixtures:

```bash
# Run with EC_NG fixtures
python scripts/run_headless_test.py --company EC_NG --cutoff-date 2025-09-30

# This will load fixtures from:
# - tests/fixtures/EC_NG/fixture_IPE_07.csv (company-specific)
# - tests/fixtures/EC_NG/fixture_IPE_08.csv (company-specific)
# - tests/fixtures/fixture_CR_05.csv (shared FX rates)
```

**Backward Compatibility**: The system still supports the old single-folder structure.
If no company subfolders exist, all fixtures are loaded from `tests/fixtures/`.
