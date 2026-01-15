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

## Phase 3: Voucher Categorization and NAV Pivot

The Phase 3 reconciliation pipeline processes NAV GL entries (CR_03) to categorize voucher transactions and generate pivot tables for variance analysis.

### Voucher Categorization Pipeline

**Input**: Raw NAV GL entries (CR_03) filtered for GL account 18412 (Voucher Liability)

**Processing**: The categorization pipeline (`src/core/reconciliation/voucher_classification/cat_pipeline.py`) applies business rules to classify each transaction:

1. **Integration Type Classification**: Determines if transaction is Manual or Integration-based
2. **Category Assignment** (priority order):
   - VTC via Bank Account (highest priority - any amount + Bank Account)
   - Issuance (negative amounts - voucher creation)
   - Usage (positive + integration - voucher consumption)
   - Expired (manual + positive + EXPR_* pattern)
   - VTC Pattern (manual + positive + RND/PYT+GTB)
   - Manual Cancellation (credit memo)
   - Manual Usage (ITEMPRICECREDIT pattern)

3. **Voucher Type Enrichment**: Matches voucher numbers to specific types:
   - Refund
   - Apology (Commercial Gesture)
   - Store Credit
   - JForce (PYT_PF)
   - Unknown (when type cannot be determined)

**Output**: Categorized CR_03 DataFrame with added columns:
- `bridge_category`: The assigned category (e.g., "Issuance - Refund")
- `voucher_type`: The specific voucher type (e.g., "Refund", "Apology")
- `Integration_Type`: Manual vs Integration classification

### NAV Pivot Generation

**Function**: `build_nav_pivot()` in `src/core/reconciliation/analysis/pivots.py`

**Input**: Categorized CR_03 DataFrame from the categorization pipeline

**Processing**:
1. Validates required columns: `bridge_category`, `voucher_type`, `amount`
2. Handles missing values:
   - Missing `voucher_type` → "Unknown"
   - Missing `bridge_category` → "Uncategorized"
3. Groups by (Category × Voucher Type) with deterministic alphabetical ordering
4. Aggregates:
   - `amount_lcy`: Sum of transaction amounts
   - `row_count`: Count of transactions
5. Generates margin totals (grand total row)

**Output**:
- **NAV Pivot DataFrame**: MultiIndex pivot table
  - Index: (category, voucher_type)
  - Columns: amount_lcy, row_count
  - Includes `__TOTAL__` row for overall totals
  - Deterministically sorted (alphabetical)

- **NAV Lines DataFrame**: Enriched transaction-level data
  - All transactions with category/type assignments
  - Includes optional fields: country_code, voucher_no, document_no, posting_date
  - Used for drilldown analysis

**Example Usage**:
```python
from src.core.reconciliation.analysis.pivots import build_nav_pivot
from src.core.reconciliation.voucher_classification.cat_pipeline import categorize_nav_vouchers

# Step 1: Categorize raw CR_03 data
categorized_df = categorize_nav_vouchers(
    cr_03_df=raw_cr_03_df,
    ipe_08_df=ipe_08_df,
    doc_voucher_usage_df=doc_voucher_usage_df,
)

# Step 2: Build NAV pivot for variance analysis
nav_pivot_df, nav_lines_df = build_nav_pivot(categorized_df, dataset_id='CR_03')

# Step 3: Analyze results
print(nav_pivot_df.head())
# Output:
#                              amount_lcy  row_count
# category        voucher_type                      
# Expired         Apology         5000.0         12
# Issuance        Apology       -25000.0         45
# Issuance        Refund        -50000.0        125
# Usage           Store Credit   30000.0         78
# __TOTAL__                     -40000.0        260
```

**Integration**: The pivot generation is automatically wired into `run_reconciliation()` and executed after the categorization phase. Results are stored in the reconciliation result dictionary under:
- `processed_data['NAV_pivot']`: The pivot DataFrame
- `processed_data['NAV_lines']`: The enriched lines DataFrame
- `result['categorization']['nav_pivot_summary']`: Summary statistics

**Column Validation**: Uses schema contracts (`CR_03.yaml`) via `require_columns()` to validate that all required fields are present before pivoting. This ensures data quality and prevents KeyError exceptions.

Prerequisites

- SQL Server connectivity validated via `python scripts/check_mssql_connection.py`
- `DB_CONNECTION_STRING` (or MSSQL_* env vars) exported in your shell
- Optional: `CUTOFF_DATE` environment variable is included in evidence metadata

Run end-to-end

```bash
python3 scripts/run_full_reconciliation.py
```
