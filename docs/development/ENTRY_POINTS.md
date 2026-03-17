# SOXauto PG-01 — Entry Points Guide

**Last Updated**: 16 March 2026

This document describes all ways to run the SOXauto PG-01 reconciliation system.

---

## 1. Streamlit UI (Interactive)

The primary interface for running reconciliations interactively.

```bash
# Prerequisites: Teleport tunnel must be active
tsh login --proxy=teleport.jumia.com --user=<your-username>
tsh db connect fin-sql

# Start the UI
streamlit run src/frontend/app.py
```

Opens on `http://localhost:8501` by default.

**What the UI provides:**
- Select `cutoff_date` and company (`EC_NG`, `EC_KE`, `JD_GH`, etc.)
- Choose which IPEs / CRs to run
- View reconciliation results inline
- Download Digital Evidence Packages
- Inspect bridge classification results and variance thresholds

---

## 2. CLI / Headless (`run_headless_test.py`)

Used for batch runs, CI/CD pipelines, or when GUI is not needed. Outputs JSON.

### Basic Usage

```bash
python scripts/run_headless_test.py --cutoff-date 2025-09-30 --company EC_NG
```

### All Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--cutoff-date` | Cutoff date (YYYY-MM-DD) | `2025-09-30` |
| `--company` | Company code | `EC_NG`, `EC_KE`, `JD_GH` |
| `--config` | JSON config file (alternative to flags) | `my_config.json` |
| `--ipes` | Comma-separated IPE/CR IDs to run | `IPE_07,IPE_08,CR_03` |
| `--output` | Write JSON results to file (default: stdout) | `results.json` |
| `--no-bridges` | Skip bridge analysis (faster) | — |
| `--no-quality` | Skip quality checks | — |
| `--summary-only` | Output summary only (no full DataFrames) | — |
| `--verbose` / `-v` | Enable verbose logging | — |
| `--quiet` / `-q` | Suppress all non-JSON output | — |

### Examples

```bash
# Run all IPEs for Nigeria September 2025 close
python scripts/run_headless_test.py \
  --cutoff-date 2025-10-01 \
  --company EC_NG

# Run specific IPEs only, save to file
python scripts/run_headless_test.py \
  --cutoff-date 2025-10-01 \
  --company EC_NG \
  --ipes IPE_07,IPE_08,CR_03 \
  --output results_NG_sep2025.json

# Faster run without bridges
python scripts/run_headless_test.py \
  --cutoff-date 2025-10-01 \
  --company EC_NG \
  --no-bridges

# Config file approach
python scripts/run_headless_test.py --config config.json
```

**Config file format (`config.json`)**:
```json
{
  "cutoff_date": "2025-10-01",
  "company": "EC_NG",
  "ipes": ["IPE_07", "IPE_08", "CR_03"],
  "no_bridges": false
}
```

---

## 3. Offline Demo (no DB required)

For testing and demos without a live SQL Server connection.

```bash
python scripts/run_demo.py --ipe IPE_07
```

What it does:
- Loads sample CSV fixtures from `tests/fixtures/historical_data/`
- Auto-creates minimal CSVs if missing: `<IPE>.csv`, `actuals_nav_gl.csv`, `i31_transactions.csv`
- Runs extraction → reconciliation → bridge classification pipeline
- Generates a Digital Evidence Package under `evidence/<IPE>/...`

---

## 4. Individual Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/check_mssql_connection.py` | Verify SQL Server connectivity via Teleport | `python scripts/check_mssql_connection.py` |
| `scripts/validate_ipe_config.py` | Validate IPE catalog definitions | `python scripts/validate_ipe_config.py` |
| `scripts/run_sql_from_catalog.py` | Execute a single IPE SQL query | `python scripts/run_sql_from_catalog.py --ipe IPE_07` |
| `scripts/inspect_schemas.py` | Inspect DB table schemas | `python scripts/inspect_schemas.py` |
| `scripts/fetch_live_fixtures.py` | Fetch live test fixtures from DB | `python scripts/fetch_live_fixtures.py` |

---

## 5. Environment Variables

Set these before running any entry point (or source a `.env` file):

```bash
# Required for live DB runs
export CUTOFF_DATE="2025-10-01"            # Cutoff date (YYYY-MM-DD)

# Authentication
export AWS_PROFILE="007809111365_Data-Prod-DataAnalyst-NonFinance"
export AWS_REGION="eu-west-1"

# Optional overrides
export DB_CONNECTION_STRING="DRIVER=...;SERVER=...;"   # Override Secrets Manager
export S3_BUCKET_EVIDENCE="your-s3-bucket-name"        # S3 bucket for evidence
export USE_OKTA_AUTH="true"                             # Enable Okta SSO
```

For Okta setup, see [`docs/setup/OKTA_AWS_SETUP.md`](../setup/OKTA_AWS_SETUP.md).
For DB connection details, see [`docs/setup/DATABASE_CONNECTION.md`](../setup/DATABASE_CONNECTION.md).

---

## 6. Pre-run Checklist

```
[ ] Teleport tunnel active: tsh login + tsh db connect fin-sql
[ ] AWS credentials refreshed (Okta): see OKTA_QUICK_REFERENCE.md
[ ] CUTOFF_DATE set correctly (first day of FOLLOWING month)
[ ] Company code confirmed (EC_NG, EC_KE, JD_GH, ...)
[ ] SQL Server accessible: python scripts/check_mssql_connection.py
```
