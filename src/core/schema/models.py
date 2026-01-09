"""
Schema Contract Models

Core data structures for schema contracts, transformation tracking, and validation reporting.
Implements the foundational types for treating columns as enforceable contracts with full
lineage tracking for SOX audit compliance.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class SemanticTag(str, Enum):
    """Semantic type tags for columns."""
    AMOUNT = "amount"
    DATE = "date"
    KEY = "key"
    ID = "id"
    CODE = "code"
    NAME = "name"
    FLAG = "flag"
    COUNT = "count"
    RATE = "rate"
    OTHER = "other"


class FillPolicy(str, Enum):
    """Policy for handling NaN/null values after coercion."""
    KEEP_NAN = "keep_nan"          # Preserve NaN values (default for raw extracts)
    FILL_ZERO = "fill_zero"        # Fill NaN with 0.0 (for derived totals)
    FILL_EMPTY = "fill_empty"      # Fill NaN with empty string
    FAIL_ON_NAN = "fail_on_nan"    # Raise error if NaN detected


class TransformType(str, Enum):
    """Types of column transformations."""
    RENAME = "rename"
    CAST = "cast"
    DROP = "drop"
    ADD = "add"
    DERIVE = "derive"
    NORMALIZE = "normalize"
    FILL = "fill"


@dataclass
class CoercionRules:
    """Rules for coercing string values to target types."""
    strip_whitespace: bool = True
    remove_commas: bool = True          # For amounts: "1,234.56" → 1234.56
    remove_spaces: bool = True          # For amounts: "1 234.56" → 1234.56
    remove_currency_symbols: bool = True # For amounts: "$1,234" → 1234.0
    date_formats: List[str] = field(default_factory=lambda: [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"
    ])
    
    @staticmethod
    def strict() -> 'CoercionRules':
        """Strict coercion: fail on unexpected formats."""
        return CoercionRules(
            strip_whitespace=True,
            remove_commas=False,
            remove_spaces=False,
            remove_currency_symbols=False
        )
    
    @staticmethod
    def permissive() -> 'CoercionRules':
        """Permissive coercion: handle various formats (default)."""
        return CoercionRules()


@dataclass
class SchemaField:
    """Definition of a single field/column in a schema contract."""
    name: str                                    # Canonical column name
    required: bool                               # Must exist in dataset
    aliases: List[str] = field(default_factory=list)  # Alternative names
    dtype: str = "string"                        # Expected Python/pandas dtype
    semantic_tag: SemanticTag = SemanticTag.OTHER
    coercion_rules: Optional[CoercionRules] = None
    fill_policy: FillPolicy = FillPolicy.KEEP_NAN
    description: Optional[str] = None
    reconciliation_critical: bool = False        # Flag for audit importance
    validation_rules: Dict[str, Any] = field(default_factory=dict)  # min/max, patterns, etc.
    
    def __post_init__(self):
        """Set default coercion rules based on semantic tag."""
        if self.coercion_rules is None:
            if self.semantic_tag == SemanticTag.AMOUNT:
                self.coercion_rules = CoercionRules.permissive()
            elif self.semantic_tag == SemanticTag.DATE:
                self.coercion_rules = CoercionRules(
                    strip_whitespace=True,
                    remove_commas=False,
                    remove_spaces=False,
                    remove_currency_symbols=False
                )
            else:
                self.coercion_rules = CoercionRules.strict()


@dataclass
class SchemaContract:
    """
    Complete schema contract for a dataset (IPE/CR/DOC).
    
    Defines the canonical structure, validation rules, and transformation policies
    for a specific dataset and version.
    """
    dataset_id: str                              # e.g., "IPE_07", "CR_04"
    version: int                                 # Schema version (1, 2, 3...)
    fields: List[SchemaField]                    # Column definitions
    primary_keys: List[str] = field(default_factory=list)
    description: Optional[str] = None
    source_system: Optional[str] = None          # e.g., "NAV", "Jdash"
    created_at: Optional[datetime] = None
    deprecated: bool = False
    
    # Contract metadata
    contract_hash: Optional[str] = None          # SHA-256 of contract content
    
    def get_field(self, column_name: str) -> Optional[SchemaField]:
        """Get field definition by canonical name."""
        for field_def in self.fields:
            if field_def.name == column_name:
                return field_def
        return None
    
    def get_field_by_alias(self, alias: str) -> Optional[SchemaField]:
        """Get field definition by any alias (including canonical name)."""
        for field_def in self.fields:
            if alias == field_def.name or alias in field_def.aliases:
                return field_def
        return None
    
    def get_required_fields(self) -> List[SchemaField]:
        """Get all required field definitions."""
        return [f for f in self.fields if f.required]
    
    def get_canonical_names(self) -> List[str]:
        """Get list of all canonical column names."""
        return [f.name for f in self.fields]


@dataclass
class TransformEvent:
    """
    Record of a single transformation operation on a DataFrame.
    
    Used for audit trails and debugging column lineage issues.
    """
    event_type: TransformType
    timestamp: datetime
    source: str                                  # e.g., "schema.apply", "bridge:timing"
    columns: List[str]                           # Affected column names
    
    # Before/after state
    before_dtype: Optional[str] = None
    after_dtype: Optional[str] = None
    before_name: Optional[str] = None            # For renames
    after_name: Optional[str] = None
    
    # Impact metrics
    row_count_before: Optional[int] = None
    row_count_after: Optional[int] = None
    null_count_before: Optional[int] = None
    null_count_after: Optional[int] = None
    invalid_coerced_to_nan: int = 0              # Values that couldn't be coerced
    values_filled: int = 0                       # NaN values filled per fill_policy
    
    # Derivation info (for derived columns)
    derived_from: List[str] = field(default_factory=list)
    formula: Optional[str] = None
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        def _convert_value(v):
            """Convert numpy/pandas types to native Python types for JSON."""
            import numpy as np
            if isinstance(v, (np.integer, np.int64, np.int32)):
                return int(v)
            elif isinstance(v, (np.floating, np.float64, np.float32)):
                return float(v)
            elif isinstance(v, np.bool_):
                return bool(v)
            elif isinstance(v, dict):
                return {k: _convert_value(val) for k, val in v.items()}
            elif isinstance(v, (list, tuple)):
                return [_convert_value(val) for val in v]
            return v
        
        return {
            "event_type": self.event_type.value if isinstance(self.event_type, Enum) else self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "columns": self.columns,
            "before_dtype": self.before_dtype,
            "after_dtype": self.after_dtype,
            "before_name": self.before_name,
            "after_name": self.after_name,
            "row_count_before": _convert_value(self.row_count_before),
            "row_count_after": _convert_value(self.row_count_after),
            "null_count_before": _convert_value(self.null_count_before),
            "null_count_after": _convert_value(self.null_count_after),
            "invalid_coerced_to_nan": _convert_value(self.invalid_coerced_to_nan),
            "values_filled": _convert_value(self.values_filled),
            "derived_from": self.derived_from,
            "formula": self.formula,
            "metadata": _convert_value(self.metadata)
        }


@dataclass
class SchemaReport:
    """
    Comprehensive report of schema validation and transformations.
    
    Contains all transformation events and summary statistics for audit trails.
    """
    dataset_id: str
    version: int
    contract_hash: str
    timestamp: datetime
    success: bool
    
    # Transformation events
    events: List[TransformEvent] = field(default_factory=list)
    
    # Summary statistics
    columns_renamed: Dict[str, str] = field(default_factory=dict)  # before -> after
    columns_cast: Dict[str, tuple] = field(default_factory=dict)   # name -> (before, after)
    columns_added: List[str] = field(default_factory=list)
    columns_dropped: List[str] = field(default_factory=list)
    unknown_columns_kept: List[str] = field(default_factory=list)
    
    # Validation results
    required_columns_missing: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    
    # Row impact
    row_count_before: int = 0
    row_count_after: int = 0
    total_invalid_coerced: int = 0
    total_values_filled: int = 0
    
    def add_event(self, event: TransformEvent):
        """Add a transformation event to the report."""
        self.events.append(event)
        
        # Update summary statistics
        if event.event_type == TransformType.RENAME and event.before_name and event.after_name:
            self.columns_renamed[event.before_name] = event.after_name
        elif event.event_type == TransformType.CAST and event.before_dtype and event.after_dtype:
            for col in event.columns:
                self.columns_cast[col] = (event.before_dtype, event.after_dtype)
        elif event.event_type == TransformType.ADD:
            self.columns_added.extend(event.columns)
        elif event.event_type == TransformType.DROP:
            self.columns_dropped.extend(event.columns)
        
        # Update row impact
        self.total_invalid_coerced += event.invalid_coerced_to_nan
        self.total_values_filled += event.values_filled
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        def _convert_value(v):
            """Convert numpy/pandas types to native Python types for JSON."""
            import numpy as np
            if isinstance(v, (np.integer, np.int64, np.int32)):
                return int(v)
            elif isinstance(v, (np.floating, np.float64, np.float32)):
                return float(v)
            elif isinstance(v, np.bool_):
                return bool(v)
            elif isinstance(v, dict):
                return {k: _convert_value(val) for k, val in v.items()}
            elif isinstance(v, (list, tuple)):
                return [_convert_value(val) for val in v]
            return v
        
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "contract_hash": self.contract_hash,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "summary": {
                "columns_renamed": self.columns_renamed,
                "columns_cast": {k: {"before": v[0], "after": v[1]} for k, v in self.columns_cast.items()},
                "columns_added": self.columns_added,
                "columns_dropped": self.columns_dropped,
                "unknown_columns_kept": self.unknown_columns_kept,
                "required_columns_missing": self.required_columns_missing,
                "row_count_before": _convert_value(self.row_count_before),
                "row_count_after": _convert_value(self.row_count_after),
                "total_invalid_coerced": _convert_value(self.total_invalid_coerced),
                "total_values_filled": _convert_value(self.total_values_filled)
            },
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
            "events": [event.to_dict() for event in self.events]
        }


# Validation result types
@dataclass
class ValidationResult:
    """Result of a single validation check."""
    passed: bool
    rule_name: str
    message: str
    column: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
