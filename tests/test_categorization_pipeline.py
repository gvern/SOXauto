"""
Tests for the new modular categorization rules engine.

Tests the individual classifiers and the main categorization pipeline.
"""

import pandas as pd

from src.bridges.cat_nav_classifier import (
    classify_integration_type,
    is_integration_user,
)
from src.bridges.cat_issuance_classifier import (
    classify_issuance,
    COUNTRY_CODES,
)
from src.bridges.cat_usage_classifier import (
    classify_usage,
    classify_manual_usage,
    lookup_voucher_type,
)
from src.bridges.cat_vtc_classifier import (
    classify_vtc,
    classify_vtc_bank_account,
    classify_vtc_pattern,
)
from src.bridges.cat_expired_classifier import (
    classify_expired,
    classify_manual_cancellation,
)
from src.bridges.cat_pipeline import (
    categorize_nav_vouchers,
    get_categorization_summary,
)


# =============================================================================
# NAV Classifier Tests (Integration Type Detection)
# =============================================================================

class TestClassifyIntegrationType:
    """Tests for classify_integration_type function."""

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = classify_integration_type(df)
        assert "Integration_Type" in result.columns
        assert len(result) == 0

    def test_none_dataframe(self):
        """Test with None input."""
        result = classify_integration_type(None)
        assert result is not None
        assert "Integration_Type" in result.columns
        assert len(result) == 0

    def test_integration_user_nav_batch_srvc(self):
        """Test that JUMIA/NAV*.BATCH.SRVC is detected as Integration."""
        df = pd.DataFrame({
            "User ID": ["JUMIA/NAV31AFR.BATCH.SRVC"]
        })
        result = classify_integration_type(df)
        assert result.loc[0, "Integration_Type"] == "Integration"

    def test_integration_user_nav13(self):
        """Test that NAV13AFR.BATCH.SRVC is detected as Integration."""
        df = pd.DataFrame({
            "User ID": ["NAV13AFR.BATCH.SRVC"]
        })
        result = classify_integration_type(df)
        assert result.loc[0, "Integration_Type"] == "Integration"

    def test_manual_user_nav_without_batch_srvc(self):
        """Test that NAV without BATCH/SRVC is Manual."""
        df = pd.DataFrame({
            "User ID": ["NAV/13"]
        })
        result = classify_integration_type(df)
        assert result.loc[0, "Integration_Type"] == "Manual"

    def test_manual_user_regular(self):
        """Test that regular user is Manual."""
        df = pd.DataFrame({
            "User ID": ["USER/01"]
        })
        result = classify_integration_type(df)
        assert result.loc[0, "Integration_Type"] == "Manual"

    def test_case_insensitivity(self):
        """Test case insensitivity for user ID detection."""
        df = pd.DataFrame({
            "User ID": ["jumia/nav31afr.batch.srvc"]
        })
        result = classify_integration_type(df)
        assert result.loc[0, "Integration_Type"] == "Integration"


class TestIsIntegrationUser:
    """Tests for is_integration_user helper function."""

    def test_integration_pattern(self):
        assert is_integration_user("JUMIA/NAV31AFR.BATCH.SRVC") is True
        assert is_integration_user("NAV13AFR.BATCH.SRVC") is True

    def test_manual_pattern(self):
        assert is_integration_user("USER/01") is False
        assert is_integration_user("NAV/13") is False
        assert is_integration_user("ADMIN/02") is False

    def test_empty_and_none(self):
        assert is_integration_user("") is False
        assert is_integration_user(None) is False


# =============================================================================
# Issuance Classifier Tests
# =============================================================================

class TestClassifyIssuance:
    """Tests for classify_issuance function."""

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = classify_issuance(df)
        assert len(result) == 0

    def test_integrated_refund_issuance(self):
        """Test integrated refund issuance detection."""
        df = pd.DataFrame({
            "Amount": [-100.0],
            "Document Description": ["Refund voucher issued"],
            "Integration_Type": ["Integration"]
        })
        result = classify_issuance(df)
        assert result.loc[0, "bridge_category"] == "Issuance - Refund"
        assert result.loc[0, "voucher_type"] == "Refund"

    def test_integrated_rf_prefix_issuance(self):
        """Test integrated RF_ prefix detection."""
        df = pd.DataFrame({
            "Amount": [-100.0],
            "Document Description": ["RF_317489956_0925"],
            "Integration_Type": ["Integration"]
        })
        result = classify_issuance(df)
        assert result.loc[0, "bridge_category"] == "Issuance - Refund"

    def test_integrated_apology_issuance(self):
        """Test integrated commercial gesture detection."""
        df = pd.DataFrame({
            "Amount": [-75.0],
            "Document Description": ["COMMERCIAL GESTURE voucher"],
            "Integration_Type": ["Integration"]
        })
        result = classify_issuance(df)
        assert result.loc[0, "bridge_category"] == "Issuance - Apology"
        assert result.loc[0, "voucher_type"] == "Apology"

    def test_integrated_jforce_issuance(self):
        """Test integrated JForce detection."""
        df = pd.DataFrame({
            "Amount": [-200.0],
            "Document Description": ["PYT_PF JForce payout"],
            "Integration_Type": ["Integration"]
        })
        result = classify_issuance(df)
        assert result.loc[0, "bridge_category"] == "Issuance - JForce"
        assert result.loc[0, "voucher_type"] == "JForce"

    def test_manual_store_credit_issuance(self):
        """Test manual store credit issuance via country code prefix."""
        df = pd.DataFrame({
            "Amount": [-150.0],
            "Document Description": ["Store credit issued"],
            "Document No": ["NG-SC-2024-001"],
            "Integration_Type": ["Manual"]
        })
        result = classify_issuance(df)
        assert result.loc[0, "bridge_category"] == "Issuance - Store Credit"
        assert result.loc[0, "voucher_type"] == "Store Credit"

    def test_manual_refund_issuance(self):
        """Test manual refund issuance."""
        df = pd.DataFrame({
            "Amount": [-50.0],
            "Document Description": ["RFN voucher for customer"],
            "Document No": ["INV-001"],
            "Integration_Type": ["Manual"]
        })
        result = classify_issuance(df)
        assert result.loc[0, "bridge_category"] == "Issuance - Refund"
        assert result.loc[0, "voucher_type"] == "Refund"

    def test_positive_amount_not_classified(self):
        """Test that positive amounts are not classified as issuance."""
        df = pd.DataFrame({
            "Amount": [100.0],
            "Document Description": ["Refund voucher"],
            "Integration_Type": ["Integration"]
        })
        result = classify_issuance(df)
        assert pd.isna(result.loc[0, "bridge_category"]) or result.loc[0, "bridge_category"] is None


# =============================================================================
# Usage Classifier Tests
# =============================================================================

class TestClassifyUsage:
    """Tests for classify_usage function."""

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = classify_usage(df)
        assert len(result) == 0

    def test_integrated_usage(self):
        """Test integrated usage detection."""
        df = pd.DataFrame({
            "Amount": [75.0],
            "Document Description": ["Item price credit applied"],
            "Integration_Type": ["Integration"]
        })
        result = classify_usage(df)
        assert result.loc[0, "bridge_category"] == "Usage"

    def test_voucher_accrual_cancellation(self):
        """Test Voucher Accrual cancellation detection."""
        df = pd.DataFrame({
            "Amount": [45.0],
            "Document Description": ["Voucher Accrual reversal"],
            "Integration_Type": ["Integration"]
        })
        result = classify_usage(df)
        assert result.loc[0, "bridge_category"] == "Cancellation - Apology"
        assert result.loc[0, "voucher_type"] == "Apology"

    def test_manual_not_classified_as_integrated_usage(self):
        """Test that manual transactions are not classified as integrated usage."""
        df = pd.DataFrame({
            "Amount": [100.0],
            "Document Description": ["Item price credit"],
            "Integration_Type": ["Manual"]
        })
        result = classify_usage(df)
        assert pd.isna(result.loc[0, "bridge_category"]) or result.loc[0, "bridge_category"] is None


class TestClassifyManualUsage:
    """Tests for classify_manual_usage function."""

    def test_itempricecredit_pattern(self):
        """Test ITEMPRICECREDIT pattern detection (Nigeria exception)."""
        df = pd.DataFrame({
            "Amount": [60.0],
            "Document Description": ["ITEMPRICECREDIT adjustment"],
            "Integration_Type": ["Manual"]
        })
        result = classify_manual_usage(df)
        assert result.loc[0, "bridge_category"] == "Usage"

    def test_non_itempricecredit_not_classified(self):
        """Test that non-ITEMPRICECREDIT patterns are not classified."""
        df = pd.DataFrame({
            "Amount": [60.0],
            "Document Description": ["Some other description"],
            "Integration_Type": ["Manual"]
        })
        result = classify_manual_usage(df)
        assert pd.isna(result.loc[0, "bridge_category"]) or result.loc[0, "bridge_category"] is None


# =============================================================================
# VTC Classifier Tests
# =============================================================================

class TestClassifyVTC:
    """Tests for classify_vtc function."""

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = classify_vtc(df)
        assert len(result) == 0

    def test_vtc_bank_account_negative(self):
        """Test VTC via Bank Account with negative amount."""
        df = pd.DataFrame({
            "Amount": [-5437.0],
            "Bal_ Account Type": ["Bank Account"],
            "Integration_Type": ["Manual"]
        })
        result = classify_vtc(df)
        assert result.loc[0, "bridge_category"] == "VTC"
        assert result.loc[0, "voucher_type"] == "Refund"

    def test_vtc_bank_account_positive(self):
        """Test VTC via Bank Account with positive amount."""
        df = pd.DataFrame({
            "Amount": [5437.0],
            "Bal_ Account Type": ["Bank Account"],
            "Integration_Type": ["Manual"]
        })
        result = classify_vtc(df)
        assert result.loc[0, "bridge_category"] == "VTC"
        assert result.loc[0, "voucher_type"] == "Refund"

    def test_vtc_manual_rnd(self):
        """Test VTC via Manual RND pattern."""
        df = pd.DataFrame({
            "Amount": [100.0],
            "Document Description": ["Manual RND voucher entry"],
            "Integration_Type": ["Manual"]
        })
        result = classify_vtc(df)
        assert result.loc[0, "bridge_category"] == "VTC"
        assert result.loc[0, "voucher_type"] == "Refund"

    def test_vtc_pyt_gtb(self):
        """Test VTC via PYT_ with GTB in Comment."""
        df = pd.DataFrame({
            "Amount": [150.0],
            "Document Description": ["PYT_123 voucher"],
            "Comment": ["GTB bank transfer"],
            "Integration_Type": ["Manual"]
        })
        result = classify_vtc(df)
        assert result.loc[0, "bridge_category"] == "VTC"
        assert result.loc[0, "voucher_type"] == "Refund"

    def test_integration_not_classified_as_vtc(self):
        """Test that Integration transactions are not classified as VTC."""
        df = pd.DataFrame({
            "Amount": [100.0],
            "Bal_ Account Type": ["Bank Account"],
            "Integration_Type": ["Integration"]
        })
        result = classify_vtc(df)
        assert pd.isna(result.loc[0, "bridge_category"]) or result.loc[0, "bridge_category"] is None


# =============================================================================
# Expired Classifier Tests
# =============================================================================

class TestClassifyExpired:
    """Tests for classify_expired function."""

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = classify_expired(df)
        assert len(result) == 0

    def test_expired_apology(self):
        """Test EXPR_APLGY pattern detection."""
        df = pd.DataFrame({
            "Amount": [30.0],
            "Document Description": ["EXPR_APLGY voucher cleanup"],
            "Integration_Type": ["Manual"]
        })
        result = classify_expired(df)
        assert result.loc[0, "bridge_category"] == "Expired - Apology"
        assert result.loc[0, "voucher_type"] == "Apology"

    def test_expired_refund(self):
        """Test EXPR_JFORCE pattern detection."""
        df = pd.DataFrame({
            "Amount": [25.0],
            "Document Description": ["EXPR_JFORCE voucher expiry"],
            "Integration_Type": ["Manual"]
        })
        result = classify_expired(df)
        assert result.loc[0, "bridge_category"] == "Expired - Refund"
        assert result.loc[0, "voucher_type"] == "Refund"

    def test_expired_store_credit(self):
        """Test EXPR_STR CRDT pattern detection."""
        df = pd.DataFrame({
            "Amount": [20.0],
            "Document Description": ["EXPR_STR CRDT voucher"],
            "Integration_Type": ["Manual"]
        })
        result = classify_expired(df)
        assert result.loc[0, "bridge_category"] == "Expired - Store Credit"
        assert result.loc[0, "voucher_type"] == "Store Credit"

    def test_expired_generic(self):
        """Test generic EXPR pattern detection."""
        df = pd.DataFrame({
            "Amount": [35.0],
            "Document Description": ["EXPR-2024-001 cleanup"],
            "Integration_Type": ["Manual"]
        })
        result = classify_expired(df)
        assert result.loc[0, "bridge_category"] == "Expired"


class TestClassifyManualCancellation:
    """Tests for classify_manual_cancellation function."""

    def test_credit_memo_cancellation(self):
        """Test Manual Cancellation via Credit Memo."""
        df = pd.DataFrame({
            "Amount": [85.0],
            "Document Type": ["Credit Memo"],
            "Integration_Type": ["Manual"]
        })
        result = classify_manual_cancellation(df)
        assert result.loc[0, "bridge_category"] == "Cancellation - Store Credit"
        assert result.loc[0, "voucher_type"] == "Store Credit"


# =============================================================================
# Pipeline Tests
# =============================================================================

class TestCategorizationPipeline:
    """Tests for the main categorization pipeline."""

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = categorize_nav_vouchers(df)
        assert "bridge_category" in result.columns
        assert "voucher_type" in result.columns
        assert "Integration_Type" in result.columns
        assert len(result) == 0

    def test_none_dataframe(self):
        """Test with None input."""
        result = categorize_nav_vouchers(None)
        assert result is not None
        assert "bridge_category" in result.columns
        assert len(result) == 0

    def test_mixed_scenarios(self):
        """Test a mix of different categorization rules."""
        df = pd.DataFrame([
            # Issuance - Refund (Integrated)
            {
                "Chart of Accounts No_": "18412",
                "Amount": -75.0,
                "User ID": "JUMIA/NAV13AFR.BATCH.SRVC",
                "Document Description": "Refund voucher",
            },
            # Usage (Integrated)
            {
                "Chart of Accounts No_": "18412",
                "Amount": 50.0,
                "User ID": "JUMIA/NAV13AFR.BATCH.SRVC",
                "Document Description": "Item price credit",
            },
            # VTC (Manual + RND)
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "User ID": "USER/01",
                "Document Description": "Manual RND entry",
            },
            # Expired (Manual + EXPR)
            {
                "Chart of Accounts No_": "18412",
                "Amount": 25.0,
                "User ID": "USER/02",
                "Document Description": "EXPR_APLGY-2024-123",
            },
            # Non-18412 (should not be categorized)
            {
                "Chart of Accounts No_": "13011",
                "Amount": 200.0,
                "User ID": "USER/03",
                "Document Description": "Different account",
            },
        ])
        result = categorize_nav_vouchers(df)
        
        assert result.loc[0, "bridge_category"] == "Issuance - Refund"
        assert result.loc[1, "bridge_category"] == "Usage"
        assert result.loc[2, "bridge_category"] == "VTC"
        assert result.loc[3, "bridge_category"] == "Expired - Apology"
        assert (
            pd.isna(result.loc[4, "bridge_category"])
            or result.loc[4, "bridge_category"] is None
        )

    def test_vtc_priority_over_issuance(self):
        """Test that VTC Bank Account has priority over Issuance."""
        df = pd.DataFrame([
            {
                "Chart of Accounts No_": "18412",
                "Amount": -5437.0,
                "User ID": "JUMIA\\ABIR.OUALI",
                "Document Description": "Customer refund payment",
                "Bal_ Account Type": "Bank Account",
            },
        ])
        result = categorize_nav_vouchers(df)
        assert result.loc[0, "bridge_category"] == "VTC"
        assert result.loc[0, "voucher_type"] == "Refund"


class TestGetCategorizationSummary:
    """Tests for get_categorization_summary function."""

    def test_empty_dataframe(self):
        """Test summary with empty DataFrame."""
        result = get_categorization_summary(pd.DataFrame())
        assert result["total_rows"] == 0
        assert result["categorized_rows"] == 0
        assert result["uncategorized_rows"] == 0

    def test_summary_counts(self):
        """Test summary counts are correct."""
        df = pd.DataFrame({
            "bridge_category": ["Usage", "Issuance", None, "VTC"],
            "voucher_type": ["Refund", None, None, "Refund"],
            "Integration_Type": ["Integration", "Integration", "Manual", "Manual"]
        })
        result = get_categorization_summary(df)
        
        assert result["total_rows"] == 4
        assert result["categorized_rows"] == 3
        assert result["uncategorized_rows"] == 1
        assert "Usage" in result["by_category"]
        assert result["by_integration_type"]["Integration"] == 2
        assert result["by_integration_type"]["Manual"] == 2


# =============================================================================
# Backward Compatibility Tests
# =============================================================================

class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with original _categorize_nav_vouchers."""

    def test_same_output_for_basic_scenarios(self):
        """Test that new pipeline produces same output as original for basic scenarios."""
        from src.bridges.classifier import _categorize_nav_vouchers as original_categorize

        df = pd.DataFrame([
            {
                "Chart of Accounts No_": "18412",
                "Amount": -100.0,
                "User ID": "JUMIA/NAV13AFR.BATCH.SRVC",
                "Document Description": "Refund voucher",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 50.0,
                "User ID": "JUMIA/NAV13AFR.BATCH.SRVC",
                "Document Description": "Item price credit",
            },
        ])

        original_result = original_categorize(df.copy())
        new_result = categorize_nav_vouchers(df.copy())

        # Compare results
        assert original_result.loc[0, "bridge_category"] == new_result.loc[0, "bridge_category"]
        assert original_result.loc[1, "bridge_category"] == new_result.loc[1, "bridge_category"]
        assert original_result.loc[0, "Integration_Type"] == new_result.loc[0, "Integration_Type"]
        assert original_result.loc[1, "Integration_Type"] == new_result.loc[1, "Integration_Type"]
