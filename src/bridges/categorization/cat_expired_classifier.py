"""
Expired Vouchers Classifier Module.

Classifies NAV GL entries as Expired voucher transactions based on EXPR_* patterns.

Business Rules:
- Expired - Apology: Manual + Positive + EXPR_APLGY pattern
- Expired - Refund: Manual + Positive + EXPR_JFORCE pattern
- Expired - Store Credit: Manual + Positive + EXPR_STR CRDT or EXPR_STR_CRDT pattern
- Expired (generic): Manual + Positive + EXPR pattern without specific sub-type

This is a pure function: DataFrame -> DataFrame
No st.session_state or st.cache usage.
"""

from typing import Optional
import pandas as pd


def classify_expired(
    df: pd.DataFrame,
    amount_col: Optional[str] = None,
    description_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Classify NAV GL entries as Expired voucher transactions.

    Only applies to rows where:
    - Amount is positive
    - Integration_Type is 'Manual'
    - bridge_category is not already set
    - Description contains 'EXPR' pattern

    Args:
        df: DataFrame containing GL entries with amount, description, and Integration_Type columns.
        amount_col: Name of the amount column. If None, auto-detects.
        description_col: Name of the description column. If None, auto-detects.

    Returns:
        DataFrame with 'bridge_category' and 'voucher_type' columns populated
        for rows matching expired criteria.

    Example:
        >>> df = pd.DataFrame({
        ...     'Amount': [30.0],
        ...     'Document Description': ['EXPR_APLGY voucher cleanup'],
        ...     'Integration_Type': ['Manual']
        ... })
        >>> result = classify_expired(df)
        >>> print(result['bridge_category'].iloc[0])
        'Expired - Apology'
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

    if amount_col is None or amount_col not in out.columns:
        # Cannot classify without amount column
        return out

    # Apply expired classification for each row
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

        # Only process manual transactions for expired
        if integration_type != "Manual":
            continue

        description = (
            str(row[description_col]).upper().strip()
            if description_col and pd.notna(row.get(description_col))
            else ""
        )

        # Check for EXPR patterns
        if "EXPR" not in description:
            continue

        # Classify based on specific EXPR pattern
        if "EXPR_APLGY" in description:
            out.at[idx, "bridge_category"] = "Expired - Apology"
            out.at[idx, "voucher_type"] = "Apology"
        elif "EXPR_JFORCE" in description:
            out.at[idx, "bridge_category"] = "Expired - Refund"
            out.at[idx, "voucher_type"] = "Refund"
        elif "EXPR_STR CRDT" in description or "EXPR_STR_CRDT" in description:
            out.at[idx, "bridge_category"] = "Expired - Store Credit"
            out.at[idx, "voucher_type"] = "Store Credit"
        else:
            # Generic expired
            out.at[idx, "bridge_category"] = "Expired"

    return out


def classify_manual_cancellation(
    df: pd.DataFrame,
    amount_col: Optional[str] = None,
    doc_type_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Classify Manual Cancellation transactions via Credit Memo.

    Only applies to rows where:
    - Amount is positive
    - Integration_Type is 'Manual'
    - bridge_category is not already set
    - Document Type is 'Credit Memo'

    Args:
        df: DataFrame containing GL entries.
        amount_col: Name of the amount column. If None, auto-detects.
        doc_type_col: Name of the document type column. If None, auto-detects.

    Returns:
        DataFrame with classifications for manual cancellation entries.
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    out = df.copy()

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

    if doc_type_col is None:
        for col in ["Document Type", "Document_Type", "doc_type", "Doc_Type"]:
            if col in out.columns:
                doc_type_col = col
                break

    if amount_col is None or amount_col not in out.columns:
        return out

    # Apply manual cancellation classification
    for idx, row in out.iterrows():
        if pd.notna(out.at[idx, "bridge_category"]):
            continue

        amount = row[amount_col] if pd.notna(row[amount_col]) else 0

        if amount <= 0:
            continue

        integration_type = (
            str(row["Integration_Type"]).strip()
            if "Integration_Type" in row.index and pd.notna(row["Integration_Type"])
            else "Manual"
        )

        if integration_type != "Manual":
            continue

        doc_type = (
            str(row[doc_type_col]).lower().strip()
            if doc_type_col and pd.notna(row.get(doc_type_col))
            else ""
        )

        if doc_type == "credit memo":
            out.at[idx, "bridge_category"] = "Cancellation - Store Credit"
            out.at[idx, "voucher_type"] = "Store Credit"

    return out


__all__ = ["classify_expired", "classify_manual_cancellation"]
