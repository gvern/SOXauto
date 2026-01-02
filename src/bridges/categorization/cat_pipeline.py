"""
Categorization Pipeline Module.

Main orchestration function that applies all categorization rules in sequence.
Takes a raw NAV DataFrame and returns a categorized DataFrame.

Rule Priority (highest to lowest):
1. VTC via Bank Account - Manual + any amount + Bank Account
2. Issuance - Negative amounts
3. Usage - Positive + Integration
4. Expired - Manual + Positive + EXPR_*
5. VTC Pattern - Manual + Positive + RND/PYT+GTB
6. Manual Cancellation - Manual + Positive + Credit Memo
7. Manual Usage - Manual + Positive + ITEMPRICECREDIT

Note: "VTC via Bank Account" has the highest priority among all rules,
as described in the PR ("VTC > Issuance > Usage > Expired > Manual").

This is a pure function: DataFrame -> DataFrame
No st.session_state or st.cache usage.
"""

from typing import Optional
import pandas as pd

from src.bridges.categorization.cat_nav_classifier import classify_integration_type
from src.bridges.categorization.cat_issuance_classifier import classify_issuance
from src.bridges.categorization.cat_usage_classifier import classify_usage, classify_manual_usage
from src.bridges.categorization.cat_vtc_classifier import (
    classify_vtc_bank_account,
    classify_vtc_pattern,
)
from src.bridges.categorization.cat_expired_classifier import (
    classify_expired,
    classify_manual_cancellation,
)


def categorize_nav_vouchers(
    cr_03_df: pd.DataFrame,
    ipe_08_df: Optional[pd.DataFrame] = None,
    doc_voucher_usage_df: Optional[pd.DataFrame] = None,
    gl_account_filter: str = "18412",
) -> pd.DataFrame:
    """
    Main categorization pipeline for NAV GL entries.

    Applies all categorization rules in priority order to classify NAV GL entries
    (CR_03) according to the voucher accrual analysis business rules.

    Categories produced:
    - 'Issuance - Refund': Voucher issuance for refunds
    - 'Issuance - Apology': Voucher issuance for apologies (COMMERCIAL GESTURE)
    - 'Issuance - JForce': Voucher issuance for JForce (PYT_PF)
    - 'Issuance - Store Credit': Manual voucher issuance (Document No starts with country code)
    - 'Issuance': Generic issuance if no sub-category matches
    - 'Usage': Voucher usage transactions
    - 'Cancellation - Apology': Automated cancellation (Voucher Accrual description)
    - 'Cancellation - Store Credit': Manual cancellation via Credit Memo
    - 'Expired - Apology': Expired apology vouchers (EXPR_APLGY)
    - 'Expired - Refund': Expired refund vouchers (EXPR_JFORCE)
    - 'Expired - Store Credit': Expired store credit vouchers (EXPR_STR CRDT)
    - 'Expired': Generic expired vouchers
    - 'VTC': Voucher to Cash refund transactions
    - None: Transactions that don't match any rule

    Args:
        cr_03_df: DataFrame containing NAV GL entries with columns like:
                  'Chart of Accounts No_', 'Amount', 'Bal_ Account Type',
                  'User ID', 'Document Description', 'Document Type',
                  'Document No', '[Voucher No_]'
        ipe_08_df: Optional DataFrame from IPE_08 (Issuance TV) for voucher type lookups.
                   Expected columns: 'id', 'business_use'
        doc_voucher_usage_df: Optional DataFrame from DOC_VOUCHER_USAGE (Usage TV).
                              Expected columns: 'id', 'business_use', 'Transaction_No'
        gl_account_filter: GL account to filter for categorization (default: "18412")

    Returns:
        DataFrame with added 'bridge_category', 'voucher_type', and 'Integration_Type' columns

    Example:
        >>> cr_03_df = pd.DataFrame({
        ...     'Chart of Accounts No_': ['18412', '18412'],
        ...     'Amount': [-100.0, 50.0],
        ...     'User ID': ['JUMIA/NAV13AFR.BATCH.SRVC', 'USER/01'],
        ...     'Document Description': ['Refund voucher', 'Manual RND entry']
        ... })
        >>> result = categorize_nav_vouchers(cr_03_df)
        >>> print(result[['bridge_category', 'voucher_type']].to_dict())
    """
    if cr_03_df is None or cr_03_df.empty:
        result = cr_03_df.copy() if cr_03_df is not None else pd.DataFrame()
        result["bridge_category"] = None
        result["voucher_type"] = None
        result["Integration_Type"] = None
        return result

    out = cr_03_df.copy()

    # Initialize output columns
    out["bridge_category"] = None
    out["voucher_type"] = None

    # Find GL account column
    gl_col = _find_gl_account_column(out)

    # Step 1: Determine Integration_Type for all rows
    out = classify_integration_type(out)

    # For rows not matching GL filter, skip categorization
    # but keep Integration_Type set
    if gl_col is not None:
        # Create mask for GL account filter
        gl_mask = out[gl_col].astype(str).str.strip() == gl_account_filter
    else:
        # If no GL column found, process all rows
        gl_mask = pd.Series([True] * len(out), index=out.index)

    # Step 2 (Priority): VTC via Bank Account
    # This must come before Issuance because it can have negative amounts
    out = _apply_to_masked_rows(
        out,
        gl_mask,
        classify_vtc_bank_account,
    )

    # Step 3: Issuance (Negative Amounts)
    out = _apply_to_masked_rows(
        out,
        gl_mask,
        classify_issuance,
    )

    # Step 4: Usage (Positive Amounts + Integrated)
    out = _apply_to_masked_rows(
        out,
        gl_mask,
        lambda df: classify_usage(
            df,
            ipe_08_df=ipe_08_df,
            doc_voucher_usage_df=doc_voucher_usage_df,
        ),
    )

    # Step 5: Expired (Manual + Positive + EXPR_*)
    out = _apply_to_masked_rows(
        out,
        gl_mask,
        classify_expired,
    )

    # Step 6: VTC Pattern (Manual + Positive + RND/PYT+GTB)
    out = _apply_to_masked_rows(
        out,
        gl_mask,
        classify_vtc_pattern,
    )

    # Step 7: Manual Cancellation (Credit Memo)
    out = _apply_to_masked_rows(
        out,
        gl_mask,
        classify_manual_cancellation,
    )

    # Step 8: Manual Usage (Nigeria Exception - ITEMPRICECREDIT)
    out = _apply_to_masked_rows(
        out,
        gl_mask,
        lambda df: classify_manual_usage(
            df,
            ipe_08_df=ipe_08_df,
            doc_voucher_usage_df=doc_voucher_usage_df,
        ),
    )

    return out


def _find_gl_account_column(df: pd.DataFrame) -> Optional[str]:
    """
    Find the GL account column in the DataFrame.

    Args:
        df: DataFrame to search for GL account column.

    Returns:
        Column name if found, None otherwise.
    """
    gl_column_variants = [
        "Chart of Accounts No_",
        "GL Account",
        "gl_account",
        "GL_Account",
        "Account_No",
        "account_no",
    ]

    for col in gl_column_variants:
        if col in df.columns:
            return col

    # Try to find by partial match
    for col in df.columns:
        col_lower = col.lower().strip()
        if "chart of accounts" in col_lower or col_lower == "gl account":
            return col

    return None


def _apply_to_masked_rows(
    df: pd.DataFrame,
    mask: pd.Series,
    classifier_func,
) -> pd.DataFrame:
    """
    Apply a classifier function only to rows matching a mask.

    This helper ensures that classifiers only operate on relevant rows
    (e.g., GL 18412 rows) while preserving other rows unchanged.

    Args:
        df: DataFrame to process.
        mask: Boolean Series indicating which rows to process.
        classifier_func: Function that takes a DataFrame and returns a classified DataFrame.

    Returns:
        DataFrame with classified rows merged back with non-classified rows.
    """
    if mask.sum() == 0:
        return df

    # Get the rows to classify
    rows_to_classify = df[mask].copy()

    # Apply classifier
    classified = classifier_func(rows_to_classify)

    # Update the original DataFrame with classified values
    for col in ["bridge_category", "voucher_type"]:
        if col in classified.columns:
            df.loc[mask, col] = classified[col].values

    return df


def get_categorization_summary(df: pd.DataFrame) -> dict:
    """
    Generate a summary of categorization results.

    Args:
        df: DataFrame with categorization columns.

    Returns:
        Dictionary with summary statistics:
        {
            'total_rows': int,
            'categorized_rows': int,
            'uncategorized_rows': int,
            'by_category': dict,
            'by_voucher_type': dict,
            'by_integration_type': dict
        }
    """
    if df is None or df.empty:
        return {
            "total_rows": 0,
            "categorized_rows": 0,
            "uncategorized_rows": 0,
            "by_category": {},
            "by_voucher_type": {},
            "by_integration_type": {},
        }

    total = len(df)
    categorized = df["bridge_category"].notna().sum() if "bridge_category" in df.columns else 0

    by_category = {}
    by_voucher_type = {}
    by_integration_type = {}

    if "bridge_category" in df.columns:
        by_category = df["bridge_category"].value_counts(dropna=False).to_dict()

    if "voucher_type" in df.columns:
        by_voucher_type = df["voucher_type"].value_counts(dropna=False).to_dict()

    if "Integration_Type" in df.columns:
        by_integration_type = df["Integration_Type"].value_counts(dropna=False).to_dict()

    return {
        "total_rows": total,
        "categorized_rows": int(categorized),
        "uncategorized_rows": total - int(categorized),
        "by_category": by_category,
        "by_voucher_type": by_voucher_type,
        "by_integration_type": by_integration_type,
    }


__all__ = [
    "categorize_nav_vouchers",
    "get_categorization_summary",
]
