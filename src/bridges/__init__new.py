"""
Bridges module for PG-1 reconciliation analysis.

This module provides bridge classification and categorization functionality
for SOX compliance workflows.

Submodules:
- classifier: General bridge classification rules
- catalog: Bridge rules catalog definitions
- cat_nav_classifier: Integration type detection (Manual vs Integration)
- cat_issuance_classifier: Issuance categorization rules
- cat_usage_classifier: Usage categorization rules
- cat_vtc_classifier: VTC (Voucher to Cash) categorization rules
- cat_expired_classifier: Expired voucher categorization rules
- cat_pipeline: Main categorization pipeline
"""

from src.bridges.cat_nav_classifier import (
    classify_integration_type,
    is_integration_user,
)
from src.bridges.cat_issuance_classifier import (
    classify_issuance,
    COUNTRY_CODES,
)
from src.bridges.cat_usage_classifier import (
    classify_usage,
    classify_manual_usage,
    lookup_voucher_type,
)
from src.bridges.cat_vtc_classifier import (
    classify_vtc,
    classify_vtc_bank_account,
    classify_vtc_pattern,
)
from src.bridges.cat_expired_classifier import (
    classify_expired,
    classify_manual_cancellation,
)
from src.bridges.cat_pipeline import (
    categorize_nav_vouchers,
    get_categorization_summary,
)

__all__ = [
    # NAV Classifier
    "classify_integration_type",
    "is_integration_user",
    # Issuance Classifier
    "classify_issuance",
    "COUNTRY_CODES",
    # Usage Classifier
    "classify_usage",
    "classify_manual_usage",
    "lookup_voucher_type",
    # VTC Classifier
    "classify_vtc",
    "classify_vtc_bank_account",
    "classify_vtc_pattern",
    # Expired Classifier
    "classify_expired",
    "classify_manual_cancellation",
    # Pipeline
    "categorize_nav_vouchers",
    "get_categorization_summary",
]
