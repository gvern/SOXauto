# Reconciliation Flow (Manual Process Replication)

This document summarizes the automation flow that reproduces the manual monthly process.

```mermaid
flowchart TD
    A[Customer Accounts (IPE_07)] --> D[Consolidation]
    B[Collection Accounts (IPE_31)] --> D
    C[Other AR related Accounts (IPE_10, IPE_08, ...)] --> D
    D --> E[Bridges / Timing Differences]
    E --> F[Final Variance and Dashboard]
```

- Step 1: Customer Accounts (IPE_07)
  - Script: `scripts/generate_customer_accounts.py`
  - Output: `data/outputs/customer_accounts.csv`
  - Evidence: `evidence/IPE_07/<timestamp>/*` (8 files)

- Step 2: Collection Accounts (IPE_31)
  - Script: `scripts/generate_collection_accounts.py`
  - Output: `data/outputs/collection_accounts.csv`
  - Evidence: `evidence/IPE_31/<timestamp>/*`

- Step 3: Other AR related Accounts (e.g., IPE_10, IPE_08)
  - Script: `scripts/generate_other_ar.py`
  - Output: `data/outputs/other_ar_related_accounts.csv`
  - Evidence: one package per contributor (e.g., `IPE_10`, `IPE_08`)

- Step 4: Consolidation and Variance
  - Script: `scripts/run_consolidation.py` (to be created)
  - Inputs: three CSVs above + CR_04
  - Logic: joins/aggregations, compute variances and classifications
  - Output: `data/outputs/Consolidation.xlsx`

- Bridges and Timing Differences
  - Utility: `src/bridges/timing_difference.py` to support classification from voucher extracts
  - Improve the presentation by separating issued vs usage flows and clarifying country/date filters.

Prerequisites

- SQL Server connectivity validated via `python scripts/check_mssql_connection.py`
- `DB_CONNECTION_STRING` (or MSSQL_* env vars) exported in your shell
- Optional: `CUTOFF_DATE` environment variable is included in evidence metadata

Run end-to-end

```bash
python3 scripts/run_full_reconciliation.py
```
