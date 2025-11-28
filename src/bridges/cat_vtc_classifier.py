"""
VTC (Voucher to Cash) Classifier Module.

Classifies NAV GL entries as VTC (Voucher to Cash) refund transactions.

Business Rules (Priority Order):
1. VTC via Bank Account: Manual + Amount != 0 + Bal_ Account Type = "Bank Account"
2. VTC via RND: Manual + Positive + "MANUAL RND" in description
3. VTC via PYT/GTB: Manual + Positive + "PYT_" in description + "GTB" in comment

This is a pure function: DataFrame -> DataFrame
No st.session_state or st.cache usage.
"""

from typing import Optional
import pandas as pd


def classify_vtc(
    df: pd.DataFrame,
    amount_col: Optional[str] = None,
    description_col: Optional[str] = None,
    bal_account_type_col: Optional[str] = None,
    comment_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Classify NAV GL entries as VTC (Voucher to Cash) transactions.

    VTC transactions represent voucher refunds paid to customers via bank transfer.
    This classifier handles both Bank Account-based VTC (highest priority) and
    pattern-based VTC (MANUAL RND, PYT_/GTB).

    Args:
        df: DataFrame containing GL entries with amount, description, and Integration_Type columns.
        amount_col: Name of the amount column. If None, auto-detects.
        description_col: Name of the description column. If None, auto-detects.
        bal_account_type_col: Name of the balancing account type column. If None, auto-detects.
        comment_col: Name of the comment column. If None, auto-detects.

    Returns:
        DataFrame with 'bridge_category' and 'voucher_type' columns populated
        for rows matching VTC criteria.

    Example:
        >>> df = pd.DataFrame({
        ...     'Amount': [-100.0],
        ...     'Bal_ Account Type': ['Bank Account'],
        ...     'Integration_Type': ['Manual']
        ... })
        >>> result = classify_vtc(df)
        >>> print(result['bridge_category'].iloc[0])
        'VTC'
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

    if bal_account_type_col is None:
        for col in ["Bal_ Account Type", "Bal_Account_Type", "bal_account_type"]:
            if col in out.columns:
                bal_account_type_col = col
                break

    if comment_col is None:
        for col in ["Comment", "Comments", "comment", "comments"]:
            if col in out.columns:
                comment_col = col
                break

    if amount_col is None or amount_col not in out.columns:
        # Cannot classify without amount column
        return out

    # Apply VTC classification for each row
    for idx, row in out.iterrows():
        # Skip if already categorized
        if pd.notna(out.at[idx, "bridge_category"]):
            continue

        amount = row[amount_col] if pd.notna(row[amount_col]) else 0

        integration_type = (
            str(row["Integration_Type"]).strip()
            if "Integration_Type" in row.index and pd.notna(row["Integration_Type"])
            else "Manual"
        )

        # Only process manual transactions for VTC
        if integration_type != "Manual":
            continue

        # Get field values
        bal_account_type = (
            str(row[bal_account_type_col]).upper().strip()
            if bal_account_type_col and pd.notna(row.get(bal_account_type_col))
            else ""
        )

        description = (
            str(row[description_col]).upper().strip()
            if description_col and pd.notna(row.get(description_col))
            else ""
        )

        comment = (
            str(row[comment_col]).upper().strip()
            if comment_col and pd.notna(row.get(comment_col))
            else ""
        )

        # Priority 1: VTC via Bank Account (any non-zero amount)
        if amount != 0 and bal_account_type == "BANK ACCOUNT":
            out.at[idx, "bridge_category"] = "VTC"
            out.at[idx, "voucher_type"] = "Refund"
            continue

        # Priority 2 & 3: Pattern-based VTC (positive amounts only)
        if amount > 0:
            is_vtc = False

            # Pattern: MANUAL RND
            if "MANUAL RND" in description:
                is_vtc = True

            # Pattern: PYT_ with GTB in comment
            elif "PYT_" in description and "GTB" in comment:
                is_vtc = True

            if is_vtc:
                out.at[idx, "bridge_category"] = "VTC"
                out.at[idx, "voucher_type"] = "Refund"

    return out


def classify_vtc_bank_account(
    df: pd.DataFrame,
    amount_col: Optional[str] = None,
    bal_account_type_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Classify VTC transactions based on Bank Account balancing type.

    This is a specialized version that only checks the Bank Account pattern.
    Should be called with highest priority in the categorization pipeline.

    Business Rule:
    - Manual user
    - Non-zero amount
    - Balancing Account Type = "Bank Account"

    Args:
        df: DataFrame containing GL entries.
        amount_col: Name of the amount column. If None, auto-detects.
        bal_account_type_col: Name of the balancing account type column. If None, auto-detects.

    Returns:
        DataFrame with VTC classifications for Bank Account entries.
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

    if bal_account_type_col is None:
        for col in ["Bal_ Account Type", "Bal_Account_Type", "bal_account_type"]:
            if col in out.columns:
                bal_account_type_col = col
                break

    if amount_col is None or amount_col not in out.columns:
        return out

    # Apply Bank Account VTC classification
    for idx, row in out.iterrows():
        if pd.notna(out.at[idx, "bridge_category"]):
            continue

        amount = row[amount_col] if pd.notna(row[amount_col]) else 0

        integration_type = (
            str(row["Integration_Type"]).strip()
            if "Integration_Type" in row.index and pd.notna(row["Integration_Type"])
            else "Manual"
        )

        if integration_type != "Manual":
            continue

        bal_account_type = (
            str(row[bal_account_type_col]).upper().strip()
            if bal_account_type_col and pd.notna(row.get(bal_account_type_col))
            else ""
        )

        if amount != 0 and bal_account_type == "BANK ACCOUNT":
            out.at[idx, "bridge_category"] = "VTC"
            out.at[idx, "voucher_type"] = "Refund"

    return out


def classify_vtc_pattern(
    df: pd.DataFrame,
    amount_col: Optional[str] = None,
    description_col: Optional[str] = None,
    comment_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Classify VTC transactions based on description/comment patterns.

    This handles:
    - MANUAL RND pattern
    - PYT_ with GTB in comment

    Args:
        df: DataFrame containing GL entries.
        amount_col: Name of the amount column. If None, auto-detects.
        description_col: Name of the description column. If None, auto-detects.
        comment_col: Name of the comment column. If None, auto-detects.

    Returns:
        DataFrame with VTC classifications for pattern-based entries.
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

    if description_col is None:
        for col in ["Document Description", "description", "Description", "desc"]:
            if col in out.columns:
                description_col = col
                break

    if comment_col is None:
        for col in ["Comment", "Comments", "comment", "comments"]:
            if col in out.columns:
                comment_col = col
                break

    if amount_col is None or amount_col not in out.columns:
        return out

    # Apply pattern-based VTC classification
    for idx, row in out.iterrows():
        if pd.notna(out.at[idx, "bridge_category"]):
            continue

        amount = row[amount_col] if pd.notna(row[amount_col]) else 0

        # Only positive amounts for pattern-based VTC
        if amount <= 0:
            continue

        integration_type = (
            str(row["Integration_Type"]).strip()
            if "Integration_Type" in row.index and pd.notna(row["Integration_Type"])
            else "Manual"
        )

        if integration_type != "Manual":
            continue

        description = (
            str(row[description_col]).upper().strip()
            if description_col and pd.notna(row.get(description_col))
            else ""
        )

        comment = (
            str(row[comment_col]).upper().strip()
            if comment_col and pd.notna(row.get(comment_col))
            else ""
        )

        is_vtc = False
        if "MANUAL RND" in description:
            is_vtc = True
        elif "PYT_" in description and "GTB" in comment:
            is_vtc = True

        if is_vtc:
            out.at[idx, "bridge_category"] = "VTC"
            out.at[idx, "voucher_type"] = "Refund"

    return out


__all__ = ["classify_vtc", "classify_vtc_bank_account", "classify_vtc_pattern"]
