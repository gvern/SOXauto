"""
Pivot Generation Module for PG-01 Reconciliation.

This module provides functionality for generating NAV (Microsoft Dynamics NAV) pivots
for variance analysis in the Phase 3 reconciliation pipeline.

Key Functions:
    - build_nav_pivot(cr_03_df, dataset_id): Build NAV pivot from classified CR_03

Example:
    >>> from src.core.reconciliation.analysis.pivots import build_nav_pivot
    >>> nav_pivot, nav_lines = build_nav_pivot(categorized_cr_03_df, dataset_id="CR_03")
    >>> print(nav_pivot.head())
"""

from typing import Optional, List, Union, Tuple
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


def _validate_required_columns(df: pd.DataFrame, required_cols: List[str], dataset_id: str) -> None:
    """
    Validate that required columns exist in DataFrame.
    
    Args:
        df: DataFrame to validate
        required_cols: List of required column names
        dataset_id: Dataset identifier for error messages
    
    Raises:
        ValueError: If required columns are missing
    """
    missing = [col for col in required_cols if col not in df.columns]
    
    if missing:
        raise ValueError(
            f"Required columns missing from {dataset_id}: {missing}. "
            f"Available columns: {list(df.columns)}. "
            f"Ensure the DataFrame has been categorized via categorize_nav_vouchers() "
            f"before calling build_nav_pivot()."
        )


def build_nav_pivot(
    cr_03_df: pd.DataFrame,
    dataset_id: str = "CR_03",
    currency_name: str = "lcy",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build NAV reconciliation pivot from classified CR_03 voucher accrual entries.
    
    Creates a canonical NAV pivot table (Category × Voucher Type → Amount) 
    used by Phase 3 reconciliation. Expects a canonicalized + casted CR_03 subset 
    (GL 18412) that has already been schema-normalized and categorized.
    
    Supports multi-country operations by parametrizing the currency name in the
    output column (e.g., amount_ngn, amount_egp, amount_lcy).
    
    Expected Canonical Values (from categorization pipeline):
    - Categories: Issuance, Cancellation, Usage, Expired, VTC
    - Voucher Types: Refund, Apology, JForce, Store Credit
    - Integration Type: Manual, Integration
    
    Expected Category × Voucher Type Combinations:
    - Issuance: Refund, Apology, JForce, Store Credit
    - Cancellation: Apology, Store Credit
    - Usage: Refund, Apology, JForce, Store Credit
    - Expired: Apology, JForce, Refund, Store Credit
    - VTC: Refund
    
    Args:
        cr_03_df: Categorized CR_03 DataFrame with required columns:
                  - bridge_category: Bridge category (from categorization pipeline)
                  - voucher_type: Voucher type (may be missing/None)
                  - amount: Transaction amount in local currency
                  - Optional: country_code, voucher_no, document_no, etc.
        dataset_id: Dataset identifier for column validation (default: "CR_03")
        currency_name: Currency code for output column naming (default: "lcy")
                      Output column will be named as amount_{currency_name}
                      e.g., "ngn" → amount_ngn, "egp" → amount_egp
    
    Returns:
        Tuple of (nav_pivot_df, nav_lines_df):
        - nav_pivot_df: Pivot table with deterministically ordered rows:
            * Index: MultiIndex of (category, voucher_type) 
            * Columns: amount_{currency_name} (sum), row_count
            * Includes margin totals
            * Missing voucher_type values mapped to "Unknown"
        - nav_lines_df: Enriched lines DataFrame with category/type for drilldown
    
    Raises:
        ValueError: If required columns are missing
    
    Example:
        >>> categorized_df = categorize_nav_vouchers(cr_03_df)
        >>> nav_pivot, nav_lines = build_nav_pivot(categorized_df, currency_name="NGN")
        >>> print(nav_pivot.loc[('Issuance', 'Refund'), :])
        amount_ngn    -50000.0
        row_count          125
        Name: (Issuance, Refund), dtype: object
    """
    # Validate and normalize currency name
    # Currency codes should be alphanumeric (typically 2-3 uppercase letters like NGN, EGP)
    # We normalize to lowercase for consistent column naming (amount_ngn, amount_egp)
    if not currency_name or not currency_name.replace('_', '').isalnum():
        raise ValueError(
            f"Invalid currency_name '{currency_name}': must contain only alphanumeric characters. "
            f"Expected format: 2-3 letter currency codes like 'NGN', 'EGP', 'KES', or 'lcy'."
        )
    
    currency_col = f"amount_{currency_name.lower()}"
    
    # Handle empty DataFrame
    if cr_03_df is None or cr_03_df.empty:
        empty_pivot = pd.DataFrame(
            columns=[currency_col, "row_count"]
        )
        empty_pivot.index = pd.MultiIndex.from_tuples(
            [], names=["category", "voucher_type"]
        )
        return empty_pivot, pd.DataFrame()
    
    # Validate required columns exist
    # Note: bridge_category and voucher_type are added by categorization pipeline,
    # not part of the base CR_03 schema contract
    required_cols = ["bridge_category", "voucher_type", "amount"]
    _validate_required_columns(cr_03_df, required_cols, dataset_id)
    
    # Create working copy
    df = cr_03_df.copy()
    
    # Normalize column names for pivot
    # Map 'amount' to 'amount_{currency_name}' for consistency
    if "amount" in df.columns and currency_col not in df.columns:
        df = df.rename(columns={"amount": currency_col})
    
    # Handle missing voucher_type: fill with "Unknown"
    df["voucher_type"] = df["voucher_type"].fillna("Unknown")
    
    # Handle missing bridge_category: fill with "Uncategorized"
    df["bridge_category"] = df["bridge_category"].fillna("Uncategorized")
    
    # Normalize category and voucher_type to strings for grouping.
    # Note: fillna above already replaces missing values with "Unknown"/"Uncategorized",
    # but we still cast to str as defensive programming to ensure any remaining pandas
    # NA/nullable types are coerced to plain Python strings for type-safe grouping.
    df["category"] = df["bridge_category"].astype(str)
    df["voucher_type"] = df["voucher_type"].astype(str)
    
    # Build enriched lines DataFrame for drilldown
    # Include key columns for later analysis
    keep_cols = ["category", "voucher_type", currency_col]
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
        **{currency_col: (currency_col, "sum")},
        row_count=(currency_col, "count")
    )
    
    # Sort index for deterministic ordering
    # Primary sort: category (alphabetical)
    # Secondary sort: voucher_type (alphabetical)
    pivot_data = pivot_data.sort_index(level=["category", "voucher_type"])
    
    # Add margin totals (grand total row)
    # Calculate totals across all categories and voucher types
    total_amount = pivot_data[currency_col].sum()
    total_count = pivot_data["row_count"].sum()
    
    # Create a new row for totals with special index
    totals_row = pd.DataFrame(
        {currency_col: [total_amount], "row_count": [total_count]},
        index=pd.MultiIndex.from_tuples([("__TOTAL__", "")], names=["category", "voucher_type"])
    )
    
    # Append totals to pivot
    nav_pivot_df = pd.concat([pivot_data, totals_row])
    
    return nav_pivot_df, nav_lines_df


__all__ = [
    "build_target_values_pivot_local",
    "build_nav_pivot",
]
