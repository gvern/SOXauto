"""
config_cpg1_athena.py (DEPRECATED - SPLIT)

This module has been split into focused components:
- IPE definitions → src.core.catalog.pg1_catalog
- Reconciliation logic → src.core.recon.cpg1
- Legacy config archived → src.core.legacy.config_cpg1_athena.py
"""

import warnings

warnings.warn(
    "config_cpg1_athena is deprecated. Use src.core.catalog for IPE definitions "
    "and src.core.recon.cpg1 for reconciliation logic",
    DeprecationWarning,
    stacklevel=2
)

# Re-export reconciliation functionality
from src.core.recon.cpg1 import CPG1ReconciliationConfig  # noqa: F401
