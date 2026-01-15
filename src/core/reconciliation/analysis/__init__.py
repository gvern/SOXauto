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
    >>> from src.core.reconciliation.analysis import build_target_values_pivot_local
    >>> from src.core.reconciliation.analysis import compute_variance_pivot_local
    >>> from src.utils.fx_utils import FXConverter
    >>> 
    >>> # Build TV pivot from raw data
    >>> tv_pivot = build_target_values_pivot_local(issuance_df)
    >>> 
    >>> # Compute variance with FX conversion
    >>> fx_converter = FXConverter(cr05_df)
    >>> variance_df = compute_variance_pivot_local(
    ...     nav_pivot, tv_pivot, fx_converter, "2025-09-30"
    ... )
"""

# Import implemented functions
from src.core.reconciliation.analysis.pivots import (
    build_target_values_pivot_local,
    build_nav_pivot,
)
from src.core.reconciliation.analysis.variance import (
    compute_variance_pivot_local,
)

__all__ = [
    "build_target_values_pivot_local",
    "build_nav_pivot",
    "compute_variance_pivot_local",
]
