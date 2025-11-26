"""
Rule-based classifier for PG-1 reconciliation bridges.

Takes input DataFrames (e.g., IPE_31 open items, IPE_10 prepayments) and applies
BridgeRule triggers to produce a standardized classification with GL expectations.
"""

from __future__ import annotations
from typing import List, Optional, Tuple
import pandas as pd

from src.bridges.catalog import BridgeRule


def _row_matches_rule(row: pd.Series, rule: BridgeRule) -> bool:
    for col, values in rule.triggers.items():
        if col not in row.index:
            # If the column isn't present, this rule can't fire on this row
            return False
        val = row[col]
        if pd.isna(val):
            return False
        sval = str(val)
        if not any(sval == v or sval.lower() == str(v).lower() for v in values):
            return False
    return True


def classify_bridges(df: pd.DataFrame, rules: List[BridgeRule]) -> pd.DataFrame:
    """Return a copy of df with added classification columns:
    - bridge_key
    - bridge_title
    - dr_gl_accounts (comma string)
    - cr_gl_accounts (comma string)
    - required_enrichments (comma string)

    If multiple rules match, the first in the list wins (order defines priority).
    """
    if df is None or df.empty:
        return df.copy()

    out = df.copy()
    out["bridge_key"] = None
    out["bridge_title"] = None
    out["dr_gl_accounts"] = None
    out["cr_gl_accounts"] = None
    out["required_enrichments"] = None

    # Sort rules by explicit priority rank (lower is higher priority)
    rules_sorted = sorted(rules, key=lambda r: getattr(r, "priority_rank", 2))

    for idx, row in out.iterrows():
        for rule in rules_sorted:
            if _row_matches_rule(row, rule):
                out.at[idx, "bridge_key"] = rule.key
                out.at[idx, "bridge_title"] = rule.title
                out.at[idx, "dr_gl_accounts"] = ",".join(rule.dr_gl_accounts)
                out.at[idx, "cr_gl_accounts"] = ",".join(rule.cr_gl_accounts)
                out.at[idx, "required_enrichments"] = ",".join(
                    rule.required_enrichments
                )
                break

    return out


def calculate_customer_posting_group_bridge(
    ipe_07_df: pd.DataFrame,
) -> tuple[float, pd.DataFrame]:
    """
    Identify customers with multiple posting groups for manual review.

    This bridge does not calculate a monetary value but identifies customers
    that have inconsistent posting group assignments across entries.

    Args:
        ipe_07_df: DataFrame from IPE_07 extraction containing customer ledger entries
                   Expected columns: 'Customer No_', 'Customer Name', 'Customer Posting Group'

    Returns:
        tuple: (bridge_amount, proof_df)
            - bridge_amount: Always 0 (this is an identification task, not a calculation)
            - proof_df: DataFrame with customers that have multiple posting groups,
                       including 'Customer No_', 'Customer Name', and all associated
                       'Customer Posting Group' values (comma-separated)
    """
    # Return empty result if input is empty or None
    if ipe_07_df is None or ipe_07_df.empty:
        return 0.0, pd.DataFrame(
            columns=["Customer No_", "Customer Name", "Customer Posting Group"]
        )

    # Validate required columns exist
    required_cols = ["Customer No_", "Customer Name", "Customer Posting Group"]
    missing_cols = [col for col in required_cols if col not in ipe_07_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Group by Customer No_ and get unique posting groups
    customer_groups = (
        ipe_07_df.groupby("Customer No_")
        .agg(
            {
                "Customer Name": "first",  # Get the first name (they should all be the same)
                "Customer Posting Group": lambda x: list(x.dropna().unique()),
            }
        )
        .reset_index()
    )

    # Filter to only customers with more than one unique posting group
    problem_customers = customer_groups[
        customer_groups["Customer Posting Group"].apply(lambda x: len(x) > 1)
    ].copy()

    # Convert list of posting groups to comma-separated string for output
    if not problem_customers.empty:
        problem_customers["Customer Posting Group"] = problem_customers[
            "Customer Posting Group"
        ].apply(lambda x: ", ".join(sorted(str(pg) for pg in x)))

    # Bridge amount is always 0 for identification tasks
    bridge_amount = 0.0

    return bridge_amount, problem_customers


def calculate_vtc_adjustment(
    ipe_08_df: Optional[pd.DataFrame],
    categorized_cr_03_df: Optional[pd.DataFrame],
    fx_converter: Optional["FXConverter"] = None,
) -> tuple[float, pd.DataFrame]:
    """Calculate VTC (Voucher to Cash) refund reconciliation adjustment.

    This function identifies "canceled refund vouchers" from BOB (IPE_08) that do not
    have a corresponding cancellation entry in NAV (CR_03).

    Args:
        ipe_08_df: DataFrame containing voucher liabilities from BOB with columns:
            - id: Voucher ID
            - business_use_formatted: Business use type
            - is_valid: Validity status
            - is_active: Active status (0 for canceled)
            - Remaining Amount: Amount for the voucher
            - ID_COMPANY: Company code (required if fx_converter is provided)
        categorized_cr_03_df: DataFrame containing categorized NAV GL entries with columns:
            - [Voucher No_]: Voucher number from NAV
            - bridge_category: Category of the entry (e.g., 'Cancellation', 'VTC Manual')
        fx_converter: Optional FXConverter instance for USD conversion.
                     If None, returns amounts in local currency.

    Returns:
        tuple: (adjustment_amount_usd, proof_df) where:
            - adjustment_amount_usd: Sum of unmatched voucher amounts in USD
            - proof_df: DataFrame of unmatched vouchers with Amount_USD column
    """
    # Handle empty inputs
    if ipe_08_df is None or ipe_08_df.empty:
        return 0.0, pd.DataFrame()

    # Filter source vouchers (BOB): canceled refund vouchers
    source_vouchers_df = ipe_08_df[
        (ipe_08_df["business_use_formatted"] == "refund")
        & (ipe_08_df["Is_Valid"] == "valid")
        & (ipe_08_df["is_active"] == 0)
    ].copy()

    if categorized_cr_03_df is None or categorized_cr_03_df.empty:
        # All source vouchers are unmatched
        unmatched_df = source_vouchers_df.copy()

        # Calculate USD amounts if FXConverter is provided
        if fx_converter is not None:
            # Check if ID_COMPANY column exists
            company_col = None
            for col in ["ID_COMPANY", "id_company", "Company_Code"]:
                if col in unmatched_df.columns:
                    company_col = col
                    break

            if company_col is not None:
                # Convert to USD
                unmatched_df["Amount_USD"] = fx_converter.convert_series_to_usd(
                    unmatched_df["remaining_amount"], unmatched_df[company_col]
                )
                adjustment_amount = unmatched_df["Amount_USD"].sum()
            else:
                # No company column, cannot convert - use LCY
                adjustment_amount = unmatched_df["remaining_amount"].sum()
        else:
            # No FX converter provided - use local currency
            adjustment_amount = unmatched_df["remaining_amount"].sum()

        return adjustment_amount, unmatched_df

    # Filter target entries (NAV): cancellation categories
    # Include entries where bridge_category starts with 'Cancellation' or equals 'VTC'/'VTC Manual'
    # Convert to string once for efficiency
    bridge_categories = categorized_cr_03_df["bridge_category"].astype(str)
    target_entries_df = categorized_cr_03_df[
        bridge_categories.str.startswith("Cancellation")
        | (bridge_categories == "VTC Manual")
        | (bridge_categories == "VTC")
    ].copy()

    # Perform left anti-join: find vouchers in source that are NOT in target
    # Left anti-join means: keep rows from left where the join key does NOT match any row in right
    unmatched_df = source_vouchers_df[
        ~source_vouchers_df["id"].isin(target_entries_df["Voucher No_"])
    ].copy()

    # Calculate USD amounts if FXConverter is provided
    if fx_converter is not None:
        # Check if ID_COMPANY column exists
        company_col = None
        for col in ["ID_COMPANY", "id_company", "Company_Code"]:
            if col in unmatched_df.columns:
                company_col = col
                break

        if company_col is not None:
            # Convert to USD
            unmatched_df["Amount_USD"] = fx_converter.convert_series_to_usd(
                unmatched_df["remaining_amount"], unmatched_df[company_col]
            )
            adjustment_amount = unmatched_df["Amount_USD"].sum()
        else:
            # No company column, cannot convert - use LCY
            adjustment_amount = unmatched_df["remaining_amount"].sum()
    else:
        # No FX converter provided - use local currency
        adjustment_amount = unmatched_df["remaining_amount"].sum()

    return adjustment_amount, unmatched_df


def _categorize_nav_vouchers(
    cr_03_df: pd.DataFrame,
    ipe_08_df: Optional[pd.DataFrame] = None,
    doc_voucher_usage_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Categorize NAV General Ledger entries (CR_03) for GL account 18412
    according to the full voucher accrual analysis business rules.

    Adds 'bridge_category', 'voucher_type', and 'Integration_Type' columns.

    Categories:
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

    Returns:
        DataFrame with added 'bridge_category', 'voucher_type', and 'Integration_Type' columns
    """
    if cr_03_df is None or cr_03_df.empty:
        result = cr_03_df.copy() if cr_03_df is not None else pd.DataFrame()
        result["bridge_category"] = None
        result["voucher_type"] = None
        result["Integration_Type"] = None
        return result

    out = cr_03_df.copy()
    out["bridge_category"] = None
    out["voucher_type"] = None
    out["Integration_Type"] = None

    # Normalize column names for easier access (handle variations)
    col_map = {}
    for col in out.columns:
        col_lower = col.lower().strip()
        if "chart of accounts" in col_lower or col_lower == "gl account":
            col_map["gl_account"] = col
        elif col_lower in ["amount", "amt"]:
            col_map["amount"] = col
        elif "bal" in col_lower and "account type" in col_lower:
            col_map["bal_account_type"] = col
        elif col_lower in ["user id", "user_id", "userid"]:
            col_map["user_id"] = col
        elif "document description" in col_lower or col_lower in [
            "description",
            "desc",
        ]:
            col_map["description"] = col
        elif "document type" in col_lower or col_lower == "doc_type":
            col_map["doc_type"] = col
        elif col_lower in ["document no", "document no_", "doc_no"]:
            col_map["doc_no"] = col
        elif col_lower in ["voucher no_", "[voucher no_]", "voucher_no"]:
            col_map["voucher_no"] = col
        elif col_lower in ["comment", "comments"]:
            col_map["comment"] = col

    # Check if we have the required columns
    if "gl_account" not in col_map or "amount" not in col_map:
        # Cannot categorize without at least GL account and amount
        return out

    gl_col = col_map["gl_account"]
    amt_col = col_map["amount"]
    bal_type_col = col_map.get("bal_account_type")
    user_col = col_map.get("user_id")
    desc_col = col_map.get("description")
    doc_type_col = col_map.get("doc_type")
    doc_no_col = col_map.get("doc_no")
    voucher_no_col = col_map.get("voucher_no")
    comment_col = col_map.get("comment")

    # Country codes for Store Credit issuance detection
    COUNTRY_CODES = ["NG", "EG", "KE", "GH", "CI", "MA", "TN", "ZA", "UG", "SN"]

    # Step 1: Determine Integration_Type for all rows
    # Relaxed logic: If User ID contains "NAV" AND ("BATCH" OR "SRVC"), treat as Integration
    for idx, row in out.iterrows():
        user_id = (
            str(row[user_col]).strip().upper()
            if user_col and pd.notna(row[user_col])
            else ""
        )
        # Check if user_id matches integration pattern: contains NAV AND (BATCH OR SRVC)
        is_integration = "NAV" in user_id and ("BATCH" in user_id or "SRVC" in user_id)
        out.at[idx, "Integration_Type"] = "Integration" if is_integration else "Manual"

    # Apply categorization rules in order for each row
    for idx, row in out.iterrows():
        # Skip if not GL account 18412
        gl_account = str(row[gl_col]).strip() if pd.notna(row[gl_col]) else ""
        if gl_account != "18412":
            continue

        amount = row[amt_col] if pd.notna(row[amt_col]) else 0
        integration_type = out.at[idx, "Integration_Type"]
        description = (
            str(row[desc_col]).upper().strip()
            if desc_col and pd.notna(row[desc_col])
            else ""
        )
        description_lower = description.lower()
        doc_type = (
            str(row[doc_type_col]).lower().strip()
            if doc_type_col and pd.notna(row[doc_type_col])
            else ""
        )
        doc_no = (
            str(row[doc_no_col]).strip().upper()
            if doc_no_col and pd.notna(row[doc_no_col])
            else ""
        )
        voucher_no = (
            str(row[voucher_no_col]).strip()
            if voucher_no_col and pd.notna(row[voucher_no_col])
            else ""
        )
        comment = (
            str(row[comment_col]).upper().strip()
            if comment_col and pd.notna(row[comment_col])
            else ""
        )
        bal_account_type = (
            str(row[bal_type_col]).upper().strip()
            if bal_type_col and pd.notna(row[bal_type_col])
            else ""
        )

        # =====================================================
        # Step 2 (Priority): VTC Manual via Bank Account
        # Manual payments to customers (VTC) appear as negative amounts
        # =====================================================
        if (
            integration_type == "Manual"
            and amount != 0
            and bal_account_type == "BANK ACCOUNT"
        ):
            out.at[idx, "bridge_category"] = "VTC"
            out.at[idx, "voucher_type"] = "Refund"
            continue

        # =====================================================
        # Step 2: Issuance (Negative Amounts)
        # =====================================================
        if amount < 0:
            if integration_type == "Integration":
                # Integrated Issuance rules
                # Check for Refund: match "REFUND", "RF_", or "RF " patterns
                if (
                    "REFUND" in description
                    or "RF_" in description
                    or "RF " in description
                ):
                    out.at[idx, "bridge_category"] = "Issuance - Refund"
                    out.at[idx, "voucher_type"] = "Refund"
                elif "COMMERCIAL GESTURE" in description:
                    out.at[idx, "bridge_category"] = "Issuance - Apology"
                    out.at[idx, "voucher_type"] = "Apology"
                elif "PYT_PF" in description or "PYT_" in description:
                    out.at[idx, "bridge_category"] = "Issuance - JForce"
                    out.at[idx, "voucher_type"] = "JForce"
                else:
                    # Fallback: Generic integrated issuance
                    out.at[idx, "bridge_category"] = "Issuance"
            else:
                # Manual Issuance rules
                # Check if Document No starts with Country Code
                is_store_credit = any(doc_no.startswith(cc) for cc in COUNTRY_CODES)
                if is_store_credit:
                    out.at[idx, "bridge_category"] = "Issuance - Store Credit"
                    out.at[idx, "voucher_type"] = "Store Credit"
                elif (
                    "REFUND" in description
                    or "RFN" in description
                    or "RF_" in description
                    or "RF " in description
                ):
                    out.at[idx, "bridge_category"] = "Issuance - Refund"
                    out.at[idx, "voucher_type"] = "Refund"
                elif (
                    "COMMERCIAL" in description
                    or "CXP" in description
                    or "APOLOGY" in description
                ):
                    out.at[idx, "bridge_category"] = "Issuance - Apology"
                    out.at[idx, "voucher_type"] = "Apology"
                elif "PYT_PF" in description or "PYT_" in description:
                    out.at[idx, "bridge_category"] = "Issuance - JForce"
                    out.at[idx, "voucher_type"] = "JForce"
                else:
                    # Generic issuance
                    out.at[idx, "bridge_category"] = "Issuance"
            continue

        # =====================================================
        # Step 3: Usage (Positive Amounts + Integrated)
        # =====================================================
        if amount > 0 and integration_type == "Integration":
            # Cancellation Logic: Voucher Accrual description
            if "VOUCHER ACCRUAL" in description:
                out.at[idx, "bridge_category"] = "Cancellation - Apology"
                out.at[idx, "voucher_type"] = "Apology"
            else:
                # Usage category
                out.at[idx, "bridge_category"] = "Usage"
                # Lookup voucher type from IPE_08 or doc_voucher_usage_df
                voucher_type = _lookup_voucher_type(
                    voucher_no, doc_no, ipe_08_df, doc_voucher_usage_df
                )
                if voucher_type:
                    out.at[idx, "voucher_type"] = voucher_type
            continue

        # =====================================================
        # Step 4: Expired (Manual + Positive + 'EXPR')
        # =====================================================
        if amount > 0 and integration_type == "Manual" and "EXPR" in description:
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
                out.at[idx, "bridge_category"] = "Expired"
            continue

        # =====================================================
        # Step 5: VTC (Manual + Positive + 'RND'/'PYT')
        # =====================================================
        if amount > 0 and integration_type == "Manual":
            is_vtc = False
            if "MANUAL RND" in description:
                is_vtc = True
            elif "PYT_" in description and "GTB" in comment:
                is_vtc = True

            if is_vtc:
                out.at[idx, "bridge_category"] = "VTC"
                out.at[idx, "voucher_type"] = "Refund"
                continue

        # =====================================================
        # Step 6: Manual Cancellation (Manual + Positive + Credit Memo)
        # =====================================================
        if amount > 0 and integration_type == "Manual" and doc_type == "credit memo":
            out.at[idx, "bridge_category"] = "Cancellation - Store Credit"
            out.at[idx, "voucher_type"] = "Store Credit"
            continue

        # =====================================================
        # Step 7: Remaining Manual Usage (Nigeria Exception)
        # =====================================================
        if amount > 0 and integration_type == "Manual":
            if "ITEMPRICECREDIT" in description:
                out.at[idx, "bridge_category"] = "Usage"
                # Lookup type via Voucher No
                voucher_type = _lookup_voucher_type(
                    voucher_no, doc_no, ipe_08_df, doc_voucher_usage_df
                )
                if voucher_type:
                    out.at[idx, "voucher_type"] = voucher_type
                continue

    return out


def _lookup_voucher_type(
    voucher_no: str,
    doc_no: str,
    ipe_08_df: Optional[pd.DataFrame],
    doc_voucher_usage_df: Optional[pd.DataFrame],
) -> Optional[str]:
    """
    Lookup voucher type from IPE_08 or doc_voucher_usage_df.

    First tries to match by voucher_no ('id' column in TV DataFrames).
    If voucher_no is missing/empty, falls back to matching doc_no against 'Transaction_No'.

    Args:
        voucher_no: The voucher number from NAV ([Voucher No_])
        doc_no: The document number from NAV (Document No)
        ipe_08_df: IPE_08 DataFrame with 'id' and 'business_use' columns
        doc_voucher_usage_df: Usage TV DataFrame with 'id', 'business_use', 'Transaction_No' columns

    Returns:
        The voucher type (business_use) if found, None otherwise
    """
    # Try IPE_08 first
    if ipe_08_df is not None and not ipe_08_df.empty:
        # Try matching by voucher_no
        if voucher_no:
            match = ipe_08_df[ipe_08_df["id"].astype(str) == voucher_no]
            if not match.empty and "business_use" in match.columns:
                return str(match.iloc[0]["business_use"])

    # Try doc_voucher_usage_df
    if doc_voucher_usage_df is not None and not doc_voucher_usage_df.empty:
        # Try matching by voucher_no
        if voucher_no:
            match = doc_voucher_usage_df[
                doc_voucher_usage_df["id"].astype(str) == voucher_no
            ]
            if not match.empty and "business_use" in match.columns:
                return str(match.iloc[0]["business_use"])

        # Fallback: Try matching by doc_no against Transaction_No
        if doc_no and "Transaction_No" in doc_voucher_usage_df.columns:
            match = doc_voucher_usage_df[
                doc_voucher_usage_df["Transaction_No"].astype(str) == doc_no
            ]
            if not match.empty and "business_use" in match.columns:
                return str(match.iloc[0]["business_use"])

    return None


def calculate_timing_difference_bridge(
    ipe_08_df: pd.DataFrame,
    cutoff_date: str,
    fx_converter: Optional["FXConverter"] = None,
) -> Tuple[float, pd.DataFrame]:
    """
    Calculates the Timing Difference Bridge using "Month N vs N+1" cut-off logic.

    Logic (Validated Oct 2025):
    Identifies vouchers that were ordered in the reconciliation month (N) but not
    finalized (delivered or canceled) by the cutoff date, meaning they remain pending
    or late in the following month (N+1).

    Business Rules:
    1. Filter Scope: business_use in NON_MARKETING_USES
    2. Filter "Used in N": Order_Creation_Date within reconciliation month
    3. Filter "Pending/Late in N+1":
       - Order_Delivery_Date > cutoff_date OR Order_Delivery_Date is NaT (Null)
       - AND Order_Cancellation_Date > cutoff_date OR Order_Cancellation_Date is NaT (Null)
       (The order was placed in time, but not finalized by the closing date)

    Args:
        ipe_08_df: DataFrame from IPE_08 with columns:
            - id: Voucher ID
            - business_use: Business use type
            - Order_Creation_Date: Date when order was created
            - Order_Delivery_Date: Date when order was delivered (or NaT if not delivered)
            - Order_Cancellation_Date: Date when order was canceled (or NaT if not canceled)
            - remaining_amount: Amount for the voucher
            - ID_COMPANY: Company code (required if fx_converter is provided)
        cutoff_date: Reconciliation cutoff date (YYYY-MM-DD), typically last day of month N
        fx_converter: Optional FXConverter instance for USD conversion.
                     If None, returns amounts in local currency.

    Returns:
        tuple: (bridge_amount, proof_df) where:
            - bridge_amount: Sum of remaining_amount (in USD if fx_converter provided)
            - proof_df: DataFrame with vouchers meeting the criteria and Amount_USD column
    """
    # Handle empty or None input
    if ipe_08_df is None or ipe_08_df.empty:
        return 0.0, pd.DataFrame()

    # 1. Define Non-Marketing Types
    NON_MARKETING_USES = [
        "apology_v2",
        "jforce",
        "refund",
        "store_credit",
        "Jpay store_credit",
    ]

    # 2. Prepare cutoff date and reconciliation month boundaries
    cutoff_dt = pd.to_datetime(cutoff_date)
    # Start of reconciliation month
    recon_month_start = cutoff_dt.replace(day=1)
    # End of reconciliation month (should be cutoff_date in most cases)
    recon_month_end = cutoff_dt

    # 3. Work with a copy and convert date columns to datetime
    df = ipe_08_df.copy()
    df["Order_Creation_Date"] = pd.to_datetime(
        df["Order_Creation_Date"], errors="coerce"
    )
    df["Order_Delivery_Date"] = pd.to_datetime(
        df["Order_Delivery_Date"], errors="coerce"
    )
    df["Order_Cancellation_Date"] = pd.to_datetime(
        df["Order_Cancellation_Date"], errors="coerce"
    )

    # 4. Apply filters per business rules

    # Filter Scope: Non-marketing uses only
    filter_scope = df["business_use"].isin(NON_MARKETING_USES)

    # Filter "Used in N": Order created within the reconciliation month
    filter_used_in_n = (df["Order_Creation_Date"] >= recon_month_start) & (
        df["Order_Creation_Date"] <= recon_month_end
    )

    # Filter "Pending/Late in N+1": Order not finalized by cutoff date
    # Delivery date is after cutoff OR null (not delivered)
    delivery_pending = (df["Order_Delivery_Date"] > cutoff_dt) | (
        df["Order_Delivery_Date"].isna()
    )

    # Cancellation date is after cutoff OR null (not canceled)
    cancellation_pending = (df["Order_Cancellation_Date"] > cutoff_dt) | (
        df["Order_Cancellation_Date"].isna()
    )

    # Both delivery and cancellation must be pending
    filter_pending_in_n_plus_1 = delivery_pending & cancellation_pending

    # Combine all filters
    filtered_df = df[
        filter_scope & filter_used_in_n & filter_pending_in_n_plus_1
    ].copy()

    # 5. Calculate bridge amount
    if filtered_df.empty:
        return 0.0, pd.DataFrame()

    # Calculate USD amounts if FXConverter is provided
    if fx_converter is not None:
        # Check if ID_COMPANY column exists
        company_col = None
        for col in ["ID_COMPANY", "id_company", "Company_Code"]:
            if col in filtered_df.columns:
                company_col = col
                break

        if company_col is not None:
            # Convert to USD
            filtered_df["Amount_USD"] = fx_converter.convert_series_to_usd(
                filtered_df["remaining_amount"], filtered_df[company_col]
            )
            bridge_amount = filtered_df["Amount_USD"].sum()
        else:
            # No company column, cannot convert - use LCY
            bridge_amount = filtered_df["remaining_amount"].sum()
    else:
        # No FX converter provided - use local currency
        bridge_amount = filtered_df["remaining_amount"].sum()

    # 6. Prepare proof DataFrame with relevant columns
    cols_to_keep = [
        "id",
        "business_use",
        "Order_Creation_Date",
        "Order_Delivery_Date",
        "Order_Cancellation_Date",
        "remaining_amount",
    ]

    # Add Amount_USD if it exists
    if "Amount_USD" in filtered_df.columns:
        cols_to_keep.append("Amount_USD")

    # Keep only columns that exist in the dataframe
    proof_df = filtered_df[[c for c in cols_to_keep if c in filtered_df.columns]]

    return bridge_amount, proof_df


__all__ = [
    "classify_bridges",
    "calculate_customer_posting_group_bridge",
    "calculate_vtc_adjustment",
    "_categorize_nav_vouchers",
    "_lookup_voucher_type",
    "calculate_timing_difference_bridge",
]
