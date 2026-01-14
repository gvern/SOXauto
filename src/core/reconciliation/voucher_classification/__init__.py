"""
Voucher Classification Package for PG-01 Reconciliation.

This package contains voucher lifecycle classification logic for NAV reconciliation (Phase 3).
Vouchers are classified by integration type, issuance, usage, expiration, and VTC status
to explain variance between NAV and Target Values.

Modules:
    cat_pipeline: Main orchestrator for voucher classification
    cat_nav_classifier: NAV integration type classification
    cat_issuance_classifier: Issuance classification (refund, apology, store_credit)
    cat_usage_classifier: Usage classification (positive amounts, integrated)
    cat_expired_classifier: Expired voucher classification
    cat_vtc_classifier: VTC (Voucher to Cash) classification
    voucher_utils: Shared utilities and lookup functions

Example:
    >>> from src.core.reconciliation.voucher_classification import categorize_vouchers
    >>> results = categorize_vouchers(nav_df, country_code="NG", cutoff_date="2025-09-30")
"""

# Import main pipeline orchestrator
from src.core.reconciliation.voucher_classification.cat_pipeline import (
    categorize_nav_vouchers,
    get_categorization_summary,
)

# Alias for backward compatibility
categorize_vouchers = categorize_nav_vouchers
run_categorization_pipeline = categorize_nav_vouchers

# Import individual classifiers
from src.core.reconciliation.voucher_classification.cat_nav_classifier import (
    classify_integration_type,
    is_integration_user,
)
# Alias for consistency
classify_nav_integration_type = classify_integration_type

from src.core.reconciliation.voucher_classification.cat_issuance_classifier import (
    classify_issuance,
)
from src.core.reconciliation.voucher_classification.cat_usage_classifier import (
    classify_usage,
)
from src.core.reconciliation.voucher_classification.cat_expired_classifier import (
    classify_expired,
)
from src.core.reconciliation.voucher_classification.cat_vtc_classifier import (
    classify_vtc,
)

# Import utilities
from src.core.reconciliation.voucher_classification.voucher_utils import (
    COUNTRY_CODES,
    lookup_voucher_type,
)

__all__ = [
    "categorize_nav_vouchers",
    "run_categorization_pipeline",  # Alias
    "categorize_vouchers",  # Alias
    "get_categorization_summary",
    "classify_integration_type",
    "classify_nav_integration_type",  # Alias
    "is_integration_user",
    "classify_issuance",
    "classify_usage",
    "classify_expired",
    "classify_vtc",
    "COUNTRY_CODES",
    "lookup_voucher_type",
]
