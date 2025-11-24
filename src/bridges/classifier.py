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
    ipe_08_df: Optional[pd.DataFrame], categorized_cr_03_df: Optional[pd.DataFrame]
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
        categorized_cr_03_df: DataFrame containing categorized NAV GL entries with columns:
            - [Voucher No_]: Voucher number from NAV
            - bridge_category: Category of the entry (e.g., 'Cancellation', 'VTC Manual')

    Returns:
        tuple: (adjustment_amount, proof_df) where:
            - adjustment_amount: Sum of unmatched voucher amounts
            - proof_df: DataFrame of unmatched vouchers (the adjustment items)
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
        adjustment_amount = source_vouchers_df["remaining_amount"].sum()
        return adjustment_amount, source_vouchers_df

    # Filter target entries (NAV): cancellation categories
    # Include entries where bridge_category starts with 'Cancellation' or equals 'VTC Manual'
    # Convert to string once for efficiency
    bridge_categories = categorized_cr_03_df["bridge_category"].astype(str)
    target_entries_df = categorized_cr_03_df[
        bridge_categories.str.startswith("Cancellation")
        | (bridge_categories == "VTC Manual")
    ].copy()

    # Perform left anti-join: find vouchers in source that are NOT in target
    # Left anti-join means: keep rows from left where the join key does NOT match any row in right
    unmatched_df = source_vouchers_df[
        ~source_vouchers_df["id"].isin(target_entries_df["Voucher No_"])
    ].copy()

    # Calculate adjustment amount
    adjustment_amount = unmatched_df["remaining_amount"].sum()

    return adjustment_amount, unmatched_df


def _categorize_nav_vouchers(cr_03_df: pd.DataFrame) -> pd.DataFrame:
    """
    Categorize NAV General Ledger entries (CR_03) for GL account 18412
    according to VTC Part 1 rules.

    Adds a 'bridge_category' column with one of the following values:
    - 'VTC Manual': Manual voucher transactions
    - 'Usage': Voucher usage transactions
    - 'Issuance - Refund': Voucher issuance for refunds
    - 'Issuance - Apology': Voucher issuance for apologies
    - 'Issuance - JForce': Voucher issuance for JForce
    - 'Cancellation - Store Credit': Voucher cancellation via store credit
    - 'Cancellation - Apology': Voucher cancellation for apologies
    - 'Expired': Expired vouchers
    - None: Transactions that don't match any rule

    Args:
        cr_03_df: DataFrame containing NAV GL entries with columns like:
                  'Chart of Accounts No_', 'Amount', 'Bal_ Account Type',
                  'User ID', 'Document Description', 'Document Type'

    Returns:
        DataFrame with added 'bridge_category' column
    """
    if cr_03_df is None or cr_03_df.empty:
        result = cr_03_df.copy() if cr_03_df is not None else pd.DataFrame()
        result["bridge_category"] = None
        return result

    out = cr_03_df.copy()
    out["bridge_category"] = None

    # Normalize column names for easier access (handle variations)
    # Map common column name variations to standard names
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

    # Apply categorization rules in order
    for idx, row in out.iterrows():
        # Skip if not GL account 18412
        if pd.notna(row[gl_col]) and str(row[gl_col]).strip() != "18412":
            continue

        amount = row[amt_col] if pd.notna(row[amt_col]) else 0
        user_id = (
            str(row[user_col]).strip() if user_col and pd.notna(row[user_col]) else ""
        )
        description = (
            str(row[desc_col]).lower().strip()
            if desc_col and pd.notna(row[desc_col])
            else ""
        )
        bal_type = (
            str(row[bal_type_col]).lower().strip()
            if bal_type_col and pd.notna(row[bal_type_col])
            else ""
        )
        doc_type = (
            str(row[doc_type_col]).lower().strip()
            if doc_type_col and pd.notna(row[doc_type_col])
            else ""
        )

        # Rule 1: VTC Manual
        if amount > 0 and bal_type == "bank account" and user_id != "NAV/13":
            out.at[idx, "bridge_category"] = "VTC Manual"

        # Rule 2: Usage
        elif (
            amount > 0
            and user_id == "NAV/13"
            and any(
                keyword in description
                for keyword in [
                    "item price credit",
                    "item shipping fees",
                    "voucher application",
                ]
            )
        ):
            out.at[idx, "bridge_category"] = "Usage"

        # Rule 3: Issuance (amount < 0)
        elif amount < 0:
            if "refund" in description or "rfn" in description:
                out.at[idx, "bridge_category"] = "Issuance - Refund"
            elif "commercial register" in description or "cxp" in description:
                out.at[idx, "bridge_category"] = "Issuance - Apology"
            elif "pyt_pf" in description:
                out.at[idx, "bridge_category"] = "Issuance - JForce"
            else:
                # Generic issuance if no sub-category matches
                out.at[idx, "bridge_category"] = "Issuance"

        # Rule 4: Cancellation (amount > 0)
        elif amount > 0 and doc_type == "credit memo" and user_id != "NAV/13":
            out.at[idx, "bridge_category"] = "Cancellation - Store Credit"
        elif amount > 0 and description == "voucher occur" and user_id == "NAV/13":
            out.at[idx, "bridge_category"] = "Cancellation - Apology"

        # Rule 5: Expired
        elif amount > 0 and description.startswith("exp") and user_id != "NAV/13":
            out.at[idx, "bridge_category"] = "Expired"

    return out


def calculate_timing_difference_bridge(
    jdash_df: pd.DataFrame, 
    ipe_08_df: pd.DataFrame, 
    cutoff_date: str
) -> Tuple[float, pd.DataFrame]:
    """
    Calculates the Timing Difference Bridge (Task 1) based on the "Issuance vs Jdash" logic.
    
    Logic (Validated Nov 2025):
    1. Source A (IPE_08 - Issuance): 
       - Filter for Non-marketing, Inactive, Created in last 12 months.
       - Represents the "Target" usage according to BOB Issuance history.
    2. Source B (Jdash - Usage):
       - Represents the actual usage in the period (filtered at export time).
    3. Reconciliation:
       - Left Join A -> B on Voucher ID.
       - Variance = (A.TotalAmountUsed) - (B.Amount Used).
       - Positive variance means BOB Issuance sees more usage than Jdash report for this period.
    """
    # 1. Define Non-Marketing Types
    NON_MARKETING_USES = [
        'apology_v2', 'jforce', 'refund', 'store_credit', 'Jpay store_credit'
    ]

    # 2. Prepare Dates
    recon_date = pd.to_datetime(cutoff_date)
    start_date_1yr = recon_date - pd.DateOffset(years=1)
    
    # 3. Filter IPE_08 (The "File A" - Issuance)
    # Ensure dates are datetime
    ipe_08_df = ipe_08_df.copy() # Avoid SettingWithCopyWarning
    ipe_08_df['created_at'] = pd.to_datetime(ipe_08_df['created_at'])
    
    # Apply filters per business rules:
    # - Voucher Type: Non-marketing only
    # - Status: Inactive (fully used/expired)
    # - Creation Date: Within last 12 months
    filtered_ipe_08 = ipe_08_df[
        (ipe_08_df['business_use'].isin(NON_MARKETING_USES)) &
        (ipe_08_df['is_active'] == 0) &
        (ipe_08_df['created_at'] >= start_date_1yr) & 
        (ipe_08_df['created_at'] <= recon_date)
    ].copy()

    # 4. Prepare Jdash (The "File B" - Usage)
    # Aggregate by Voucher Id to handle potential multiple usage lines
    # Note: Jdash export is already filtered for the control period.
    jdash_agg = jdash_df.groupby('Voucher Id')['Amount Used'].sum().reset_index()
    
    # 5. Merge (Left Join: Focus on Issued Vouchers from File A)
    # ID mapping: IPE_08 'id' == Jdash 'Voucher Id'
    filtered_ipe_08['id'] = filtered_ipe_08['id'].astype(str)
    jdash_agg['Voucher Id'] = jdash_agg['Voucher Id'].astype(str)
    
    merged_df = pd.merge(
        filtered_ipe_08, 
        jdash_agg, 
        left_on='id', 
        right_on='Voucher Id', 
        how='left'
    )
    
    # Fill NaNs for Jdash amount (if not found in Jdash, usage for this period is 0)
    merged_df['Amount Used'] = merged_df['Amount Used'].fillna(0.0)
    
    # 6. Calculate Variance (Timing Difference)
    # Logic: Difference between Total Issuance Usage and Jdash Period Usage
    merged_df['variance'] = merged_df['TotalAmountUsed'] - merged_df['Amount Used']
    
    # Filter for meaningful variances (> 0.01 to handle float precision)
    proof_df = merged_df[abs(merged_df['variance']) > 0.01].copy()
    
    # Select relevant columns for evidence output
    cols_to_keep = [
        'id', 'business_use', 'created_at', 'TotalAmountUsed', 'Amount Used', 'variance'
    ]
    # Keep only columns that exist in the dataframe
    proof_df = proof_df[[c for c in cols_to_keep if c in proof_df.columns]]
    
    bridge_amount = proof_df['variance'].sum()
    
    return bridge_amount, proof_df

def calculate_integration_error_adjustment(
    ipe_rec_errors_df: pd.DataFrame,
) -> tuple[float, pd.DataFrame]:
    """
    Calculate integration error adjustments for reconciliation (Task 3).

    This function processes integration errors from the IPE_REC_ERRORS query,
    which consolidates 36 source tables into a standard format. It filters for
    actual errors, maps them to the correct GL Account based on business rules,
    and calculates the total adjustment per account.

    Args:
        ipe_rec_errors_df: DataFrame from IPE_REC_ERRORS query containing:
            - Source_System: Name of the source table/system
            - Amount: Transaction amount
            - Integration_Status: Status of the integration (Posted, Integrated, Error, etc.)
            - Transaction_ID: (optional) Unique transaction identifier

    Returns:
        tuple: (adjustment_amount, proof_df)
            - adjustment_amount: Total sum of all error amounts
            - proof_df: DataFrame containing error transactions with columns:
                       ['Source_System', 'Amount', 'Target_GL'] and optionally
                       'Transaction_ID' (if present in input)
    """
    # Define the mapping from Source_System to GL Account
    SOURCE_TO_GL_MAP = {
        # GL 13023 (Accrued MPL Revenue)
        "SC Account Statement": "13023",
        "Seller Account Statements": "13023",
        # GL 18412 (Voucher Accrual)
        "JForce Payouts": "18412",
        "Refunds": "18412",
        # GL 18314 (MPL Vendor Liability)
        "Prepaid Deliveries": "18314",
        # GL 13012 (PSP / Collection)
        "Cash Deposits": "13012",
        "Cash Deposit Cancel": "13012",
        "Payment Reconciles": "13012",
    }

    # Handle empty inputs
    if ipe_rec_errors_df is None or ipe_rec_errors_df.empty:
        return 0.0, pd.DataFrame(
            columns=["Source_System", "Transaction_ID", "Amount", "Target_GL"]
        )

    # Validate required columns exist
    required_cols = ["Source_System", "Amount", "Integration_Status"]
    missing_cols = [
        col for col in required_cols if col not in ipe_rec_errors_df.columns
    ]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Filter for actual errors (not Posted or Integrated)
    errors_df = ipe_rec_errors_df[
        ~ipe_rec_errors_df["Integration_Status"].isin(["Posted", "Integrated"])
    ].copy()

    if errors_df.empty:
        return 0.0, pd.DataFrame(
            columns=["Source_System", "Transaction_ID", "Amount", "Target_GL"]
        )

    # Map Source_System to Target_GL
    errors_df["Target_GL"] = errors_df["Source_System"].map(SOURCE_TO_GL_MAP)

    # Filter out unmapped sources (Unclassified)
    mapped_errors_df = errors_df[errors_df["Target_GL"].notna()].copy()

    if mapped_errors_df.empty:
        return 0.0, pd.DataFrame(
            columns=["Source_System", "Transaction_ID", "Amount", "Target_GL"]
        )

    # Calculate total adjustment amount
    adjustment_amount = mapped_errors_df["Amount"].sum()

    # Prepare proof DataFrame
    proof_columns = ["Source_System", "Amount", "Target_GL"]
    if "Transaction_ID" in mapped_errors_df.columns:
        proof_columns.insert(1, "Transaction_ID")

    proof_df = mapped_errors_df[proof_columns].copy()

    return adjustment_amount, proof_df


__all__ = [
    "classify_bridges",
    "calculate_customer_posting_group_bridge",
    "calculate_vtc_adjustment",
    "_categorize_nav_vouchers",
    "calculate_timing_difference_bridge",
    "calculate_integration_error_adjustment",
]
