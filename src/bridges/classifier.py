"""
Rule-based classifier for PG-1 reconciliation bridges.

Takes input DataFrames (e.g., IPE_31 open items, IPE_10 prepayments) and applies
BridgeRule triggers to produce a standardized classification with GL expectations.
"""

from __future__ import annotations
from typing import List
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


__all__ = ["classify_bridges", "calculate_customer_posting_group_bridge"]
