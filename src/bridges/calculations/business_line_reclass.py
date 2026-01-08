"""
Business Line Reclass Bridge calculation for PG-01 reconciliation.

This module implements CLE (Customer Ledger Entries) pivot logic to identify
business line reclassification candidates. Business line reclass is a NAV-only
reclassification of balances between business lines within NAV (not a cross-system
variance driver).

The module analyzes Customer Ledger Entries from NAV for the control period and
identifies customers with balances across multiple business lines. For such customers,
it generates a candidate reclass table for review by Accounting Excellence and
validation by local finance.

Key Concepts:
    - CLE-based pivot: Group by customer and business_line_code
    - Multi-business line detection: Identify customers with > 1 business line
    - Candidate generation: Output review-friendly table with proposed reclass
    - Heuristic selection: Largest absolute balance determines proposed primary BL

Business Logic:
    1. Download Customer Ledger Entries (CLE) from NAV for the period
    2. Pivot CLE per customer and business_line_code
    3. If a single customer has balances across multiple business lines:
       - Identify "incorrect balances" to reclass into "correct business line"
       - Output candidate table for review (final decision is manual)

Data Source:
    - Input: IPE_07 (NAV Customer Ledger Entries) with business_line_code
    - Extracted using FINREC database (NAV source)
"""

from typing import Dict, Any, Optional
import pandas as pd
import logging

from src.utils.pandas_utils import ensure_required_numeric
from src.utils.date_utils import normalize_date

logger = logging.getLogger(__name__)


def identify_business_line_reclass_candidates(
    cle_df: pd.DataFrame,
    cutoff_date: str,
    *,
    customer_id_col: str = "customer_id",
    business_line_col: str = "business_line_code",
    amount_col: str = "amount_lcy",
    min_abs_amount: float = 0.01,
) -> pd.DataFrame:
    """
    Identify business line reclassification candidates from Customer Ledger Entries.

    This function analyzes CLE data to find customers with balances across multiple
    business lines. For such customers, it generates a candidate table showing:
    - Current business line allocation
    - Proposed primary business line (heuristic: largest absolute balance)
    - Proposed reclass amounts
    - Review flags

    The output is review-driven. Final decision on "correct" business line requires
    Accounting Excellence review and local finance confirmation.

    Args:
        cle_df: DataFrame containing Customer Ledger Entries from NAV.
                Must contain at minimum: customer_id, business_line_code, amount_lcy
        cutoff_date: Cutoff date for the control period (YYYY-MM-DD format).
                     Used for metadata and potential filtering.
        customer_id_col: Name of customer ID column (default: "customer_id")
        business_line_col: Name of business line code column (default: "business_line_code")
        amount_col: Name of amount column in local currency (default: "amount_lcy")
        min_abs_amount: Minimum absolute balance to consider (default: 0.01).
                       Balances below this threshold are ignored to reduce noise.

    Returns:
        pd.DataFrame: Candidate reclass table with columns:
            - customer_id: Customer identifier
            - business_line_code: Current business line code
            - balance_lcy: Balance in local currency for this customer+BL combination
            - num_business_lines_for_customer: Number of distinct BLs this customer has
            - proposed_primary_business_line: Heuristic selection (largest abs balance)
            - proposed_reclass_amount_lcy: Amount to reclass FROM this BL TO primary BL
            - reasoning: Human-readable explanation of the heuristic
            - review_required: Always True (manual review needed)

    Raises:
        ValueError: If required columns are missing from cle_df
        ValueError: If cutoff_date is not in valid YYYY-MM-DD format
        TypeError: If cle_df is not a pandas DataFrame

    Examples:
        >>> # Customer with single business line - no candidates
        >>> cle_df = pd.DataFrame([
        ...     {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
        ...     {"customer_id": "C002", "business_line_code": "BL02", "amount_lcy": 500.0},
        ... ])
        >>> result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")
        >>> len(result)
        0

        >>> # Customer with multiple business lines - generates candidates
        >>> cle_df = pd.DataFrame([
        ...     {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
        ...     {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
        ...     {"customer_id": "C001", "business_line_code": "BL03", "amount_lcy": -50.0},
        ... ])
        >>> result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")
        >>> len(result)
        3
        >>> result.iloc[0]["proposed_primary_business_line"]
        'BL01'

    Notes:
        - This function does NOT automatically determine the "true" correct business line
        - It does NOT post journal entries
        - It does NOT make final decisions (review-driven process)
        - Heuristic uses absolute balance magnitude (largest wins)
        - Ties are broken deterministically (alphabetical)
        - All output rows have review_required=True
    """
    # Validate input DataFrame
    if not isinstance(cle_df, pd.DataFrame):
        raise TypeError(
            f"cle_df must be a pandas DataFrame, got {type(cle_df).__name__}"
        )

    # Normalize cutoff_date (validates format)
    try:
        cutoff_ts = normalize_date(cutoff_date)
        logger.info(f"Using cutoff date: {cutoff_ts.strftime('%Y-%m-%d')}")
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid cutoff_date '{cutoff_date}'. "
            f"Expected YYYY-MM-DD format. Error: {e}"
        )

    # Handle empty input
    if cle_df.empty:
        logger.warning("Input CLE DataFrame is empty. Returning empty candidates.")
        return _create_empty_result()

    # Validate required columns exist
    required_cols = [customer_id_col, business_line_col, amount_col]
    missing_cols = [col for col in required_cols if col not in cle_df.columns]
    if missing_cols:
        raise ValueError(
            f"Required columns missing from cle_df: {missing_cols}. "
            f"Available columns: {list(cle_df.columns)}"
        )

    # Create working copy and ensure numeric amount column
    logger.info(f"Processing {len(cle_df)} CLE rows...")
    df = cle_df.copy()

    # Cast amount column to numeric (handles strings with commas, NaN, etc.)
    try:
        df = ensure_required_numeric(df, required=[amount_col], fillna=0.0)
    except Exception as e:
        raise ValueError(
            f"Failed to cast '{amount_col}' column to numeric: {e}. "
            f"Check for invalid values in the amount column."
        )

    # Normalize column names for internal processing
    df = df.rename(columns={
        customer_id_col: "customer_id",
        business_line_col: "business_line_code",
        amount_col: "balance_lcy",
    })

    # Drop rows with missing customer_id or business_line_code
    before_drop = len(df)
    df = df.dropna(subset=["customer_id", "business_line_code"])
    after_drop = len(df)
    if before_drop > after_drop:
        logger.warning(
            f"Dropped {before_drop - after_drop} rows with missing "
            f"customer_id or business_line_code"
        )

    # Aggregate: Group by customer + business line and sum balances
    agg_df = (
        df.groupby(["customer_id", "business_line_code"], as_index=False)
        .agg({"balance_lcy": "sum"})
    )

    # Filter out negligible balances (reduce noise)
    agg_df = agg_df[agg_df["balance_lcy"].abs() >= min_abs_amount].copy()

    if agg_df.empty:
        logger.info("No balances above minimum threshold. Returning empty candidates.")
        return _create_empty_result()

    # Count number of business lines per customer
    bl_counts = (
        agg_df.groupby("customer_id")["business_line_code"]
        .nunique()
        .rename("num_business_lines_for_customer")
    )

    # Join count back to aggregated data
    agg_df = agg_df.merge(bl_counts, on="customer_id", how="left")

    # Filter: Only customers with multiple business lines
    candidates_df = agg_df[agg_df["num_business_lines_for_customer"] > 1].copy()

    if candidates_df.empty:
        logger.info(
            "No customers found with balances across multiple business lines. "
            "Returning empty candidates."
        )
        return _create_empty_result()

    logger.info(
        f"Found {candidates_df['customer_id'].nunique()} customers with "
        f"balances across multiple business lines."
    )

    # For each customer, determine proposed primary business line
    # Heuristic: Business line with largest absolute balance
    def _compute_primary_bl(group: pd.DataFrame) -> pd.Series:
        """
        Compute proposed primary business line for a customer group.

        Uses heuristic: largest absolute balance.
        Tie-breaker: alphabetical order (deterministic).
        """
        # Find row with largest absolute balance
        max_abs_idx = group["balance_lcy"].abs().idxmax()
        primary_bl = group.loc[max_abs_idx, "business_line_code"]

        # Handle tie-breaker: if multiple BLs have same abs balance, choose alphabetically
        max_abs_value = group["balance_lcy"].abs().max()
        tied_bls = group[group["balance_lcy"].abs() == max_abs_value][
            "business_line_code"
        ].sort_values()

        if len(tied_bls) > 1:
            primary_bl = tied_bls.iloc[0]  # First alphabetically

        # Assign primary BL to all rows in group
        group["proposed_primary_business_line"] = primary_bl
        return group

    # Apply primary BL computation per customer
    candidates_df = (
        candidates_df.groupby("customer_id", group_keys=False)
        .apply(_compute_primary_bl)
        .reset_index(drop=True)
    )

    # Compute proposed reclass amount
    # Logic: If current BL is NOT primary, reclass FULL balance to primary
    # If current BL IS primary, no reclass needed (0.0)
    candidates_df["proposed_reclass_amount_lcy"] = candidates_df.apply(
        lambda row: row["balance_lcy"]
        if row["business_line_code"] != row["proposed_primary_business_line"]
        else 0.0,
        axis=1,
    )

    # Generate reasoning column
    candidates_df["reasoning"] = candidates_df.apply(
        lambda row: (
            f"Customer {row['customer_id']} has {row['num_business_lines_for_customer']} "
            f"business lines. Proposed primary: {row['proposed_primary_business_line']} "
            f"(largest absolute balance). "
            + (
                f"Reclass {row['balance_lcy']:.2f} from {row['business_line_code']} to "
                f"{row['proposed_primary_business_line']}."
                if row["business_line_code"] != row["proposed_primary_business_line"]
                else f"Current BL is proposed primary. No reclass needed."
            )
        ),
        axis=1,
    )

    # All candidates require manual review
    candidates_df["review_required"] = True

    # Reorder columns for readability
    final_columns = [
        "customer_id",
        "business_line_code",
        "balance_lcy",
        "num_business_lines_for_customer",
        "proposed_primary_business_line",
        "proposed_reclass_amount_lcy",
        "reasoning",
        "review_required",
    ]

    result_df = candidates_df[final_columns].copy()

    # Sort for deterministic output
    result_df = result_df.sort_values(
        by=["customer_id", "business_line_code"]
    ).reset_index(drop=True)

    logger.info(
        f"Generated {len(result_df)} candidate reclass rows for "
        f"{result_df['customer_id'].nunique()} customers."
    )

    return result_df


def _create_empty_result() -> pd.DataFrame:
    """
    Create an empty DataFrame with the expected output schema.

    Returns:
        pd.DataFrame: Empty DataFrame with correct column types
    """
    return pd.DataFrame(
        columns=[
            "customer_id",
            "business_line_code",
            "balance_lcy",
            "num_business_lines_for_customer",
            "proposed_primary_business_line",
            "proposed_reclass_amount_lcy",
            "reasoning",
            "review_required",
        ]
    ).astype({
        "customer_id": "object",
        "business_line_code": "object",
        "balance_lcy": "float64",
        "num_business_lines_for_customer": "Int64",
        "proposed_primary_business_line": "object",
        "proposed_reclass_amount_lcy": "float64",
        "reasoning": "object",
        "review_required": "bool",
    })


__all__ = [
    "identify_business_line_reclass_candidates",
]
