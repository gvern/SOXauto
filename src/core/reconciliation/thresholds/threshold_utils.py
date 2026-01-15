"""
Threshold Resolution Utilities for SOXauto Threshold Catalog System.

This module provides threshold resolution logic with precedence rules
and fallback behavior for backward compatibility.

Key Functions:
    - resolve_threshold: Resolve threshold for a specific context with precedence
    - get_fallback_threshold: Get fallback threshold when no contract available

Precedence Rules (most specific wins):
1. (country, gl_account, category, voucher_type, threshold_type)
2. (country, gl_account, category, threshold_type)
3. (country, gl_account, threshold_type)
4. (country, threshold_type)
5. DEFAULT contract
6. Hardcoded fallback (for backward compatibility)
"""

import logging
from typing import Optional

from .models import ThresholdType, ResolvedThreshold
from .registry import get_contract

logger = logging.getLogger(__name__)


# Fallback thresholds for backward compatibility
FALLBACK_THRESHOLDS = {
    ThresholdType.BUCKET_USD: 1000.0,
    ThresholdType.LINE_ITEM_USD: 1000.0,
    ThresholdType.COUNTRY_MATERIALITY_USD: 10000.0,
}


def get_fallback_threshold(
    threshold_type: ThresholdType,
    country_code: str = "UNKNOWN"
) -> ResolvedThreshold:
    """
    Get fallback threshold when no contract is available.
    
    Returns hardcoded default for backward compatibility.
    
    Args:
        threshold_type: Type of threshold to resolve
        country_code: Country code (for logging only)
    
    Returns:
        ResolvedThreshold with source="fallback"
    """
    value_usd = FALLBACK_THRESHOLDS.get(threshold_type, 1000.0)
    
    logger.warning(
        f"Using fallback threshold for {country_code}/{threshold_type.value}: "
        f"{value_usd} USD. Consider adding a threshold contract."
    )
    
    return ResolvedThreshold(
        value_usd=value_usd,
        threshold_type=threshold_type,
        country_code=country_code,
        contract_version=0,  # 0 indicates fallback
        contract_hash="fallback",
        matched_rule_description=f"Hardcoded fallback: {value_usd} USD",
        source="fallback",
        specificity_score=0,
    )


def resolve_threshold(
    country_code: str,
    threshold_type: ThresholdType,
    gl_account: Optional[str] = None,
    category: Optional[str] = None,
    voucher_type: Optional[str] = None,
    version: Optional[int] = None,
) -> ResolvedThreshold:
    """
    Resolve threshold for a specific context using precedence rules.
    
    Precedence (most specific wins):
    1. Country-specific contract with matching rule (most specific scope)
    2. DEFAULT contract with matching rule (most specific scope)
    3. Hardcoded fallback (for backward compatibility)
    
    Within a contract, rules are matched by specificity:
    - (gl_account, category, voucher_type) > (gl_account, category) > (gl_account) > (no filters)
    
    Args:
        country_code: Country code (e.g., "EG", "NG")
        threshold_type: Type of threshold to resolve
        gl_account: Optional GL account filter
        category: Optional category filter
        voucher_type: Optional voucher type filter
        version: Optional version number (defaults to env var or version 1)
    
    Returns:
        ResolvedThreshold with full audit metadata
    
    Examples:
        >>> # Resolve bucket threshold for Egypt GL 18412
        >>> resolved = resolve_threshold("EG", ThresholdType.BUCKET_USD, gl_account="18412")
        >>> print(resolved.value_usd)
        1000.0
        >>> print(resolved.source)
        'catalog'
        
        >>> # Resolve with full context
        >>> resolved = resolve_threshold(
        ...     "EG",
        ...     ThresholdType.BUCKET_USD,
        ...     gl_account="18412",
        ...     category="Voucher",
        ...     voucher_type="refund"
        ... )
        
        >>> # Fallback for unknown country
        >>> resolved = resolve_threshold("XX", ThresholdType.BUCKET_USD)
        >>> print(resolved.source)
        'fallback'
    """
    # Try country-specific contract first
    try:
        contract, contract_hash = get_contract(country_code, version)
        
        # Find matching rules (sorted by specificity)
        matching_rules = contract.find_matching_rules(
            threshold_type=threshold_type,
            gl_account=gl_account,
            category=category,
            voucher_type=voucher_type,
        )
        
        if matching_rules:
            # Use most specific rule (first in sorted list)
            best_rule = matching_rules[0]
            
            logger.debug(
                f"Resolved threshold for {country_code}/{threshold_type.value}: "
                f"{best_rule.value_usd} USD (specificity={best_rule.specificity_score()})"
            )
            
            return ResolvedThreshold(
                value_usd=best_rule.value_usd,
                threshold_type=threshold_type,
                country_code=country_code,
                contract_version=contract.version,
                contract_hash=contract_hash,
                matched_rule_description=best_rule.description,
                source="catalog",
                specificity_score=best_rule.specificity_score(),
            )
        
        logger.debug(
            f"No matching rules in {country_code} contract for {threshold_type.value}, "
            f"falling back to DEFAULT"
        )
    
    except FileNotFoundError:
        logger.debug(
            f"No contract found for {country_code}, falling back to DEFAULT"
        )
    except Exception as e:
        logger.warning(
            f"Error loading contract for {country_code}: {e}. "
            f"Falling back to DEFAULT"
        )
    
    # Try DEFAULT contract
    try:
        contract, contract_hash = get_contract("DEFAULT", version)
        
        matching_rules = contract.find_matching_rules(
            threshold_type=threshold_type,
            gl_account=gl_account,
            category=category,
            voucher_type=voucher_type,
        )
        
        if matching_rules:
            best_rule = matching_rules[0]
            
            logger.debug(
                f"Resolved threshold for {country_code}/{threshold_type.value} "
                f"using DEFAULT contract: {best_rule.value_usd} USD"
            )
            
            return ResolvedThreshold(
                value_usd=best_rule.value_usd,
                threshold_type=threshold_type,
                country_code=country_code,  # Keep original country code
                contract_version=contract.version,
                contract_hash=contract_hash,
                matched_rule_description=f"DEFAULT: {best_rule.description}",
                source="catalog",
                specificity_score=best_rule.specificity_score(),
            )
    
    except Exception as e:
        logger.warning(
            f"Error loading DEFAULT contract: {e}. Using hardcoded fallback."
        )
    
    # Final fallback to hardcoded values
    return get_fallback_threshold(threshold_type, country_code)


def resolve_bucket_threshold(
    country_code: str,
    gl_account: Optional[str] = None,
    category: Optional[str] = None,
    voucher_type: Optional[str] = None,
) -> ResolvedThreshold:
    """
    Convenience function to resolve BUCKET_USD threshold.
    
    Args:
        country_code: Country code
        gl_account: Optional GL account filter
        category: Optional category filter
        voucher_type: Optional voucher type filter
    
    Returns:
        ResolvedThreshold for BUCKET_USD
    """
    return resolve_threshold(
        country_code=country_code,
        threshold_type=ThresholdType.BUCKET_USD,
        gl_account=gl_account,
        category=category,
        voucher_type=voucher_type,
    )


def resolve_line_item_threshold(
    country_code: str,
    gl_account: Optional[str] = None,
    category: Optional[str] = None,
    voucher_type: Optional[str] = None,
) -> ResolvedThreshold:
    """
    Convenience function to resolve LINE_ITEM_USD threshold.
    
    Args:
        country_code: Country code
        gl_account: Optional GL account filter
        category: Optional category filter
        voucher_type: Optional voucher type filter
    
    Returns:
        ResolvedThreshold for LINE_ITEM_USD
    """
    return resolve_threshold(
        country_code=country_code,
        threshold_type=ThresholdType.LINE_ITEM_USD,
        gl_account=gl_account,
        category=category,
        voucher_type=voucher_type,
    )


__all__ = [
    "resolve_threshold",
    "resolve_bucket_threshold",
    "resolve_line_item_threshold",
    "get_fallback_threshold",
]
