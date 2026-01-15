"""
Threshold Models for SOXauto Threshold Catalog System.

This module defines the data models for threshold contracts and resolved thresholds.
These models are used to load, validate, and resolve threshold rules from YAML contracts.

Key Models:
    - ThresholdRule: A single threshold rule with type, value, scope, and description
    - ThresholdContract: A complete contract containing multiple rules and metadata
    - ResolvedThreshold: The result of resolving a threshold for a specific context
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ThresholdType(str, Enum):
    """
    Threshold types supported by the catalog system.
    
    BUCKET_USD: Applied to variance pivot aggregates (Category × Voucher Type)
                Used to flag buckets requiring investigation.
    
    LINE_ITEM_USD: Applied to individual voucher/transaction line items
                   Used to mark material line items in review tables.
    
    COUNTRY_MATERIALITY_USD: Country-level materiality threshold
                            Reserved for future aggregate reporting.
                            Not applied to bucket or line-item evaluation.
    """
    BUCKET_USD = "BUCKET_USD"
    LINE_ITEM_USD = "LINE_ITEM_USD"
    COUNTRY_MATERIALITY_USD = "COUNTRY_MATERIALITY_USD"


@dataclass
class ThresholdScope:
    """
    Scope filters for a threshold rule.
    
    Defines which GL accounts, categories, and voucher types a rule applies to.
    All filters are optional - missing filters mean the rule applies to all.
    
    Attributes:
        gl_accounts: List of GL account numbers (e.g., ["18412"])
        categories: List of category names (e.g., ["Compensation", "Voucher"])
        voucher_types: List of voucher types (e.g., ["refund", "store_credit"])
    """
    gl_accounts: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    voucher_types: Optional[List[str]] = None
    
    def matches(
        self,
        gl_account: Optional[str] = None,
        category: Optional[str] = None,
        voucher_type: Optional[str] = None
    ) -> bool:
        """
        Check if this scope matches the given context.
        
        Returns True if all non-None context values match the scope filters.
        Empty/None scope filters match any value.
        
        Args:
            gl_account: GL account number to check
            category: Category name to check
            voucher_type: Voucher type to check
        
        Returns:
            True if the scope matches the context, False otherwise
        """
        # Check GL account
        if self.gl_accounts and gl_account:
            if gl_account not in self.gl_accounts:
                return False
        
        # Check category
        if self.categories and category:
            if category not in self.categories:
                return False
        
        # Check voucher type
        if self.voucher_types and voucher_type:
            if voucher_type not in self.voucher_types:
                return False
        
        return True
    
    def specificity_score(self) -> int:
        """
        Calculate specificity score for precedence resolution.
        
        Higher score = more specific rule.
        Used to implement "most specific wins" precedence.
        
        Returns:
            Specificity score (0-3)
        """
        score = 0
        if self.gl_accounts:
            score += 1
        if self.categories:
            score += 1
        if self.voucher_types:
            score += 1
        return score


@dataclass
class ThresholdRule:
    """
    A single threshold rule from a contract.
    
    Attributes:
        threshold_type: Type of threshold (BUCKET_USD, LINE_ITEM_USD, etc.)
        value_usd: Threshold value in USD
        description: Human-readable description of the rule
        scope: Optional scope filters (GL accounts, categories, voucher types)
    """
    threshold_type: ThresholdType
    value_usd: float
    description: str
    scope: ThresholdScope = field(default_factory=ThresholdScope)
    
    def __post_init__(self):
        """Validate rule after initialization."""
        if self.value_usd < 0:
            raise ValueError(f"Threshold value must be non-negative, got {self.value_usd}")
        
        # Convert string threshold_type to enum if needed
        if isinstance(self.threshold_type, str):
            self.threshold_type = ThresholdType(self.threshold_type)
    
    def matches(
        self,
        gl_account: Optional[str] = None,
        category: Optional[str] = None,
        voucher_type: Optional[str] = None
    ) -> bool:
        """Check if this rule matches the given context."""
        return self.scope.matches(gl_account, category, voucher_type)
    
    def specificity_score(self) -> int:
        """Calculate specificity score for precedence."""
        return self.scope.specificity_score()


@dataclass
class ThresholdContract:
    """
    A complete threshold contract containing multiple rules and metadata.
    
    Attributes:
        version: Contract version number (integer)
        effective_date: Date when contract becomes effective (YYYY-MM-DD)
        description: Human-readable description of the contract
        country_code: Country code this contract applies to (or "DEFAULT")
        rules: List of threshold rules in this contract
    """
    version: int
    effective_date: str
    description: str
    country_code: str
    rules: List[ThresholdRule]
    
    def __post_init__(self):
        """Validate contract after initialization."""
        if self.version < 1:
            raise ValueError(f"Contract version must be >= 1, got {self.version}")
        
        if not self.rules:
            raise ValueError("Contract must contain at least one rule")
        
        # Validate country_code format
        if not self.country_code or not isinstance(self.country_code, str):
            raise ValueError(f"Invalid country_code: {self.country_code}")
    
    def find_matching_rules(
        self,
        threshold_type: ThresholdType,
        gl_account: Optional[str] = None,
        category: Optional[str] = None,
        voucher_type: Optional[str] = None
    ) -> List[ThresholdRule]:
        """
        Find all rules matching the given criteria.
        
        Args:
            threshold_type: Type of threshold to find
            gl_account: Optional GL account filter
            category: Optional category filter
            voucher_type: Optional voucher type filter
        
        Returns:
            List of matching rules, sorted by specificity (most specific first)
        """
        matching = [
            rule for rule in self.rules
            if rule.threshold_type == threshold_type
            and rule.matches(gl_account, category, voucher_type)
        ]
        
        # Sort by specificity (most specific first)
        matching.sort(key=lambda r: r.specificity_score(), reverse=True)
        
        return matching


@dataclass
class ResolvedThreshold:
    """
    Result of resolving a threshold for a specific context.
    
    Contains the threshold value plus full audit trail metadata.
    
    Attributes:
        value_usd: Resolved threshold value in USD
        threshold_type: Type of threshold resolved
        country_code: Country code used for resolution
        contract_version: Version of contract used
        contract_hash: SHA256 hash of contract file for evidence
        matched_rule_description: Description from the matched rule
        source: Source of threshold ("catalog" or "fallback")
        specificity_score: Specificity score of matched rule (for audit)
    """
    value_usd: float
    threshold_type: ThresholdType
    country_code: str
    contract_version: int
    contract_hash: str
    matched_rule_description: str
    source: str  # "catalog" or "fallback"
    specificity_score: int = 0
    
    def __post_init__(self):
        """Validate resolved threshold after initialization."""
        if self.value_usd < 0:
            raise ValueError(f"Resolved threshold must be non-negative, got {self.value_usd}")
        
        if self.source not in ["catalog", "fallback"]:
            raise ValueError(f"Invalid source: {self.source}. Must be 'catalog' or 'fallback'")
        
        # Convert string threshold_type to enum if needed
        if isinstance(self.threshold_type, str):
            self.threshold_type = ThresholdType(self.threshold_type)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/evidence."""
        return {
            "value_usd": self.value_usd,
            "threshold_type": self.threshold_type.value,
            "country_code": self.country_code,
            "contract_version": self.contract_version,
            "contract_hash": self.contract_hash,
            "matched_rule_description": self.matched_rule_description,
            "source": self.source,
            "specificity_score": self.specificity_score,
        }


__all__ = [
    "ThresholdType",
    "ThresholdScope",
    "ThresholdRule",
    "ThresholdContract",
    "ResolvedThreshold",
]
