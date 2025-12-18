# Quick Reference: Company Subfolder Fixtures

## TL;DR

Fixtures can now be organized by company. The system automatically looks in company subfolders first, then falls back to root fixtures.

## Structure

```
tests/fixtures/
├── EC_NG/                    # Company-specific (Nigeria)
│   ├── fixture_IPE_07.csv
│   └── fixture_JDASH.csv
├── JD_GH/                    # Company-specific (Ghana)
│   └── fixture_IPE_07.csv
└── fixture_CR_05.csv         # Shared (all companies)
```

## Usage

```bash
# Run with EC_NG fixtures
python scripts/run_headless_test.py --company EC_NG --cutoff-date 2025-09-30

# Loads:
# ✅ tests/fixtures/EC_NG/fixture_IPE_07.csv (company-specific)
# ✅ tests/fixtures/fixture_CR_05.csv (shared, fallback)
```

## Setup

```bash
# Create directories
mkdir -p tests/fixtures/EC_NG
mkdir -p tests/fixtures/JD_GH

# Add files
# Company-specific: tests/fixtures/EC_NG/fixture_*.csv
# Shared: tests/fixtures/fixture_*.csv
```

## Loading Priority

1. **First**: `tests/fixtures/{company}/fixture_{item}.csv`
2. **Then**: `tests/fixtures/fixture_{item}.csv`
3. **Finally**: Empty DataFrame

## Backward Compatible

Old structure still works:
```
tests/fixtures/
├── fixture_IPE_07.csv
└── fixture_CR_05.csv
```

No changes needed to existing code or fixtures.

## Documentation

- **Setup Guide**: `tests/FIXTURE_SETUP_GUIDE.md`
- **File Specs**: `tests/fixtures_README.md`
- **Implementation**: `IMPLEMENTATION_SUMMARY_FIXTURES.md`

## Testing

```bash
pytest tests/test_fixture_subfolder_loading.py -v
```

## Questions?

See `tests/FIXTURE_SETUP_GUIDE.md` for detailed instructions.
