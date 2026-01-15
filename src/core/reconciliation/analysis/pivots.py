"""
Pivot Generation Module for PG-01 Reconciliation.

This module provides functionality for generating NAV (Microsoft Dynamics NAV) pivots
and TV (Target Values) pivots for variance analysis.

TODO: Extract pivot generation logic from run_reconciliation.py

Expected Functions:
    - generate_nav_pivot(nav_df, cutoff_date, country_code): Generate NAV pivot table
    - generate_tv_pivot(tv_df, cutoff_date, country_code): Generate TV pivot table
    - aggregate_by_category(df, group_by_cols): Generic pivot aggregation

Example (future implementation):
    >>> from src.core.reconciliation.analysis.pivots import generate_nav_pivot
    >>> nav_pivot = generate_nav_pivot(nav_df, cutoff_date="2025-09-30", country_code="NG")
    >>> print(nav_pivot.columns)
    Index(['Category', 'Amount_NAV', 'Count_NAV'], dtype='object')
"""

from typing import Optional, List, Union
import pandas as pd
import logging

from src.utils.pandas_utils import require_columns, ensure_required_numeric

logger = logging.getLogger(__name__)


def _harmonize_voucher_type(voucher_type: str) -> str:
    """
    Harmonize voucher_type labels to canonical enum.
    
    Maps various voucher type labels to canonical standardized values.
    Handles None/NaN values by returning "Unknown".
    
    Args:
        voucher_type: Raw voucher type label from source data
        
    Returns:
        Canonical voucher type string (one of: refund, store_credit, apology, 
        jforce, expired, vtc, other, Unknown)
    
    Examples:
        >>> _harmonize_voucher_type("Refund")
        'refund'
        >>> _harmonize_voucher_type("STORE CREDIT")
        'store_credit'
        >>> _harmonize_voucher_type(None)
        'Unknown'
        >>> _harmonize_voucher_type("")
        'Unknown'
    """
    if pd.isna(voucher_type) or not voucher_type or str(voucher_type).strip() == "":
        return "Unknown"
    
    # Normalize: lowercase and strip
    vt = str(voucher_type).lower().strip()
    
    # Canonical mapping
    # Based on voucher classification system in cat_issuance_classifier.py
    if vt in ["refund", "rf_", "rfn"]:
        return "refund"
    elif vt in ["store credit", "store_credit", "storecredit"]:
        return "store_credit"
    elif vt in ["apology", "commercial gesture", "cxp"]:
        return "apology"
    elif vt in ["jforce", "pyt_", "pyt_pf"]:
        return "jforce"
    elif vt in ["expired", "exp"]:
        return "expired"
    elif vt in ["vtc", "voucher to cash"]:
        return "vtc"
    elif vt in ["other", "unknown", ""]:
        return "other"
    else:
        # Unknown voucher types should be mapped to "other"
        logger.debug(f"Unknown voucher_type '{voucher_type}' mapped to 'other'")
        return "other"


def build_target_values_pivot_local(
    tv_tables: Union[pd.DataFrame, List[pd.DataFrame]],
    amount_col: str = "amount_local",
    group_cols: Optional[List[str]] = None,
    default_category: str = "Voucher",
) -> pd.DataFrame:
    """
    Build Target Values pivot aggregated in local currency per country.
    
    Aggregates Target Values from BOB extract tables (Issuance/Usage/Expired/VTC)
    into a pivot table with local currency amounts. The output grain matches NAV pivot:
    (country_code, category, voucher_type).
    
    USD conversion is NOT performed here - it will be handled later in the FX step.
    
    Args:
        tv_tables: Single DataFrame or list of DataFrames from Target Values extracts
                   (e.g., IPE_08 Issuance, DOC_VOUCHER_USAGE Usage, etc.)
        amount_col: Name of the local currency amount column in input data.
                    Default: "amount_local". Can also be dataset-specific columns
                    like "remaining_amount", "totalamountused", etc.
        group_cols: Optional explicit list of grouping columns. 
                    Default: ["country_code", "category", "voucher_type"]
        default_category: Default category value if not present in input data.
                         Default: "Voucher"
    
    Returns:
        DataFrame with columns:
            - country_code: Country code (NG, EG, KE, etc.)
            - category: Category classification
            - voucher_type: Harmonized voucher type (refund, store_credit, etc.)
            - tv_amount_local: Sum of amounts in local currency
        
        Rows are sorted deterministically by (country_code, category, voucher_type).
    
    Raises:
        ValueError: If required columns are missing from input data
    
    Examples:
        >>> # Single table input
        >>> issuance_df = pd.DataFrame({
        ...     'country_code': ['NG', 'NG', 'EG'],
        ...     'category': ['Voucher', 'Voucher', 'Voucher'],
        ...     'voucher_type': ['refund', 'store_credit', 'refund'],
        ...     'amount_local': [1000.0, 2000.0, 500.0]
        ... })
        >>> pivot = build_target_values_pivot_local(issuance_df)
        >>> pivot.columns.tolist()
        ['country_code', 'category', 'voucher_type', 'tv_amount_local']
        
        >>> # Multiple tables input
        >>> usage_df = pd.DataFrame({
        ...     'country_code': ['NG'],
        ...     'category': ['Voucher'],
        ...     'voucher_type': ['refund'],
        ...     'amount_local': [-100.0]
        ... })
        >>> pivot = build_target_values_pivot_local([issuance_df, usage_df])
        
        >>> # Handle missing voucher_type
        >>> data = pd.DataFrame({
        ...     'country_code': ['NG'],
        ...     'category': ['Voucher'],
        ...     'voucher_type': [None],
        ...     'amount_local': [100.0]
        ... })
        >>> pivot = build_target_values_pivot_local(data)
        >>> pivot['voucher_type'].iloc[0]
        'Unknown'
        
        >>> # Handle missing category (auto-filled)
        >>> data_no_cat = pd.DataFrame({
        ...     'country_code': ['NG'],
        ...     'voucher_type': ['refund'],
        ...     'amount_local': [100.0]
        ... })
        >>> pivot = build_target_values_pivot_local(data_no_cat)
        >>> pivot['category'].iloc[0]
        'Voucher'
    
    Notes:
        - Enforces schema contracts via require_columns() to prevent KeyError
        - Harmonizes voucher_type labels to canonical enum before aggregation
        - Handles missing voucher_type by mapping to "Unknown"
        - Handles missing category by using default_category
        - Empty datasets return empty DataFrame with correct schema
        - Deterministic sorting ensures reproducible results
        - No FX conversion - USD amounts will be added later using fx_utils
    """
    # Default grouping columns match NAV pivot grain
    if group_cols is None:
        group_cols = ["country_code", "category", "voucher_type"]
    
    # Handle single DataFrame or list of DataFrames
    if isinstance(tv_tables, pd.DataFrame):
        tv_tables = [tv_tables]
    
    # Filter out None/empty DataFrames
    tv_tables = [df for df in tv_tables if df is not None and not df.empty]
    
    if not tv_tables:
        # Return empty DataFrame with correct schema
        return pd.DataFrame(columns=group_cols + ["tv_amount_local"])
    
    # Concatenate all tables
    combined_df = pd.concat(tv_tables, ignore_index=True)
    
    if combined_df.empty:
        return pd.DataFrame(columns=group_cols + ["tv_amount_local"])
    
    # Validate required columns exist (excluding category which can be auto-added)
    required_base_cols = ["country_code", "voucher_type", amount_col]
    require_columns(combined_df, required_base_cols, context="Target Values tables")
    
    # Create working copy
    df = combined_df.copy()
    
    # Add category column if missing (using default)
    if "category" not in df.columns:
        df["category"] = default_category
        logger.debug(f"Added missing 'category' column with default value: {default_category}")
    
    # Harmonize voucher_type to canonical enum
    if "voucher_type" in df.columns:
        df["voucher_type"] = df["voucher_type"].apply(_harmonize_voucher_type)
    
    # Ensure amount column is numeric (fillna=0.0 for aggregation safety)
    df = ensure_required_numeric(df, required=[amount_col], fillna=0.0)
    
    # Aggregate by grouping columns
    pivot_df = (
        df.groupby(group_cols, as_index=False, dropna=False)
        .agg({amount_col: "sum"})
        .rename(columns={amount_col: "tv_amount_local"})
    )
    
    # Deterministic sorting for reproducible results
    pivot_df = pivot_df.sort_values(by=group_cols, ignore_index=True)
    
    logger.info(
        f"Built Target Values pivot: {len(pivot_df)} rows, "
        f"{pivot_df['tv_amount_local'].sum():.2f} total local amount"
    )
    
    return pivot_df


def generate_nav_pivot(
    nav_df: pd.DataFrame,
    cutoff_date: Optional[str] = None,
    country_code: Optional[str] = None,
) -> pd.DataFrame:
    """
    Generate NAV pivot table for variance analysis.
    
    TODO: Implement NAV pivot generation logic.
    Currently returns empty DataFrame with expected structure.
    
    Args:
        nav_df: NAV DataFrame with categorized vouchers
        cutoff_date: Optional cutoff date (YYYY-MM-DD format)
        country_code: Optional country code filter
        
    Returns:
        DataFrame: NAV pivot with categories and aggregated amounts
    """
    # Placeholder implementation
    return pd.DataFrame(columns=["Category", "Amount_NAV", "Count_NAV"])


def generate_tv_pivot(
    tv_df: pd.DataFrame,
    cutoff_date: Optional[str] = None,
    country_code: Optional[str] = None,
) -> pd.DataFrame:
    """
    Generate Target Values (TV) pivot table for variance analysis.
    
    TODO: Implement TV pivot generation logic.
    Currently returns empty DataFrame with expected structure.
    
    Args:
        tv_df: Target Values DataFrame
        cutoff_date: Optional cutoff date (YYYY-MM-DD format)
        country_code: Optional country code filter
        
    Returns:
        DataFrame: TV pivot with categories and aggregated amounts
    """
    # Placeholder implementation
    return pd.DataFrame(columns=["Category", "Amount_TV", "Count_TV"])


__all__ = [
    "generate_nav_pivot",
    "generate_tv_pivot",
    "build_target_values_pivot_local",
]
