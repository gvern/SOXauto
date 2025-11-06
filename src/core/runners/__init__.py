"""
Runners Package

IPE execution runners for SQL Server backend.
"""

from src.core.runners.mssql_runner import (
    IPERunner,
    IPEValidationError,
    IPEConnectionError,
)

# Aliases for clarity
IPERunnerMSSQL = IPERunner

__all__ = [
    'IPERunnerMSSQL',
    'IPERunner',
    'IPEValidationError',
    'IPEConnectionError',
]
