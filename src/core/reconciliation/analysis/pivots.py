"""
Pivot Generation Module for PG-01 Reconciliation.

This module provides functionality for generating NAV (Microsoft Dynamics NAV) pivots
and TV (Target Values) pivots for variance analysis.

Key Functions:
    - build_nav_pivot(cr_03_df, dataset_id): Build NAV pivot from classified CR_03
    - generate_nav_pivot(nav_df, cutoff_date, country_code): Legacy NAV pivot (deprecated)
    - generate_tv_pivot(tv_df, cutoff_date, country_code): Legacy TV pivot (deprecated)

Example:
    >>> from src.core.reconciliation.analysis.pivots import build_nav_pivot
    >>> nav_pivot, nav_lines = build_nav_pivot(categorized_cr_03_df, dataset_id="CR_03")
    >>> print(nav_pivot.head())
"""

from typing import Optional, Tuple
import pandas as pd

from src.core.schema.schema_utils import require_columns


def build_nav_pivot(
    cr_03_df: pd.DataFrame,
    dataset_id: str = "CR_03",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build NAV reconciliation pivot from classified CR_03 voucher accrual entries.
    
    Creates a canonical NAV pivot table (Category × Voucher Type → Amount_LCY) 
    used by Phase 3 reconciliation. Expects a canonicalized + casted CR_03 subset 
    (GL 18412) that has already been schema-normalized and categorized.
    
    Args:
        cr_03_df: Categorized CR_03 DataFrame with required columns:
                  - bridge_category: Bridge category (from categorization pipeline)
                  - voucher_type: Voucher type (may be missing/None)
                  - amount: Transaction amount in local currency (amount_lcy)
                  - Optional: country_code, voucher_no, document_no, etc.
        dataset_id: Dataset identifier for column validation (default: "CR_03")
    
    Returns:
        Tuple of (nav_pivot_df, nav_lines_df):
        - nav_pivot_df: Pivot table with deterministically ordered rows:
            * Index: MultiIndex of (category, voucher_type) 
            * Columns: amount_lcy (sum), row_count
            * Includes margin totals
            * Missing voucher_type values mapped to "Unknown"
        - nav_lines_df: Enriched lines DataFrame with category/type for drilldown
    
    Raises:
        ValueError: If required columns are missing (via require_columns)
    
    Example:
        >>> categorized_df = categorize_nav_vouchers(cr_03_df)
        >>> nav_pivot, nav_lines = build_nav_pivot(categorized_df)
        >>> print(nav_pivot.loc[('Issuance', 'Refund'), :])
        amount_lcy    -50000.0
        row_count          125
        Name: (Issuance, Refund), dtype: object
    """
    # Handle empty DataFrame
    if cr_03_df is None or cr_03_df.empty:
        empty_pivot = pd.DataFrame(
            columns=["amount_lcy", "row_count"]
        )
        empty_pivot.index = pd.MultiIndex.from_tuples(
            [], names=["category", "voucher_type"]
        )
        return empty_pivot, pd.DataFrame()
    
    # Validate required columns exist
    required_cols = ["bridge_category", "voucher_type", "amount"]
    try:
        require_columns(cr_03_df, dataset_id, required_cols)
    except ValueError as e:
        # If require_columns fails, provide a more helpful error message
        missing = [col for col in required_cols if col not in cr_03_df.columns]
        raise ValueError(
            f"Required columns missing from {dataset_id}: {missing}. "
            f"Available columns: {list(cr_03_df.columns)}. "
            f"Ensure the DataFrame has been categorized via categorize_nav_vouchers() "
            f"before calling build_nav_pivot()."
        ) from e
    
    # Create working copy
    df = cr_03_df.copy()
    
    # Normalize column names for pivot
    # Map 'amount' to 'amount_lcy' for consistency
    if "amount" in df.columns and "amount_lcy" not in df.columns:
        df = df.rename(columns={"amount": "amount_lcy"})
    
    # Handle missing voucher_type: fill with "Unknown"
    df["voucher_type"] = df["voucher_type"].fillna("Unknown")
    
    # Handle missing bridge_category: fill with "Uncategorized"
    df["bridge_category"] = df["bridge_category"].fillna("Uncategorized")
    
    # Normalize category and voucher_type to strings for grouping
    df["category"] = df["bridge_category"].astype(str)
    df["voucher_type"] = df["voucher_type"].astype(str)
    
    # Build enriched lines DataFrame for drilldown
    # Include key columns for later analysis
    keep_cols = ["category", "voucher_type", "amount_lcy"]
    optional_cols = [
        "country_code", "id_company", "voucher_no", "document_no", 
        "posting_date", "document_description", "user_id"
    ]
    for col in optional_cols:
        if col in df.columns:
            keep_cols.append(col)
    
    nav_lines_df = df[keep_cols].copy()
    
    # Build pivot table with deterministic ordering
    # Group by (category, voucher_type) and aggregate
    pivot_data = df.groupby(
        ["category", "voucher_type"], 
        as_index=True,
        dropna=False
    ).agg(
        amount_lcy=("amount_lcy", "sum"),
        row_count=("amount_lcy", "count")
    )
    
    # Sort index for deterministic ordering
    # Primary sort: category (alphabetical)
    # Secondary sort: voucher_type (alphabetical)
    pivot_data = pivot_data.sort_index(level=["category", "voucher_type"])
    
    # Rename index levels for clarity
    pivot_data.index.names = ["category", "voucher_type"]
    
    # Add margin totals (grand total row)
    # Calculate totals across all categories and voucher types
    total_amount = pivot_data["amount_lcy"].sum()
    total_count = pivot_data["row_count"].sum()
    
    # Create a new row for totals with special index
    totals_row = pd.DataFrame(
        {"amount_lcy": [total_amount], "row_count": [total_count]},
        index=pd.MultiIndex.from_tuples([("__TOTAL__", "")], names=["category", "voucher_type"])
    )
    
    # Append totals to pivot
    nav_pivot_df = pd.concat([pivot_data, totals_row])
    
    return nav_pivot_df, nav_lines_df


def generate_nav_pivot(
    nav_df: pd.DataFrame,
    cutoff_date: Optional[str] = None,
    country_code: Optional[str] = None,
) -> pd.DataFrame:
    """
    Generate NAV pivot table for variance analysis (DEPRECATED).
    
    DEPRECATED: Use build_nav_pivot() instead for Phase 3 reconciliation.
    This function is retained for backward compatibility only.
    
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
    Generate Target Values (TV) pivot table for variance analysis (DEPRECATED).
    
    DEPRECATED: Future implementation pending.
    
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
    "build_nav_pivot",
    "generate_nav_pivot",
    "generate_tv_pivot",
]
