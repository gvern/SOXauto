# Fixture Directory Structure Guide

This document provides instructions for setting up company-specific fixture directories
for the SOXauto reconciliation system.

## Overview

The system now supports company-specific fixture organization with automatic fallback
to shared reference files. This allows testing different companies (EC_NG, JD_GH, etc.)
with their own datasets while sharing common reference data like FX rates.

## Expected Directory Structure

```
tests/fixtures/
├── EC_NG/                          # Nigeria-specific fixtures
│   ├── fixture_IPE_07.csv         # Customer balances (EC_NG)
│   ├── fixture_IPE_08.csv         # Voucher liabilities (EC_NG)
│   ├── fixture_CR_03.csv          # NAV GL Entries (EC_NG)
│   ├── fixture_JDASH.csv          # Jdash voucher usage (EC_NG)
│   └── fixture_DOC_VOUCHER_USAGE.csv
│
├── JD_GH/                          # Ghana-specific fixtures
│   ├── fixture_IPE_07.csv         # Customer balances (JD_GH)
│   ├── fixture_IPE_08.csv         # Voucher liabilities (JD_GH)
│   ├── fixture_CR_03.csv          # NAV GL Entries (JD_GH)
│   └── fixture_JDASH.csv          # Jdash voucher usage (JD_GH)
│
├── EC_KE/                          # Kenya-specific fixtures (optional)
│   └── ...
│
└── fixture_CR_05.csv               # Shared FX rates (all companies)
```

## Setup Instructions

### Step 1: Create the fixtures base directory

```bash
mkdir -p tests/fixtures
```

### Step 2: Create company subdirectories

```bash
# Create subdirectories for each company you want to test
mkdir -p tests/fixtures/EC_NG
mkdir -p tests/fixtures/JD_GH
mkdir -p tests/fixtures/EC_KE  # Optional: add more as needed
```

### Step 3: Add company-specific fixtures

For **EC_NG (Nigeria)**:
```bash
# These files should contain EC_NG-specific data
tests/fixtures/EC_NG/fixture_IPE_07.csv
tests/fixtures/EC_NG/fixture_IPE_08.csv
tests/fixtures/EC_NG/fixture_CR_03.csv
tests/fixtures/EC_NG/fixture_JDASH.csv
tests/fixtures/EC_NG/fixture_DOC_VOUCHER_USAGE.csv
```

For **JD_GH (Ghana)**:
```bash
# These files should contain JD_GH-specific data
tests/fixtures/JD_GH/fixture_IPE_07.csv
tests/fixtures/JD_GH/fixture_IPE_08.csv
tests/fixtures/JD_GH/fixture_CR_03.csv
tests/fixtures/JD_GH/fixture_JDASH.csv
```

### Step 4: Add shared reference files

Place shared files in the root `tests/fixtures/` directory:

```bash
# FX rates for all companies (shared reference data)
tests/fixtures/fixture_CR_05.csv
```

The CR_05 file should contain FX rates for multiple companies:
```csv
Company_Code,FX_rate,year,cod_month
EC_NG,1650.0,2025,9
JD_GH,15.5,2025,9
EC_KE,142.0,2025,9
```

## Loading Priority

When you run reconciliation with `--company EC_NG`, the system follows this priority:

1. **First**: Look in `tests/fixtures/EC_NG/fixture_{ITEM_ID}.csv`
2. **Then**: Fall back to `tests/fixtures/fixture_{ITEM_ID}.csv` (shared)
3. **Finally**: Return empty DataFrame if not found in either location

### Examples

**Running with EC_NG:**
```bash
python scripts/run_headless_test.py --company EC_NG --cutoff-date 2025-09-30
```

Loads:
- ✅ `tests/fixtures/EC_NG/fixture_IPE_07.csv` (company-specific)
- ✅ `tests/fixtures/EC_NG/fixture_IPE_08.csv` (company-specific)
- ✅ `tests/fixtures/fixture_CR_05.csv` (shared, fallback to root)

**Running with JD_GH:**
```bash
python scripts/run_headless_test.py --company JD_GH --cutoff-date 2025-09-30
```

Loads:
- ✅ `tests/fixtures/JD_GH/fixture_IPE_07.csv` (company-specific)
- ✅ `tests/fixtures/JD_GH/fixture_IPE_08.csv` (company-specific)
- ✅ `tests/fixtures/fixture_CR_05.csv` (shared, fallback to root)

## Company-Specific vs Shared Files

### Company-Specific Files (Place in subfolders)

These typically vary by company and should be in company subfolders:
- `fixture_IPE_07.csv` - Customer balances
- `fixture_IPE_08.csv` - Voucher liabilities
- `fixture_CR_03.csv` - NAV GL Entries
- `fixture_JDASH.csv` - Jdash voucher usage
- `fixture_DOC_VOUCHER_USAGE.csv` - Document voucher usage

### Shared Reference Files (Place in root)

These are typically the same across companies and should be in root:
- `fixture_CR_05.csv` - FX rates (contains rates for ALL companies)
- Any other mapping files that are global

## Backward Compatibility

**The system is fully backward compatible!**

If you don't use company subfolders, the old structure still works:

```
tests/fixtures/
├── fixture_IPE_07.csv
├── fixture_IPE_08.csv
├── fixture_CR_03.csv
├── fixture_CR_05.csv
└── fixture_JDASH.csv
```

The system will simply load all files from the root directory.

## File Format Requirements

For detailed column requirements for each fixture file, see:
- `tests/fixtures_README.md` - Complete specification of required columns

## Testing the Setup

To verify your fixture structure is correct:

```bash
# Run the subfolder loading tests
pytest tests/test_fixture_subfolder_loading.py -v

# Run a headless reconciliation
python scripts/run_headless_test.py --company EC_NG --cutoff-date 2025-09-30 -v
```

## Troubleshooting

**Problem**: Fixtures not loading for company

**Solution**: Check that:
1. Company code matches exactly (case-sensitive): `EC_NG` not `ec_ng`
2. File names follow the pattern: `fixture_{ITEM_ID}.csv`
3. Files are in the correct subdirectory: `tests/fixtures/EC_NG/`

**Problem**: FileNotFoundError for shared file

**Solution**: 
- Place shared files (like CR_05) in root `tests/fixtures/` directory
- The system will fall back to root for all companies

## Security Note

⚠️ **Important**: Fixture files are gitignored to prevent committing sensitive data.
Always use anonymized or synthetic data for fixtures, never production data with PII.

## Related Documentation

- `tests/fixtures_README.md` - Detailed fixture file specifications
- `src/core/extraction_pipeline.py` - Implementation of fixture loading
- `src/core/jdash_loader.py` - JDASH-specific loader with company support
