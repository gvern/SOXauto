"""
Timing Difference Bridge calculation for PG-01 reconciliation.

Compares Ordered Amount (Usage from Ops) from Jdash export against 
the Total Amount Used (Usage from Accounting) from the Issuance IPE to 
identify timing differences (pending/timing difference).
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import warnings

from src.utils.date_utils import normalize_date
from src.utils.pandas_utils import coerce_numeric_series


def compute_rolling_window(cutoff_date: str) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Compute rolling 1-year window for timing difference analysis.
    
    Business Rule: Include vouchers created within 1 year before cutoff date,
    starting from the 1st day of the month one year before cutoff month.
    
    Formula:
    - End date = cutoff_date (inclusive)
    - Start date = 1st of (cutoff_month + 1) - 1 year
    
    Args:
        cutoff_date: Reconciliation cutoff date (YYYY-MM-DD format)
    
    Returns:
        tuple: (start_date, end_date) as pd.Timestamp objects
    
    Examples:
        >>> compute_rolling_window("2025-09-30")
        (Timestamp('2024-10-01'), Timestamp('2025-09-30'))
        
        >>> compute_rolling_window("2024-10-31")
        (Timestamp('2023-11-01'), Timestamp('2024-10-31'))
    
    Note:
        This implements the spec: "from 1 Oct N-1 to 30 Sep N (inclusive)"
        rolling forward based on the actual cutoff date.
    """
    cutoff_dt = normalize_date(cutoff_date)
    
    # Calculate start date: 1st of (cutoff_month + 1) - 1 year
    # Example: cutoff = 2025-09-30 → next_month = 2025-10-01 → start = 2024-10-01
    # Example: cutoff = 2024-10-31 → next_month = 2024-11-01 → start = 2023-11-01
    next_month_first = (cutoff_dt.replace(day=1) + pd.DateOffset(months=1))
    start_dt = next_month_first - pd.DateOffset(years=1)
    
    return start_dt, cutoff_dt


def _normalize_column_names(
    df: pd.DataFrame, 
    column_mapping: Dict[str, List[str]]
) -> pd.DataFrame:
    """
    Normalize DataFrame column names to canonical format.
    
    This adapter function handles various naming conventions in source data
    by renaming columns to standard names, reducing fragility in downstream logic.
    
    Args:
        df: DataFrame to normalize
        column_mapping: Dict mapping canonical names to list of possible variants
                       Example: {"voucher_id": ["Voucher Id", "Voucher_Id", "voucher_id"]}
    
    Returns:
        DataFrame with normalized column names
    
    Example:
        >>> df = pd.DataFrame({"Voucher Id": ["V1"], "Amount Used": [100]})
        >>> mapping = {
        ...     "voucher_id": ["Voucher Id", "Voucher_Id"],
        ...     "amount_used": ["Amount Used", "Amount_Used"]
        ... }
        >>> normalized = _normalize_column_names(df, mapping)
        >>> list(normalized.columns)
        ['voucher_id', 'amount_used']
    
    Note:
        - Only the first matching variant is used (priority order matters)
        - Columns not in mapping are left unchanged
        - If no variant is found, canonical name is not added
    """
    df_normalized = df.copy()
    rename_dict = {}
    
    for canonical_name, variants in column_mapping.items():
        for variant in variants:
            if variant in df_normalized.columns:
                rename_dict[variant] = canonical_name
                break  # Use first matching variant only
    
    if rename_dict:
        df_normalized = df_normalized.rename(columns=rename_dict)
    
    return df_normalized


def calculate_timing_difference_bridge(
    jdash_df: pd.DataFrame,
    ipe_08_df: pd.DataFrame,
    cutoff_date: str,
) -> Tuple[float, pd.DataFrame]:
    """
    Calculates the Timing Difference Bridge by comparing Amount Used (Jdash - Ops)
    against Total Amount Used (IPE_08 - Accounting).

    Logic (Validated Manual Process - Finance Team):
    Compares the Amount Used (Usage from Ops) from Jdash export against 
    the Total Amount Used (Usage from Accounting) from the IPE_08 Issuance extract 
    to identify timing differences (pending/timing difference).

    Business Rules:
    1. Filter Source A (IPE_08 - Issuance baseline):
       - IPE_08 is the issuance baseline extract from V_STORECREDITVOUCHER_CLOSING
         with aggregated TotalAmountUsed from RPT_SOI
       - Filter vouchers created within 1 year before cutoff_date
         (from 1st of month one year before, to cutoff date inclusive)
       - Filter for is_active == 0 (Inactive)
       - Filter for business_use in NON_MARKETING_USES
    2. Prepare Source B (Jdash):
       - Aggregate by Voucher Id summing Amount Used (Ops)
    3. Reconciliation Logic:
       - Left Join of Filtered IPE_08 (Left) with Jdash (Right) on Voucher ID
       - Fill missing Jdash amounts with 0
    4. Calculate Variance:
       - Variance = Jdash['Amount Used'] - IPE_08['Total Amount Used']
       - (Amount Used from Ops - Total Amount Used from Accounting = Pending/Timing Difference)
       - IMPORTANT: Use "Total Amount Used" NOT "Remaining Amount" or "Discount Amount"

    Args:
        jdash_df: DataFrame from Jdash export with columns:
            - Voucher Id (or variants): Voucher identifier
            - Amount Used (or variants): Amount used from Ops
        ipe_08_df: DataFrame from IPE_08 (Issuance baseline) with columns:
            - id: Voucher ID
            - business_use: Business use type
            - is_active: Active status (0 for inactive)
            - Total Amount Used (or usage_tv): Total amount used from Accounting (aggregated from RPT_SOI)
            - created_at: Creation date of voucher
        cutoff_date: Reconciliation cutoff date (YYYY-MM-DD)

    Returns:
        tuple: (variance_sum, proof_df) where:
            - variance_sum: Sum of variance (Jdash Amount Used from Ops - IPE_08 Total Amount Used from Accounting)
            - proof_df: DataFrame with reconciliation details including variance
    
    Note:
        - This function does NOT use delivery_date or cancellation_date logic 
          (per business clarification Nov 6, 2025)
        - The timing difference is identified purely by comparing usage amounts 
          between the two systems for the same period
        - Date window: From 1st day of month one year before cutoff, to cutoff date inclusive
          Example: cutoff = 2025-09-30 → window is 2024-10-01 to 2025-09-30
    """
    # Define Non-Marketing voucher types
    NON_MARKETING_USES = [
        "apology_v2",
        "jforce",
        "refund",
        "store_credit",
        "Jpay store_credit",
    ]

    # Handle empty or None input for IPE_08
    if ipe_08_df is None or ipe_08_df.empty:
        return 0.0, pd.DataFrame()

    # Step 1: Filter Source A (IPE_08 - Issuance)
    df_ipe = ipe_08_df.copy()

    # Calculate date window using pure function (testable independently)
    start_dt, cutoff_dt = compute_rolling_window(cutoff_date)

    # Find the created_at column (handle various naming conventions)
    created_at_col = None
    for col in ["created_at", "Created_At", "creation_date", "Creation_Date"]:
        if col in df_ipe.columns:
            created_at_col = col
            break

    # Apply date filter if created_at column exists
    if created_at_col:
        df_ipe[created_at_col] = pd.to_datetime(df_ipe[created_at_col], errors="coerce")
        # Filter: created_at >= start_dt AND created_at <= cutoff_dt (inclusive window)
        df_ipe = df_ipe[
            (df_ipe[created_at_col] >= start_dt) & 
            (df_ipe[created_at_col] <= cutoff_dt)
        ].copy()
    else:
        # Log warning when date filter cannot be applied
        warnings.warn(
            "Column 'created_at' not found in IPE_08 DataFrame. "
            "Date filter (1 year lookback window) cannot be applied. "
            "All vouchers will be included regardless of creation date.",
            UserWarning
        )

    # Filter for is_active == 0 (Inactive)
    if "is_active" not in df_ipe.columns:
        raise ValueError("Mandatory column 'is_active' not found in IPE_08 DataFrame. Cannot apply required inactive voucher filter.")
    df_ipe = df_ipe[df_ipe["is_active"] == 0].copy()

    # Filter for Non-Marketing business_use
    business_use_col = None
    if "business_use" in df_ipe.columns:
        business_use_col = "business_use"
    elif "business_use_formatted" in df_ipe.columns:
        business_use_col = "business_use_formatted"

    if business_use_col:
        df_ipe = df_ipe[df_ipe[business_use_col].isin(NON_MARKETING_USES)].copy()

    if df_ipe.empty:
        return 0.0, pd.DataFrame()

    # Find the amount column in IPE_08 (handle various naming conventions)
    # Priority: Look for "Total Amount Used" or "usage_tv" (NOT "Remaining Amount" or "Discount Amount")
    ipe_amount_col = None
    for col in ["Total Amount Used", "total_amount_used", "TotalAmountUsed", "usage_tv", "Usage_TV"]:
        if col in df_ipe.columns:
            ipe_amount_col = col
            break

    if ipe_amount_col is None:
        return 0.0, pd.DataFrame()
    
    # Ensure IPE amount column is numeric using centralized utility
    df_ipe[ipe_amount_col] = coerce_numeric_series(df_ipe[ipe_amount_col], fillna=0.0)

    # Step 2: Prepare Source B (Jdash) - Aggregate by Voucher Id summing Amount Used
    if jdash_df is None or jdash_df.empty:
        # If Jdash is empty, all IPE amounts are considered unmatched (variance = -IPE amount)
        df_ipe["Jdash_Amount_Used"] = 0.0
        df_ipe["Variance"] = df_ipe["Jdash_Amount_Used"] - df_ipe[ipe_amount_col]
        variance_sum = df_ipe["Variance"].sum()
        
        # Return consistent proof_df format (not raw df_ipe)
        cols_to_keep = ["id"]
        if business_use_col and business_use_col in df_ipe.columns:
            cols_to_keep.append(business_use_col)
        cols_to_keep.extend([ipe_amount_col, "Jdash_Amount_Used", "Variance"])
        proof_df = df_ipe[[c for c in cols_to_keep if c in df_ipe.columns]].copy()
        
        return variance_sum, proof_df

    df_jdash = jdash_df.copy()

    # Normalize Jdash column names using adapter (reduces fragility)
    jdash_column_mapping = {
        "voucher_id": ["Voucher Id", "Voucher_Id", "voucher_id", "VoucherId"],
        "jdash_amount_used": ["Amount Used", "Amount_Used", "amount_used", "AmountUsed"]
    }
    df_jdash = _normalize_column_names(df_jdash, jdash_column_mapping)

    # Validate required columns exist after normalization
    if "voucher_id" not in df_jdash.columns or "jdash_amount_used" not in df_jdash.columns:
        # Cannot perform reconciliation without proper columns - treat as empty Jdash
        warnings.warn(
            "Jdash DataFrame is missing required columns for voucher id or amount used. "
            "Treating as empty Jdash data (all vouchers unmatched).",
            UserWarning
        )
        df_ipe["Jdash_Amount_Used"] = 0.0
        df_ipe["Variance"] = df_ipe["Jdash_Amount_Used"] - df_ipe[ipe_amount_col]
        variance_sum = df_ipe["Variance"].sum()
        
        # Prepare proof DataFrame with relevant columns
        cols_to_keep = ["id"]
        if business_use_col and business_use_col in df_ipe.columns:
            cols_to_keep.append(business_use_col)
        cols_to_keep.extend([ipe_amount_col, "Jdash_Amount_Used", "Variance"])
        proof_df = df_ipe[[c for c in cols_to_keep if c in df_ipe.columns]].copy()
        
        return variance_sum, proof_df

    # Ensure Jdash amount is numeric BEFORE aggregation (handles string amounts with commas)
    df_jdash["jdash_amount_used"] = coerce_numeric_series(
        df_jdash["jdash_amount_used"], fillna=0.0
    )
    
    # Aggregate Jdash by voucher_id summing jdash_amount_used (using canonical names)
    # Rename immediately to output format (Jdash_Amount_Used) for consistency downstream
    jdash_agg = (
        df_jdash.groupby("voucher_id", as_index=False)["jdash_amount_used"]
        .sum()
        .rename(columns={"jdash_amount_used": "Jdash_Amount_Used"})
    )

    # Step 3: Reconciliation Logic - Left Join of Filtered IPE_08 with Jdash on Voucher ID
    # Ensure 'id' column is string for proper joining
    df_ipe["id"] = df_ipe["id"].astype(str)
    jdash_agg["voucher_id"] = jdash_agg["voucher_id"].astype(str)

    # Perform left join using canonical column names
    merged_df = df_ipe.merge(
        jdash_agg,
        left_on="id",
        right_on="voucher_id",
        how="left"
    )
    # Drop redundant voucher_id column after merge
    merged_df = merged_df.drop(columns=["voucher_id"], errors="ignore")

    # Fill missing Jdash amounts with 0 (using consistent column name from aggregation)
    merged_df["Jdash_Amount_Used"] = merged_df["Jdash_Amount_Used"].fillna(0.0)

    # Step 4: Calculate Variance = Jdash['Amount Used'] - IPE_08['Total Amount Used']
    merged_df["Variance"] = merged_df["Jdash_Amount_Used"] - merged_df[ipe_amount_col]

    # Step 5: Output - Return the sum of variance and the proof DataFrame
    variance_sum = merged_df["Variance"].sum()

    # Prepare proof DataFrame with relevant columns
    cols_to_keep = ["id"]
    if business_use_col and business_use_col in merged_df.columns:
        cols_to_keep.append(business_use_col)
    cols_to_keep.extend([ipe_amount_col, "Jdash_Amount_Used", "Variance"])

    # Keep only columns that exist in the dataframe
    proof_df = merged_df[[c for c in cols_to_keep if c in merged_df.columns]].copy()

    return variance_sum, proof_df


__all__ = [
    "calculate_timing_difference_bridge",
    "compute_rolling_window",  # Pure function for testing
    "_normalize_column_names",  # Internal adapter (exported for testing)
]
