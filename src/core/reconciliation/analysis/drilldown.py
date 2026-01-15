"""
Drilldown Views Module for PG-01 Reconciliation.

This module provides voucher-level drilldown views for detailed reconciliation analysis.
Supports drilling down from bucket-level variance summaries to individual voucher transactions
with threshold-based materiality evaluation.

Key Functions:
    - extract_nav_line_items: Extract NAV line items with LINE_ITEM_USD threshold evaluation
    - extract_tv_line_items: Extract Target Value line items with threshold evaluation
    - generate_drilldown_view: Generate voucher-level view for category (placeholder)
    - get_voucher_details: Get detailed voucher information (placeholder)

Line-Item Drilldown Features:
    - Filters source data to specific bucket (country_code, category, voucher_type)
    - Converts local currency amounts to USD
    - Applies LINE_ITEM_USD thresholds to mark material items
    - Supports filtering to material items only
    - Includes full threshold metadata (version, hash, description)

Expected Data Structures:
    - NAV Source (enriched CR_03): category, voucher_type, country_code, amount_local,
      document_no, voucher_no, posting_date
    - TV Source (IPE_08 or DOC_VOUCHER_USAGE): ID_COMPANY, category, voucher_type,
      remaining_amount or TotalAmountUsed, voucher ID

Usage Example:
    >>> from src.core.reconciliation.analysis.drilldown import extract_nav_line_items
    >>> from src.core.reconciliation.thresholds import resolve_line_item_threshold
    >>> 
    >>> # Resolve threshold for specific bucket
    >>> threshold = resolve_line_item_threshold(
    ...     country_code="EG",
    ...     gl_account="18412",
    ...     category="Issuance",
    ...     voucher_type="refund"
    ... )
    >>> 
    >>> # Extract NAV line items with threshold evaluation
    >>> nav_items = extract_nav_line_items(
    ...     nav_source_df=categorized_cr03_df,
    ...     country_code="EG",
    ...     category="Issuance",
    ...     voucher_type="refund",
    ...     gl_account="18412",
    ...     line_item_threshold=threshold,
    ...     fx_converter=fx_converter,
    ...     bucket_threshold_usd=1000.0,
    ...     bucket_contract_version=1,
    ...     bucket_contract_hash="abc123",
    ...     filter_non_material=False
    ... )
    >>> 
    >>> # Check material items
    >>> material_count = sum(1 for item in nav_items if item['line_item_material'])
    >>> print(f"Material line items: {material_count}/{len(nav_items)}")
"""

from typing import Optional
import pandas as pd
from src.utils.fx_utils import FXConverter


def generate_drilldown_view(
    nav_df: pd.DataFrame,
    category: Optional[str] = None,
    country_code: Optional[str] = None,
) -> pd.DataFrame:
    """
    Generate voucher-level drilldown view for specified category.

    Args:
        nav_df: NAV DataFrame with categorized vouchers
        category: Optional category filter (e.g., "Issuance", "Usage", "VTC")
        country_code: Optional country code filter
        
    Returns:
        DataFrame: Voucher-level details for drilldown analysis
    """
    if nav_df is None or nav_df.empty:
        return pd.DataFrame(columns=[
            "Voucher_ID",
            "Category",
            "Amount",
            "Date",
            "Country_Code",
            "Business_Line",
            "Details",
        ])

    def _first_existing_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
        for col in candidates:
            if col in df.columns:
                return col
        return None

    category_col = _first_existing_column(nav_df, ["category", "bridge_category"])
    country_col = _first_existing_column(nav_df, ["country_code", "id_company", "Company_Code"])
    voucher_col = _first_existing_column(
        nav_df,
        ["voucher_id", "voucher_no", "Voucher_ID", "Voucher No_", "Voucher Id", "VoucherId", "Voucher No"],
    )
    amount_col = _first_existing_column(
        nav_df,
        ["amount_local", "amount_lcy", "amount", "Amount", "Amount_LCY"],
    )
    date_col = _first_existing_column(
        nav_df,
        ["posting_date", "Posting Date", "Posting_Date", "PostingDate", "Date"],
    )
    business_col = _first_existing_column(
        nav_df,
        ["business_line", "Business Line", "Business_Line", "Integration_Type"],
    )
    details_col = _first_existing_column(
        nav_df,
        ["document_description", "Document Description", "description", "Document Type"],
    )

    mask = pd.Series(True, index=nav_df.index)
    if category is not None and category_col is not None:
        mask &= nav_df[category_col] == category
    if country_code is not None and country_col is not None:
        mask &= nav_df[country_col] == country_code

    filtered = nav_df.loc[mask]
    result = pd.DataFrame(index=filtered.index)
    result["Voucher_ID"] = filtered[voucher_col] if voucher_col else None
    result["Category"] = filtered[category_col] if category_col else None
    result["Amount"] = filtered[amount_col] if amount_col else None
    result["Date"] = filtered[date_col] if date_col else None
    result["Country_Code"] = filtered[country_col] if country_col else None
    result["Business_Line"] = filtered[business_col] if business_col else None
    result["Details"] = filtered[details_col] if details_col else None

    return result.reset_index(drop=True)


def get_voucher_details(
    voucher_id: str,
    nav_df: pd.DataFrame,
) -> Optional[pd.Series]:
    """
    Get detailed information for a specific voucher.

    Args:
        voucher_id: Voucher identifier
        nav_df: NAV DataFrame with voucher data
        
    Returns:
        Series: Voucher details or None if not found
    """
    if nav_df is None or nav_df.empty:
        return None

    def _first_existing_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
        for col in candidates:
            if col in df.columns:
                return col
        return None

    voucher_col = _first_existing_column(
        nav_df,
        ["voucher_id", "voucher_no", "Voucher_ID", "Voucher No_", "Voucher Id", "VoucherId", "Voucher No"],
    )
    if voucher_col is None:
        return None

    matches = nav_df[nav_df[voucher_col].astype(str) == str(voucher_id)]
    if matches.empty:
        return None

    return matches.iloc[0]


def extract_nav_line_items(
    nav_source_df: pd.DataFrame,
    country_code: str,
    category: str,
    voucher_type: str,
    gl_account: str,
    line_item_threshold,
    fx_converter: FXConverter,
    bucket_threshold_usd: float,
    bucket_contract_version: int,
    bucket_contract_hash: str,
    filter_non_material: bool = False,
) -> list:
    """
    Extract NAV line items for a specific bucket with threshold evaluation.
    
    Drills down from bucket-level variance to individual NAV voucher line items.
    Applies LINE_ITEM_USD threshold to mark material items.
    
    Args:
        nav_source_df: Source DataFrame for NAV data (enriched CR_03 with categorization).
            Expected columns: country_code, category, voucher_type, document_no, 
            amount_lcy (or amount_local), posting_date, document_description
        country_code: Country code filter
        category: Category filter (e.g., "Issuance", "Usage")
        voucher_type: Voucher type filter
        gl_account: GL account number (e.g., "18412")
        line_item_threshold: ResolvedThreshold object for LINE_ITEM_USD
        fx_converter: FXConverter instance for local-to-USD conversion
        bucket_threshold_usd: Bucket-level threshold in USD
        bucket_contract_version: Contract version from bucket evaluation
        bucket_contract_hash: Contract hash from bucket evaluation
        filter_non_material: If True, return only material line items
        
    Returns:
        List of dictionaries, each representing a NAV line item with:
        - country_code, gl_account, category, voucher_type
        - row_type: "line_item"
        - voucher_id, document_no
        - nav_amount_local, tv_amount_local (None), variance_amount_local
        - nav_amount_usd, tv_amount_usd (None), variance_amount_usd
        - bucket_threshold_usd, bucket_status: "INVESTIGATE"
        - line_item_threshold_usd, line_item_material: bool
        - threshold_contract_version, threshold_contract_hash, threshold_rule_description
    
    Notes:
        - Filters nav_source_df to matching bucket (country_code, category, voucher_type)
        - Converts amounts from local currency to USD using FXConverter
        - Compares abs(amount_usd) >= line_item_threshold.threshold_usd
        - Sets line_item_material flag
        - Optionally filters to material items only if filter_non_material=True
    """
    import logging
    from src.utils.pandas_utils import ensure_required_numeric
    
    logger = logging.getLogger(__name__)
    
    # Validate required columns
    required_cols = ["category", "voucher_type"]
    missing_cols = [col for col in required_cols if col not in nav_source_df.columns]
    if missing_cols:
        logger.warning(f"Missing columns in nav_source_df: {missing_cols}. Returning empty list.")
        return []
    
    # Filter to matching bucket
    mask = (
        (nav_source_df["category"] == category) &
        (nav_source_df["voucher_type"] == voucher_type)
    )
    
    # Add country_code filter if column exists
    if "country_code" in nav_source_df.columns:
        mask = mask & (nav_source_df["country_code"] == country_code)
    elif "id_company" in nav_source_df.columns:
        # Fallback to id_company if country_code not present
        mask = mask & (nav_source_df["id_company"] == country_code)
    
    bucket_df = nav_source_df[mask].copy()
    
    if bucket_df.empty:
        logger.debug(
            f"No NAV line items found for {country_code}/{category}/{voucher_type}"
        )
        return []
    
    # Find amount column (local currency)
    amount_col = None
    for col in ["amount_local", "amount_lcy", "amount"]:
        if col in bucket_df.columns:
            amount_col = col
            break
    
    if amount_col is None:
        logger.warning(
            f"No amount column found in nav_source_df. "
            f"Expected: amount_local, amount_lcy, or amount. "
            f"Returning empty list."
        )
        return []
    
    # Ensure amount is numeric
    bucket_df = ensure_required_numeric(bucket_df, [amount_col], force_numeric=True)
    
    # Find company code column for FX conversion
    company_col = None
    for col in ["country_code", "id_company", "Company_Code"]:
        if col in bucket_df.columns:
            company_col = col
            break
    
    if company_col is None:
        company_series = pd.Series([country_code] * len(bucket_df), index=bucket_df.index)
    else:
        company_series = bucket_df[company_col]
    
    bucket_df["amount_usd"] = fx_converter.convert_series_to_usd(
        bucket_df[amount_col].abs(),
        company_series,
    )
    
    # Extract line items
    line_items = []
    
    for _, row in bucket_df.iterrows():
        # Determine if line item is material
        amount_usd = abs(row["amount_usd"])
        is_material = amount_usd >= line_item_threshold.threshold_usd
        
        # Skip non-material items if filtering
        if filter_non_material and not is_material:
            continue
        
        # Build line item dict
        line_item = {
            "country_code": row.get(company_col, country_code),
            "gl_account": gl_account,
            "category": category,
            "voucher_type": voucher_type,
            "row_type": "line_item",
            "voucher_id": row.get("voucher_no", None),
            "document_no": row.get("document_no", None),
            "nav_amount_local": row[amount_col],
            "tv_amount_local": None,
            "variance_amount_local": row[amount_col],  # NAV only, no TV match
            "nav_amount_usd": row["amount_usd"] if row[amount_col] >= 0 else -row["amount_usd"],
            "tv_amount_usd": None,
            "variance_amount_usd": row["amount_usd"] if row[amount_col] >= 0 else -row["amount_usd"],
            "bucket_threshold_usd": bucket_threshold_usd,
            "bucket_status": "INVESTIGATE",
            "line_item_threshold_usd": line_item_threshold.threshold_usd,
            "line_item_material": is_material,
            "threshold_contract_version": bucket_contract_version,
            "threshold_contract_hash": bucket_contract_hash,
            "threshold_rule_description": line_item_threshold.matched_rule_description,
        }
        
        line_items.append(line_item)
    
    logger.info(
        f"Extracted {len(line_items)} NAV line items for "
        f"{country_code}/{category}/{voucher_type} "
        f"({sum(1 for item in line_items if item['line_item_material'])} material)"
    )
    
    return line_items


def extract_tv_line_items(
    tv_source_df: pd.DataFrame,
    country_code: str,
    category: str,
    voucher_type: str,
    gl_account: str,
    line_item_threshold,
    fx_converter: FXConverter,
    bucket_threshold_usd: float,
    bucket_contract_version: int,
    bucket_contract_hash: str,
    filter_non_material: bool = False,
) -> list:
    """
    Extract TV line items for a specific bucket with threshold evaluation.
    
    Drills down from bucket-level variance to individual Target Value voucher line items.
    Applies LINE_ITEM_USD threshold to mark material items.
    
    Args:
        tv_source_df: Source DataFrame for Target Values data (e.g., IPE_08, DOC_VOUCHER_USAGE).
            Expected columns: country_code (or ID_COMPANY), category, voucher_type, 
            voucher_id (or id), remaining_amount (or TotalAmountUsed)
        country_code: Country code filter
        category: Category filter (e.g., "Issuance", "Usage")
        voucher_type: Voucher type filter
        gl_account: GL account number (e.g., "18412")
        line_item_threshold: ResolvedThreshold object for LINE_ITEM_USD
        fx_converter: FXConverter instance for local-to-USD conversion
        bucket_threshold_usd: Bucket-level threshold in USD
        bucket_contract_version: Contract version from bucket evaluation
        bucket_contract_hash: Contract hash from bucket evaluation
        filter_non_material: If True, return only material line items
        
    Returns:
        List of dictionaries, each representing a TV line item with:
        - country_code, gl_account, category, voucher_type
        - row_type: "line_item"
        - voucher_id, document_no (None)
        - nav_amount_local (None), tv_amount_local, variance_amount_local
        - nav_amount_usd (None), tv_amount_usd, variance_amount_usd
        - bucket_threshold_usd, bucket_status: "INVESTIGATE"
        - line_item_threshold_usd, line_item_material: bool
        - threshold_contract_version, threshold_contract_hash, threshold_rule_description
    
    Notes:
        - Filters tv_source_df to matching bucket (country_code, category, voucher_type)
        - Converts amounts from local currency to USD using FXConverter
        - Compares abs(amount_usd) >= line_item_threshold.threshold_usd
        - Sets line_item_material flag
        - Optionally filters to material items only if filter_non_material=True
    """
    import logging
    from src.utils.pandas_utils import ensure_required_numeric
    
    logger = logging.getLogger(__name__)
    
    # Validate required columns (flexible for different TV sources)
    # TV data may have different column structures depending on source
    has_category = "category" in tv_source_df.columns
    has_voucher_type = "voucher_type" in tv_source_df.columns or "business_use" in tv_source_df.columns
    
    if not (has_category or has_voucher_type):
        logger.warning(
            f"TV source missing categorization columns. "
            f"Expected 'category' and 'voucher_type' or 'business_use'. "
            f"Returning empty list."
        )
        return []
    
    # Filter to matching bucket
    mask = pd.Series([True] * len(tv_source_df), index=tv_source_df.index)
    
    # Filter by category if available
    if "category" in tv_source_df.columns:
        mask = mask & (tv_source_df["category"] == category)
    
    # Filter by voucher_type (may be called business_use in some TV sources)
    if "voucher_type" in tv_source_df.columns:
        mask = mask & (tv_source_df["voucher_type"] == voucher_type)
    elif "business_use" in tv_source_df.columns:
        # Map voucher_type to business_use values
        # This requires understanding the mapping, for now use direct match
        mask = mask & (tv_source_df["business_use"].str.lower() == voucher_type.lower())
    elif "business_use_formatted" in tv_source_df.columns:
        mask = mask & (tv_source_df["business_use_formatted"].str.lower() == voucher_type.lower())
    
    # Filter by country_code if available
    if "country_code" in tv_source_df.columns:
        mask = mask & (tv_source_df["country_code"] == country_code)
    elif "ID_COMPANY" in tv_source_df.columns:
        mask = mask & (tv_source_df["ID_COMPANY"] == country_code)
    elif "id_company" in tv_source_df.columns:
        mask = mask & (tv_source_df["id_company"] == country_code)
    
    bucket_df = tv_source_df[mask].copy()
    
    if bucket_df.empty:
        logger.debug(
            f"No TV line items found for {country_code}/{category}/{voucher_type}"
        )
        return []
    
    # Find amount column (local currency)
    # Different TV sources use different column names
    amount_col = None
    for col in ["remaining_amount", "Remaining Amount", "Remaining_Amount", 
                "TotalAmountUsed", "Total Amount Used", "amount_local", "amount"]:
        if col in bucket_df.columns:
            amount_col = col
            break
    
    if amount_col is None:
        logger.warning(
            f"No amount column found in tv_source_df. "
            f"Expected: remaining_amount, TotalAmountUsed, amount_local, or amount. "
            f"Returning empty list."
        )
        return []
    
    # Ensure amount is numeric
    bucket_df = ensure_required_numeric(bucket_df, [amount_col], force_numeric=True)
    
    # Find company code column for FX conversion
    company_col = None
    for col in ["ID_COMPANY", "id_company", "country_code", "Company_Code"]:
        if col in bucket_df.columns:
            company_col = col
            break
    
    if company_col is None:
        company_series = pd.Series([country_code] * len(bucket_df), index=bucket_df.index)
    else:
        company_series = bucket_df[company_col]
    
    bucket_df["amount_usd"] = fx_converter.convert_series_to_usd(
        bucket_df[amount_col].abs(),
        company_series,
    )
    
    # Find voucher ID column
    voucher_id_col = None
    for col in ["id", "voucher_id", "Voucher_ID", "voucher_no"]:
        if col in bucket_df.columns:
            voucher_id_col = col
            break
    
    # Extract line items
    line_items = []
    
    for _, row in bucket_df.iterrows():
        # Determine if line item is material
        amount_usd = abs(row["amount_usd"])
        is_material = amount_usd >= line_item_threshold.threshold_usd
        
        # Skip non-material items if filtering
        if filter_non_material and not is_material:
            continue
        
        # Build line item dict
        line_item = {
            "country_code": row.get(company_col, country_code) if company_col else country_code,
            "gl_account": gl_account,
            "category": category,
            "voucher_type": voucher_type,
            "row_type": "line_item",
            "voucher_id": row.get(voucher_id_col, None) if voucher_id_col else None,
            "document_no": None,  # TV sources typically don't have NAV document numbers
            "nav_amount_local": None,
            "tv_amount_local": row[amount_col],
            "variance_amount_local": row[amount_col],  # TV only, no NAV match
            "nav_amount_usd": None,
            "tv_amount_usd": row["amount_usd"] if row[amount_col] >= 0 else -row["amount_usd"],
            "variance_amount_usd": row["amount_usd"] if row[amount_col] >= 0 else -row["amount_usd"],
            "bucket_threshold_usd": bucket_threshold_usd,
            "bucket_status": "INVESTIGATE",
            "line_item_threshold_usd": line_item_threshold.threshold_usd,
            "line_item_material": is_material,
            "threshold_contract_version": bucket_contract_version,
            "threshold_contract_hash": bucket_contract_hash,
            "threshold_rule_description": line_item_threshold.matched_rule_description,
        }
        
        line_items.append(line_item)
    
    logger.info(
        f"Extracted {len(line_items)} TV line items for "
        f"{country_code}/{category}/{voucher_type} "
        f"({sum(1 for item in line_items if item['line_item_material'])} material)"
    )
    
    return line_items


__all__ = [
    "generate_drilldown_view",
    "get_voucher_details",
    "extract_nav_line_items",
    "extract_tv_line_items",
]
