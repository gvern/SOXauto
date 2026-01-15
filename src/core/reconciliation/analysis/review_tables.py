"""
Review Tables Module for PG-01 Reconciliation.

This module generates "Accounting review required" tables for manual review by
the Accounting Excellence team.

Key Functions:
    - build_review_table: Generate comprehensive review table with voucher drilldown
    - flag_for_manual_review: Flag items requiring manual attention

Example:
    >>> from src.core.reconciliation.analysis.review_tables import build_review_table
    >>> 
    >>> # Build review table with LINE_ITEM_USD thresholds
    >>> review_df = build_review_table(
    ...     variance_pivot_with_status=evaluated_variance_df,
    ...     gl_account="18412",
    ...     nav_source_df=nav_cle_df,  # Optional for drilldown
    ...     tv_source_df=tv_vouchers_df,  # Optional for drilldown
    ...     fx_converter=fx_converter,
    ...     filter_non_material_lines=False
    ... )
    >>> 
    >>> print(f"Items for review: {len(review_df)}")
"""

from typing import Dict, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def build_review_table(
    variance_pivot_with_status: pd.DataFrame,
    gl_account: str,
    nav_source_df: Optional[pd.DataFrame] = None,
    tv_source_df: Optional[pd.DataFrame] = None,
    fx_converter=None,
    filter_non_material_lines: bool = False,
) -> pd.DataFrame:
    """
    Build comprehensive review table for accounting manual review.
    
    This function implements Phase 3 Step 6: Drill-down Review Table for Accounting.
    
    It processes variance pivot data (with status from threshold evaluation) and:
    1. Filters to INVESTIGATE buckets only
    2. Optionally drills down to line-item level using source DataFrames
    3. Applies LINE_ITEM_USD thresholds to mark material line items
    4. Generates accounting-friendly output with full audit trail
    
    Args:
        variance_pivot_with_status: Variance pivot DataFrame from evaluate_thresholds_variance_pivot()
            Required columns:
            - country_code, category, voucher_type
            - nav_amount_lcy, tv_amount_lcy, variance_amount_lcy (local currency)
            - nav_amount_usd, tv_amount_usd, variance_amount_usd (USD)
            - status: "OK" or "INVESTIGATE"
            - threshold_usd, threshold_contract_version, threshold_contract_hash, etc.
        
        gl_account: GL account number (e.g., "18412" for voucher liabilities)
        
        nav_source_df: Optional source DataFrame for NAV line-item drilldown.
            Should contain: country_code, category, voucher_type, document_no, amount_lcy
            If provided, will drill down to voucher level for INVESTIGATE buckets.
        
        tv_source_df: Optional source DataFrame for TV line-item drilldown.
            Should contain: country_code, category, voucher_type, voucher_id, amount_lcy
            If provided, will drill down to voucher level for INVESTIGATE buckets.
        
        fx_converter: FXConverter instance required for drilldown FX conversion.
        
        filter_non_material_lines: If True, filter out line items below LINE_ITEM_USD threshold.
            Default False: keep all lines but mark line_item_material flag.
            Useful for focused review on material items only.
    
    Returns:
        DataFrame with accounting review table. Columns include:
        - country_code: Country code
        - gl_account: GL account number
        - category: Category classification
        - voucher_type: Voucher type
        - row_type: "bucket_summary" or "line_item" (if drilldown available)
        - voucher_id: Voucher ID (line items only)
        - document_no: Document number (line items only)
        - nav_amount_lcy: NAV amount in local currency
        - tv_amount_lcy: TV amount in local currency
        - variance_amount_lcy: Variance in local currency
        - nav_amount_usd: NAV amount in USD
        - tv_amount_usd: TV amount in USD
        - variance_amount_usd: Variance in USD
        - bucket_threshold_usd: Bucket-level threshold
        - bucket_status: "INVESTIGATE" (all rows in this table)
        - line_item_threshold_usd: Line-item threshold (line items only)
        - line_item_material: Boolean flag for material line items
        - threshold_contract_version: Contract version
        - threshold_contract_hash: Contract hash for evidence
        - threshold_rule_description: Matched rule description
        
        If no drilldown sources provided, returns bucket-level summaries only.
        If drilldown available, includes both bucket summaries and line items.
    
    Raises:
        ValueError: If required columns missing from variance_pivot_with_status
    
    Examples:
        >>> # Bucket-level review only (no drilldown)
        >>> review_df = build_review_table(evaluated_df, gl_account="18412")
        >>> print(review_df[["country_code", "category", "variance_amount_usd", "bucket_status"]])
        
        >>> # With line-item drilldown
        >>> review_df = build_review_table(
        ...     evaluated_df,
        ...     gl_account="18412",
        ...     nav_source_df=cle_df,
        ...     tv_source_df=vouchers_df,
        ...     fx_converter=fx_converter
        ... )
        >>> line_items = review_df[review_df["row_type"] == "line_item"]
        >>> print(f"Total line items for review: {len(line_items)}")
        >>> material_items = line_items[line_items["line_item_material"]]
        >>> print(f"Material line items: {len(material_items)}")
    
    Notes:
        - Only INVESTIGATE buckets are included in the review table
        - Line-item drilldown requires source DataFrames with matching keys
        - LINE_ITEM_USD threshold is resolved per (country, gl_account, category, voucher_type)
        - All threshold metadata included for complete audit trail
        - Non-material line items are included by default (filter_non_material_lines=False)
    """
    # Import here to avoid circular dependency
    from src.core.reconciliation.thresholds import resolve_line_item_threshold
    
    # Validate required columns (thresholds applied to USD amounts post-FX conversion)
    required_cols = [
        "country_code", "category", "voucher_type", "status",
        "nav_amount_local", "tv_amount_local", "variance_amount_local",
        "nav_amount_usd", "tv_amount_usd", "variance_amount_usd",
        "threshold_usd", "threshold_contract_version", "threshold_contract_hash",
        "threshold_rule_description",
    ]
    
    missing_cols = [col for col in required_cols if col not in variance_pivot_with_status.columns]
    if missing_cols:
        raise ValueError(
            f"Required columns missing from variance_pivot_with_status: {missing_cols}. "
            f"Available columns: {list(variance_pivot_with_status.columns)}"
        )
    
    # Filter to INVESTIGATE buckets only
    investigate_df = variance_pivot_with_status[
        variance_pivot_with_status["status"] == "INVESTIGATE"
    ].copy()
    
    if investigate_df.empty:
        logger.info("No INVESTIGATE buckets found. Returning empty review table.")
        return pd.DataFrame(columns=[
            "country_code", "gl_account", "category", "voucher_type", "row_type",
            "voucher_id", "document_no",
            "nav_amount_local", "tv_amount_local", "variance_amount_local",
            "nav_amount_usd", "tv_amount_usd", "variance_amount_usd",
            "bucket_threshold_usd", "bucket_status",
            "line_item_threshold_usd", "line_item_material",
            "threshold_contract_version", "threshold_contract_hash",
            "threshold_rule_description",
        ])
    
    logger.info(
        f"Building review table for {len(investigate_df)} INVESTIGATE buckets "
        f"(GL {gl_account})"
    )
    
    # Build bucket-level summaries
    bucket_summaries = []
    
    for _, row in investigate_df.iterrows():
        bucket_summary = {
            "country_code": row["country_code"],
            "gl_account": gl_account,
            "category": row["category"],
            "voucher_type": row["voucher_type"],
            "row_type": "bucket_summary",
            "voucher_id": None,
            "document_no": None,
            "nav_amount_local": row["nav_amount_local"],
            "tv_amount_local": row["tv_amount_local"],
            "variance_amount_local": row["variance_amount_local"],
            "nav_amount_usd": row["nav_amount_usd"],
            "tv_amount_usd": row["tv_amount_usd"],
            "variance_amount_usd": row["variance_amount_usd"],
            "bucket_threshold_usd": row["threshold_usd"],
            "bucket_status": "INVESTIGATE",
            "line_item_threshold_usd": None,
            "line_item_material": None,
            "threshold_contract_version": row["threshold_contract_version"],
            "threshold_contract_hash": row["threshold_contract_hash"],
            "threshold_rule_description": row["threshold_rule_description"],
        }
        bucket_summaries.append(bucket_summary)
    
    review_rows = bucket_summaries
    
    # Add line-item drilldown if source data available
    if (nav_source_df is not None or tv_source_df is not None) and fx_converter is None:
        raise ValueError("fx_converter is required when line-item drilldown is enabled.")
    
    if nav_source_df is not None or tv_source_df is not None:
        logger.info("Adding line-item drilldown to review table")
        line_items = _build_line_item_drilldown(
            investigate_df=investigate_df,
            gl_account=gl_account,
            nav_source_df=nav_source_df,
            tv_source_df=tv_source_df,
            fx_converter=fx_converter,
            filter_non_material_lines=filter_non_material_lines,
        )
        review_rows.extend(line_items)
    
    # Create final DataFrame
    review_df = pd.DataFrame(review_rows)
    
    # Sort for consistent output
    sort_cols = ["country_code", "category", "voucher_type", "row_type"]
    if "voucher_id" in review_df.columns:
        sort_cols.append("voucher_id")
    review_df = review_df.sort_values(by=sort_cols, ignore_index=True)
    
    logger.info(
        f"Review table built: {len(review_df)} total rows "
        f"({len(bucket_summaries)} bucket summaries, "
        f"{len(review_df) - len(bucket_summaries)} line items)"
    )
    
    return review_df


def _build_line_item_drilldown(
    investigate_df: pd.DataFrame,
    gl_account: str,
    nav_source_df: Optional[pd.DataFrame],
    tv_source_df: Optional[pd.DataFrame],
    fx_converter,
    filter_non_material_lines: bool,
) -> list:
    """
    Build line-item drilldown rows for INVESTIGATE buckets.
    
    Internal helper function for build_review_table().
    
    Returns list of line-item dictionaries with LINE_ITEM_USD threshold evaluation.
    """
    from src.core.reconciliation.thresholds import resolve_line_item_threshold
    from src.core.reconciliation.analysis.drilldown import (
        extract_nav_line_items,
        extract_tv_line_items,
    )
    
    line_items = []
    
    # Process each INVESTIGATE bucket
    for _, bucket_row in investigate_df.iterrows():
        country_code = bucket_row["country_code"]
        category = bucket_row["category"]
        voucher_type = bucket_row["voucher_type"]
        
        # Resolve LINE_ITEM_USD threshold for this bucket
        line_item_threshold_resolved = resolve_line_item_threshold(
            country_code=country_code,
            gl_account=gl_account,
            category=category,
            voucher_type=voucher_type,
        )
        
        # Extract NAV line items
        if nav_source_df is not None:
            nav_items = extract_nav_line_items(
                nav_source_df=nav_source_df,
                country_code=country_code,
                category=category,
                voucher_type=voucher_type,
                gl_account=gl_account,
                line_item_threshold=line_item_threshold_resolved,
                fx_converter=fx_converter,
                bucket_threshold_usd=bucket_row["threshold_usd"],
                bucket_contract_version=bucket_row["threshold_contract_version"],
                bucket_contract_hash=bucket_row["threshold_contract_hash"],
                filter_non_material=filter_non_material_lines,
            )
            line_items.extend(nav_items)
        
        # Extract TV line items
        if tv_source_df is not None:
            tv_items = extract_tv_line_items(
                tv_source_df=tv_source_df,
                country_code=country_code,
                category=category,
                voucher_type=voucher_type,
                gl_account=gl_account,
                line_item_threshold=line_item_threshold_resolved,
                fx_converter=fx_converter,
                bucket_threshold_usd=bucket_row["threshold_usd"],
                bucket_contract_version=bucket_row["threshold_contract_version"],
                bucket_contract_hash=bucket_row["threshold_contract_hash"],
                filter_non_material=filter_non_material_lines,
            )
            line_items.extend(tv_items)
    
    return line_items


def flag_for_manual_review(
    df: pd.DataFrame,
    criteria: Dict[str, Any],
) -> pd.DataFrame:
    """
    Flag items requiring manual review based on criteria.
    
    TODO: Implement flagging logic.
    Currently returns empty DataFrame.
    
    Args:
        df: DataFrame to analyze
        criteria: Dictionary of flagging criteria
        
    Returns:
        DataFrame: Flagged items requiring manual review
    """
    # Placeholder implementation
    return pd.DataFrame(columns=["Item_ID", "Flag_Reason", "Priority"])


__all__ = [
    "build_review_table",
    "flag_for_manual_review",
]
