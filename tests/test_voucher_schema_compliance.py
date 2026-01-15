"""
Test Suite for Voucher Classification Schema Compliance.

Validates that the voucher classification system produces only
schema-compliant values and combinations.
"""

import pytest
import pandas as pd
from typing import Set, Tuple

from src.core.reconciliation.voucher_classification.cat_pipeline import categorize_nav_vouchers
from src.core.reconciliation.voucher_classification.cat_nav_classifier import classify_integration_type
from src.core.reconciliation.voucher_classification.cat_issuance_classifier import classify_issuance
from src.core.reconciliation.voucher_classification.cat_usage_classifier import classify_usage
from src.core.reconciliation.voucher_classification.cat_expired_classifier import classify_expired
from src.core.reconciliation.voucher_classification.cat_vtc_classifier import (
    classify_vtc_bank_account,
    classify_vtc_pattern,
)


# Schema Definition
ALLOWED_INTEGRATION_TYPES = {"Manual", "Integration"}
ALLOWED_CATEGORIES = {"Issuance", "Cancellation", "Usage", "Expired", "VTC"}
ALLOWED_VOUCHER_TYPES = {"Refund", "Apology", "JForce", "Store Credit"}

VALID_COMBINATIONS = {
    "Issuance": {"Refund", "Apology", "JForce", "Store Credit"},
    "Cancellation": {"Apology", "Store Credit"},
    "Usage": {"Refund", "Apology", "JForce", "Store Credit"},
    "Expired": {"Apology", "JForce", "Refund", "Store Credit"},
    "VTC": {"Refund"},
}

INTEGRATION_USER_ID = "JUMIA/NAV31AFR.BATCH.SRVC"


@pytest.fixture
def sample_nav_data():
    """Create sample NAV GL entries for testing."""
    return pd.DataFrame({
        "Chart of Accounts No_": ["18412"] * 10,
        "Amount": [-100.0, -50.0, 100.0, 50.0, 30.0, -75.0, 25.0, 150.0, -200.0, 40.0],
        "User ID": [
            INTEGRATION_USER_ID,  # Integration
            "USER/01",  # Manual
            INTEGRATION_USER_ID,  # Integration
            "USER/02",  # Manual
            "USER/03",  # Manual
            INTEGRATION_USER_ID,  # Integration
            "USER/04",  # Manual
            INTEGRATION_USER_ID,  # Integration
            "USER/05",  # Manual
            "USER/06",  # Manual
        ],
        "Document Description": [
            "REFUND voucher",
            "COMMERCIAL GESTURE",
            "ITEMPRICECREDIT usage",
            "EXPR_APLGY cleanup",
            "MANUAL RND payment",
            "PYT_PF issuance",
            "EXPR_JFORCE expired",
            "VOUCHER ACCRUAL cancellation",
            "Regular issuance",
            "EXPR_STR CRDT expired",
        ],
        "Bal_ Account Type": [""] * 10,
        "Document Type": [""] * 10,
        "Document No": ["DOC001"] * 10,
        "Voucher No_": [""] * 10,
        "Comment": [""] * 10,
    })


class TestIntegrationTypeClassification:
    """Test Integration_Type classification."""
    
    def test_integration_user_detection(self):
        """Test that integration user is correctly detected."""
        df = pd.DataFrame({
            "User ID": [INTEGRATION_USER_ID, "USER/01", INTEGRATION_USER_ID.lower()]
        })
        
        result = classify_integration_type(df)
        
        assert "Integration_Type" in result.columns
        assert result["Integration_Type"].iloc[0] == "Integration"
        assert result["Integration_Type"].iloc[1] == "Manual"
        assert result["Integration_Type"].iloc[2] == "Integration"  # Case-insensitive
    
    def test_integration_type_allowed_values(self, sample_nav_data):
        """Test that only allowed Integration_Type values are produced."""
        result = classify_integration_type(sample_nav_data)
        
        observed_types = set(result["Integration_Type"].dropna().unique())
        assert observed_types <= ALLOWED_INTEGRATION_TYPES, (
            f"Invalid Integration_Type values: {observed_types - ALLOWED_INTEGRATION_TYPES}"
        )


class TestCategoryClassification:
    """Test Category (bridge_category) classification."""
    
    def test_category_allowed_values(self, sample_nav_data):
        """Test that only allowed Category values are produced."""
        result = categorize_nav_vouchers(sample_nav_data)
        
        observed_categories = set(result["bridge_category"].dropna().unique())
        assert observed_categories <= ALLOWED_CATEGORIES, (
            f"Invalid bridge_category values: {observed_categories - ALLOWED_CATEGORIES}"
        )
    
    def test_no_subcategories_in_category(self, sample_nav_data):
        """Test that bridge_category contains no sub-categories (no hyphens)."""
        result = categorize_nav_vouchers(sample_nav_data)
        
        categories_with_hyphens = result[
            result["bridge_category"].notna() & result["bridge_category"].str.contains("-", na=False)
        ]["bridge_category"].unique()
        
        assert len(categories_with_hyphens) == 0, (
            f"Found categories with sub-categories (hyphens): {categories_with_hyphens}"
        )


class TestVoucherTypeClassification:
    """Test Voucher Type classification."""
    
    def test_voucher_type_allowed_values(self, sample_nav_data):
        """Test that only allowed Voucher Type values are produced."""
        result = categorize_nav_vouchers(sample_nav_data)
        
        observed_types = set(result["voucher_type"].dropna().unique())
        assert observed_types <= ALLOWED_VOUCHER_TYPES, (
            f"Invalid voucher_type values: {observed_types - ALLOWED_VOUCHER_TYPES}"
        )


class TestCombinationCompliance:
    """Test that Category + Voucher Type combinations are schema-compliant."""
    
    def test_valid_combinations_only(self, sample_nav_data):
        """Test that only valid (category, voucher_type) combinations are produced."""
        result = categorize_nav_vouchers(sample_nav_data)
        
        # Get all non-null combinations
        combinations_df = result[
            result["bridge_category"].notna() & result["voucher_type"].notna()
        ][["bridge_category", "voucher_type"]]
        
        observed_combinations = set(
            zip(combinations_df["bridge_category"], combinations_df["voucher_type"])
        )
        
        # Check each combination
        invalid_combinations = []
        for category, voucher_type in observed_combinations:
            if category not in VALID_COMBINATIONS:
                invalid_combinations.append((category, voucher_type, "Unknown category"))
            elif voucher_type not in VALID_COMBINATIONS[category]:
                expected = VALID_COMBINATIONS[category]
                invalid_combinations.append((category, voucher_type, f"Expected: {expected}"))
        
        assert len(invalid_combinations) == 0, (
            f"Invalid combinations found: {invalid_combinations}"
        )
    
    def test_vtc_only_produces_refund(self):
        """Test that VTC category only produces Refund voucher type."""
        df = pd.DataFrame({
            "Chart of Accounts No_": ["18412"] * 3,
            "Amount": [100.0, 50.0, 75.0],
            "User ID": ["USER/01", "USER/02", "USER/03"],
            "Document Description": ["MANUAL RND", "PYT_ something", "Another RND"],
            "Bal_ Account Type": ["Bank Account", "", ""],
            "Comment": ["", "GTB payment", ""],
            "Integration_Type": ["Manual", "Manual", "Manual"],
            "bridge_category": [None, None, None],
            "voucher_type": [None, None, None],
        })
        
        result = classify_vtc_bank_account(df)
        result = classify_vtc_pattern(result)
        
        vtc_rows = result[result["bridge_category"] == "VTC"]
        if not vtc_rows.empty:
            assert all(vtc_rows["voucher_type"] == "Refund"), (
                "VTC must only produce Refund voucher type"
            )
    
    def test_cancellation_limited_types(self):
        """Test that Cancellation only produces Apology or Store Credit."""
        df = pd.DataFrame({
            "Chart of Accounts No_": ["18412"] * 2,
            "Amount": [50.0, 100.0],
            "User ID": [INTEGRATION_USER_ID, "USER/01"],
            "Document Description": ["VOUCHER ACCRUAL reversal", "Manual adjustment"],
            "Document Type": ["", "Credit Memo"],
            "Integration_Type": ["Integration", "Manual"],
            "bridge_category": [None, None],
            "voucher_type": [None, None],
        })
        
        from src.core.reconciliation.voucher_classification.cat_usage_classifier import classify_usage
        from src.core.reconciliation.voucher_classification.cat_expired_classifier import classify_manual_cancellation
        
        result = classify_usage(df)
        result = classify_manual_cancellation(result)
        
        cancellation_rows = result[result["bridge_category"] == "Cancellation"]
        if not cancellation_rows.empty:
            observed_types = set(cancellation_rows["voucher_type"].unique())
            assert observed_types <= {"Apology", "Store Credit"}, (
                f"Cancellation produced invalid types: {observed_types}"
            )


class TestIssuanceCompliance:
    """Test Issuance-specific schema compliance."""
    
    def test_issuance_produces_valid_types(self):
        """Test that Issuance produces only Refund, Apology, JForce, Store Credit."""
        df = pd.DataFrame({
            "Amount": [-100.0, -50.0, -75.0, -200.0],
            "Document Description": ["REFUND", "COMMERCIAL GESTURE", "PYT_PF", "General"],
            "Document No": ["DOC001", "DOC002", "DOC003", "NG-123"],
            "User ID": [INTEGRATION_USER_ID, INTEGRATION_USER_ID, INTEGRATION_USER_ID, "USER/01"],
            "Integration_Type": ["Integration", "Integration", "Integration", "Manual"],
            "bridge_category": [None, None, None, None],
            "voucher_type": [None, None, None, None],
        })
        
        result = classify_issuance(df)
        
        issuance_rows = result[result["bridge_category"] == "Issuance"]
        if not issuance_rows.empty:
            observed_types = set(issuance_rows["voucher_type"].dropna().unique())
            assert observed_types <= VALID_COMBINATIONS["Issuance"], (
                f"Issuance produced invalid types: {observed_types}"
            )


class TestExpiredCompliance:
    """Test Expired-specific schema compliance."""
    
    def test_expired_jforce_not_refund(self):
        """Test that EXPR_JFORCE produces JForce type, not Refund."""
        df = pd.DataFrame({
            "Amount": [30.0],
            "Document Description": ["EXPR_JFORCE cleanup"],
            "User ID": ["USER/01"],
            "Integration_Type": ["Manual"],
            "bridge_category": [None],
            "voucher_type": [None],
        })
        
        result = classify_expired(df)
        
        expired_rows = result[result["bridge_category"] == "Expired"]
        if not expired_rows.empty:
            assert expired_rows["voucher_type"].iloc[0] == "JForce", (
                "EXPR_JFORCE should produce JForce, not Refund"
            )
    
    def test_expired_produces_valid_types(self):
        """Test that Expired produces only Apology, JForce, Refund, Store Credit."""
        df = pd.DataFrame({
            "Amount": [30.0, 40.0, 50.0],
            "Document Description": ["EXPR_APLGY", "EXPR_JFORCE", "EXPR_STR CRDT"],
            "User ID": ["USER/01", "USER/02", "USER/03"],
            "Integration_Type": ["Manual", "Manual", "Manual"],
            "bridge_category": [None, None, None],
            "voucher_type": [None, None, None],
        })
        
        result = classify_expired(df)
        
        expired_rows = result[result["bridge_category"] == "Expired"]
        if not expired_rows.empty:
            observed_types = set(expired_rows["voucher_type"].dropna().unique())
            assert observed_types <= VALID_COMBINATIONS["Expired"], (
                f"Expired produced invalid types: {observed_types}"
            )


class TestFullPipelineCompliance:
    """Test the full categorization pipeline for schema compliance."""
    
    def test_pipeline_produces_only_valid_values(self, sample_nav_data):
        """Test that the full pipeline produces only schema-compliant values."""
        result = categorize_nav_vouchers(sample_nav_data)
        
        # Check Integration_Type
        observed_integration = set(result["Integration_Type"].dropna().unique())
        assert observed_integration <= ALLOWED_INTEGRATION_TYPES
        
        # Check Category
        observed_categories = set(result["bridge_category"].dropna().unique())
        assert observed_categories <= ALLOWED_CATEGORIES
        
        # Check Voucher Type
        observed_voucher_types = set(result["voucher_type"].dropna().unique())
        assert observed_voucher_types <= ALLOWED_VOUCHER_TYPES
        
        # Check Combinations
        combinations_df = result[
            result["bridge_category"].notna() & result["voucher_type"].notna()
        ][["bridge_category", "voucher_type"]]
        
        for _, row in combinations_df.iterrows():
            category = row["bridge_category"]
            voucher_type = row["voucher_type"]
            
            assert category in VALID_COMBINATIONS, f"Unknown category: {category}"
            assert voucher_type in VALID_COMBINATIONS[category], (
                f"Invalid combination: {category} + {voucher_type}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
