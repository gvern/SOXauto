"""
Centralized pandas casting utilities for Amount columns.

Provides explicit, tested functions for normalizing numeric dtypes across
the reconciliation and bridge analysis pipelines.

This module addresses inconsistent numeric handling from CSV uploads, SQL extractions,
and fixture data by providing:
- Safe string-to-float coercion with comma/space stripping
- Configurable NaN filling (default: 0.0 for Amount aggregations)
- Column pattern matching for automatic amount detection
- Type validation for required columns

Usage:
    from src.utils.pandas_utils import cast_amount_columns, ensure_required_numeric
    
    # Automatic detection and casting
    df_clean = cast_amount_columns(df, fillna=0.0)
    
    # Explicit column list
    df_clean = cast_amount_columns(df, columns=['Amount', 'Balance'], fillna=0.0)
    
    # Validate required columns exist and are numeric
    df_clean = ensure_required_numeric(df, required=['Amount', 'Total'], fillna=0.0)
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


def coerce_numeric_series(
    s: pd.Series,
    *,
    fillna: Optional[float] = None,
) -> pd.Series:
    """
    Coerce a pandas Series to numeric dtype (float64).
    
    This function handles common data quality issues in amount columns:
    - String values with commas: "1,234.56" → 1234.56
    - String values with spaces: "1 234.56" → 1234.56
    - Empty strings: "" → NaN
    - Mixed types: object/str → float
    - Already numeric: passthrough
    
    Args:
        s: Input Series to coerce
        fillna: If provided, fill NaNs with this value after coercion
    
    Returns:
        Series with numeric (float64) dtype
    
    Examples:
        >>> s = pd.Series(["1,234.56", "2,000", ""])
        >>> coerce_numeric_series(s, fillna=0.0)
        0    1234.56
        1    2000.00
        2       0.00
        dtype: float64
        
        >>> s = pd.Series([100.5, 200.0, None])
        >>> coerce_numeric_series(s, fillna=0.0)
        0    100.5
        1    200.0
        2      0.0
        dtype: float64
    
    Note:
        Uses pd.to_numeric(..., errors="coerce") to safely handle invalid values.
        Invalid values become NaN before optional fillna.
    """
    # Short-circuit for already-numeric series
    if pd.api.types.is_numeric_dtype(s):
        result = s.astype('float64')
        if fillna is not None:
            result = result.fillna(fillna)
        return result
    
    # For object/string dtype, strip commas and spaces before coercion
    if pd.api.types.is_object_dtype(s):
        # Handle None/NaN values and empty strings
        s_clean = s.apply(
            lambda x: str(x).replace(',', '').replace(' ', '').strip()
            if pd.notna(x) and str(x).strip() != ''
            else np.nan
        )
    else:
        s_clean = s
    
    # Coerce to numeric (converts invalid values to NaN)
    result = pd.to_numeric(s_clean, errors='coerce')
    
    # Fill NaNs if requested
    if fillna is not None:
        result = result.fillna(fillna)
    
    return result


def cast_amount_columns(
    df: pd.DataFrame,
    *,
    columns: Optional[List[str]] = None,
    pattern: Optional[str] = None,
    fillna: float = 0.0,
    inplace: bool = False,
) -> pd.DataFrame:
    """
    Cast target columns to float and fill NaNs.
    
    Default behavior: If columns not provided, detects amount columns via pattern matching.
    
    Args:
        df: Input DataFrame
        columns: Explicit list of column names to cast. If None, uses pattern.
        pattern: Regex pattern for auto-detection (default: case-insensitive "amount")
        fillna: Value to fill NaNs with (default: 0.0 for Amount aggregations)
        inplace: If True, modify DataFrame in place; if False, return copy
    
    Returns:
        DataFrame with amount columns cast to float64
    
    Examples:
        >>> df = pd.DataFrame({
        ...     'Amount': ['1,234.56', '2,000'],
        ...     'Amount_USD': ['100.5', '200'],
        ...     'ID': ['A1', 'A2']
        ... })
        >>> df_clean = cast_amount_columns(df, fillna=0.0)
        >>> df_clean['Amount'].dtype
        dtype('float64')
        >>> df_clean['ID'].dtype  # Non-amount columns unchanged
        dtype('O')
    
    Raises:
        ValueError: If a specified column doesn't exist in the DataFrame
    
    Note:
        - Default pattern matches: Amount, amount, Amount_USD, amount_lcy, etc.
        - Does NOT accidentally cast IDs, dates, or other non-numeric fields
        - Warns if pattern matches zero columns
    """
    if not inplace:
        df = df.copy()
    
    # Determine target columns
    if columns is not None:
        # Explicit column list
        target_cols = columns
        # Validate all columns exist
        missing = [col for col in target_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Columns not found in DataFrame: {missing}")
    else:
        # Auto-detect using pattern
        if pattern is None:
            # Default pattern: case-insensitive "amount"
            pattern = r'amount'
        
        # Find columns matching pattern
        target_cols = [
            col for col in df.columns
            if re.search(pattern, col, re.IGNORECASE)
        ]
        
        if not target_cols:
            logger.warning(
                f"Pattern '{pattern}' matched zero columns. "
                f"Available columns: {list(df.columns)}"
            )
            return df
    
    # Cast each target column
    for col in target_cols:
        df[col] = coerce_numeric_series(df[col], fillna=fillna)
    
    return df


def ensure_required_numeric(
    df: pd.DataFrame,
    required: List[str],
    *,
    fillna: float = 0.0,
) -> pd.DataFrame:
    """
    Validate required columns exist, coerce to numeric, and fill NaNs.
    
    This function is stricter than cast_amount_columns() - it will raise
    an error if any required column is missing.
    
    Args:
        df: Input DataFrame
        required: List of required column names
        fillna: Value to fill NaNs with (default: 0.0)
    
    Returns:
        DataFrame (copy) with required columns as float64
    
    Raises:
        ValueError: If any required column is missing from the DataFrame
    
    Examples:
        >>> df = pd.DataFrame({
        ...     'Amount': ['1,234.56', '2,000'],
        ...     'Balance': ['500', '750']
        ... })
        >>> df_clean = ensure_required_numeric(df, required=['Amount', 'Balance'], fillna=0.0)
        >>> df_clean['Amount'].dtype
        dtype('float64')
        
        >>> df_missing = pd.DataFrame({'Amount': [100]})
        >>> ensure_required_numeric(df_missing, required=['Amount', 'Balance'])
        Traceback (most recent call last):
            ...
        ValueError: Required columns missing from DataFrame: ['Balance']
    
    Note:
        - Always returns a copy (never modifies in place)
        - Use this for critical columns where missing data would cause errors
        - For optional columns, use cast_amount_columns() instead
    """
    # Validate all required columns exist
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Required columns missing from DataFrame: {missing}")
    
    # Create copy
    df_clean = df.copy()
    
    # Cast each required column
    for col in required:
        df_clean[col] = coerce_numeric_series(df_clean[col], fillna=fillna)
    
    return df_clean


__all__ = [
    'coerce_numeric_series',
    'cast_amount_columns',
    'ensure_required_numeric',
]
