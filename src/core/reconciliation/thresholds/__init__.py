"""
Threshold Catalog System for SOXauto.

This package provides a catalog-driven threshold system for variance analysis
and reconciliation. It replaces hardcoded thresholds with YAML-based contracts
that support precedence rules, versioning, and cryptographic hashing for evidence.

Key Components:
    - models: Data models for threshold rules, contracts, and resolved thresholds
    - registry: YAML loading, caching, and contract management
    - threshold_utils: Threshold resolution with precedence logic

Quick Start:
    >>> from src.core.reconciliation.thresholds import resolve_threshold, ThresholdType
    >>> 
    >>> # Resolve a bucket threshold for Egypt
    >>> resolved = resolve_threshold("EG", ThresholdType.BUCKET_USD, gl_account="18412")
    >>> print(f"Threshold: {resolved.value_usd} USD")
    >>> print(f"Source: {resolved.source}")
    >>> print(f"Contract version: {resolved.contract_version}")
    >>> print(f"Contract hash: {resolved.contract_hash[:8]}...")

Threshold Types:
    - BUCKET_USD: Variance pivot aggregates (Category × Voucher Type)
    - LINE_ITEM_USD: Individual voucher/transaction line items
    - COUNTRY_MATERIALITY_USD: Country-level materiality (future use)

Precedence Rules (most specific wins):
    1. Country-specific contract with matching rule
    2. DEFAULT contract with matching rule
    3. Hardcoded fallback (1000 USD for backward compatibility)
"""

from .models import (
    ThresholdType,
    ThresholdScope,
    ThresholdRule,
    ThresholdContract,
    ResolvedThreshold,
)
from .registry import (
    load_contract,
    get_contract,
    get_contract_hash,
    get_available_countries,
    clear_cache,
)
from .threshold_utils import (
    resolve_threshold,
    resolve_bucket_threshold,
    resolve_line_item_threshold,
    get_fallback_threshold,
)

__all__ = [
    # Models
    "ThresholdType",
    "ThresholdScope",
    "ThresholdRule",
    "ThresholdContract",
    "ResolvedThreshold",
    # Registry
    "load_contract",
    "get_contract",
    "get_contract_hash",
    "get_available_countries",
    "clear_cache",
    # Threshold resolution
    "resolve_threshold",
    "resolve_bucket_threshold",
    "resolve_line_item_threshold",
    "get_fallback_threshold",
]
