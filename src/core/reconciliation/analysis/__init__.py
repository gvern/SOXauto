"""
Reconciliation Analysis Package for PG-01.

This package contains variance analysis and review table generation logic (Phase 3).
Modules support pivot generation, variance calculation, drilldown views, and review tables
for accounting team analysis.

Modules:
    pivots: NAV pivot + TV pivot generation
    variance: Variance calculation + thresholding
    drilldown: Voucher-level reconciliation views
    review_tables: "Accounting review required" tables

Example:
    >>> from src.core.reconciliation.analysis import generate_nav_pivot, calculate_variance
    >>> nav_pivot = generate_nav_pivot(nav_df, cutoff_date="2025-09-30")
    >>> variance_df = calculate_variance(nav_pivot, tv_pivot, threshold=1000)
"""

# Placeholder imports - to be populated as modules are implemented
# from src.core.reconciliation.analysis.pivots import generate_nav_pivot, generate_tv_pivot
# from src.core.reconciliation.analysis.variance import calculate_variance, apply_thresholds
# from src.core.reconciliation.analysis.drilldown import generate_drilldown_view
# from src.core.reconciliation.analysis.review_tables import generate_review_tables

__all__ = [
    # To be populated as modules are implemented
]
