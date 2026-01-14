"""
Issuance Classifier Module.

Classifies NAV GL entries with negative amounts as Issuance transactions.
Determines sub-categories: Refund, Commercial Gesture (Apology), JForce, Store Credit.

Business Rules:
- Integrated Issuance:
  - REFUND/RF_/RF  -> Issuance - Refund
  - COMMERCIAL GESTURE -> Issuance - Apology
  - PYT_ -> Issuance - JForce
  
- Manual Issuance:
  - Document No starts with country code -> Issuance - Store Credit
  - REFUND/RFN/RF_ patterns -> Issuance - Refund
  - COMMERCIAL/CXP/APOLOGY -> Issuance - Apology
  - PYT_ -> Issuance - JForce

This is a pure function: DataFrame -> DataFrame
No st.session_state or st.cache usage.
"""

from typing import Optional
import pandas as pd

from src.core.reconciliation.voucher_classification.voucher_utils import COUNTRY_CODES


def classify_issuance(
    df: pd.DataFrame,
    amount_col: Optional[str] = None,
    description_col: Optional[str] = None,
    doc_no_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Classify NAV GL entries with negative amounts as Issuance transactions.

    Only applies to rows where:
    - Amount is negative
    - Integration_Type is already set (from nav_classifier)
    - bridge_category is not already set

    Args:
        df: DataFrame containing GL entries with amount, description, and Integration_Type columns.
        amount_col: Name of the amount column. If None, auto-detects.
        description_col: Name of the description column. If None, auto-detects.
        doc_no_col: Name of the document number column. If None, auto-detects.

    Returns:
        DataFrame with 'bridge_category' and 'voucher_type' columns populated
        for rows matching issuance criteria.

    Example:
        >>> df = pd.DataFrame({
        ...     'Amount': [-100.0],
        ...     'Document Description': ['Refund voucher'],
        ...     'Integration_Type': ['Integration']
        ... })
        >>> result = classify_issuance(df)
        >>> print(result['bridge_category'].iloc[0])
        'Issuance - Refund'
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

    if doc_no_col is None:
        for col in ["Document No", "Document No_", "doc_no", "Doc_No"]:
            if col in out.columns:
                doc_no_col = col
                break

    if amount_col is None or amount_col not in out.columns:
        # Cannot classify without amount column
        return out

    # Apply issuance classification for each row
    for idx, row in out.iterrows():
        # Skip if already categorized
        if pd.notna(out.at[idx, "bridge_category"]):
            continue

        amount = row[amount_col] if pd.notna(row[amount_col]) else 0

        # Only process negative amounts (issuance)
        if amount >= 0:
            continue

        integration_type = (
            str(row["Integration_Type"]).strip()
            if "Integration_Type" in row.index and pd.notna(row["Integration_Type"])
            else "Manual"
        )

        description = (
            str(row[description_col]).upper().strip()
            if description_col and pd.notna(row.get(description_col))
            else ""
        )

        doc_no = (
            str(row[doc_no_col]).strip().upper()
            if doc_no_col and pd.notna(row.get(doc_no_col))
            else ""
        )

        # Apply classification based on integration type
        if integration_type == "Integration":
            _classify_integrated_issuance(out, idx, description)
        else:
            _classify_manual_issuance(out, idx, description, doc_no)

    return out


def _classify_integrated_issuance(df: pd.DataFrame, idx: int, description: str) -> None:
    """
    Apply integrated issuance rules to a single row.

    Priority:
    1. Refund: REFUND, RF_, RF (space)
    2. Apology: COMMERCIAL GESTURE
    3. JForce: PYT_ (includes PYT_PF)
    4. Generic Issuance (fallback)
    """
    if "REFUND" in description or "RF_" in description or "RF " in description:
        df.at[idx, "bridge_category"] = "Issuance - Refund"
        df.at[idx, "voucher_type"] = "Refund"
    elif "COMMERCIAL GESTURE" in description:
        df.at[idx, "bridge_category"] = "Issuance - Apology"
        df.at[idx, "voucher_type"] = "Apology"
    elif "PYT_" in description:
        df.at[idx, "bridge_category"] = "Issuance - JForce"
        df.at[idx, "voucher_type"] = "JForce"
    else:
        # Fallback: Generic integrated issuance
        df.at[idx, "bridge_category"] = "Issuance"


def _classify_manual_issuance(
    df: pd.DataFrame, idx: int, description: str, doc_no: str
) -> None:
    """
    Apply manual issuance rules to a single row.

    Priority:
    1. Store Credit: Document No starts with country code
    2. Refund: REFUND, RFN, RF_
    3. Apology: COMMERCIAL, CXP, APOLOGY
    4. JForce: PYT_ (includes PYT_PF)
    5. Generic Issuance (fallback)
    """
    # Check if Document No starts with Country Code
    is_store_credit = any(doc_no.startswith(cc) for cc in COUNTRY_CODES)
    
    if is_store_credit:
        df.at[idx, "bridge_category"] = "Issuance - Store Credit"
        df.at[idx, "voucher_type"] = "Store Credit"
    elif "REFUND" in description or "RFN" in description or "RF_" in description or "RF " in description:
        df.at[idx, "bridge_category"] = "Issuance - Refund"
        df.at[idx, "voucher_type"] = "Refund"
    elif "COMMERCIAL" in description or "CXP" in description or "APOLOGY" in description:
        df.at[idx, "bridge_category"] = "Issuance - Apology"
        df.at[idx, "voucher_type"] = "Apology"
    elif "PYT_" in description:
        df.at[idx, "bridge_category"] = "Issuance - JForce"
        df.at[idx, "voucher_type"] = "JForce"
    else:
        # Generic issuance
        df.at[idx, "bridge_category"] = "Issuance"


# Re-export for backward compatibility
__all__ = ["classify_issuance", "COUNTRY_CODES"]
