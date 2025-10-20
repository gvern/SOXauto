"""
config_athena.py (DEPRECATED SHIM)

WARNING: This module is deprecated.

Use src.core.catalog.get_athena_config() instead.
"""

import warnings
from typing import Dict, Any, List

warnings.warn(
    "config_athena is deprecated. Use src.core.catalog instead.",
    DeprecationWarning,
    stacklevel=2
)


class IPEConfigAthena:
    """DEPRECATED: Use src.core.catalog instead."""

    @classmethod
    def load_ipe_config(cls, ipe_id: str) -> Dict[str, Any]:
        from src.core.catalog import get_athena_config
        return get_athena_config(ipe_id)

    @classmethod
    def list_ipes(cls) -> List[str]:
        from src.core.catalog import list_athena_ipes
        return list_athena_ipes()
