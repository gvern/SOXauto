# Reconciliation Phases Architecture

## Overview

The SOXauto PG-01 reconciliation system is organized into clear architectural phases that separate concerns between data reconciliation (Phase 3) and bridge variance analysis (Phase 4).

## Phase 3: Reconciliation & Variance Analysis

**Location:** `src/core/reconciliation/`

Phase 3 focuses on voucher lifecycle classification and variance analysis between NAV (Microsoft Dynamics NAV) and Target Values systems.

### Components

#### Voucher Classification Pipeline (`voucher_classification/`)

Classifies vouchers by integration type and lifecycle status to explain variance between NAV and Target Values.

**Modules:**
- `cat_pipeline.py` - Main orchestrator for voucher classification workflow
- `cat_nav_classifier.py` - NAV integration type classification (Manual vs Integration)
- `cat_issuance_classifier.py` - Issuance classification (Refund, Apology, Store Credit)
- `cat_usage_classifier.py` - Usage classification (positive amounts, integrated vouchers)
- `cat_expired_classifier.py` - Expired voucher classification
- `cat_vtc_classifier.py` - VTC (Voucher to Cash) classification
- `voucher_utils.py` - Shared utilities (COUNTRY_CODES, voucher type lookups)

**Example Usage:**
```python
from src.core.reconciliation.voucher_classification import run_categorization_pipeline

results = run_categorization_pipeline(
    nav_df=cr_03_df,
    country_code="NG",
    cutoff_date="2025-09-30"
)
```

#### Variance Analysis (`analysis/`)

Generates pivots, calculates variances, and produces review tables for accounting team analysis.

**Modules:**
- `pivots.py` - NAV pivot + TV pivot generation
- `variance.py` - Variance calculation + thresholding
- `drilldown.py` - Voucher-level reconciliation views
- `review_tables.py` - "Accounting review required" tables

**Status:** Placeholder modules (v1) - Logic to be extracted from `run_reconciliation.py` incrementally.

#### Reconciliation Orchestration

- `run_reconciliation.py` - Coordinates voucher classification and variance analysis
- `summary_builder.py` - Aggregates results and metrics
- `cpg1.py` - Business rules and formulas for C-PG-1 reconciliation

---

## Phase 4: Bridge Analysis

**Location:** `src/bridges/`

Phase 4 focuses on identifying and quantifying specific variance patterns through bridge calculations and entity-level categorization.

### Entity-Level Categorization (`categorization/`)

Assigns category flags to entities (customers, business lines) for bridge drill-down and analysis.

**Modules:**
- `business_line_reclass.py` - Business line reclassification candidates (CLE-based pivot analysis)
  - Purpose: Identify customers with multi-business-line balances requiring manual review
  - Output: Candidate table for Accounting Excellence team
  
- `customer_posting_group.py` - Customer posting group categorization
  - Purpose: Categorize customers by posting group for variance analysis
  - Output: Bridge amount + proof DataFrame + metrics

**Example Usage:**
```python
from src.bridges.categorization import identify_business_line_reclass_candidates

candidates_df, metrics = identify_business_line_reclass_candidates(
    cle_df=customer_ledger_entries,
    cutoff_date="2025-09-30"
)
```

### Bridge Variance Calculations (`calculations/`)

Calculate specific bridge variances (timing, VTC, payment errors) with proof tables.

**Modules:**
- `timing.py` - Timing difference bridge (date/period differences between systems)
- `vtc.py` - VTC adjustment bridge (voucher-to-cash variance)
- *(Future)* `payment_reconciliation_errors.py` - Payment reconciliation error bridge

**Bridge Output Format:**

Each bridge calculation returns:
1. **Bridge Amount** (float): Monetary variance
2. **Proof DataFrame** (pd.DataFrame): Detailed transactions supporting the bridge amount
3. **Metrics** (dict): Analysis metadata (rows scanned, flagged, etc.)

**Example Usage:**
```python
from src.bridges.calculations import calculate_timing_difference_bridge

bridge_amount, proof_df, metrics = calculate_timing_difference_bridge(
    ipe_31_df=payment_gateway_data,
    cr_03_df=nav_gl_entries,
    cutoff_date="2025-09-30"
)
```

---

## Migration Notes

### Deprecated Imports

Voucher classification functions previously exported from `src.bridges` are deprecated:

```python
# ❌ Deprecated (will show DeprecationWarning)
from src.bridges import categorize_nav_vouchers, get_categorization_summary

# ✅ Use new location
from src.core.reconciliation.voucher_classification import (
    categorize_vouchers,
    run_categorization_pipeline
)
```

### File Reorganization (2025-01-14)

**Moved to reconciliation:**
- `cat_pipeline.py` - Voucher classification orchestrator
- `cat_nav_classifier.py`, `cat_issuance_classifier.py`, `cat_usage_classifier.py`, `cat_expired_classifier.py`, `cat_vtc_classifier.py` - Voucher classifiers
- `voucher_utils.py` - Shared utilities

**Moved within bridges:**
- `customer_posting_group.py` - From `calculations/` to `categorization/` (entity-level categorization)

**Removed:**
- `biz_line.py` - Deprecated placeholder, never implemented

---

## Decision Rationale

### Why separate reconciliation from bridges?

**Phase 3 (Reconciliation):**
- **Purpose:** Explain what caused the variance (voucher lifecycle events)
- **Input:** Raw NAV and TV data
- **Output:** Categorized data + variance summary
- **Audience:** Accounting team doing reconciliation review

**Phase 4 (Bridges):**
- **Purpose:** Quantify and prove specific variance patterns
- **Input:** Categorized/normalized data from Phase 3
- **Output:** Bridge amounts + proof tables
- **Audience:** Auditors requiring explicit variance explanations

### Why is business_line_reclass in bridges/categorization?

`business_line_reclass` identifies **entity-level** reclassification candidates (customers with multi-business-line balances), not voucher lifecycle classification. It's categorization for bridge analysis, not reconciliation variance explanation.

### Why is customer_posting_group in categorization, not calculations?

`customer_posting_group` **categorizes** customers (assigns category flags), even though it produces a bridge output. Categorization = assigning labels; Calculation = computing variances.

---

## References

- [Project Dashboard](../../PROJECT_DASHBOARD.md) - Current project status
- [Business Line Reclass Guide](../development/BUSINESS_LINE_RECLASS.md) - Detailed business line reclassification documentation
- [IPE Catalog](../../src/core/catalog/cpg1.py) - IPE definitions and critical columns
