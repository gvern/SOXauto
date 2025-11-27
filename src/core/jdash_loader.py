"""
JDASH Loader Module

Provides loading and cleaning utilities for JDASH (Jdash) data.
This module is independent of Streamlit and returns standard Pandas DataFrames.
"""

import os
import logging
from typing import Tuple, Optional, Union, Any

import pandas as pd

logger = logging.getLogger(__name__)

# Repository root path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def load_jdash_data(
    source: Optional[Union[str, Any]] = None,
    fixture_fallback: bool = True
) -> Tuple[pd.DataFrame, str]:
    """
    Load and normalize JDASH (voucher usage) data.
    
    Supports multiple input types:
    - File path (string)
    - File-like object (with read method)
    - DataFrame (passed through)
    - None (uses fixture fallback if enabled)
    
    Args:
        source: Data source - can be file path, file-like object, DataFrame, or None
        fixture_fallback: If True, falls back to local fixture when source is None
    
    Returns:
        Tuple of (DataFrame, source_description) where:
            - DataFrame: Normalized JDASH data with columns 'Voucher Id' and 'Amount Used'
            - source_description: String describing the data source
    
    Example:
        >>> df, source = load_jdash_data("/path/to/jdash.csv")
        >>> print(f"Loaded {len(df)} rows from {source}")
    """
    # Case 1: DataFrame passed directly
    if isinstance(source, pd.DataFrame):
        return _normalize_jdash_columns(source), "Direct DataFrame"
    
    # Case 2: File path
    if isinstance(source, str) and os.path.exists(source):
        try:
            df = pd.read_csv(source, low_memory=False)
            return _normalize_jdash_columns(df), f"File: {os.path.basename(source)}"
        except Exception as e:
            logger.warning(f"Failed to load JDASH from path {source}: {e}")
    
    # Case 3: File-like object
    if source is not None and hasattr(source, 'read'):
        try:
            df = pd.read_csv(source, low_memory=False)
            name = getattr(source, 'name', 'Uploaded File')
            return _normalize_jdash_columns(df), f"Uploaded: {name}"
        except Exception as e:
            logger.warning(f"Failed to load JDASH from file object: {e}")
    
    # Case 4: Fallback to fixture
    if fixture_fallback:
        fixture_path = os.path.join(REPO_ROOT, "tests", "fixtures", "fixture_JDASH.csv")
        if os.path.exists(fixture_path):
            try:
                df = pd.read_csv(fixture_path, low_memory=False)
                return _normalize_jdash_columns(df), "Local Fixture"
            except Exception as e:
                logger.warning(f"Failed to load JDASH fixture: {e}")
    
    # Default: Return empty DataFrame with expected columns
    return pd.DataFrame(columns=["Voucher Id", "Amount Used"]), "No Data"


def _normalize_jdash_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize JDASH column names to canonical format.
    
    Expected canonical columns:
    - 'Voucher Id': Voucher identifier
    - 'Amount Used': Amount used
    
    Handles various naming conventions from different sources.
    
    Args:
        df: Raw JDASH DataFrame
    
    Returns:
        DataFrame with normalized column names
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Column name mappings (source_name -> canonical_name)
    voucher_id_variants = ['Voucher Id', 'Voucher_Id', 'voucher_id', 'VoucherId', 'id', 'voucher']
    amount_variants = ['Amount Used', 'Amount_Used', 'amount_used', 'AmountUsed', 'amount']
    
    # Normalize Voucher Id column
    for variant in voucher_id_variants:
        if variant in df.columns and variant != 'Voucher Id':
            df = df.rename(columns={variant: 'Voucher Id'})
            break
    
    # Normalize Amount Used column
    for variant in amount_variants:
        if variant in df.columns and variant != 'Amount Used':
            df = df.rename(columns={variant: 'Amount Used'})
            break
    
    return df


def aggregate_jdash_by_voucher(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate JDASH data by Voucher Id.
    
    Sums up 'Amount Used' for each unique Voucher Id.
    
    Args:
        df: JDASH DataFrame with 'Voucher Id' and 'Amount Used' columns
    
    Returns:
        Aggregated DataFrame with one row per voucher
    """
    if df.empty:
        return pd.DataFrame(columns=['Voucher Id', 'Amount Used'])
    
    # Ensure required columns exist
    if 'Voucher Id' not in df.columns or 'Amount Used' not in df.columns:
        logger.warning("JDASH DataFrame missing required columns for aggregation")
        return df
    
    # Convert Amount Used to numeric, coercing errors to NaN
    df = df.copy()
    df['Amount Used'] = pd.to_numeric(df['Amount Used'], errors='coerce')
    
    # Aggregate by Voucher Id
    aggregated = df.groupby('Voucher Id', as_index=False)['Amount Used'].sum()
    
    return aggregated


def validate_jdash_data(df: pd.DataFrame) -> dict:
    """
    Validate JDASH data quality.
    
    Checks for:
    - Required columns presence
    - Null values in key columns
    - Duplicate voucher IDs
    - Negative amounts
    
    Args:
        df: JDASH DataFrame to validate
    
    Returns:
        Dictionary with validation results:
            {
                'valid': bool,
                'errors': list of error messages,
                'warnings': list of warning messages,
                'stats': dict with basic statistics
            }
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'stats': {}
    }
    
    if df.empty:
        result['warnings'].append("DataFrame is empty")
        result['stats'] = {'row_count': 0}
        return result
    
    # Check required columns
    required_cols = ['Voucher Id', 'Amount Used']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        result['valid'] = False
        result['errors'].append(f"Missing required columns: {missing_cols}")
        return result
    
    # Basic stats
    result['stats'] = {
        'row_count': len(df),
        'unique_vouchers': df['Voucher Id'].nunique(),
        'total_amount': df['Amount Used'].sum() if pd.api.types.is_numeric_dtype(df['Amount Used']) else None
    }
    
    # Check for null voucher IDs
    null_vouchers = df['Voucher Id'].isna().sum()
    if null_vouchers > 0:
        result['warnings'].append(f"{null_vouchers} rows have null Voucher Id")
    
    # Check for null amounts
    null_amounts = df['Amount Used'].isna().sum()
    if null_amounts > 0:
        result['warnings'].append(f"{null_amounts} rows have null Amount Used")
    
    # Check for duplicates
    duplicate_count = len(df) - df['Voucher Id'].nunique()
    if duplicate_count > 0:
        result['warnings'].append(f"{duplicate_count} duplicate Voucher Id entries found")
    
    # Check for negative amounts
    if pd.api.types.is_numeric_dtype(df['Amount Used']):
        negative_count = (df['Amount Used'] < 0).sum()
        if negative_count > 0:
            result['warnings'].append(f"{negative_count} rows have negative Amount Used")
    
    return result


__all__ = [
    'load_jdash_data',
    'aggregate_jdash_by_voucher',
    'validate_jdash_data',
]
