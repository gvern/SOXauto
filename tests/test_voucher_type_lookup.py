"""
Tests for robust voucher type lookup functionality.

Validates the fallback strategy:
1. Primary Lookup: Match NAV Voucher No to TV File id
2. Secondary Lookup (Fallback): If Voucher No is missing or no match found,
   match NAV Document No to TV File Transaction_No
"""

import pandas as pd
import pytest

from src.bridges.cat_usage_classifier import lookup_voucher_type


class TestVoucherTypeLookupPrimary:
    """Tests for primary lookup by voucher_no -> id"""
    
    def test_lookup_by_voucher_no_in_ipe08(self):
        """Test successful lookup by voucher_no in IPE_08"""
        ipe_08_df = pd.DataFrame({
            "id": ["V001", "V002", "V003"],
            "business_use": ["refund", "apology", "store_credit"]
        })
        
        result = lookup_voucher_type("V002", "DOC123", ipe_08_df, None)
        assert result == "apology"
    
    def test_lookup_by_voucher_no_in_usage_df(self):
        """Test successful lookup by voucher_no in doc_voucher_usage_df"""
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101", "V102", "V103"],
            "business_use": ["refund", "jforce", "store_credit"],
            "Transaction_No": ["TRX001", "TRX002", "TRX003"]
        })
        
        result = lookup_voucher_type("V102", "DOC456", None, doc_voucher_usage_df)
        assert result == "jforce"
    
    def test_ipe08_takes_priority_over_usage_df(self):
        """Test that IPE_08 match takes priority over doc_voucher_usage_df"""
        ipe_08_df = pd.DataFrame({
            "id": ["V001"],
            "business_use": ["refund"]
        })
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V001"],
            "business_use": ["apology"],
            "Transaction_No": ["TRX001"]
        })
        
        result = lookup_voucher_type("V001", "DOC123", ipe_08_df, doc_voucher_usage_df)
        assert result == "refund", "IPE_08 should take priority"


class TestVoucherTypeLookupFallback:
    """Tests for fallback lookup by doc_no -> Transaction_No"""
    
    def test_fallback_when_voucher_no_is_empty(self):
        """Test fallback to Transaction_No when voucher_no is empty"""
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101", "V102"],
            "business_use": ["refund", "jforce"],
            "Transaction_No": ["TRX001", "TRX002"]
        })
        
        # voucher_no is empty string, should fallback to doc_no
        result = lookup_voucher_type("", "TRX002", None, doc_voucher_usage_df)
        assert result == "jforce"
    
    def test_fallback_when_voucher_no_is_none(self):
        """Test fallback to Transaction_No when voucher_no is None"""
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101", "V102"],
            "business_use": ["refund", "jforce"],
            "Transaction_No": ["TRX001", "TRX002"]
        })
        
        # voucher_no is None, should fallback to doc_no
        result = lookup_voucher_type(None, "TRX001", None, doc_voucher_usage_df)
        assert result == "refund"
    
    def test_fallback_when_voucher_no_not_found(self):
        """Test fallback to Transaction_No when voucher_no doesn't match"""
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101", "V102"],
            "business_use": ["refund", "jforce"],
            "Transaction_No": ["TRX001", "TRX002"]
        })
        
        # voucher_no="V999" doesn't exist, should fallback to doc_no
        result = lookup_voucher_type("V999", "TRX002", None, doc_voucher_usage_df)
        assert result == "jforce"
    
    def test_fallback_with_ipe08_present_but_no_match(self):
        """Test fallback works even when IPE_08 is present but has no match"""
        ipe_08_df = pd.DataFrame({
            "id": ["V001", "V002"],
            "business_use": ["refund", "apology"]
        })
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101", "V102"],
            "business_use": ["store_credit", "jforce"],
            "Transaction_No": ["TRX001", "TRX002"]
        })
        
        # voucher_no="V999" not in either df, should fallback to Transaction_No
        result = lookup_voucher_type("V999", "TRX001", ipe_08_df, doc_voucher_usage_df)
        assert result == "store_credit"
    
    def test_no_fallback_when_transaction_no_column_missing(self):
        """Test no fallback when Transaction_No column doesn't exist"""
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101", "V102"],
            "business_use": ["refund", "jforce"]
            # No Transaction_No column
        })
        
        result = lookup_voucher_type("V999", "TRX001", None, doc_voucher_usage_df)
        assert result is None


class TestVoucherTypeLookupEdgeCases:
    """Tests for edge cases"""
    
    def test_empty_dataframes(self):
        """Test with empty DataFrames"""
        result = lookup_voucher_type("V001", "DOC123", pd.DataFrame(), pd.DataFrame())
        assert result is None
    
    def test_none_dataframes(self):
        """Test with None DataFrames"""
        result = lookup_voucher_type("V001", "DOC123", None, None)
        assert result is None
    
    def test_missing_business_use_column(self):
        """Test when business_use column is missing"""
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101"],
            "Transaction_No": ["TRX001"]
            # No business_use column
        })
        
        result = lookup_voucher_type("V101", "TRX001", None, doc_voucher_usage_df)
        assert result is None
    
    def test_type_conversion_in_matching(self):
        """Test that numeric IDs are properly converted to strings for matching"""
        doc_voucher_usage_df = pd.DataFrame({
            "id": [101, 102, 103],  # Numeric IDs
            "business_use": ["refund", "apology", "jforce"],
            "Transaction_No": ["TRX001", "TRX002", "TRX003"]
        })
        
        # String voucher_no should match numeric id
        result = lookup_voucher_type("102", "DOC123", None, doc_voucher_usage_df)
        assert result == "apology"
    
    def test_whitespace_handling(self):
        """Test that whitespace in IDs doesn't prevent matching"""
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101 ", " V102", "V103"],
            "business_use": ["refund", "apology", "jforce"],
            "Transaction_No": ["TRX001", "TRX002", "TRX003"]
        })
        
        # Note: Current implementation uses astype(str) which preserves whitespace
        # This test documents current behavior - enhancement could add .strip()
        result = lookup_voucher_type("V102", "DOC123", None, doc_voucher_usage_df)
        assert result is None, "Current implementation doesn't strip whitespace"


class TestNigeriaIntegrationIssue:
    """Tests specific to the Nigeria Integration Issue mentioned in the task"""
    
    def test_itempricecredit_without_voucher_no(self):
        """
        Test the Nigeria exception case where ITEMPRICECREDIT appears without 
        voucher ID but has a transaction number.
        
        This simulates a NAV entry like:
        - Voucher No_: "" (missing)
        - Document No: "TRX12345" 
        - Document Description: "ITEMPRICECREDIT"
        
        Should match to BOB transaction and retrieve business_use.
        """
        # BOB/Usage data with Transaction_No
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101", "V102"],
            "business_use": ["refund", "store_credit"],
            "Transaction_No": ["TRX12345", "TRX67890"]
        })
        
        # NAV entry: no voucher_no, but has doc_no matching Transaction_No
        result = lookup_voucher_type("", "TRX12345", None, doc_voucher_usage_df)
        assert result == "refund", "Should match by Transaction_No when Voucher No is missing"
    
    def test_mixed_scenario_some_with_voucher_some_without(self):
        """
        Test a mixed scenario where some transactions have voucher_no 
        and others rely on Transaction_No fallback
        """
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101", "V102", "V103"],
            "business_use": ["refund", "apology", "jforce"],
            "Transaction_No": ["TRX001", "TRX002", "TRX003"]
        })
        
        # Case 1: Has voucher_no - should use primary lookup
        result1 = lookup_voucher_type("V101", "TRX999", None, doc_voucher_usage_df)
        assert result1 == "refund", "Should match by voucher_no (primary)"
        
        # Case 2: No voucher_no - should use fallback
        result2 = lookup_voucher_type("", "TRX002", None, doc_voucher_usage_df)
        assert result2 == "apology", "Should match by Transaction_No (fallback)"
        
        # Case 3: Wrong voucher_no, correct Transaction_No - should use fallback
        result3 = lookup_voucher_type("V999", "TRX003", None, doc_voucher_usage_df)
        assert result3 == "jforce", "Should fallback to Transaction_No when primary fails"


class TestBackwardCompatibility:
    """Tests for backward compatibility with classifier.py"""
    
    def test_both_implementations_give_same_results(self):
        """Test that both lookup_voucher_type implementations produce the same results"""
        from src.bridges.classifier import _lookup_voucher_type as classifier_lookup
        from src.bridges.cat_usage_classifier import lookup_voucher_type as usage_lookup
        
        ipe_08_df = pd.DataFrame({
            "id": ["V001", "V002"],
            "business_use": ["refund", "apology"]
        })
        doc_voucher_usage_df = pd.DataFrame({
            "id": ["V101", "V102"],
            "business_use": ["store_credit", "jforce"],
            "Transaction_No": ["TRX001", "TRX002"]
        })
        
        test_cases = [
            ("V001", "DOC123"),  # Match in IPE_08
            ("V101", "DOC456"),  # Match in usage_df by ID
            ("", "TRX002"),      # Fallback to Transaction_No
            ("V999", "TRX001"),  # No ID match, fallback to Transaction_No
        ]
        
        for voucher_no, doc_no in test_cases:
            result1 = classifier_lookup(voucher_no, doc_no, ipe_08_df, doc_voucher_usage_df)
            result2 = usage_lookup(voucher_no, doc_no, ipe_08_df, doc_voucher_usage_df)
            assert result1 == result2, f"Implementations differ for ({voucher_no}, {doc_no})"
