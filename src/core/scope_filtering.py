"""
Scope Filtering Module

Provides filtering utilities for preprocessing IPE data.
This module is independent of Streamlit and returns standard Pandas DataFrames.

Contains:
- _filter_ipe08_scope: Filters IPE_08 to Non-Marketing vouchers
- filter_gl_18412: Filters entries for GL account 18412
- NON_MARKETING_USES: Canonical list of non-marketing voucher types
"""

import logging
from typing import Optional, List

import pandas as pd

logger = logging.getLogger(__name__)


# Canonical list of Non-Marketing voucher types
NON_MARKETING_USES: List[str] = [
    "apology_v2",
    "jforce",
    "refund",
    "store_credit",
    "Jpay store_credit",
]


def filter_ipe08_scope(ipe_08_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter IPE_08 DataFrame to include only Non-Marketing voucher types.

    This helper ensures consistent filtering across all bridge calculations
    that use IPE_08 data. Only vouchers with business_use in the Non-Marketing
    category are included.

    Business Rule:
    Non-Marketing voucher types are: apology_v2, jforce, refund, 
    store_credit, Jpay store_credit

    Args:
        ipe_08_df: DataFrame from IPE_08 extraction containing voucher data
                   Expected columns: 'business_use' (or 'business_use_formatted')
                   and optional date columns

    Returns:
        DataFrame filtered to Non-Marketing vouchers with dates converted to datetime
        
    Example:
        >>> filtered = filter_ipe08_scope(ipe_08_df)
        >>> print(f"Filtered from {len(ipe_08_df)} to {len(filtered)} vouchers")
    """
    if ipe_08_df is None or ipe_08_df.empty:
        return ipe_08_df.copy() if ipe_08_df is not None else pd.DataFrame()

    # Work with a copy
    df = ipe_08_df.copy()

    # Filter for Non-Marketing types
    # Check for both business_use and business_use_formatted for backward compatibility
    business_use_col = None
    if "business_use" in df.columns:
        business_use_col = "business_use"
    elif "business_use_formatted" in df.columns:
        business_use_col = "business_use_formatted"
    
    if business_use_col:
        df = df[df[business_use_col].isin(NON_MARKETING_USES)].copy()
        logger.debug(f"Filtered to {len(df)} Non-Marketing vouchers using column '{business_use_col}'")

    # Convert date columns to datetime if they exist
    date_columns = [
        "Order_Creation_Date",
        "Order_Delivery_Date",
        "Order_Cancellation_Date",
    ]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def filter_gl_18412(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter DataFrame to include only entries for GL account 18412.
    
    GL 18412 is the voucher accrual account used for voucher liability tracking.
    
    Args:
        df: DataFrame with GL account column (various naming conventions supported)
    
    Returns:
        DataFrame filtered to GL 18412 entries only
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()
    
    df = df.copy()
    
    # Find GL account column
    gl_col = None
    gl_column_variants = [
        "Chart of Accounts No_",
        "GL Account",
        "gl_account",
        "GL_Account",
        "Account_No",
        "account_no",
    ]
    
    for col in gl_column_variants:
        if col in df.columns:
            gl_col = col
            break
    
    if gl_col is None:
        logger.warning("No GL account column found in DataFrame")
        return df
    
    # Filter for GL 18412
    original_count = len(df)
    df = df[df[gl_col].astype(str).str.strip() == "18412"].copy()
    logger.debug(f"Filtered from {original_count} to {len(df)} entries for GL 18412")
    
    return df


def apply_non_marketing_filter(
    df: pd.DataFrame, 
    business_use_column: Optional[str] = None
) -> pd.DataFrame:
    """
    Apply Non-Marketing filter to any DataFrame with a business_use column.
    
    This is a more flexible version of filter_ipe08_scope that allows
    specifying the column name.
    
    Args:
        df: DataFrame to filter
        business_use_column: Name of the column containing business use type.
                            If None, auto-detects common column names.
    
    Returns:
        Filtered DataFrame containing only Non-Marketing vouchers
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()
    
    df = df.copy()
    
    # Auto-detect business use column if not specified
    if business_use_column is None:
        candidate_cols = ["business_use", "business_use_formatted", "BusinessUse", "Business_Use"]
        for col in candidate_cols:
            if col in df.columns:
                business_use_column = col
                break
    
    if business_use_column is None or business_use_column not in df.columns:
        logger.warning("No business_use column found - returning unfiltered DataFrame")
        return df
    
    original_count = len(df)
    df = df[df[business_use_column].isin(NON_MARKETING_USES)].copy()
    logger.debug(f"Filtered from {original_count} to {len(df)} Non-Marketing vouchers")
    
    return df


def get_non_marketing_summary(df: pd.DataFrame) -> dict:
    """
    Get summary statistics for Non-Marketing filtering.
    
    Args:
        df: DataFrame with business_use column
    
    Returns:
        Dictionary with filtering statistics:
            {
                'total_vouchers': int,
                'non_marketing_count': int,
                'marketing_count': int,
                'breakdown_by_type': dict
            }
    """
    if df is None or df.empty:
        return {
            'total_vouchers': 0,
            'non_marketing_count': 0,
            'marketing_count': 0,
            'breakdown_by_type': {}
        }
    
    # Find business_use column
    business_use_col = None
    for col in ["business_use", "business_use_formatted"]:
        if col in df.columns:
            business_use_col = col
            break
    
    if business_use_col is None:
        return {
            'total_vouchers': len(df),
            'non_marketing_count': 0,
            'marketing_count': 0,
            'breakdown_by_type': {},
            'error': 'No business_use column found'
        }
    
    total = len(df)
    non_marketing_mask = df[business_use_col].isin(NON_MARKETING_USES)
    non_marketing_count = non_marketing_mask.sum()
    
    # Breakdown by type
    breakdown = df[business_use_col].value_counts().to_dict()
    
    return {
        'total_vouchers': total,
        'non_marketing_count': int(non_marketing_count),
        'marketing_count': total - int(non_marketing_count),
        'breakdown_by_type': breakdown
    }


# Alias for backward compatibility with existing imports
_filter_ipe08_scope = filter_ipe08_scope


__all__ = [
    'NON_MARKETING_USES',
    'filter_ipe08_scope',
    '_filter_ipe08_scope',  # Backward compatibility alias
    'filter_gl_18412',
    'apply_non_marketing_filter',
    'get_non_marketing_summary',
]
