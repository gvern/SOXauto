# Reconciliation Flow (Manual Process Replication)

This document summarizes the automation flow that reproduces the manual monthly process.

```mermaid
flowchart TD
    A[Customer Accounts (IPE_07)] --> D[Consolidation]
    B[Collection Accounts (IPE_31)] --> D
    C[Other AR related Accounts (IPE_10, IPE_08, ...)] --> D
    D --> E[Target Values Pivot - Local Currency]
    E --> F[FX Conversion to USD]
    F --> G[Bridges / Timing Differences]
    G --> H[Final Variance and Dashboard]
```

## Order of Operations

The reconciliation process follows these sequential steps:

1. **Data Extraction** - Extract IPE data from source systems
2. **Preprocessing** - Validate and clean extracted data
3. **Target Values Pivot (Local Currency)** - Aggregate TV amounts per country in local currency
4. **FX Conversion** - Convert local currency amounts to USD using CR_05 FX rates
5. **NAV Pivot** - Generate NAV actuals pivot from GL balances
6. **Variance Calculation** - Compare NAV vs Target Values
7. **Bridge Classification** - Categorize variances (Timing, Permanent, etc.)
8. **Reporting** - Generate final dashboard and evidence packages

### Step 3: Target Values Pivot (Local Currency)

**Module:** `src/core/reconciliation/analysis/pivots.py`  
**Function:** `build_target_values_pivot_local()`

Aggregates Target Values from BOB extract tables (Issuance/Usage/Expired/VTC) into a pivot table with local currency amounts. The output grain matches NAV pivot: `(country_code, category, voucher_type)`.

**Inputs:**
- Target Values tables: IPE_08 (Issuance), DOC_VOUCHER_USAGE (Usage), Expired, VTC
- Required columns per table: `country_code`, `category`, `voucher_type`, `amount_local`

**Processing:**
1. Harmonize `voucher_type` labels to canonical enum (refund, store_credit, apology, etc.)
2. Handle missing voucher_type → "Unknown"
3. Aggregate amounts by `(country_code, category, voucher_type)` grain
4. Apply deterministic sorting for reproducibility

**Output:**
- DataFrame with columns: `country_code`, `category`, `voucher_type`, `tv_amount_local`
- **No USD conversion** - local currency only
- Matches NAV pivot grain exactly for variance calculation

**Schema Contracts:**
- Uses `require_columns()` to enforce required columns
- Uses `ensure_required_numeric()` for amount coercion
- Prevents KeyError via schema validation

**Example:**
```python
from src.core.reconciliation.analysis.pivots import build_target_values_pivot_local

# Single table
issuance_df = load_ipe("IPE_08")
pivot = build_target_values_pivot_local(issuance_df)

# Multiple tables
issuance_df = load_ipe("IPE_08")
usage_df = load_doc("DOC_VOUCHER_USAGE")
pivot = build_target_values_pivot_local([issuance_df, usage_df])
```

### Step 4: FX Conversion

**Module:** `src/utils/fx_utils.py` (to be implemented)  
**Function:** `convert_local_to_usd()`

Converts local currency amounts from Step 3 to USD using FX rates from CR_05.

**Input:** `tv_pivot_local_df` from Step 3  
**Output:** `tv_pivot_usd_df` with additional column `tv_amount_usd`

---

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
