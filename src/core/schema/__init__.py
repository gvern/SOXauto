"""
Schema Contract System

Core infrastructure for treating columns as enforceable contracts with full
transformation tracking and audit trails.
"""

from src.core.schema.models import (
    CoercionRules,
    FillPolicy,
    SchemaContract,
    SchemaField,
    SchemaReport,
    SemanticTag,
    TransformEvent,
    TransformType,
    ValidationResult,
)

from src.core.schema.contract_registry import (
    get_active_contract,
    list_available_contracts,
    load_contract,
    clear_cache,
)

from src.core.schema.schema_utils import (
    apply_schema_contract,
    require_columns,
    ValidationPresets,
)

__all__ = [
    # Models
    "CoercionRules",
    "FillPolicy",
    "SchemaContract",
    "SchemaField",
    "SchemaReport",
    "SemanticTag",
    "TransformEvent",
    "TransformType",
    "ValidationResult",
    # Registry functions
    "get_active_contract",
    "list_available_contracts",
    "load_contract",
    "clear_cache",
    # Utility functions
    "apply_schema_contract",
    "require_columns",
    "ValidationPresets",
]
