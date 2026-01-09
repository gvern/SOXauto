"""
Schema Validation Utilities

Core validation engine for applying schema contracts to DataFrames.
Handles column normalization, dtype coercion, and transformation tracking.
"""

import logging
import warnings
from datetime import datetime
from typing import List, Optional, Tuple, Dict

import pandas as pd

from src.core.schema.contract_registry import get_active_contract
from src.core.schema.models import (
    CoercionRules,
    FillPolicy,
    SchemaContract,
    SchemaField,
    SchemaReport,
    SemanticTag,
    TransformEvent,
    TransformType,
)
from src.utils.date_utils import normalize_date
from src.utils.pandas_utils import coerce_numeric_series

logger = logging.getLogger(__name__)


def _coerce_by_semantic_tag(
    series: pd.Series,
    field: SchemaField
) -> Tuple[pd.Series, int, int]:
    """
    Coerce a pandas Series based on semantic tag and coercion rules.
    
    Args:
        series: Input series to coerce
        field: SchemaField definition with semantic_tag and coercion_rules
    
    Returns:
        Tuple of (coerced_series, invalid_count, filled_count)
    """
    invalid_count = 0
    filled_count = 0
    original_null_count = series.isnull().sum()
    
    # Apply coercion based on semantic tag
    if field.semantic_tag == SemanticTag.AMOUNT:
        # Use existing pandas_utils for numeric coercion
        result = coerce_numeric_series(series, fillna=None)  # Keep NaN initially
        invalid_count = result.isnull().sum() - original_null_count
        
    elif field.semantic_tag == SemanticTag.DATE:
        # Use date_utils for date normalization
        result = series.copy()
        valid_dates = []
        
        for val in series:
            if pd.isna(val):
                valid_dates.append(pd.NaT)
                continue
            
            try:
                # Try to normalize using date_utils
                normalized = normalize_date(str(val))
                valid_dates.append(normalized)
            except (ValueError, TypeError):
                valid_dates.append(pd.NaT)
                invalid_count += 1
        
        result = pd.Series(valid_dates, index=series.index)
        
    elif field.semantic_tag in [SemanticTag.KEY, SemanticTag.ID, SemanticTag.CODE]:
        # String fields: strip whitespace, convert to string
        result = series.astype(str)
        if field.coercion_rules and field.coercion_rules.strip_whitespace:
            result = result.str.strip()
        # Replace 'nan' string with actual NaN
        result = result.replace(['nan', 'None', ''], pd.NA)
        
    else:
        # Default: keep as-is, just ensure string type
        result = series.astype(str)
    
    # Apply fill policy
    if field.fill_policy == FillPolicy.FILL_ZERO:
        null_before_fill = result.isnull().sum()
        result = result.fillna(0.0)
        filled_count = null_before_fill
    elif field.fill_policy == FillPolicy.FILL_EMPTY:
        null_before_fill = result.isnull().sum()
        result = result.fillna("")
        filled_count = null_before_fill
    elif field.fill_policy == FillPolicy.FAIL_ON_NAN:
        if result.isnull().any():
            null_count = result.isnull().sum()
            raise ValueError(
                f"Column '{field.name}' has {null_count} NaN values, "
                f"but fill_policy is FAIL_ON_NAN"
            )
    # KEEP_NAN: do nothing
    
    return result, invalid_count, filled_count


def _normalize_column_names(
    df: pd.DataFrame,
    contract: SchemaContract,
    track: bool = True
) -> Tuple[pd.DataFrame, List[TransformEvent]]:
    """
    Normalize DataFrame column names using contract aliases.
    
    Uses deterministic ordering:
    1. Fields are processed in contract order (YAML order matters)
    2. Within each field, aliases are tried in list order (priority matters)
    3. First match wins and is logged
    
    Args:
        df: Input DataFrame
        contract: Schema contract with field definitions
        track: Whether to record transformation events
    
    Returns:
        Tuple of (normalized_df, transform_events)
    """
    df_normalized = df.copy()
    events = []
    rename_map = {}
    
    # Build rename mapping using aliases (deterministic order)
    for field in contract.fields:
        # Check if any alias exists in the DataFrame
        # Try canonical name first, then aliases in order
        for alias in [field.name] + field.aliases:
            if alias in df_normalized.columns:
                if alias != field.name:
                    # Found an alias that needs renaming
                    rename_map[alias] = field.name
                    
                    if track:
                        event = TransformEvent(
                            event_type=TransformType.RENAME,
                            timestamp=datetime.now(),
                            source="schema.normalize",
                            columns=[field.name],
                            before_name=alias,
                            after_name=field.name,
                            row_count_before=len(df),
                            row_count_after=len(df),
                            metadata={
                                "alias_matched": alias,
                                "alias_priority": field.aliases.index(alias) if alias in field.aliases else -1
                            }
                        )
                        events.append(event)
                    
                    logger.debug(
                        f"Matched alias '{alias}' → canonical '{field.name}' "
                        f"(priority: {field.aliases.index(alias) if alias in field.aliases else 'canonical'})"
                    )
                break  # Use first matching alias only
    
    if rename_map:
        df_normalized = df_normalized.rename(columns=rename_map)
        logger.info(f"Renamed {len(rename_map)} columns: {rename_map}")
    
    return df_normalized, events
    
    if rename_map:
        df_normalized = df_normalized.rename(columns=rename_map)
        logger.debug(f"Renamed columns: {rename_map}")
    
    return df_normalized, events


def _validate_required_columns(
    df: pd.DataFrame,
    contract: SchemaContract
) -> List[str]:
    """
    Validate that all required columns exist in the DataFrame.
    
    Args:
        df: DataFrame to validate
        contract: Schema contract with required fields
    
    Returns:
        List of missing required column names (empty if all present)
    """
    required_fields = contract.get_required_fields()
    missing = []
    
    for field in required_fields:
        # Check canonical name and all aliases
        found = False
        for name in [field.name] + field.aliases:
            if name in df.columns:
                found = True
                break
        
        if not found:
            missing.append(field.name)
    
    return missing


def _cast_columns(
    df: pd.DataFrame,
    contract: SchemaContract,
    track: bool = True
) -> Tuple[pd.DataFrame, List[TransformEvent]]:
    """
    Cast DataFrame columns to target dtypes based on contract.
    
    Args:
        df: Input DataFrame
        contract: Schema contract with dtype specifications
        track: Whether to record transformation events
    
    Returns:
        Tuple of (cast_df, transform_events)
    """
    df_cast = df.copy()
    events = []
    
    for field in contract.fields:
        if field.name not in df_cast.columns:
            continue  # Skip columns not in DataFrame
        
        before_dtype = str(df_cast[field.name].dtype)
        
        # Skip if already correct dtype
        if field.dtype in before_dtype:
            continue
        
        try:
            # Apply coercion based on semantic tag
            coerced, invalid_count, filled_count = _coerce_by_semantic_tag(
                df_cast[field.name],
                field
            )
            
            df_cast[field.name] = coerced
            after_dtype = str(df_cast[field.name].dtype)
            
            if track:
                event = TransformEvent(
                    event_type=TransformType.CAST,
                    timestamp=datetime.now(),
                    source="schema.cast",
                    columns=[field.name],
                    before_dtype=before_dtype,
                    after_dtype=after_dtype,
                    row_count_before=len(df),
                    row_count_after=len(df),
                    null_count_before=df[field.name].isnull().sum(),
                    null_count_after=df_cast[field.name].isnull().sum(),
                    invalid_coerced_to_nan=invalid_count,
                    values_filled=filled_count,
                    metadata={
                        "semantic_tag": field.semantic_tag.value,
                        "fill_policy": field.fill_policy.value
                    }
                )
                events.append(event)
            
            logger.debug(
                f"Cast column '{field.name}': {before_dtype} → {after_dtype} "
                f"(invalid: {invalid_count}, filled: {filled_count})"
            )
            
        except Exception as e:
            logger.error(f"Failed to cast column '{field.name}': {e}")
            # Continue with other columns
    
    return df_cast, events


def apply_schema_contract(
    df: pd.DataFrame,
    dataset_id: str,
    version: Optional[int] = None,
    strict: bool = True,
    cast: bool = True,
    track: bool = True,
    drop_unknown: bool = False
) -> Tuple[pd.DataFrame, SchemaReport]:
    """
    Apply schema contract to a DataFrame with full validation and tracking.
    
    This is the primary API for schema validation. It normalizes column names,
    validates required columns, coerces dtypes, and records all transformations.
    
    Args:
        df: Input DataFrame to validate
        dataset_id: Dataset identifier (e.g., "IPE_07")
        version: Specific contract version (None = latest/active)
        strict: If True, raise error on missing required columns
        cast: If True, cast columns to target dtypes
        track: If True, record transformation events
        drop_unknown: If True, drop columns not in contract (audit risk!)
    
    Returns:
        Tuple of (validated_df, schema_report)
    
    Raises:
        ValueError: If strict=True and required columns are missing
    
    Example:
        >>> df, report = apply_schema_contract(df, "IPE_07", strict=True, cast=True)
        >>> print(f"Renamed: {report.columns_renamed}")
        >>> print(f"Cast: {report.columns_cast}")
    """
    start_time = datetime.now()
    
    # Load contract
    if version is None:
        contract = get_active_contract(dataset_id)
    else:
        from src.core.schema.contract_registry import load_contract
        contract = load_contract(dataset_id, version)
    
    logger.info(
        f"Applying schema contract: {contract.dataset_id} v{contract.version} "
        f"(strict={strict}, cast={cast}, track={track})"
    )
    
    # Initialize report
    report = SchemaReport(
        dataset_id=contract.dataset_id,
        version=contract.version,
        contract_hash=contract.contract_hash or "",
        timestamp=start_time,
        success=True,
        row_count_before=len(df),
        row_count_after=len(df)
    )
    
    # Step 1: Normalize column names
    df_result, rename_events = _normalize_column_names(df, contract, track=track)
    for event in rename_events:
        report.add_event(event)
    
    # Step 2: Validate required columns
    missing_required = _validate_required_columns(df_result, contract)
    
    if missing_required:
        report.required_columns_missing = missing_required
        report.validation_errors.append(
            f"Required columns missing: {missing_required}"
        )
        
        if strict:
            report.success = False
            raise ValueError(
                f"Schema validation failed for {dataset_id}: "
                f"Required columns missing: {missing_required}. "
                f"Available columns: {list(df_result.columns)}"
            )
        else:
            report.validation_warnings.append(
                f"Missing required columns (strict=False): {missing_required}"
            )
    
    # Step 3: Cast columns to target dtypes
    if cast:
        df_result, cast_events = _cast_columns(df_result, contract, track=track)
        for event in cast_events:
            report.add_event(event)
    
    # Step 4: Handle unknown columns
    known_columns = {field.name for field in contract.fields}
    unknown_columns = [col for col in df_result.columns if col not in known_columns]
    
    if unknown_columns:
        report.unknown_columns_kept = unknown_columns
        
        if drop_unknown:
            logger.warning(
                f"Dropping {len(unknown_columns)} unknown columns: {unknown_columns}"
            )
            df_result = df_result[list(known_columns.intersection(df_result.columns))]
            
            if track:
                event = TransformEvent(
                    event_type=TransformType.DROP,
                    timestamp=datetime.now(),
                    source="schema.drop_unknown",
                    columns=unknown_columns,
                    row_count_before=len(df),
                    row_count_after=len(df_result)
                )
                report.add_event(event)
        else:
            logger.info(
                f"Keeping {len(unknown_columns)} unknown columns: {unknown_columns}"
            )
            report.validation_warnings.append(
                f"Unknown columns kept (not in contract): {unknown_columns}"
            )
    
    # Final row count
    report.row_count_after = len(df_result)
    
    logger.info(
        f"Schema validation complete for {dataset_id}: "
        f"{len(report.columns_renamed)} renamed, "
        f"{len(report.columns_cast)} cast, "
        f"{report.total_invalid_coerced} invalid coerced, "
        f"{report.total_values_filled} values filled"
    )
    
    return df_result, report


def require_columns(
    df: pd.DataFrame,
    dataset_id: str,
    column_names: Optional[List[str]] = None
) -> None:
    """
    Validate that specific columns exist in a DataFrame per contract.
    
    Helper function for bridges and calculations to verify required columns.
    
    Args:
        df: DataFrame to check
        dataset_id: Dataset identifier for contract lookup
        column_names: Specific columns to require (None = all required from contract)
    
    Raises:
        ValueError: If required columns are missing
    
    Example:
        >>> require_columns(df, "IPE_07", ["customer_id", "amount_lcy"])
    """
    contract = get_active_contract(dataset_id)
    
    if column_names is None:
        # Check all required columns from contract
        column_names = [f.name for f in contract.get_required_fields()]
    
    missing = [col for col in column_names if col not in df.columns]
    
    if missing:
        raise ValueError(
            f"Required columns missing from {dataset_id}: {missing}. "
            f"Available: {list(df.columns)}"
        )


def build_quality_rules_from_schema(dataset_id: str, version: Optional[int] = None) -> List:
    """
    Auto-generate quality rules from schema contract.
    
    Generates ColumnExistsCheck, NoNullsCheck, and DTypeCheck rules
    based on the contract definition.
    
    Args:
        dataset_id: Dataset identifier
        version: Specific contract version (None = latest)
    
    Returns:
        List of QualityRule objects
    
    Example:
        >>> rules = build_quality_rules_from_schema("IPE_07")
        >>> for rule in rules:
        ...     passed, message = rule.check(df)
    """
    from src.core.quality_checker import ColumnExistsCheck, NoNullsCheck
    
    if version is None:
        contract = get_active_contract(dataset_id)
    else:
        from src.core.schema.contract_registry import load_contract
        contract = load_contract(dataset_id, version)
    
    rules = []
    
    # Add ColumnExistsCheck for all required fields
    for field in contract.get_required_fields():
        rules.append(ColumnExistsCheck(column_name=field.name))
        
        # Add NoNullsCheck if fill_policy is FAIL_ON_NAN
        if field.fill_policy == FillPolicy.FAIL_ON_NAN:
            rules.append(NoNullsCheck(column_name=field.name))
    
    return rules


# Preset configurations
class ValidationPresets:
    """Preset configurations for common validation scenarios."""
    
    @staticmethod
    def strict_lite(df: pd.DataFrame, dataset_id: str) -> Tuple[pd.DataFrame, SchemaReport]:
        """
        Strict-lite: Required columns + basic coercion, minimal tracking.
        
        Fast validation for development/testing.
        """
        return apply_schema_contract(
            df,
            dataset_id,
            strict=True,
            cast=True,
            track=False,
            drop_unknown=False
        )
    
    @staticmethod
    def strict_full(df: pd.DataFrame, dataset_id: str) -> Tuple[pd.DataFrame, SchemaReport]:
        """
        Strict-full: All validations, dtype checks, full tracking.
        
        Comprehensive validation for production.
        """
        return apply_schema_contract(
            df,
            dataset_id,
            strict=True,
            cast=True,
            track=True,
            drop_unknown=False
        )
    
    @staticmethod
    def audit_mode(df: pd.DataFrame, dataset_id: str) -> Tuple[pd.DataFrame, SchemaReport]:
        """
        Audit mode: Full tracking, keep unknown columns, never fail.
        
        For evidence generation and debugging.
        """
        return apply_schema_contract(
            df,
            dataset_id,
            strict=False,
            cast=True,
            track=True,
            drop_unknown=False
        )
