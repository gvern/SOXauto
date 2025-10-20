"""
config.py (DEPRECATED - MOVED)

This module has been deprecated. The SQL Server/legacy configuration
has been archived to src.core.legacy.config.py for reference only.

For new development:
- Use src.core.catalog for IPE/CR definitions
- Use src.core.runners.mssql_runner for SQL Server execution
"""

import warnings

warnings.warn(
    "config.py is deprecated. Use src.core.catalog for IPE definitions",
    DeprecationWarning,
    stacklevel=2
)

# For backward compatibility, provide the legacy class structure
class IPEConfig:
    """Legacy compatibility shim"""
    
    @classmethod
    def load_ipe_config(cls, ipe_id: str):
        """
        DEPRECATED: Load IPE configuration (legacy SQL Server style)
        
        This method is provided for backward compatibility only.
        New code should use src.core.catalog.get_item_by_id()
        """
        raise NotImplementedError(
            "Legacy SQL Server config has been deprecated. "
            "Use src.core.catalog.get_item_by_id() for IPE definitions, "
            "or src.core.runners.mssql_runner.IPERunnerMSSQL for execution."
        )
