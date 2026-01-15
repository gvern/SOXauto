# Voucher Classification Schema Compliance

## Schema Overview

This document describes how the voucher classification system complies with the required schema for categorizing NAV GL entries.

## Schema Definition

### Allowed Values

#### Manual/Integration
- `Manual`: Entries created by manual users
- `Integration`: Entries created by integration/batch user

**Rule**: Entries are classified as `Integration` if and only if `User ID == "JUMIA/NAV31AFR.BATCH.SRVC"`, otherwise `Manual`.

**Implementation**: [cat_nav_classifier.py](cat_nav_classifier.py) - `classify_integration_type()`

#### Category (bridge_category)
- `Issuance`: Voucher creation transactions (typically negative amounts)
- `Cancellation`: Voucher cancellation transactions
- `Usage`: Voucher redemption transactions
- `Expired`: Expired voucher adjustments
- `VTC`: Voucher-to-Cash refund transactions

**Implementation**: All classifiers produce these exact category values without sub-categories.

#### Voucher Type (voucher_type)
- `Refund`: Refund vouchers
- `Apology`: Apology/Commercial Gesture vouchers
- `JForce`: JForce/PYT vouchers
- `Store Credit`: Store Credit vouchers

**Implementation**: All classifiers use these exact voucher type values.

### Expected Combinations

The schema defines valid combinations of `Category` and `Voucher Type`:

| Category      | Allowed Voucher Types                         | Implementation |
|---------------|-----------------------------------------------|----------------|
| Issuance      | Refund, Apology, JForce, Store Credit        | cat_issuance_classifier.py |
| Cancellation  | Apology, Store Credit                         | cat_usage_classifier.py, cat_expired_classifier.py |
| Usage         | Refund, Apology, JForce, Store Credit        | cat_usage_classifier.py |
| Expired       | Apology, JForce, Refund, Store Credit        | cat_expired_classifier.py |
| VTC           | Refund                                        | cat_vtc_classifier.py |

## Implementation Details

### 1. Integration Type Classification
**File**: [cat_nav_classifier.py](cat_nav_classifier.py)

- **Input**: NAV GL entries with User ID
- **Output**: `Integration_Type` column with values `Manual` or `Integration`
- **Rule**: 
  - `Integration` if `User ID == "JUMIA/NAV31AFR.BATCH.SRVC"` (case-insensitive, slash-normalized)
  - `Manual` otherwise

### 2. Issuance Classification
**File**: [cat_issuance_classifier.py](cat_issuance_classifier.py)

- **Category**: `Issuance`
- **Trigger**: Negative amount
- **Voucher Types**:
  - `Refund`: REFUND/RF_/RF patterns
  - `Apology`: COMMERCIAL GESTURE/CXP/APOLOGY patterns
  - `JForce`: PYT_ patterns
  - `Store Credit`: Document No starts with country code (manual only)

### 3. Usage Classification
**File**: [cat_usage_classifier.py](cat_usage_classifier.py)

- **Category**: `Usage`
- **Trigger**: Positive amount + Integration type OR ITEMPRICECREDIT (Nigeria exception)
- **Voucher Types**: Looked up from IPE_08 or doc_voucher_usage TV files
  - `Refund`, `Apology`, `JForce`, `Store Credit` (via TV lookup)

### 4. Cancellation Classification
**Files**: 
- [cat_usage_classifier.py](cat_usage_classifier.py) - Automated cancellation
- [cat_expired_classifier.py](cat_expired_classifier.py) - Manual cancellation

- **Category**: `Cancellation`
- **Triggers**:
  - Positive amount + Integration + "VOUCHER ACCRUAL" description → `Apology`
  - Positive amount + Manual + Credit Memo document type → `Store Credit`
- **Voucher Types**: `Apology`, `Store Credit`

### 5. Expired Classification
**File**: [cat_expired_classifier.py](cat_expired_classifier.py)

- **Category**: `Expired`
- **Trigger**: Positive amount + Manual + EXPR_* pattern
- **Voucher Types**:
  - `Apology`: EXPR_APLGY pattern
  - `JForce`: EXPR_JFORCE pattern
  - `Store Credit`: EXPR_STR CRDT/EXPR_STR_CRDT patterns
  - `Refund`: Other expired patterns

### 6. VTC Classification
**File**: [cat_vtc_classifier.py](cat_vtc_classifier.py)

- **Category**: `VTC` (Voucher-to-Cash)
- **Trigger**: Manual + (Bank Account OR MANUAL RND OR PYT_+GTB patterns)
- **Voucher Type**: `Refund` (always)
- **Priority**: Highest priority (applied before Issuance)

## Classification Pipeline

**File**: [cat_pipeline.py](cat_pipeline.py)

The pipeline applies classifiers in priority order:

1. **Integration Type** (all rows)
2. **VTC via Bank Account** (highest priority - can override negative amounts)
3. **Issuance** (negative amounts)
4. **Usage** (positive + Integration)
5. **Expired** (positive + Manual + EXPR_*)
6. **VTC Pattern** (positive + Manual + RND/PYT+GTB)
7. **Manual Cancellation** (positive + Manual + Credit Memo)
8. **Manual Usage** (positive + Manual + ITEMPRICECREDIT)

## Compliance Validation

### Schema-Compliant Output Structure

Every categorized row will have:
```python
{
    "Integration_Type": "Manual" | "Integration",
    "bridge_category": "Issuance" | "Cancellation" | "Usage" | "Expired" | "VTC" | None,
    "voucher_type": "Refund" | "Apology" | "JForce" | "Store Credit" | None
}
```

### Valid Combinations Enforced

The implementation enforces these combinations:

✅ **Valid Examples**:
- `Issuance` + `Refund`
- `Issuance` + `Store Credit`
- `Usage` + `Apology`
- `Cancellation` + `Store Credit`
- `Expired` + `JForce`
- `VTC` + `Refund`

❌ **Invalid (Not Produced)**:
- `VTC` + `Apology` (VTC only produces Refund)
- `Cancellation` + `JForce` (Cancellation only produces Apology or Store Credit)
- `Issuance` + (no voucher_type) with specific sub-types detected

### Fallback Behavior

When a transaction matches a category but no specific voucher type can be determined:
- `bridge_category` is set to the category name
- `voucher_type` remains `None`

This occurs when:
- No pattern matches for integrated issuance
- No TV lookup data available for usage
- Generic EXPR pattern without specific sub-type

## Testing Schema Compliance

To verify schema compliance, tests should validate:

1. ✅ Only allowed values appear in `Integration_Type`, `bridge_category`, `voucher_type`
2. ✅ Only valid category-voucher type combinations are produced
3. ✅ Integration type rule is correctly applied
4. ✅ Priority order is respected (VTC > Issuance > Usage > Expired)

## Version History

- **2026-01-15**: Updated to comply with normalized schema
  - Removed sub-categories from `bridge_category` (e.g., "Issuance - Refund" → "Issuance")
  - Separated category and voucher type into distinct columns
  - Corrected EXPR_JFORCE mapping from "Refund" to "JForce"
  - Enforced exact allowed values per schema requirements
