# SOXauto Data Architecture

**Last Updated**: 23 March 2026
**Architecture**: Direct Python pipeline (Streamlit UI + CLI) with SQL Server access via Teleport

## Overview

SOXauto C-PG-1 executes reconciliations through two entry points:

- Streamlit UI: `src/frontend/app.py`
- CLI headless runner: `scripts/run_headless_test.py`

Both entry points trigger the same extraction and reconciliation modules.

## Runtime Architecture

| Aspect | Current Implementation |
|--------|-------------------------|
| Orchestration | Direct Python execution (no Airflow/Temporal runtime) |
| Entry Points | Streamlit UI and CLI |
| Database Connectivity | Teleport (`tsh`) tunnel + ODBC (`pyodbc`) |
| Data Source | On-prem SQL Server (`fin-sql.jumia.local`) |
| Catalog | `src/core/catalog/cpg1.py` |
| Extraction Runner | `src/core/runners/mssql_runner.py` |
| Reconciliation Engine | `src/core/reconciliation/run_reconciliation.py` |
| Evidence | `src/core/evidence/manager.py` |

## End-to-End Data Flow

```text
User (UI or CLI)
  -> run_reconciliation
  -> ExtractionPipeline
  -> IPERunner (mssql_runner)
  -> SQL Server via Teleport tunnel
  -> validation + bridge analysis
  -> evidence package generation (SHA-256 integrity)
  -> outputs and audit artifacts
```

## Database Access Model

SOXauto accesses SQL Server through a secure Teleport tunnel:

1. Authenticate with Teleport (`tsh login`)
2. Open DB proxy/tunnel to `fin-sql.jumia.local`
3. Execute parameterized SQL from `src/core/catalog/cpg1.py`
4. Load results into pandas DataFrames

## Security and Compliance Controls

- No hardcoded DB credentials in repository code
- Parameterized SQL execution only
- Execution logs and query metadata stored in evidence package
- SHA-256 integrity hash generated for reproducibility and audit trail

## Scope Notes

- This document describes the active architecture only.
- Legacy Temporal/Athena/GCP runbooks are archived in `docs/archive/2026-03-obsolete-architecture/` and `docs/development/archive/`.
