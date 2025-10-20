"""
ipe_runner.py (DEPRECATED - MOVED)

This module has been moved to src.core.runners.mssql_runner
"""

import warnings

warnings.warn(
    "ipe_runner has been moved to src.core.runners.mssql_runner",
    DeprecationWarning,
    stacklevel=2
)

from src.core.runners.mssql_runner import *  # noqa: F401, F403
