"""
Unit Tests for Threshold Catalog System.

Tests YAML loading, hashing, precedence resolution, and fallback behavior.
"""

import os
import pytest
from pathlib import Path

from src.core.reconciliation.thresholds import (
    ThresholdType,
    ThresholdScope,
    ThresholdRule,
    ThresholdContract,
    ResolvedThreshold,
    load_contract,
    get_contract,
    get_contract_hash,
    resolve_threshold,
    resolve_bucket_threshold,
    resolve_line_item_threshold,
    get_fallback_threshold,
    clear_cache,
)


class TestThresholdModels:
    """Test threshold data models."""
    
    def test_threshold_scope_matches(self):
        """Test ThresholdScope.matches() logic."""
        # Empty scope matches everything
        scope = ThresholdScope()
        assert scope.matches() is True
        assert scope.matches(gl_account="18412") is True
        assert scope.matches(category="Voucher") is True
        
        # GL account filter
        scope = ThresholdScope(gl_accounts=["18412", "18350"])
        assert scope.matches(gl_account="18412") is True
        assert scope.matches(gl_account="18350") is True
        assert scope.matches(gl_account="13003") is False
        
        # Category filter
        scope = ThresholdScope(categories=["Voucher", "Compensation"])
        assert scope.matches(category="Voucher") is True
        assert scope.matches(category="Compensation") is True
        assert scope.matches(category="Other") is False
        
        # Combined filters (all must match)
        scope = ThresholdScope(
            gl_accounts=["18412"],
            categories=["Voucher"],
        )
        assert scope.matches(gl_account="18412", category="Voucher") is True
        assert scope.matches(gl_account="18412", category="Other") is False
        assert scope.matches(gl_account="13003", category="Voucher") is False
    
    def test_threshold_scope_specificity(self):
        """Test ThresholdScope.specificity_score()."""
        assert ThresholdScope().specificity_score() == 0
        assert ThresholdScope(gl_accounts=["18412"]).specificity_score() == 1
        assert ThresholdScope(categories=["Voucher"]).specificity_score() == 1
        assert ThresholdScope(
            gl_accounts=["18412"],
            categories=["Voucher"]
        ).specificity_score() == 2
        assert ThresholdScope(
            gl_accounts=["18412"],
            categories=["Voucher"],
            voucher_types=["refund"]
        ).specificity_score() == 3
    
    def test_threshold_rule_validation(self):
        """Test ThresholdRule validation."""
        # Valid rule
        rule = ThresholdRule(
            threshold_type=ThresholdType.BUCKET_USD,
            value_usd=1000.0,
            description="Test rule",
        )
        assert rule.value_usd == 1000.0
        
        # Negative threshold should raise error
        with pytest.raises(ValueError, match="non-negative"):
            ThresholdRule(
                threshold_type=ThresholdType.BUCKET_USD,
                value_usd=-100.0,
                description="Invalid",
            )
    
    def test_threshold_contract_validation(self):
        """Test ThresholdContract validation."""
        rule = ThresholdRule(
            threshold_type=ThresholdType.BUCKET_USD,
            value_usd=1000.0,
            description="Test",
        )
        
        # Valid contract
        contract = ThresholdContract(
            version=1,
            effective_date="2025-01-01",
            description="Test contract",
            country_code="EG",
            rules=[rule],
        )
        assert contract.version == 1
        
        # Version < 1 should raise error
        with pytest.raises(ValueError, match="version must be"):
            ThresholdContract(
                version=0,
                effective_date="2025-01-01",
                description="Invalid",
                country_code="EG",
                rules=[rule],
            )
        
        # Empty rules should raise error
        with pytest.raises(ValueError, match="at least one rule"):
            ThresholdContract(
                version=1,
                effective_date="2025-01-01",
                description="Invalid",
                country_code="EG",
                rules=[],
            )
    
    def test_contract_find_matching_rules(self):
        """Test ThresholdContract.find_matching_rules() with precedence."""
        rules = [
            # Most general
            ThresholdRule(
                threshold_type=ThresholdType.BUCKET_USD,
                value_usd=1000.0,
                description="General",
            ),
            # More specific (GL account)
            ThresholdRule(
                threshold_type=ThresholdType.BUCKET_USD,
                value_usd=2000.0,
                description="GL 18412",
                scope=ThresholdScope(gl_accounts=["18412"]),
            ),
            # Most specific (GL + category)
            ThresholdRule(
                threshold_type=ThresholdType.BUCKET_USD,
                value_usd=3000.0,
                description="GL 18412 Voucher",
                scope=ThresholdScope(
                    gl_accounts=["18412"],
                    categories=["Voucher"],
                ),
            ),
        ]
        
        contract = ThresholdContract(
            version=1,
            effective_date="2025-01-01",
            description="Test",
            country_code="EG",
            rules=rules,
        )
        
        # Most specific match should come first
        matches = contract.find_matching_rules(
            threshold_type=ThresholdType.BUCKET_USD,
            gl_account="18412",
            category="Voucher",
        )
        assert len(matches) == 3
        assert matches[0].value_usd == 3000.0  # Most specific
        assert matches[1].value_usd == 2000.0
        assert matches[2].value_usd == 1000.0
        
        # Filter by GL only
        matches = contract.find_matching_rules(
            threshold_type=ThresholdType.BUCKET_USD,
            gl_account="18412",
        )
        assert len(matches) == 3
        # Most specific that matches GL only: GL+category (specificity=2)
        # All three rules match when only GL is specified, sorted by specificity
        assert matches[0].value_usd == 3000.0  # GL+category (specificity=2)
        assert matches[1].value_usd == 2000.0  # GL only (specificity=1)
        assert matches[2].value_usd == 1000.0  # No filter (specificity=0)
    
    def test_resolved_threshold_to_dict(self):
        """Test ResolvedThreshold.to_dict()."""
        resolved = ResolvedThreshold(
            value_usd=1000.0,
            threshold_type=ThresholdType.BUCKET_USD,
            country_code="EG",
            contract_version=1,
            contract_hash="abc123",
            matched_rule_description="Test rule",
            source="catalog",
            specificity_score=2,
        )
        
        result = resolved.to_dict()
        assert result["value_usd"] == 1000.0
        assert result["threshold_type"] == "BUCKET_USD"
        assert result["country_code"] == "EG"
        assert result["source"] == "catalog"


class TestThresholdRegistry:
    """Test threshold contract loading and caching."""
    
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()
    
    def test_load_default_contract(self):
        """Test loading DEFAULT contract."""
        contract, contract_hash = load_contract("DEFAULT")
        
        assert contract.country_code == "DEFAULT"
        assert contract.version >= 1
        assert len(contract.rules) >= 2  # At least BUCKET_USD and LINE_ITEM_USD
        assert isinstance(contract_hash, str)
        assert len(contract_hash) == 64  # SHA256 hex digest length
    
    def test_load_eg_contract(self):
        """Test loading Egypt contract."""
        contract, contract_hash = load_contract("EG")
        
        assert contract.country_code == "EG"
        assert contract.version >= 1
        assert len(contract.rules) >= 2
        assert isinstance(contract_hash, str)
    
    def test_load_nonexistent_contract(self):
        """Test loading non-existent contract raises error."""
        with pytest.raises(FileNotFoundError):
            load_contract("NONEXISTENT")
    
    def test_contract_hash_consistency(self):
        """Test that contract hash is consistent across loads."""
        _, hash1 = load_contract("DEFAULT")
        _, hash2 = load_contract("DEFAULT")
        assert hash1 == hash2
    
    def test_get_contract_caching(self):
        """Test that get_contract() uses caching."""
        # First call loads from file
        contract1, hash1 = get_contract("DEFAULT")
        
        # Second call should return cached result
        contract2, hash2 = get_contract("DEFAULT")
        
        # Should be the same object (cached)
        assert contract1 is contract2
        assert hash1 == hash2
    
    def test_version_pinning_env_var(self):
        """Test version pinning via environment variable."""
        # Set environment variable
        os.environ["THRESHOLD_VERSION_DEFAULT"] = "1"
        
        try:
            clear_cache()
            contract, _ = load_contract("DEFAULT")
            assert contract.version == 1
        finally:
            # Cleanup
            del os.environ["THRESHOLD_VERSION_DEFAULT"]
            clear_cache()


class TestThresholdResolution:
    """Test threshold resolution with precedence."""
    
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()
    
    def test_resolve_default_bucket_threshold(self):
        """Test resolving threshold from DEFAULT contract."""
        resolved = resolve_threshold(
            country_code="UNKNOWN_COUNTRY",
            threshold_type=ThresholdType.BUCKET_USD,
        )
        
        assert resolved.value_usd > 0
        assert resolved.threshold_type == ThresholdType.BUCKET_USD
        assert resolved.source in ["catalog", "fallback"]
        assert isinstance(resolved.contract_version, int)
        assert isinstance(resolved.contract_hash, str)
    
    def test_resolve_eg_bucket_threshold(self):
        """Test resolving Egypt-specific bucket threshold."""
        resolved = resolve_threshold(
            country_code="EG",
            threshold_type=ThresholdType.BUCKET_USD,
            gl_account="18412",
        )
        
        assert resolved.value_usd > 0
        assert resolved.country_code == "EG"
        assert resolved.threshold_type == ThresholdType.BUCKET_USD
        assert resolved.source == "catalog"
        assert resolved.contract_version >= 1
    
    def test_resolve_line_item_threshold(self):
        """Test resolving LINE_ITEM_USD threshold."""
        resolved = resolve_line_item_threshold(
            country_code="EG",
            gl_account="18412",
        )
        
        assert resolved.threshold_type == ThresholdType.LINE_ITEM_USD
        assert resolved.value_usd > 0
    
    def test_resolve_with_full_context(self):
        """Test resolution with full context (country, GL, category, voucher_type)."""
        resolved = resolve_threshold(
            country_code="EG",
            threshold_type=ThresholdType.BUCKET_USD,
            gl_account="18412",
            category="Voucher",
            voucher_type="refund",
        )
        
        assert resolved.value_usd > 0
        assert resolved.country_code == "EG"
    
    def test_fallback_threshold(self):
        """Test fallback threshold when no contract available."""
        resolved = get_fallback_threshold(
            threshold_type=ThresholdType.BUCKET_USD,
            country_code="TEST",
        )
        
        assert resolved.value_usd == 1000.0  # Hardcoded fallback
        assert resolved.source == "fallback"
        assert resolved.contract_version == 0
        assert resolved.contract_hash == "fallback"
    
    def test_precedence_country_over_default(self):
        """Test that country-specific rules take precedence over DEFAULT."""
        # Get EG-specific threshold
        eg_resolved = resolve_threshold(
            country_code="EG",
            threshold_type=ThresholdType.BUCKET_USD,
            gl_account="18412",
        )
        
        # Should use EG contract, not DEFAULT
        # (Exact value depends on EG.yaml, but should be from catalog)
        assert eg_resolved.source == "catalog"
        assert eg_resolved.country_code == "EG"
    
    def test_convenience_functions(self):
        """Test convenience resolution functions."""
        bucket = resolve_bucket_threshold("EG", gl_account="18412")
        assert bucket.threshold_type == ThresholdType.BUCKET_USD
        
        line_item = resolve_line_item_threshold("EG", gl_account="18412")
        assert line_item.threshold_type == ThresholdType.LINE_ITEM_USD


class TestThresholdIntegration:
    """Integration tests for threshold system."""
    
    def test_round_trip_load_and_resolve(self):
        """Test full workflow: load contract, resolve threshold."""
        # Load contract
        contract, contract_hash = load_contract("EG")
        
        # Resolve threshold
        resolved = resolve_threshold(
            country_code="EG",
            threshold_type=ThresholdType.BUCKET_USD,
            gl_account="18412",
        )
        
        # Verify resolution matches contract
        assert resolved.contract_hash == contract_hash
        assert resolved.contract_version == contract.version
    
    def test_different_threshold_types(self):
        """Test resolving different threshold types for same context."""
        bucket = resolve_threshold("EG", ThresholdType.BUCKET_USD, gl_account="18412")
        line_item = resolve_threshold("EG", ThresholdType.LINE_ITEM_USD, gl_account="18412")
        
        # Should resolve to different values
        assert bucket.threshold_type != line_item.threshold_type
        # Typically line_item > bucket, but not guaranteed
        assert bucket.value_usd > 0
        assert line_item.value_usd > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
