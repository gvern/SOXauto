"""
Bridge calculations module.

Contains specialized calculation functions for PG-01 reconciliation bridges.
"""

from src.bridges.calculations.business_line_reclass import identify_business_line_reclass_candidates
from src.bridges.calculations.customer_posting_group import calculate_customer_posting_group_bridge
from src.bridges.calculations.timing import calculate_timing_difference_bridge
from src.bridges.calculations.vtc import calculate_vtc_adjustment

# Backward compatibility: Keep old import from biz_line (deprecated)
from src.bridges.calculations.biz_line import calculate_business_line_bridge

__all__ = [
    "identify_business_line_reclass_candidates",
    "calculate_business_line_bridge",  # Deprecated - use identify_business_line_reclass_candidates
    "calculate_customer_posting_group_bridge",
    "calculate_timing_difference_bridge",
    "calculate_vtc_adjustment",
]
