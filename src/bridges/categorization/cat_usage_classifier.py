"""
Usage Classifier Module.

Classifies NAV GL entries with positive amounts and Integration type as Usage transactions.
Also handles Voucher Accrual cancellation detection.

Business Rules:
- Usage (Integrated): Positive amount + Integration user
- Cancellation - Apology: Positive amount + Integration + "Voucher Accrual" in description

This is a pure function: DataFrame -> DataFrame
No st.session_state or st.cache usage.
"""

from typing import Optional
import pandas as pd

from src.bridges.categorization.voucher_utils import lookup_voucher_type


def classify_usage(
    df: pd.DataFrame,
    amount_col: Optional[str] = None,
    description_col: Optional[str] = None,
    ipe_08_df: Optional[pd.DataFrame] = None,
    doc_voucher_usage_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Classify NAV GL entries with positive amounts and Integration type as Usage.

    Only applies to rows where:
    - Amount is positive
    - Integration_Type is 'Integration'
    - bridge_category is not already set

    Special case: If description contains "VOUCHER ACCRUAL", classify as
    "Cancellation - Apology" instead of Usage.

    Args:
        df: DataFrame containing GL entries with amount, description, and Integration_Type columns.
        amount_col: Name of the amount column. If None, auto-detects.
        description_col: Name of the description column. If None, auto-detects.
        ipe_08_df: Optional DataFrame from IPE_08 for voucher type lookups.
                   Expected columns: 'id', 'business_use'
        doc_voucher_usage_df: Optional DataFrame for fallback voucher type lookups.
                              Expected columns: 'id', 'business_use', 'Transaction_No'

    Returns:
        DataFrame with 'bridge_category' and 'voucher_type' columns populated
        for rows matching usage criteria.

    Example:
        >>> df = pd.DataFrame({
        ...     'Amount': [100.0],
        ...     'Document Description': ['Item price credit'],
        ...     'Integration_Type': ['Integration']
        ... })
        >>> result = classify_usage(df)
        >>> print(result['bridge_category'].iloc[0])
        'Usage'
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    out = df.copy()

    # Ensure required output columns exist
    if "bridge_category" not in out.columns:
        out["bridge_category"] = None
    if "voucher_type" not in out.columns:
        out["voucher_type"] = None

    # Auto-detect column names
    if amount_col is None:
        for col in ["Amount", "amount", "Amt", "amt"]:
            if col in out.columns:
                amount_col = col
                break

    if description_col is None:
        for col in ["Document Description", "description", "Description", "desc"]:
            if col in out.columns:
                description_col = col
                break

    # Find voucher number and document number columns for type lookups
    voucher_no_col = None
    for col in ["Voucher No_", "[Voucher No_]", "voucher_no", "Voucher_No"]:
        if col in out.columns:
            voucher_no_col = col
            break

    doc_no_col = None
    for col in ["Document No", "Document No_", "doc_no", "Doc_No"]:
        if col in out.columns:
            doc_no_col = col
            break

    if amount_col is None or amount_col not in out.columns:
        # Cannot classify without amount column
        return out

    # Apply usage classification for each row
    for idx, row in out.iterrows():
        # Skip if already categorized
        if pd.notna(out.at[idx, "bridge_category"]):
            continue

        amount = row[amount_col] if pd.notna(row[amount_col]) else 0

        # Only process positive amounts
        if amount <= 0:
            continue

        integration_type = (
            str(row["Integration_Type"]).strip()
            if "Integration_Type" in row.index and pd.notna(row["Integration_Type"])
            else "Manual"
        )

        # Only process integrated transactions
        if integration_type != "Integration":
            continue

        description = (
            str(row[description_col]).upper().strip()
            if description_col and pd.notna(row.get(description_col))
            else ""
        )

        # Check for Voucher Accrual cancellation
        if "VOUCHER ACCRUAL" in description:
            out.at[idx, "bridge_category"] = "Cancellation - Apology"
            out.at[idx, "voucher_type"] = "Apology"
        else:
            # Standard Usage
            out.at[idx, "bridge_category"] = "Usage"

            # Lookup voucher type from reference DataFrames
            voucher_no = (
                str(row[voucher_no_col]).strip()
                if voucher_no_col and pd.notna(row.get(voucher_no_col))
                else ""
            )
            doc_no = (
                str(row[doc_no_col]).strip()
                if doc_no_col and pd.notna(row.get(doc_no_col))
                else ""
            )

            voucher_type = lookup_voucher_type(
                voucher_no, doc_no, ipe_08_df, doc_voucher_usage_df
            )
            if voucher_type:
                out.at[idx, "voucher_type"] = voucher_type

    return out


def classify_manual_usage(
    df: pd.DataFrame,
    amount_col: Optional[str] = None,
    description_col: Optional[str] = None,
    ipe_08_df: Optional[pd.DataFrame] = None,
    doc_voucher_usage_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Classify Manual Usage transactions (Nigeria exception - ITEMPRICECREDIT).

    Only applies to rows where:
    - Amount is positive
    - Integration_Type is 'Manual'
    - bridge_category is not already set
    - Description contains 'ITEMPRICECREDIT'

    Args:
        df: DataFrame containing GL entries.
        amount_col: Name of the amount column. If None, auto-detects.
        description_col: Name of the description column. If None, auto-detects.
        ipe_08_df: Optional DataFrame for voucher type lookups.
        doc_voucher_usage_df: Optional DataFrame for fallback voucher type lookups.

    Returns:
        DataFrame with updated classifications for manual usage entries.
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    out = df.copy()

    # Ensure required output columns exist
    if "bridge_category" not in out.columns:
        out["bridge_category"] = None
    if "voucher_type" not in out.columns:
        out["voucher_type"] = None

    # Auto-detect column names
    if amount_col is None:
        for col in ["Amount", "amount", "Amt", "amt"]:
            if col in out.columns:
                amount_col = col
                break

    if description_col is None:
        for col in ["Document Description", "description", "Description", "desc"]:
            if col in out.columns:
                description_col = col
                break

    # Find voucher number and document number columns
    voucher_no_col = None
    for col in ["Voucher No_", "[Voucher No_]", "voucher_no", "Voucher_No"]:
        if col in out.columns:
            voucher_no_col = col
            break

    doc_no_col = None
    for col in ["Document No", "Document No_", "doc_no", "Doc_No"]:
        if col in out.columns:
            doc_no_col = col
            break

    if amount_col is None or amount_col not in out.columns:
        return out

    # Apply manual usage classification
    for idx, row in out.iterrows():
        # Skip if already categorized
        if pd.notna(out.at[idx, "bridge_category"]):
            continue

        amount = row[amount_col] if pd.notna(row[amount_col]) else 0

        # Only process positive amounts
        if amount <= 0:
            continue

        integration_type = (
            str(row["Integration_Type"]).strip()
            if "Integration_Type" in row.index and pd.notna(row["Integration_Type"])
            else "Manual"
        )

        # Only process manual transactions
        if integration_type != "Manual":
            continue

        description = (
            str(row[description_col]).upper().strip()
            if description_col and pd.notna(row.get(description_col))
            else ""
        )

        # Check for ITEMPRICECREDIT pattern (Nigeria exception)
        if "ITEMPRICECREDIT" in description:
            out.at[idx, "bridge_category"] = "Usage"

            # Lookup voucher type
            voucher_no = (
                str(row[voucher_no_col]).strip()
                if voucher_no_col and pd.notna(row.get(voucher_no_col))
                else ""
            )
            doc_no = (
                str(row[doc_no_col]).strip()
                if doc_no_col and pd.notna(row.get(doc_no_col))
                else ""
            )

            voucher_type = lookup_voucher_type(
                voucher_no, doc_no, ipe_08_df, doc_voucher_usage_df
            )
            if voucher_type:
                out.at[idx, "voucher_type"] = voucher_type

    return out


# Re-export for backward compatibility - tests import from here
__all__ = ["classify_usage", "classify_manual_usage", "lookup_voucher_type"]
