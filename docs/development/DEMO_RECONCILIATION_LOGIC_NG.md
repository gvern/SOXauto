# SOXauto Demo: C-PG-1 Reconciliation Logic for Nigeria (NG)

**Objective:** This document outlines the precise, step-by-step logic to be implemented in the `SOXauto` prototype for the C-PG-1 reconciliation, focusing on a single country (Nigeria) for validation purposes.

---

## ## Phase 1: Data "Extraction" (Simulated from Historical Files)

The process begins by loading the pre-extracted manual IPE outputs from the `tests/fixtures/historical_data/` directory.

| Component         | Source File                                                         | Sheet/Tab Name          | Key Column for Summation    |
|-------------------|---------------------------------------------------------------------|-------------------------|-----------------------------|
| **ACTUALS** | `1. All Countries Mar-25 - IBSAR - Consolidation.xlsx`              | `NAV GLBalance PG`      | `Grand Total`               |
| **TARGET: IPE_07** | `2. All Countries Mar-25 - IBSAR - Customer Accounts.xlsx`        | `13003`                 | `Sum of Grand Total`        |
| **TARGET: IPE_31** | `3. All Countries Mar-25 - IBSAR - Collection Accounts.xlsx`      | `13011`                 | `Grand Total`               |
| **TARGET: Others** | `4. All Countries Mar-25 - IBSAR Other AR related Accounts.xlsx`    | `18350`                 | `Sum of Amount (LCY)`       |

---

## ## Phase 2: Reconciliation Calculation Logic (for Nigeria)

The core reconciliation logic compares the **ACTUALS** from the General Ledger against the sum of the **TARGETS** from the IPEs.

### ### Step 2.1: Calculate ACTUALS Total for Nigeria

1.  **Load Data**: Read the `NAV GLBalance PG` sheet.
2.  **Filter for Nigeria**: Select the row where the `Row Labels` column is **'EC_NG'**.
3.  **Extract Value**: Get the value from the **`Grand Total`** column for that row. This is the `ACTUALS_TOTAL_NG`.

### ### Step 2.2: Calculate TARGETS Total for Nigeria

1.  **Load IPE Data**: Read the sheets for each of the "TARGET" components (Customer Accounts, Collection Accounts, Other AR).
2.  **Filter each DataFrame for Nigeria**: For each loaded DataFrame, select the row where the `CompanyID` (or equivalent) column is **'EC_NG'**.
3.  **Sum Individual IPE Totals**:
    * `TARGET_IPE07` = Value from the `Sum of Grand Total` column for the 'EC_NG' row.
    * `TARGET_IPE31` = Value from the `Grand Total` column for the 'EC_NG' row.
    * `TARGET_OTHERS` = Value from the `Sum of Amount (LCY)` column for the 'EC_NG' row.
4.  **Calculate Total Targets**: `TARGETS_TOTAL_NG` = `TARGET_IPE07` + `TARGET_IPE31` + `TARGET_OTHERS`.

### ### Step 2.3: Calculate Variance

1.  **Formula**: `VARIANCE_NG` = `ACTUALS_TOTAL_NG` - `TARGETS_TOTAL_NG`.
2.  **Status Determination**:
    * If `abs(VARIANCE_NG)` is below a defined materiality threshold (e.g., $1,000 USD), the status is **"RECONCILED"**.
    * Otherwise, the status is **"VARIANCE DETECTED"**.

---

## ## Phase 3: Bridge & Adjustment Analysis Logic

This phase is triggered if a material variance is detected.

1.  **Load Transactional Data**: The analysis will run on a detailed transactional file, simulated by `1. All Countries Mar-25 - IBSAR - Consolidation.xlsx - Consolidated data.csv`.
2.  **Load Business Rules**: The system loads the classification rules from `src/bridges/catalog.py`.
3.  **Apply Classifier**: The `classify_bridges` agent iterates through each transaction and applies the rules based on trigger columns (e.g., `Transaction_Type`, `IS_PREPAYMENT`).
4.  **Output**: The result is an enriched dataset where each relevant transaction is tagged with a `bridge_key` (e.g., `CASH_DEPOSITS`, `REFUNDS`), ready for review.