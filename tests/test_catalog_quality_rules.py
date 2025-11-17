"""
Tests for Data Quality Rules Configuration in CPG1 Catalog.

This test validates that the quality rules are properly configured for critical
C-PG-1 catalog items as specified in the configuration requirements.
"""

import sys
import os

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.core.catalog.cpg1 import get_item_by_id
from src.core.quality_checker import RowCountCheck, ColumnExistsCheck, NoNullsCheck


def test_cr_04_quality_rules():
    """Test CR_04 (GL Balances) has correct quality rules."""
    item = get_item_by_id("CR_04")
    assert item is not None, "CR_04 should exist in catalog"
    
    rules = item.quality_rules
    assert len(rules) == 3, "CR_04 should have 3 quality rules"
    
    # Check rule types and parameters
    assert isinstance(rules[0], RowCountCheck), "First rule should be RowCountCheck"
    assert rules[0].min_rows == 1, "RowCountCheck should have min_rows=1"
    
    assert isinstance(rules[1], ColumnExistsCheck), "Second rule should be ColumnExistsCheck"
    assert rules[1].column_name == "BALANCE_AT_DATE", "Should check for BALANCE_AT_DATE column"
    
    assert isinstance(rules[2], ColumnExistsCheck), "Third rule should be ColumnExistsCheck"
    assert rules[2].column_name == "GROUP_COA_ACCOUNT_NO", "Should check for GROUP_COA_ACCOUNT_NO column"


def test_cr_03_quality_rules():
    """Test CR_03 (GL Entries) has correct quality rules."""
    item = get_item_by_id("CR_03")
    assert item is not None, "CR_03 should exist in catalog"
    
    rules = item.quality_rules
    assert len(rules) == 3, "CR_03 should have 3 quality rules"
    
    assert isinstance(rules[0], RowCountCheck), "First rule should be RowCountCheck"
    assert rules[0].min_rows == 1, "RowCountCheck should have min_rows=1"
    
    assert isinstance(rules[1], ColumnExistsCheck), "Second rule should be ColumnExistsCheck"
    assert rules[1].column_name == "Amount", "Should check for Amount column"
    
    assert isinstance(rules[2], ColumnExistsCheck), "Third rule should be ColumnExistsCheck"
    assert rules[2].column_name == "[Voucher No_]", "Should check for [Voucher No_] column"


def test_ipe_08_quality_rules():
    """Test IPE_08 (Voucher Issuance) has correct quality rules."""
    item = get_item_by_id("IPE_08")
    assert item is not None, "IPE_08 should exist in catalog"
    
    rules = item.quality_rules
    assert len(rules) == 3, "IPE_08 should have 3 quality rules"
    
    assert isinstance(rules[0], RowCountCheck), "First rule should be RowCountCheck"
    assert rules[0].min_rows == 1, "RowCountCheck should have min_rows=1"
    
    assert isinstance(rules[1], ColumnExistsCheck), "Second rule should be ColumnExistsCheck"
    assert rules[1].column_name == "remaining_amount", "Should check for remaining_amount column"
    
    assert isinstance(rules[2], ColumnExistsCheck), "Third rule should be ColumnExistsCheck"
    assert rules[2].column_name == "id", "Should check for id column"


def test_doc_voucher_usage_quality_rules():
    """Test DOC_VOUCHER_USAGE (Voucher Usage TV) has correct quality rules."""
    item = get_item_by_id("DOC_VOUCHER_USAGE")
    assert item is not None, "DOC_VOUCHER_USAGE should exist in catalog"
    
    rules = item.quality_rules
    assert len(rules) == 2, "DOC_VOUCHER_USAGE should have 2 quality rules"
    
    assert isinstance(rules[0], RowCountCheck), "First rule should be RowCountCheck"
    assert rules[0].min_rows == 1, "RowCountCheck should have min_rows=1"
    
    assert isinstance(rules[1], ColumnExistsCheck), "Second rule should be ColumnExistsCheck"
    assert rules[1].column_name == "TotalAmountUsed", "Should check for TotalAmountUsed column"


def test_ipe_07_quality_rules():
    """Test IPE_07 (Customer Ledger) has correct quality rules."""
    item = get_item_by_id("IPE_07")
    assert item is not None, "IPE_07 should exist in catalog"
    
    rules = item.quality_rules
    assert len(rules) == 3, "IPE_07 should have 3 quality rules"
    
    assert isinstance(rules[0], RowCountCheck), "First rule should be RowCountCheck"
    assert rules[0].min_rows == 1, "RowCountCheck should have min_rows=1"
    
    assert isinstance(rules[1], ColumnExistsCheck), "Second rule should be ColumnExistsCheck"
    assert rules[1].column_name == "Customer No_", "Should check for Customer No_ column"
    
    assert isinstance(rules[2], ColumnExistsCheck), "Third rule should be ColumnExistsCheck"
    assert rules[2].column_name == "Customer Posting Group", "Should check for Customer Posting Group column"


def test_ipe_rec_errors_quality_rules():
    """Test IPE_REC_ERRORS (Integration Errors) has correct quality rules."""
    item = get_item_by_id("IPE_REC_ERRORS")
    assert item is not None, "IPE_REC_ERRORS should exist in catalog"
    
    rules = item.quality_rules
    # NOTE: IPE_REC_ERRORS should NOT have RowCountCheck(min_rows=1) 
    # because it is valid/good to have 0 errors
    assert len(rules) == 2, "IPE_REC_ERRORS should have 2 quality rules (no RowCountCheck)"
    
    assert isinstance(rules[0], ColumnExistsCheck), "First rule should be ColumnExistsCheck"
    assert rules[0].column_name == "Integration_Status", "Should check for Integration_Status column"
    
    assert isinstance(rules[1], ColumnExistsCheck), "Second rule should be ColumnExistsCheck"
    assert rules[1].column_name == "Amount", "Should check for Amount column"
    
    # Verify NO RowCountCheck exists
    row_count_checks = [r for r in rules if isinstance(r, RowCountCheck)]
    assert len(row_count_checks) == 0, "IPE_REC_ERRORS should NOT have RowCountCheck"


def test_all_configured_items_have_rules():
    """Test that all specified items have quality rules configured."""
    required_items = ["CR_04", "CR_03", "IPE_08", "DOC_VOUCHER_USAGE", "IPE_07", "IPE_REC_ERRORS"]
    
    for item_id in required_items:
        item = get_item_by_id(item_id)
        assert item is not None, f"{item_id} should exist in catalog"
        assert len(item.quality_rules) > 0, f"{item_id} should have quality rules configured"


if __name__ == "__main__":
    # Quick manual check
    print("Running quality rules configuration tests...")
    
    test_cr_04_quality_rules()
    print("✓ CR_04 quality rules configured correctly")
    
    test_cr_03_quality_rules()
    print("✓ CR_03 quality rules configured correctly")
    
    test_ipe_08_quality_rules()
    print("✓ IPE_08 quality rules configured correctly")
    
    test_doc_voucher_usage_quality_rules()
    print("✓ DOC_VOUCHER_USAGE quality rules configured correctly")
    
    test_ipe_07_quality_rules()
    print("✓ IPE_07 quality rules configured correctly")
    
    test_ipe_rec_errors_quality_rules()
    print("✓ IPE_REC_ERRORS quality rules configured correctly")
    
    test_all_configured_items_have_rules()
    print("✓ All configured items have quality rules")
    
    print("\nAll tests passed!")
