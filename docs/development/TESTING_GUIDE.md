# Testing Guide for SOXauto PG-01

**Last Updated**: 23 March 2026
**Scope**: Current architecture only (Streamlit/CLI + SQL Server via Teleport)

## Testing Objectives

- Validate catalog and SQL template consistency
- Validate extraction/reconciliation behavior
- Validate evidence package generation
- Detect regressions in bridge classification and thresholds

## Prerequisites

```bash
python3 --version
pip install -r requirements.txt
```

For integration tests requiring database access:

```bash
tsh login --proxy=<your-teleport-proxy> --user "$USER"
```

## Quick Test Sequence

```bash
# 1. Static config checks
python3 scripts/validate_ipe_config.py

# 2. Unit/integration test suite
pytest tests/ -q

# 3. Optional targeted tests
pytest tests/test_smoke_core_modules.py -v
pytest tests/test_single_ipe_extraction.py -v
```

## Recommended Test Layers

### 1) Static Validation (No DB)

- `scripts/validate_ipe_config.py`
- SQL placeholder/rendering checks (`src/utils/sql_template.py`)
- Schema contract presence and compatibility checks

### 2) Unit Tests (No DB)

- Utilities under `src/utils/`
- Bridge rule logic under `src/bridges/`
- Reconciliation transformations and threshold checks

### 3) Integration Tests (DB + Teleport)

- SQL Server connectivity and query execution
- IPE extraction for representative IDs (for example: `IPE_07`, `IPE_08`, `CR_03`)
- Evidence package generation under `evidence/`

## Smoke Run (Headless)

Use the CLI entry point for a realistic end-to-end verification:

```bash
python3 scripts/run_headless_test.py \
  --cutoff-date 2025-10-01 \
  --company EC_NG \
  --ipes IPE_07,IPE_08,CR_03
```

Expected outcomes:

- Successful run summary in console
- Evidence directory created with run artifacts
- No unresolved SQL placeholders

## Evidence Validation Checklist

For each run, confirm:

- Query text and parameters are captured
- Row counts and validation summary are present
- Integrity hash is produced
- Execution log is complete and timestamped

## Troubleshooting

- `tsh` not authenticated: run `tsh login` again
- ODBC connectivity errors: verify tunnel and DSN/connection string
- Empty output: verify `--cutoff-date` and company scope
- SQL template error: inspect unresolved placeholders in execution logs

## Notes on Historical Content

This guide intentionally excludes old Temporal/Athena/GCP test workflows.
Historical test references are preserved in archive documentation only.
