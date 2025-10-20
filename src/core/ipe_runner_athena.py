"""
ipe_runner_athena.py (DEPRECATED - MOVED)

This module has been moved to src.core.runners.athena_runner
"""

import warnings

warnings.warn(
    "ipe_runner_athena has been moved to src.core.runners.athena_runner",
    DeprecationWarning,
    stacklevel=2
)

from src.core.runners.athena_runner import *  # noqa: F401, F403
