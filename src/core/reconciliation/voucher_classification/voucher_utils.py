"""
Shared utilities for NAV voucher categorization.

This module contains common constants and utility functions used across
categorization modules for voucher type lookups and business rules.
"""

from typing import List, Optional
import pandas as pd


# Country codes for Store Credit issuance detection
COUNTRY_CODES: List[str] = ["NG", "EG", "KE", "GH", "CI", "MA", "TN", "ZA", "UG", "SN"]


def _lookup_by_transaction_no(
    df: pd.DataFrame,
    doc_no: str
) -> Optional[str]:
    """
    Helper function to lookup business_use by matching doc_no to Transaction_No column.
    
    Handles various Transaction_No column naming conventions.
    
    Args:
        df: DataFrame to search (must have Transaction_No and business_use columns)
        doc_no: Document number to match
    
    Returns:
        The business_use value if found, None otherwise
    """
    if df is None or df.empty or not doc_no:
        return None
    
    # Find Transaction_No column (handle various naming conventions)
    transaction_col = None
    for col in ["Transaction_No", "transaction_no", "Transaction_No_", "TransactionNo"]:
        if col in df.columns:
            transaction_col = col
            break
    
    if transaction_col:
        try:
            match = df[df[transaction_col].astype(str).str.strip() == str(doc_no).strip()]
            if not match.empty and "business_use" in match.columns:
                return str(match.iloc[0]["business_use"])
        except (TypeError, ValueError, AttributeError):
            # Handle conversion errors gracefully
            pass
    
    return None


def lookup_voucher_type(
    voucher_no: str,
    doc_no: str,
    ipe_08_df: Optional[pd.DataFrame],
    doc_voucher_usage_df: Optional[pd.DataFrame],
) -> Optional[str]:
    """
    Lookup voucher type from IPE_08 or doc_voucher_usage_df with robust fallback strategy.

    Strategy:
    1. Primary Lookup: Match NAV Voucher No to TV File 'id' column
       - Try IPE_08 first (Issuance data)
       - Then try doc_voucher_usage_df (Usage data)
    2. Secondary Lookup (Fallback): If Voucher No is missing or no match found:
       - Match NAV Document No to TV File 'Transaction_No' column
       - Retrieve business_use (Voucher Type) from matching record

    This handles the Nigeria Integration Issue where descriptions like ITEMPRICECREDIT
    appear without a voucher ID but have a transaction number.

    Args:
        voucher_no: The voucher number from NAV ([Voucher No_])
        doc_no: The document number from NAV (Document No)
        ipe_08_df: IPE_08 DataFrame with 'id' and 'business_use' columns
        doc_voucher_usage_df: Usage TV DataFrame with 'id', 'business_use', 'Transaction_No' columns

    Returns:
        The voucher type (business_use) if found, None otherwise

    Examples:
        >>> # Primary lookup by voucher_no
        >>> lookup_voucher_type("V12345", "DOC-001", ipe_08_df, usage_df)
        'refund'
        
        >>> # Fallback to doc_no when voucher_no is missing
        >>> lookup_voucher_type("", "TRX-67890", ipe_08_df, usage_df)
        'store_credit'
    """
    try:
        # ============================================================
        # PRIMARY LOOKUP: Match by voucher_no -> id
        # ============================================================
        
        # Try IPE_08 first (Issuance data takes priority)
        if ipe_08_df is not None and not ipe_08_df.empty:
            if voucher_no:
                match = ipe_08_df[ipe_08_df["id"].astype(str).str.strip() == str(voucher_no).strip()]
                if not match.empty and "business_use" in match.columns:
                    return str(match.iloc[0]["business_use"])

        # Try doc_voucher_usage_df by voucher_no
        if doc_voucher_usage_df is not None and not doc_voucher_usage_df.empty:
            if voucher_no:
                match = doc_voucher_usage_df[
                    doc_voucher_usage_df["id"].astype(str).str.strip() == str(voucher_no).strip()
                ]
                if not match.empty and "business_use" in match.columns:
                    return str(match.iloc[0]["business_use"])

            # ============================================================
            # SECONDARY LOOKUP (FALLBACK): Match by doc_no -> Transaction_No
            # ============================================================
            # This handles cases where:
            # - Voucher No_ is missing/empty in NAV
            # - Voucher No_ doesn't match any records
            # - Nigeria Integration Issue (ITEMPRICECREDIT without voucher ID)
            
            result = _lookup_by_transaction_no(doc_voucher_usage_df, doc_no)
            if result:
                return result
        
        # Also try IPE_08 by Transaction_No if column exists (defensive coding)
        # Though typically IPE_08 (Issuance) doesn't have Transaction_No, 
        # we check anyway for robustness in case data schema evolves
        if ipe_08_df is not None:
            result = _lookup_by_transaction_no(ipe_08_df, doc_no)
            if result:
                return result
                    
    except (TypeError, ValueError, AttributeError):
        # Handle conversion errors gracefully
        pass

    return None


__all__ = ["COUNTRY_CODES", "lookup_voucher_type"]
