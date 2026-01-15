# Voucher Classification Module

## Overview

This module provides a robust classification system for NAV GL entries related to voucher transactions. It categorizes transactions according to strict business rules and produces schema-compliant outputs for SOX audit purposes.

## Directory Structure

```
voucher_classification/
├── __init__.py                 # Module initialization
├── cat_pipeline.py             # Main orchestration pipeline
├── cat_nav_classifier.py       # Integration/Manual type classification
├── cat_issuance_classifier.py  # Issuance category classification
├── cat_usage_classifier.py     # Usage and Cancellation classification
├── cat_expired_classifier.py   # Expired vouchers classification
├── cat_vtc_classifier.py       # VTC (Voucher-to-Cash) classification
├── voucher_utils.py            # Shared utilities and voucher type lookups
├── SCHEMA_COMPLIANCE.md        # Detailed schema documentation
└── README.md                   # This file
```

## Schema Overview

The classification system produces three key attributes:

1. **Integration_Type**: `Manual` | `Integration`
   - Determines whether transaction was created by batch integration or manual user
   - Rule: `Integration` if `User ID == "JUMIA/NAV31AFR.BATCH.SRVC"`, else `Manual`

2. **bridge_category**: `Issuance` | `Cancellation` | `Usage` | `Expired` | `VTC` | `None`
   - Primary transaction category
   - Used for bridge analysis and reconciliation

3. **voucher_type**: `Refund` | `Apology` | `JForce` | `Store Credit` | `None`
   - Specific voucher business purpose
   - Looked up from Transaction Value (TV) files or inferred from patterns

### Valid Combinations

| Category     | Allowed Voucher Types                    |
|--------------|------------------------------------------|
| Issuance     | Refund, Apology, JForce, Store Credit   |
| Cancellation | Apology, Store Credit                   |
| Usage        | Refund, Apology, JForce, Store Credit   |
| Expired      | Apology, JForce, Refund, Store Credit   |
| VTC          | Refund                                   |

See [SCHEMA_COMPLIANCE.md](SCHEMA_COMPLIANCE.md) for complete details.

## Usage

### Basic Usage

```python
from src.core.reconciliation.voucher_classification.cat_pipeline import categorize_nav_vouchers
import pandas as pd

# Load your NAV GL entries (CR_03)
cr_03_df = pd.read_csv("cr_03_data.csv")

# Optional: Load Transaction Value (TV) files for voucher type lookups
ipe_08_df = pd.read_csv("ipe_08_issuance_tv.csv")  # Issuance TV
doc_voucher_usage_df = pd.read_csv("usage_tv.csv")  # Usage TV

# Run categorization pipeline
result = categorize_nav_vouchers(
    cr_03_df=cr_03_df,
    ipe_08_df=ipe_08_df,
    doc_voucher_usage_df=doc_voucher_usage_df,
    gl_account_filter="18412"  # Default GL account for vouchers
)

# Result includes new columns: Integration_Type, bridge_category, voucher_type
print(result[["Integration_Type", "bridge_category", "voucher_type"]].head())
```

### Individual Classifiers

You can also use individual classifiers for specific tasks:

```python
from src.core.reconciliation.voucher_classification.cat_nav_classifier import classify_integration_type
from src.core.reconciliation.voucher_classification.cat_issuance_classifier import classify_issuance

# Step 1: Classify integration type
df = classify_integration_type(nav_df)

# Step 2: Classify issuance
df = classify_issuance(df)
```

## Classification Rules

### Priority Order

The pipeline applies classifiers in this priority order:

1. **Integration Type** (all rows)
2. **VTC via Bank Account** (highest priority - overrides others)
3. **Issuance** (negative amounts)
4. **Usage** (positive + Integration)
5. **Expired** (positive + Manual + EXPR_*)
6. **VTC Pattern** (positive + Manual + RND/PYT+GTB)
7. **Manual Cancellation** (positive + Manual + Credit Memo)
8. **Manual Usage** (positive + Manual + ITEMPRICECREDIT)

### Classification Details

#### Issuance (Negative Amounts)
- **Refund**: REFUND, RF_, RF patterns
- **Apology**: COMMERCIAL GESTURE, CXP, APOLOGY patterns
- **JForce**: PYT_ patterns (includes PYT_PF)
- **Store Credit**: Manual entries with Document No starting with country code

#### Usage (Positive + Integration)
- **Standard Usage**: Positive amount + Integration type
- **Cancellation**: "VOUCHER ACCRUAL" in description → Apology
- **Voucher Type**: Looked up from TV files (IPE_08 or doc_voucher_usage)

#### Expired (Positive + Manual + EXPR_*)
- **Apology**: EXPR_APLGY pattern
- **JForce**: EXPR_JFORCE pattern
- **Store Credit**: EXPR_STR CRDT or EXPR_STR_CRDT patterns

#### VTC - Voucher to Cash (Manual)
- **Bank Account**: Positive + Manual + Bal_ Account Type = "Bank Account" → Refund
- **MANUAL RND**: Positive + Manual + "MANUAL RND" in description → Refund
- **PYT + GTB**: Positive + Manual + "PYT_" in description + "GTB" in comment → Refund

#### Cancellation
- **Apology**: Integration + "VOUCHER ACCRUAL" → automated cancellation
- **Store Credit**: Manual + Credit Memo document type → manual cancellation

## Testing

### Schema Compliance Tests

Run schema compliance tests to verify that only valid values and combinations are produced:

```bash
# Run schema validation
python3 scripts/validate_voucher_schema.py

# Run pytest tests
pytest tests/test_voucher_schema_compliance.py -v
```

### Unit Tests

Individual classifier tests are available in the main test suite:

```bash
pytest tests/test_categorization_pipeline.py -v
pytest tests/test_bridges_classifier.py -v
```

## Dependencies

- **pandas**: Data manipulation
- **pytest**: Testing framework (dev)

## Integration with Bridge Analysis

The classification outputs are used by:

1. **Bridge Categorization**: Groups transactions by category for bridge analysis
2. **Reconciliation**: Matches NAV GL entries with Transaction Value (TV) files
3. **Audit Evidence**: Provides categorized transaction breakdowns for SOX audit

## Maintenance Notes

### Adding a New Category

1. Update `ALLOWED_CATEGORIES` in [SCHEMA_COMPLIANCE.md](SCHEMA_COMPLIANCE.md)
2. Define valid voucher type combinations
3. Create new classifier module (e.g., `cat_new_category_classifier.py`)
4. Add to pipeline in `cat_pipeline.py` at appropriate priority
5. Update tests in `tests/test_voucher_schema_compliance.py`

### Modifying Patterns

When updating pattern matching rules:
1. Update the classifier module (e.g., `cat_issuance_classifier.py`)
2. Update docstrings to reflect new patterns
3. Add test cases for new patterns
4. Document business rule changes in commit message

### Voucher Type Lookups

The system uses a robust fallback strategy for voucher type lookups:

1. **Primary**: Match NAV Voucher No to TV file `id` column
   - Try IPE_08 first (Issuance data)
   - Then try doc_voucher_usage_df (Usage data)

2. **Secondary (Fallback)**: Match NAV Document No to TV file `Transaction_No` column
   - Used when Voucher No is missing (e.g., Nigeria ITEMPRICECREDIT cases)
   - Retrieves `business_use` field as voucher type

## Version History

- **2026-01-15**: Schema normalization
  - Removed sub-categories from bridge_category
  - Separated category and voucher type into distinct columns
  - Corrected EXPR_JFORCE mapping (JForce, not Refund)
  - Enforced exact allowed values per schema

## Related Documentation

- [SCHEMA_COMPLIANCE.md](SCHEMA_COMPLIANCE.md) - Complete schema specification
- [Bridge Analysis Documentation](../../bridges/README.md) - How categories are used in bridge analysis
- [IPE Catalog](../../catalog/cpg1.py) - IPE definitions and queries

## Contact

For questions or issues related to voucher classification, consult:
- Project Dashboard: `PROJECT_DASHBOARD.md`
- Bridge documentation: `src/bridges/README.md`
- Copilot instructions: `.github/copilot-instructions.md`
