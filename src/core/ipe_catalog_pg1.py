"""
ipe_catalog_pg1.py (DEPRECATED - MOVED)

This module has been moved to src.core.catalog.pg1_catalog
"""

import warnings

warnings.warn(
    "ipe_catalog_pg1 has been moved to src.core.catalog.pg1_catalog",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
from src.core.catalog.pg1_catalog import *  # noqa: F401, F403
