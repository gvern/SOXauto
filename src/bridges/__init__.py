"""
Bridges subsystem for SOX compliance reconciliation.

This package provides components for bridge classification, categorization,
and calculation in the context of financial reconciliation:

Public API:
-----------
Registry:
    - BridgeRule: Dataclass representing bridge business rules
    - load_rules: Factory function to load bridge rule definitions

Generic Bridge Classification:
    - classify_bridges: Generic rule-based bridge classification engine

Bridge Calculations:
    - identify_business_line_reclass_candidates: Identify business line reclass candidates (CLE-based)
    - calculate_business_line_bridge: Calculate business line (Biz Line) bridge (placeholder v1, deprecated)
    - calculate_customer_posting_group_bridge: Calculate customer posting group bridge
    - calculate_vtc_adjustment: Calculate VTC (Voucher to Cash) adjustment bridge
    - calculate_timing_difference_bridge: Calculate timing difference bridge

NAV Voucher Categorization:
    - categorize_nav_vouchers: Main categorization orchestrator for NAV vouchers
    - get_categorization_summary: Get summary statistics for categorized data

Usage Example:
--------------
    >>> from src.bridges import BridgeRule, load_rules, classify_bridges
    >>> rules = load_rules()
    >>> classified_df = classify_bridges(df, rules)
    
    >>> from src.bridges import categorize_nav_vouchers
    >>> categorized_df = categorize_nav_vouchers(cr_03_df, ipe_08_df)
    
    >>> from src.bridges import calculate_vtc_adjustment
    >>> variance, proof_df, metrics = calculate_vtc_adjustment(ipe_08_df, cr_03_df, cutoff_date)
    
    >>> from src.bridges import identify_business_line_reclass_candidates
    >>> candidates = identify_business_line_reclass_candidates(cle_df, "2025-09-30")
"""

# Core registry - Bridge business rules
from src.bridges.catalog import BridgeRule, load_rules

# Generic bridge classification
from src.bridges.classifier import classify_bridges

# Bridge calculations (from calculations package)
from src.bridges.calculations import (
    identify_business_line_reclass_candidates,
    calculate_business_line_bridge,
    calculate_customer_posting_group_bridge,
    calculate_vtc_adjustment,
    calculate_timing_difference_bridge,
)

# NAV voucher categorization pipeline
from src.bridges.categorization import (
    categorize_nav_vouchers,
    get_categorization_summary,
)

__all__ = [
    # Registry
    "BridgeRule",
    "load_rules",
    # Generic Bridge Classification
    "classify_bridges",
    # Bridge Calculations
    "identify_business_line_reclass_candidates",
    "calculate_business_line_bridge",
    "calculate_customer_posting_group_bridge",
    "calculate_vtc_adjustment",
    "calculate_timing_difference_bridge",
    # NAV Voucher Categorization
    "categorize_nav_vouchers",
    "get_categorization_summary",
]
