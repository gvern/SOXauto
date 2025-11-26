"""
Rule-based classifier for PG-1 reconciliation bridges.

Takes input DataFrames (e.g., IPE_31 open items, IPE_10 prepayments) and applies
BridgeRule triggers to produce a standardized classification with GL expectations.
"""

from __future__ import annotations
from typing import List, Optional, Tuple
import pandas as pd

from src.bridges.catalog import BridgeRule


def _filter_ipe08_scope(ipe_08_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter IPE_08 DataFrame to include only Non-Marketing voucher types.

    This helper ensures consistent filtering across all bridge calculations
    that use IPE_08 data. Only vouchers with business_use in the Non-Marketing
    category are included.

    Args:
        ipe_08_df: DataFrame from IPE_08 extraction containing voucher data
                   Expected columns: 'business_use' and date columns

    Returns:
        DataFrame filtered to Non-Marketing vouchers with dates converted to datetime
    """
    if ipe_08_df is None or ipe_08_df.empty:
        return ipe_08_df.copy() if ipe_08_df is not None else pd.DataFrame()

    # Define Non-Marketing voucher types
    NON_MARKETING_USES = [
        "apology_v2",
        "jforce",
        "refund",
        "store_credit",
        "Jpay store_credit",
    ]

    # Work with a copy
    df = ipe_08_df.copy()

    # Filter for Non-Marketing types
    # Check for both business_use and business_use_formatted for backward compatibility
    business_use_col = None
    if "business_use" in df.columns:
        business_use_col = "business_use"
    elif "business_use_formatted" in df.columns:
        business_use_col = "business_use_formatted"
    
    if business_use_col:
        df = df[df[business_use_col].isin(NON_MARKETING_USES)].copy()

    # Convert date columns to datetime if they exist
    date_columns = [
        "Order_Creation_Date",
        "Order_Delivery_Date",
        "Order_Cancellation_Date",
    ]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


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
            - business_use: Business use type
            - is_valid: Validity status (or Is_Valid)
            - is_active: Active status (0 for canceled)
            - remaining_amount: Amount for the voucher
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

    # Step 1: Apply Non-Marketing filter using helper
    filtered_ipe_08 = _filter_ipe08_scope(ipe_08_df)

    if filtered_ipe_08.empty:
        return 0.0, pd.DataFrame()

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
    
    source_vouchers_df = filtered_ipe_08[filter_condition].copy()

    # Find the amount column (handle various naming conventions)
    amount_col = None
    for col in ["remaining_amount", "Remaining Amount", "Remaining_Amount"]:
        if col in source_vouchers_df.columns:
            amount_col = col
            break
    
    if amount_col is None:
        # No amount column found, return empty result
        return 0.0, pd.DataFrame()

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
                    unmatched_df[amount_col], unmatched_df[company_col]
                )
                adjustment_amount = unmatched_df["Amount_USD"].sum()
            else:
                # No company column, cannot convert - use LCY
                adjustment_amount = unmatched_df[amount_col].sum()
        else:
            # No FX converter provided - use local currency
            adjustment_amount = unmatched_df[amount_col].sum()

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
                unmatched_df[amount_col], unmatched_df[company_col]
            )
            adjustment_amount = unmatched_df["Amount_USD"].sum()
        else:
            # No company column, cannot convert - use LCY
            adjustment_amount = unmatched_df[amount_col].sum()
    else:
        # No FX converter provided - use local currency
        adjustment_amount = unmatched_df[amount_col].sum()

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
    jdash_df: pd.DataFrame,
    ipe_08_df: pd.DataFrame,
    cutoff_date: str,
) -> Tuple[float, pd.DataFrame]:
    """
    Calculates the Timing Difference Bridge by comparing Ordered Amount (Jdash)
    against Delivered Amount (IPE_08 - Issuance).

    Logic (Validated Manual Process - Finance Team):
    Compares the Ordered Amount from Jdash export against the Delivered Amount
    from the Issuance IPE to identify timing differences (pending/timing difference).

    Business Rules:
    1. Filter Source A (IPE_08 - Issuance):
       - Filter vouchers created within 1 year before cutoff_date
       - Filter for is_active == 0 (Inactive)
       - Filter for business_use in NON_MARKETING_USES
    2. Prepare Source B (Jdash):
       - Aggregate by Voucher Id summing Amount Used
    3. Reconciliation Logic:
       - Left Join of Filtered IPE_08 (Left) with Jdash (Right) on Voucher ID
       - Fill missing Jdash amounts with 0
    4. Calculate Variance:
       - Variance = Jdash['Amount Used'] - IPE_08['TotalAmountUsed']
       - (Ordered Amount - Delivered Amount = Pending/Timing Difference)

    Args:
        jdash_df: DataFrame from Jdash export with columns:
            - Voucher Id: Voucher identifier
            - Amount Used: Amount ordered/used
        ipe_08_df: DataFrame from IPE_08 (Issuance) with columns:
            - id: Voucher ID
            - business_use: Business use type
            - is_active: Active status (0 for inactive)
            - TotalAmountUsed: Delivered amount
            - created_at: Creation date of voucher
        cutoff_date: Reconciliation cutoff date (YYYY-MM-DD)

    Returns:
        tuple: (variance_sum, proof_df) where:
            - variance_sum: Sum of variance (Jdash Amount - IPE_08 Amount)
            - proof_df: DataFrame with reconciliation details including variance
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

    # Convert cutoff_date to datetime
    cutoff_dt = pd.to_datetime(cutoff_date)
    # Calculate 1 year before cutoff
    one_year_before = cutoff_dt - pd.DateOffset(years=1)

    # Find the created_at column (handle various naming conventions)
    created_at_col = None
    for col in ["created_at", "Created_At", "creation_date", "Creation_Date"]:
        if col in df_ipe.columns:
            created_at_col = col
            break

    # Apply date filter if created_at column exists
    if created_at_col:
        df_ipe[created_at_col] = pd.to_datetime(df_ipe[created_at_col], errors="coerce")
        df_ipe = df_ipe[df_ipe[created_at_col] >= one_year_before].copy()

    # Filter for is_active == 0 (Inactive)
    if "is_active" in df_ipe.columns:
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
    ipe_amount_col = None
    for col in ["TotalAmountUsed", "total_amount_used", "Remaining Amount", "remaining_amount"]:
        if col in df_ipe.columns:
            ipe_amount_col = col
            break

    if ipe_amount_col is None:
        return 0.0, pd.DataFrame()

    # Step 2: Prepare Source B (Jdash) - Aggregate by Voucher Id summing Amount Used
    if jdash_df is None or jdash_df.empty:
        # If Jdash is empty, all IPE amounts are considered unmatched (variance = -IPE amount)
        df_ipe["Jdash_Amount_Used"] = 0.0
        df_ipe["Variance"] = df_ipe["Jdash_Amount_Used"] - df_ipe[ipe_amount_col]
        variance_sum = df_ipe["Variance"].sum()
        return variance_sum, df_ipe

    df_jdash = jdash_df.copy()

    # Find the Voucher Id column in Jdash (handle various naming conventions)
    jdash_voucher_col = None
    for col in ["Voucher Id", "Voucher_Id", "voucher_id", "VoucherId"]:
        if col in df_jdash.columns:
            jdash_voucher_col = col
            break

    # Find the Amount Used column in Jdash (handle various naming conventions)
    jdash_amount_col = None
    for col in ["Amount Used", "Amount_Used", "amount_used", "AmountUsed"]:
        if col in df_jdash.columns:
            jdash_amount_col = col
            break

    if jdash_voucher_col is None or jdash_amount_col is None:
        # Cannot perform reconciliation without proper columns
        return 0.0, pd.DataFrame()

    # Aggregate Jdash by Voucher Id summing Amount Used
    jdash_agg = df_jdash.groupby(jdash_voucher_col)[jdash_amount_col].sum().reset_index()
    jdash_agg.columns = ["Voucher_Id", "Jdash_Amount_Used"]

    # Step 3: Reconciliation Logic - Left Join of Filtered IPE_08 with Jdash on Voucher ID
    # Ensure 'id' column is string for proper joining
    df_ipe["id"] = df_ipe["id"].astype(str)
    jdash_agg["Voucher_Id"] = jdash_agg["Voucher_Id"].astype(str)

    # Perform left join
    merged_df = df_ipe.merge(
        jdash_agg,
        left_on="id",
        right_on="Voucher_Id",
        how="left"
    )

    # Fill missing Jdash amounts with 0
    merged_df["Jdash_Amount_Used"] = merged_df["Jdash_Amount_Used"].fillna(0.0)

    # Step 4: Calculate Variance = Jdash['Amount Used'] - IPE_08['TotalAmountUsed']
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
    "_filter_ipe08_scope",
    "classify_bridges",
    "calculate_customer_posting_group_bridge",
    "calculate_vtc_adjustment",
    "_categorize_nav_vouchers",
    "_lookup_voucher_type",
    "calculate_timing_difference_bridge",
]
