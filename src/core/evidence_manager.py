"""
evidence_manager.py (DEPRECATED - MOVED)

This module has been moved to src.core.evidence.manager
"""

import warnings

warnings.warn(
    "evidence_manager has been moved to src.core.evidence.manager",
    DeprecationWarning,
    stacklevel=2
)

from src.core.evidence.manager import *  # noqa: F401, F403
