"""
Customer Posting Group Bridge calculation for PG-01 reconciliation.

Identifies customers with multiple posting groups for manual review.
"""

from typing import Tuple
import pandas as pd


def calculate_customer_posting_group_bridge(
    ipe_07_df: pd.DataFrame,
) -> Tuple[float, pd.DataFrame]:
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


__all__ = [
    "calculate_customer_posting_group_bridge",
]
