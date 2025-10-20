"""
Runners Package

IPE execution runners for different backends (Athena, SQL Server).
"""

from src.core.runners.athena_runner import (
    IPERunnerAthena,
    IPEValidationError,
    IPEConnectionError,
)
from src.core.runners.mssql_runner import (
    IPERunner,
)

# Aliases for clarity
IPERunnerMSSQL = IPERunner

__all__ = [
    'IPERunnerAthena',
    'IPERunnerMSSQL',
    'IPERunner',
    'IPEValidationError',
    'IPEConnectionError',
]
