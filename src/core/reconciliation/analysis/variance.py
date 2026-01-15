"""
Variance Calculation Module for PG-01 Reconciliation.

This module provides variance calculation and thresholding logic for comparing
NAV and Target Values pivots.

Key Functions:
    - compute_variance_pivot_local(): Compute variance in local currency and convert to USD

Example:
    >>> from src.core.reconciliation.analysis.variance import compute_variance_pivot_local
    >>> from src.utils.fx_utils import FXConverter
    >>> 
    >>> # Prepare FX converter with CR_05 rates
    >>> fx_converter = FXConverter(cr_05_df)
    >>> 
    >>> # Compute variance with FX conversion
    >>> variance_df = compute_variance_pivot_local(
    ...     nav_pivot_local_df=nav_pivot,
    ...     tv_pivot_local_df=tv_pivot,
    ...     fx_converter=fx_converter,
    ...     cutoff_date="2025-09-30"
    ... )
    >>> 
    >>> # Result has both local and USD columns
    >>> print(variance_df.columns)
    ['country_code', 'category', 'voucher_type', 'nav_amount_local', 
     'tv_amount_local', 'variance_amount_local', 'nav_amount_usd', 
     'tv_amount_usd', 'variance_amount_usd', 'fx_rate_used', 'fx_missing']
"""

from typing import Optional
import pandas as pd
import logging

from src.utils.fx_utils import FXConverter

logger = logging.getLogger(__name__)


def compute_variance_pivot_local(
    nav_pivot_local_df: pd.DataFrame,
    tv_pivot_local_df: pd.DataFrame,
    fx_converter: FXConverter,
    cutoff_date: str,
) -> pd.DataFrame:
    """
    Compute reconciliation variance pivot in local currency, then apply FX conversion to USD.
    
    This function performs the following steps:
    1. Outer-join NAV and TV pivots on (country_code, category, voucher_type)
    2. Fill missing amounts with 0.0 to ensure no bucket is dropped
    3. Compute variance in local currency: variance = NAV - TV
    4. Apply FX conversion to get USD columns for NAV, TV, and variance
    5. Return a single DataFrame with both local and USD columns
    
    The output is ready for downstream thresholding and reporting with full audit transparency.
    Missing FX rates result in NaN USD values with fx_missing flag set to True.
    
    Args:
        nav_pivot_local_df: NAV pivot DataFrame with columns:
            - country_code: Country code (NG, EG, KE, etc.)
            - category: Category classification
            - voucher_type: Voucher type (refund, store_credit, etc.)
            - nav_amount_local: NAV amount in local currency
        tv_pivot_local_df: Target Values pivot DataFrame with columns:
            - country_code: Country code
            - category: Category classification
            - voucher_type: Voucher type
            - tv_amount_local: TV amount in local currency
        fx_converter: FXConverter instance initialized with CR_05 rates.
                     Must support fetching closing rate for country_code.
        cutoff_date: Cutoff date for FX rate lookup (format: YYYY-MM-DD).
                    Currently used for logging; actual FX rates are pre-loaded
                    in fx_converter based on Company_Code mapping.
    
    Returns:
        DataFrame with columns:
            - country_code: Country code
            - category: Category classification
            - voucher_type: Voucher type
            - nav_amount_local: NAV amount in local currency
            - tv_amount_local: TV amount in local currency
            - variance_amount_local: Variance in local currency (NAV - TV)
            - nav_amount_usd: NAV amount in USD
            - tv_amount_usd: TV amount in USD
            - variance_amount_usd: Variance in USD
            - fx_rate_used: FX rate used for conversion (or NaN if missing)
            - fx_missing: Boolean flag indicating missing FX rate
        
        Rows are sorted deterministically by (country_code, category, voucher_type).
    
    Raises:
        ValueError: If required columns are missing from input DataFrames
    
    Examples:
        >>> # Single country example
        >>> nav_pivot = pd.DataFrame({
        ...     'country_code': ['NG', 'NG'],
        ...     'category': ['Voucher', 'Voucher'],
        ...     'voucher_type': ['refund', 'store_credit'],
        ...     'nav_amount_local': [1000.0, 2000.0]
        ... })
        >>> tv_pivot = pd.DataFrame({
        ...     'country_code': ['NG', 'NG'],
        ...     'category': ['Voucher', 'Voucher'],
        ...     'voucher_type': ['refund', 'apology'],
        ...     'tv_amount_local': [900.0, 500.0]
        ... })
        >>> cr05_df = pd.DataFrame({
        ...     'Company_Code': ['EC_NG'],
        ...     'FX_rate': [1650.0]
        ... })
        >>> fx_converter = FXConverter(cr05_df)
        >>> 
        >>> result = compute_variance_pivot_local(
        ...     nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        ... )
        >>> 
        >>> # Check variance computation
        >>> result.columns.tolist()
        ['country_code', 'category', 'voucher_type', 'nav_amount_local', 
         'tv_amount_local', 'variance_amount_local', 'nav_amount_usd', 
         'tv_amount_usd', 'variance_amount_usd', 'fx_rate_used', 'fx_missing']
        >>> 
        >>> # Missing NAV bucket (apology) has nav_amount_local = 0.0
        >>> apology_row = result[result['voucher_type'] == 'apology']
        >>> apology_row['nav_amount_local'].iloc[0]
        0.0
        >>> apology_row['variance_amount_local'].iloc[0]
        -500.0
        
        >>> # Multi-country example
        >>> nav_pivot_multi = pd.DataFrame({
        ...     'country_code': ['NG', 'EG', 'KE'],
        ...     'category': ['Voucher', 'Voucher', 'Voucher'],
        ...     'voucher_type': ['refund', 'refund', 'refund'],
        ...     'nav_amount_local': [1000.0, 500.0, 1500.0]
        ... })
        >>> tv_pivot_multi = pd.DataFrame({
        ...     'country_code': ['NG', 'EG'],
        ...     'category': ['Voucher', 'Voucher'],
        ...     'voucher_type': ['refund', 'refund'],
        ...     'tv_amount_local': [900.0, 600.0]
        ... })
        >>> result_multi = compute_variance_pivot_local(
        ...     nav_pivot_multi, tv_pivot_multi, fx_converter, "2025-09-30"
        ... )
        >>> # KE has no TV data, so tv_amount_local = 0.0
        >>> ke_row = result_multi[result_multi['country_code'] == 'KE']
        >>> ke_row['tv_amount_local'].iloc[0]
        0.0
    
    Notes:
        - Uses outer join to ensure no buckets are dropped from either side
        - Missing values are explicitly filled with 0.0 for audit transparency
        - FX conversion is centralized via fx_utils.FXConverter
        - Missing FX rates result in NaN USD amounts with fx_missing=True
        - Output is deterministically sorted for reproducible results
        - country_code is mapped to Company_Code for FX rate lookup
          (e.g., 'NG' → 'EC_NG', 'EG' → 'JM_EG', etc.)
    """
    # Validate required columns in NAV pivot
    required_nav_cols = ["country_code", "category", "voucher_type", "nav_amount_local"]
    missing_nav = [col for col in required_nav_cols if col not in nav_pivot_local_df.columns]
    if missing_nav:
        raise ValueError(
            f"Required columns missing from NAV pivot: {missing_nav}. "
            f"Available columns: {list(nav_pivot_local_df.columns)}"
        )
    
    # Validate required columns in TV pivot
    required_tv_cols = ["country_code", "category", "voucher_type", "tv_amount_local"]
    missing_tv = [col for col in required_tv_cols if col not in tv_pivot_local_df.columns]
    if missing_tv:
        raise ValueError(
            f"Required columns missing from TV pivot: {missing_tv}. "
            f"Available columns: {list(tv_pivot_local_df.columns)}"
        )
    
    # Perform outer join to ensure no buckets are dropped
    merge_keys = ["country_code", "category", "voucher_type"]
    variance_df = pd.merge(
        nav_pivot_local_df,
        tv_pivot_local_df,
        on=merge_keys,
        how="outer",
        suffixes=("_nav", "_tv")
    )
    
    # Fill missing amounts with 0.0 for explicit audit transparency
    variance_df["nav_amount_local"] = variance_df["nav_amount_local"].fillna(0.0)
    variance_df["tv_amount_local"] = variance_df["tv_amount_local"].fillna(0.0)
    
    # Compute variance in local currency: variance = NAV - TV
    variance_df["variance_amount_local"] = (
        variance_df["nav_amount_local"] - variance_df["tv_amount_local"]
    )
    
    # Apply FX conversion to USD
    # Map country_code to Company_Code for FX rate lookup
    # Common mappings: NG→EC_NG, EG→JM_EG, KE→EC_KE, GH→JD_GH, etc.
    variance_df["company_code"] = variance_df["country_code"].apply(_map_country_to_company)
    
    # Convert NAV amounts to USD
    variance_df["nav_amount_usd"] = fx_converter.convert_series_to_usd(
        variance_df["nav_amount_local"],
        variance_df["company_code"]
    )
    
    # Convert TV amounts to USD
    variance_df["tv_amount_usd"] = fx_converter.convert_series_to_usd(
        variance_df["tv_amount_local"],
        variance_df["company_code"]
    )
    
    # Convert variance amounts to USD
    variance_df["variance_amount_usd"] = fx_converter.convert_series_to_usd(
        variance_df["variance_amount_local"],
        variance_df["company_code"]
    )
    
    # Add audit fields: fx_rate_used and fx_missing
    variance_df["fx_rate_used"] = variance_df["company_code"].apply(
        lambda cc: fx_converter.rates_dict.get(str(cc)) if pd.notna(cc) else None
    )
    variance_df["fx_missing"] = variance_df["fx_rate_used"].isna()
    
    # Warn about missing FX rates
    missing_fx_count = variance_df["fx_missing"].sum()
    if missing_fx_count > 0:
        missing_countries = variance_df[variance_df["fx_missing"]]["country_code"].unique()
        logger.warning(
            f"Missing FX rates for {missing_fx_count} rows. "
            f"Countries affected: {list(missing_countries)}. "
            f"USD amounts for these rows may not reflect actual FX rates and will follow FXConverter's default behavior."
        )
    
    # Drop temporary company_code column
    variance_df = variance_df.drop(columns=["company_code"])
    
    # Deterministic ordering for reproducible results
    variance_df = variance_df.sort_values(
        by=["country_code", "category", "voucher_type"],
        ignore_index=True
    )
    
    # Select and order output columns
    output_cols = [
        "country_code",
        "category",
        "voucher_type",
        "nav_amount_local",
        "tv_amount_local",
        "variance_amount_local",
        "nav_amount_usd",
        "tv_amount_usd",
        "variance_amount_usd",
        "fx_rate_used",
        "fx_missing",
    ]
    variance_df = variance_df[output_cols]
    
    logger.info(
        f"Computed variance pivot: {len(variance_df)} rows, "
        f"{variance_df['variance_amount_local'].sum():.2f} total variance (local), "
        f"{missing_fx_count} rows with missing FX rates"
    )
    
    return variance_df


def _map_country_to_company(country_code: str) -> Optional[str]:
    """
    Map country code to Company_Code for FX rate lookup.
    
    This mapping is based on the company structure in CR_05 FX rates data.
    Common patterns:
    - Most countries use 'EC_' prefix (E-commerce operations)
    - Egypt uses 'JM_' prefix (Jumia Egypt)
    - Ghana uses 'JD_' prefix (Jumia Deals Ghana)
    
    Args:
        country_code: Country code (NG, EG, KE, etc.)
    
    Returns:
        Company_Code for FX rate lookup, or None if mapping not found
    
    Examples:
        >>> _map_country_to_company('NG')
        'EC_NG'
        >>> _map_country_to_company('EG')
        'JM_EG'
        >>> _map_country_to_company('GH')
        'JD_GH'
        >>> _map_country_to_company('UNKNOWN')
        'EC_UNKNOWN'
    """
    if pd.isna(country_code):
        return None
    
    country_code = str(country_code).upper()
    
    # Special cases with non-EC prefix
    special_mappings = {
        "EG": "JM_EG",  # Jumia Egypt
        "GH": "JD_GH",  # Jumia Deals Ghana
    }
    
    if country_code in special_mappings:
        return special_mappings[country_code]
    
    # Default: EC_ prefix for most countries
    return f"EC_{country_code}"


def evaluate_thresholds_variance_pivot(
    variance_df: pd.DataFrame,
    gl_account: str,
) -> pd.DataFrame:
    """
    Evaluate BUCKET_USD thresholds on variance pivot and mark status (OK/INVESTIGATE).
    
    This function applies threshold evaluation AFTER FX conversion to USD.
    It resolves thresholds using the catalog system with full precedence logic.
    
    For each (country_code, category, voucher_type) bucket, it:
    1. Resolves the BUCKET_USD threshold using country + gl_account + category + voucher_type
    2. Compares abs(variance_usd) against the threshold
    3. Marks status as "OK" or "INVESTIGATE"
    4. Adds threshold metadata for audit trail
    
    Args:
        variance_df: Variance DataFrame from compute_variance_pivot_local() with columns:
            - country_code: Country code
            - category: Category classification
            - voucher_type: Voucher type
            - variance_amount_usd: Variance in USD (required)
            - nav_amount_usd, tv_amount_usd, etc. (optional but preserved)
        gl_account: GL account number for threshold resolution (e.g., "18412")
    
    Returns:
        DataFrame with additional threshold columns:
            - threshold_usd: Resolved threshold value in USD
            - status: "OK" or "INVESTIGATE"
            - threshold_contract_version: Contract version used
            - threshold_contract_hash: Contract hash for evidence
            - threshold_rule_description: Matched rule description
            - threshold_source: "catalog" or "fallback"
            - threshold_specificity: Specificity score of matched rule
        
        All original columns are preserved.
    
    Raises:
        ValueError: If required columns are missing from variance_df
    
    Examples:
        >>> # After computing variance with FX conversion
        >>> variance_df = compute_variance_pivot_local(nav_pivot, tv_pivot, fx_converter, cutoff_date)
        >>> 
        >>> # Evaluate thresholds for GL 18412 (Voucher Liabilities)
        >>> evaluated_df = evaluate_thresholds_variance_pivot(variance_df, gl_account="18412")
        >>> 
        >>> # Check results
        >>> print(evaluated_df[["country_code", "category", "variance_amount_usd", "threshold_usd", "status"]])
        >>> 
        >>> # Find buckets requiring investigation
        >>> investigate = evaluated_df[evaluated_df["status"] == "INVESTIGATE"]
        >>> print(f"Buckets to investigate: {len(investigate)}")
    
    Notes:
        - Threshold evaluation happens on USD amounts (post-FX conversion)
        - Missing FX rates (NaN variance_usd) are marked as "INVESTIGATE" by default
        - Threshold resolution uses full precedence: country → gl_account → category → voucher_type
        - All threshold metadata is included for complete audit trail
    """
    # Import here to avoid circular dependency
    from src.core.reconciliation.thresholds import resolve_bucket_threshold
    
    # Validate required columns
    required_cols = ["country_code", "category", "voucher_type", "variance_amount_usd"]
    missing_cols = [col for col in required_cols if col not in variance_df.columns]
    if missing_cols:
        raise ValueError(
            f"Required columns missing from variance_df: {missing_cols}. "
            f"Available columns: {list(variance_df.columns)}"
        )
    
    if variance_df.empty:
        logger.warning("Empty variance DataFrame, returning as-is with threshold columns")
        # Add empty threshold columns
        variance_df["threshold_usd"] = pd.Series(dtype=float)
        variance_df["status"] = pd.Series(dtype=str)
        variance_df["threshold_contract_version"] = pd.Series(dtype=int)
        variance_df["threshold_contract_hash"] = pd.Series(dtype=str)
        variance_df["threshold_rule_description"] = pd.Series(dtype=str)
        variance_df["threshold_source"] = pd.Series(dtype=str)
        variance_df["threshold_specificity"] = pd.Series(dtype=int)
        return variance_df
    
    # Make a copy to avoid modifying input
    result_df = variance_df.copy()
    
    # Initialize threshold columns
    threshold_data = []
    
    # Resolve threshold for each row
    for idx, row in result_df.iterrows():
        country_code = row["country_code"]
        category = row["category"]
        voucher_type = row["voucher_type"]
        variance_usd = row["variance_amount_usd"]
        
        # Resolve threshold with full context
        resolved = resolve_bucket_threshold(
            country_code=country_code,
            gl_account=gl_account,
            category=category,
            voucher_type=voucher_type,
        )
        
        # Determine status
        # If variance_usd is NaN (missing FX rate), mark as INVESTIGATE by default
        if pd.isna(variance_usd):
            status = "INVESTIGATE"
            logger.warning(
                f"Missing variance_usd for {country_code}/{category}/{voucher_type}, "
                f"marking as INVESTIGATE"
            )
        else:
            abs_variance = abs(variance_usd)
            status = "OK" if abs_variance < resolved.value_usd else "INVESTIGATE"
        
        # Store threshold metadata
        threshold_data.append({
            "threshold_usd": resolved.value_usd,
            "status": status,
            "threshold_contract_version": resolved.contract_version,
            "threshold_contract_hash": resolved.contract_hash,
            "threshold_rule_description": resolved.matched_rule_description,
            "threshold_source": resolved.source,
            "threshold_specificity": resolved.specificity_score,
        })
    
    # Add threshold columns to result
    threshold_df = pd.DataFrame(threshold_data, index=result_df.index)
    result_df = pd.concat([result_df, threshold_df], axis=1)
    
    # Log summary
    investigate_count = (result_df["status"] == "INVESTIGATE").sum()
    ok_count = (result_df["status"] == "OK").sum()
    
    logger.info(
        f"Evaluated thresholds for {len(result_df)} buckets (GL {gl_account}): "
        f"{investigate_count} INVESTIGATE, {ok_count} OK"
    )
    
    if result_df["threshold_source"].eq("fallback").any():
        fallback_count = result_df["threshold_source"].eq("fallback").sum()
        logger.warning(
            f"{fallback_count} rows used fallback thresholds. "
            f"Consider adding threshold contracts for better control."
        )
    
    return result_df


__all__ = [
    "compute_variance_pivot_local",
    "evaluate_thresholds_variance_pivot",
]
