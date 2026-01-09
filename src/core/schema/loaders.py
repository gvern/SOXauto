"""
Data Loading Utilities with Schema Validation

Helpers for loading CSV, Excel, and fixture data with automatic schema validation.
Ensures all uploaded data goes through the same schema contract enforcement as SQL extractions.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Union

import pandas as pd

from src.core.schema.contract_registry import get_active_contract
from src.core.schema.models import SchemaReport
from src.core.schema.schema_utils import apply_schema_contract

logger = logging.getLogger(__name__)


def load_csv_with_schema(
    filepath: Union[str, Path],
    dataset_id: str,
    version: Optional[int] = None,
    strict: bool = True,
    cast: bool = True,
    track: bool = True,
    **csv_kwargs
) -> Tuple[pd.DataFrame, SchemaReport]:
    """
    Load CSV file with automatic schema validation.
    
    Applies the same schema contract enforcement as SQL extractions to ensure
    consistency across all data sources.
    
    Args:
        filepath: Path to CSV file
        dataset_id: Dataset identifier (e.g., "IPE_07", "JDASH")
        version: Specific contract version (None = latest/active)
        strict: If True, fail on missing required columns
        cast: If True, cast columns to target dtypes
        track: If True, record transformation events
        **csv_kwargs: Additional arguments passed to pd.read_csv()
    
    Returns:
        Tuple of (validated_df, schema_report)
    
    Example:
        >>> df, report = load_csv_with_schema(
        ...     "data/jdash_export.csv",
        ...     dataset_id="JDASH",
        ...     strict=True
        ... )
        >>> print(f"Loaded {len(df)} rows with {len(report.columns_renamed)} renames")
    """
    logger.info(f"Loading CSV with schema validation: {filepath} (dataset: {dataset_id})")
    
    # Load CSV
    df_raw = pd.read_csv(filepath, **csv_kwargs)
    logger.debug(f"Loaded {len(df_raw)} rows, {len(df_raw.columns)} columns from {filepath}")
    
    # Apply schema contract
    df_validated, report = apply_schema_contract(
        df_raw,
        dataset_id=dataset_id,
        version=version,
        strict=strict,
        cast=cast,
        track=track
    )
    
    # Add source metadata to report
    report.validation_warnings.insert(0, f"Data source: CSV file {filepath}")
    
    logger.info(
        f"CSV validation complete: {len(df_validated)} rows, "
        f"{len(report.columns_renamed)} renamed, "
        f"{len(report.columns_cast)} cast"
    )
    
    return df_validated, report


def load_excel_with_schema(
    filepath: Union[str, Path],
    dataset_id: str,
    sheet_name: Union[str, int] = 0,
    version: Optional[int] = None,
    strict: bool = True,
    cast: bool = True,
    track: bool = True,
    **excel_kwargs
) -> Tuple[pd.DataFrame, SchemaReport]:
    """
    Load Excel file with automatic schema validation.
    
    Args:
        filepath: Path to Excel file
        dataset_id: Dataset identifier
        sheet_name: Sheet to load (name or index)
        version: Specific contract version (None = latest/active)
        strict: If True, fail on missing required columns
        cast: If True, cast columns to target dtypes
        track: If True, record transformation events
        **excel_kwargs: Additional arguments passed to pd.read_excel()
    
    Returns:
        Tuple of (validated_df, schema_report)
    
    Example:
        >>> df, report = load_excel_with_schema(
        ...     "data/monthly_extract.xlsx",
        ...     dataset_id="IPE_07",
        ...     sheet_name="Customer_Ledger"
        ... )
    """
    logger.info(
        f"Loading Excel with schema validation: {filepath} "
        f"sheet={sheet_name} (dataset: {dataset_id})"
    )
    
    # Load Excel
    df_raw = pd.read_excel(filepath, sheet_name=sheet_name, **excel_kwargs)
    logger.debug(
        f"Loaded {len(df_raw)} rows, {len(df_raw.columns)} columns "
        f"from {filepath} (sheet: {sheet_name})"
    )
    
    # Apply schema contract
    df_validated, report = apply_schema_contract(
        df_raw,
        dataset_id=dataset_id,
        version=version,
        strict=strict,
        cast=cast,
        track=track
    )
    
    # Add source metadata to report
    report.validation_warnings.insert(
        0,
        f"Data source: Excel file {filepath}, sheet '{sheet_name}'"
    )
    
    logger.info(
        f"Excel validation complete: {len(df_validated)} rows, "
        f"{len(report.columns_renamed)} renamed, "
        f"{len(report.columns_cast)} cast"
    )
    
    return df_validated, report


def load_fixture_with_schema(
    fixture_name: str,
    dataset_id: str,
    fixtures_dir: Optional[Path] = None,
    version: Optional[int] = None,
    strict: bool = False,  # Less strict for fixtures by default
    cast: bool = True,
    track: bool = True
) -> Tuple[pd.DataFrame, SchemaReport]:
    """
    Load test fixture with automatic schema validation.
    
    Fixtures are typically less strict (strict=False by default) to allow
    test data with minor variations, but still benefit from normalization.
    
    Args:
        fixture_name: Fixture filename (e.g., "fixture_IPE_07.csv")
        dataset_id: Dataset identifier
        fixtures_dir: Path to fixtures directory (default: tests/fixtures/)
        version: Specific contract version (None = latest/active)
        strict: If True, fail on missing required columns (default: False for fixtures)
        cast: If True, cast columns to target dtypes
        track: If True, record transformation events
    
    Returns:
        Tuple of (validated_df, schema_report)
    
    Example:
        >>> df, report = load_fixture_with_schema(
        ...     "fixture_JDASH.csv",
        ...     dataset_id="JDASH"
        ... )
    """
    if fixtures_dir is None:
        # Default to tests/fixtures/ relative to project root
        import os
        project_root = Path(__file__).parent.parent.parent.parent
        fixtures_dir = project_root / "tests" / "fixtures"
    
    filepath = Path(fixtures_dir) / fixture_name
    
    if not filepath.exists():
        raise FileNotFoundError(f"Fixture not found: {filepath}")
    
    logger.info(
        f"Loading fixture with schema validation: {fixture_name} (dataset: {dataset_id})"
    )
    
    return load_csv_with_schema(
        filepath=filepath,
        dataset_id=dataset_id,
        version=version,
        strict=strict,
        cast=cast,
        track=track
    )


def validate_dataframe(
    df: pd.DataFrame,
    dataset_id: str,
    source_description: str = "Unknown source",
    version: Optional[int] = None,
    strict: bool = True,
    cast: bool = True,
    track: bool = True
) -> Tuple[pd.DataFrame, SchemaReport]:
    """
    Validate an existing DataFrame against a schema contract.
    
    Use this for DataFrames already loaded by other means (e.g., from database,
    API, or programmatically constructed).
    
    Args:
        df: DataFrame to validate
        dataset_id: Dataset identifier
        source_description: Description of data source (for logging/evidence)
        version: Specific contract version (None = latest/active)
        strict: If True, fail on missing required columns
        cast: If True, cast columns to target dtypes
        track: If True, record transformation events
    
    Returns:
        Tuple of (validated_df, schema_report)
    
    Example:
        >>> df_raw = fetch_data_from_api()
        >>> df, report = validate_dataframe(
        ...     df_raw,
        ...     dataset_id="IPE_08",
        ...     source_description="REST API /vouchers endpoint"
        ... )
    """
    logger.info(
        f"Validating DataFrame against schema: {dataset_id} "
        f"(source: {source_description})"
    )
    
    # Apply schema contract
    df_validated, report = apply_schema_contract(
        df,
        dataset_id=dataset_id,
        version=version,
        strict=strict,
        cast=cast,
        track=track
    )
    
    # Add source metadata to report
    report.validation_warnings.insert(0, f"Data source: {source_description}")
    
    return df_validated, report
