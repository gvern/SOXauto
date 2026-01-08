"""
VTC (Voucher to Cash) Adjustment calculation for PG-01 reconciliation.

Identifies canceled refund vouchers from BOB that do not have 
corresponding cancellation entries in NAV.
"""

from typing import Any, Dict, Optional, Tuple
import pandas as pd

from src.core.scope_filtering import filter_ipe08_scope
from src.utils.fx_utils import FXConverter
from src.utils.date_utils import normalize_date, month_start, month_end


def calculate_vtc_adjustment(
    ipe_08_df: Optional[pd.DataFrame],
    categorized_cr_03_df: Optional[pd.DataFrame],
    fx_converter: Optional[FXConverter] = None,
    cutoff_date: Optional[str] = None,
) -> Tuple[float, pd.DataFrame, Dict[str, Any]]:
    """Calculate VTC (Voucher to Cash) refund reconciliation adjustment.

    This function identifies "canceled refund vouchers" from BOB (IPE_08) that do not
    have a corresponding cancellation entry in NAV (CR_03).

    Args:
        ipe_08_df: DataFrame containing voucher liabilities from BOB with columns:
            - id: Voucher ID
            - business_use: Business use type
            - is_valid: Validity status (or Is_Valid)
            - is_active: Active status (0 for canceled)
            - inactive_at: Date when voucher became inactive (for date filtering)
            - remaining_amount: Amount for the voucher
            - ID_COMPANY: Company code (required if fx_converter is provided)
        categorized_cr_03_df: DataFrame containing categorized NAV GL entries with columns:
            - [Voucher No_]: Voucher number from NAV
            - bridge_category: Category of the entry (e.g., 'Cancellation', 'VTC Manual')
        fx_converter: Optional FXConverter instance for USD conversion.
                     If None, returns amounts in local currency.
        cutoff_date: Optional cutoff date (YYYY-MM-DD format) for filtering by reconciliation month.
                     If provided, only vouchers where inactive_at falls within the cutoff month
                     will be included.

    Returns:
        tuple: (adjustment_amount_usd, proof_df, vtc_metrics) where:
            - adjustment_amount_usd: Sum of unmatched voucher amounts in USD
            - proof_df: DataFrame of unmatched vouchers with Amount_USD column
            - vtc_metrics: Dict containing total_count and breakdown_by_type
    """
    # Handle empty inputs
    if ipe_08_df is None or ipe_08_df.empty:
        return 0.0, pd.DataFrame(), {"total_count": 0, "breakdown_by_type": {}}

    # Step 1: Apply Non-Marketing filter using helper
    filtered_ipe_08 = filter_ipe08_scope(ipe_08_df)

    if filtered_ipe_08.empty:
        return 0.0, pd.DataFrame(), {"total_count": 0, "breakdown_by_type": {}}

    # Step 2: Filter source vouchers (BOB): canceled refund vouchers
    # Check for both business_use_formatted and business_use columns for backward compatibility
    business_use_col = None
    if "business_use_formatted" in filtered_ipe_08.columns:
        business_use_col = "business_use_formatted"
    elif "business_use" in filtered_ipe_08.columns:
        business_use_col = "business_use"
    
    # Check for both Is_Valid and is_valid columns for backward compatibility
    is_valid_col = None
    if "Is_Valid" in filtered_ipe_08.columns:
        is_valid_col = "Is_Valid"
    elif "is_valid" in filtered_ipe_08.columns:
        is_valid_col = "is_valid"

    # Build filter condition
    filter_condition = pd.Series([True] * len(filtered_ipe_08), index=filtered_ipe_08.index)
    
    if business_use_col:
        filter_condition &= (filtered_ipe_08[business_use_col] == "refund")
    
    if is_valid_col:
        filter_condition &= (filtered_ipe_08[is_valid_col] == "valid")
    
    if "is_active" in filtered_ipe_08.columns:
        filter_condition &= (filtered_ipe_08["is_active"] == 0)
    
    # Apply date filter if cutoff_date is provided and inactive_at column exists
    if cutoff_date is not None:
        # Find the inactive_at column (handle various naming conventions)
        inactive_at_col = None
        for col in ["inactive_at", "Inactive_At", "inactive_date", "Inactive_Date"]:
            if col in filtered_ipe_08.columns:
                inactive_at_col = col
                break
        
        if inactive_at_col:
            # Use centralized date utilities for month boundaries
            cutoff_dt = normalize_date(cutoff_date)
            month_start_dt = month_start(cutoff_dt)
            month_end_dt = month_end(cutoff_dt)
            
            # Convert inactive_at column to datetime
            inactive_at_series = pd.to_datetime(filtered_ipe_08[inactive_at_col], errors="coerce")
            
            # Filter: inactive_at must be within the reconciliation month
            filter_condition &= (inactive_at_series >= month_start_dt) & (inactive_at_series <= month_end_dt)
    
    source_vouchers_df = filtered_ipe_08[filter_condition].copy()

    # Find the amount column (handle various naming conventions)
    amount_col = None
    for col in ["remaining_amount", "Remaining Amount", "Remaining_Amount"]:
        if col in source_vouchers_df.columns:
            amount_col = col
            break
    
    if amount_col is None:
        # No amount column found, return empty result
        return 0.0, pd.DataFrame(), {"total_count": 0, "breakdown_by_type": {}}

    if categorized_cr_03_df is None or categorized_cr_03_df.empty:
        # All source vouchers are unmatched
        unmatched_df = source_vouchers_df.copy()
    else:
        # Filter target entries (NAV): cancellation categories
        # Include entries where bridge_category starts with 'Cancellation' or equals 'VTC'/'VTC Manual'
        # Convert to string once for efficiency
        bridge_categories = categorized_cr_03_df["bridge_category"].astype(str)
        target_entries_df = categorized_cr_03_df[
            bridge_categories.str.startswith("Cancellation")
            | (bridge_categories == "VTC Manual")
            | (bridge_categories == "VTC")
        ].copy()

        # Determine voucher number column variants
        voucher_no_col = None
        for col in ["Voucher No_", "[Voucher No_]", "voucher_no", "Voucher_No"]:
            if col in target_entries_df.columns:
                voucher_no_col = col
                break

        matched_voucher_series = (
            target_entries_df[voucher_no_col]
            if voucher_no_col is not None
            else pd.Series(dtype=object)
        )

        # Perform left anti-join: find vouchers in source that are NOT in target
        # Left anti-join means: keep rows from left where the join key does NOT match any row in right
        unmatched_df = source_vouchers_df[
            ~source_vouchers_df["id"].isin(matched_voucher_series)
        ].copy()
    proof_df = unmatched_df.copy()

    # Calculate USD amounts if FXConverter is provided
    if fx_converter is not None:
        # Check if ID_COMPANY column exists
        company_col = None
        for col in ["ID_COMPANY", "id_company", "Company_Code"]:
            if col in proof_df.columns:
                company_col = col
                break

        if company_col is not None:
            # Convert to USD
            proof_df["Amount_USD"] = fx_converter.convert_series_to_usd(
                proof_df[amount_col], proof_df[company_col]
            )
            adjustment_amount = proof_df["Amount_USD"].sum()
        else:
            # No company column, cannot convert - use LCY
            adjustment_amount = proof_df[amount_col].sum()
    else:
        # No FX converter provided - use local currency
        adjustment_amount = proof_df[amount_col].sum()

    # --- VTC Metrics ---
    vtc_metrics: Dict[str, Any] = {
        "total_count": len(proof_df),
        "breakdown_by_type": {},
    }

    if not proof_df.empty:
        if "business_use_formatted" in proof_df.columns:
            vtc_metrics["breakdown_by_type"] = (
                proof_df["business_use_formatted"].value_counts().to_dict()
            )
        elif "business_use" in proof_df.columns:
            vtc_metrics["breakdown_by_type"] = (
                proof_df["business_use"].value_counts().to_dict()
            )

    return adjustment_amount, proof_df, vtc_metrics


__all__ = [
    "calculate_vtc_adjustment",
]
