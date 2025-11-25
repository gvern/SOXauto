import os
import sys
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.bridges.catalog import load_rules
from src.bridges.classifier import (
    classify_bridges,
    calculate_vtc_adjustment,
    _categorize_nav_vouchers,
    calculate_customer_posting_group_bridge,
    calculate_timing_difference_bridge,
    calculate_integration_error_adjustment,
)
from src.utils.fx_utils import FXConverter


def test_rules_loading():
    rules = load_rules()
    assert len(rules) >= 5
    keys = {r.key for r in rules}
    assert "CASH_DEPOSITS" in keys
    assert "REFUNDS" in keys


def test_classify_simple_matches():
    rules = load_rules()
    df = pd.DataFrame(
        [
            {"Transaction_Type": "Transfer to", "Amount": 100},
            {"Transaction_Type": "Refund", "Amount": 50},
            {"IS_PREPAYMENT": "1", "Amount": 30},
        ]
    )
    out = classify_bridges(df, rules)
    assert "bridge_key" in out.columns
    assert out.loc[0, "bridge_key"] in ("CASH_DEPOSITS", "PAYMENT_RECONCILES")
    assert out.loc[1, "bridge_key"] == "REFUNDS"
    assert out.loc[2, "bridge_key"] in ("PREPAYMENTS", "PREPAID_DELIVERIES")


def test_customer_posting_group_bridge_empty_input():
    """Test with empty DataFrame"""
    empty_df = pd.DataFrame()
    bridge_amount, proof_df = calculate_customer_posting_group_bridge(empty_df)

    assert bridge_amount == 0.0
    assert proof_df.empty
    assert list(proof_df.columns) == [
        "Customer No_",
        "Customer Name",
        "Customer Posting Group",
    ]


def test_customer_posting_group_bridge_none_input():
    """Test with None input"""
    bridge_amount, proof_df = calculate_customer_posting_group_bridge(None)

    assert bridge_amount == 0.0
    assert proof_df.empty
    assert list(proof_df.columns) == [
        "Customer No_",
        "Customer Name",
        "Customer Posting Group",
    ]


def test_customer_posting_group_bridge_missing_columns():
    """Test that missing required columns raise ValueError"""
    df = pd.DataFrame(
        {
            "Customer No_": ["C001"],
            "Customer Name": ["Test Customer"],
            # Missing 'Customer Posting Group'
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_customer_posting_group_bridge(df)


def test_customer_posting_group_bridge_single_posting_group():
    """Test customers with only one posting group - should return empty"""
    df = pd.DataFrame(
        {
            "Customer No_": ["C001", "C001", "C002", "C002"],
            "Customer Name": ["Customer 1", "Customer 1", "Customer 2", "Customer 2"],
            "Customer Posting Group": ["RETAIL", "RETAIL", "WHOLESALE", "WHOLESALE"],
        }
    )

    bridge_amount, proof_df = calculate_customer_posting_group_bridge(df)

    assert bridge_amount == 0.0
    assert proof_df.empty


def test_customer_posting_group_bridge_multiple_posting_groups():
    """Test customers with multiple posting groups - should identify them"""
    df = pd.DataFrame(
        {
            "Customer No_": ["C001", "C001", "C002", "C002", "C003"],
            "Customer Name": [
                "Customer 1",
                "Customer 1",
                "Customer 2",
                "Customer 2",
                "Customer 3",
            ],
            "Customer Posting Group": [
                "RETAIL",
                "WHOLESALE",
                "CORPORATE",
                "CORPORATE",
                "VIP",
            ],
        }
    )

    bridge_amount, proof_df = calculate_customer_posting_group_bridge(df)

    assert bridge_amount == 0.0
    assert len(proof_df) == 1  # Only C001 has multiple posting groups
    assert proof_df.iloc[0]["Customer No_"] == "C001"
    assert proof_df.iloc[0]["Customer Name"] == "Customer 1"
    # Check that both posting groups are present (sorted and comma-separated)
    posting_groups = proof_df.iloc[0]["Customer Posting Group"]
    assert "RETAIL" in posting_groups
    assert "WHOLESALE" in posting_groups
    assert ", " in posting_groups


def test_customer_posting_group_bridge_multiple_problem_customers():
    """Test multiple customers with posting group issues"""
    df = pd.DataFrame(
        {
            "Customer No_": ["C001", "C001", "C002", "C002", "C002", "C003"],
            "Customer Name": [
                "Customer 1",
                "Customer 1",
                "Customer 2",
                "Customer 2",
                "Customer 2",
                "Customer 3",
            ],
            "Customer Posting Group": [
                "RETAIL",
                "WHOLESALE",
                "VIP",
                "CORPORATE",
                "RETAIL",
                "SINGLE",
            ],
        }
    )

    bridge_amount, proof_df = calculate_customer_posting_group_bridge(df)

    assert bridge_amount == 0.0
    assert len(proof_df) == 2  # C001 and C002 have multiple posting groups

    # Check C001
    c001_row = proof_df[proof_df["Customer No_"] == "C001"]
    assert len(c001_row) == 1
    assert "RETAIL" in c001_row.iloc[0]["Customer Posting Group"]
    assert "WHOLESALE" in c001_row.iloc[0]["Customer Posting Group"]

    # Check C002
    c002_row = proof_df[proof_df["Customer No_"] == "C002"]
    assert len(c002_row) == 1
    assert "CORPORATE" in c002_row.iloc[0]["Customer Posting Group"]
    assert "RETAIL" in c002_row.iloc[0]["Customer Posting Group"]
    assert "VIP" in c002_row.iloc[0]["Customer Posting Group"]


def test_customer_posting_group_bridge_with_null_values():
    """Test handling of NULL/NaN values in posting groups"""
    df = pd.DataFrame(
        {
            "Customer No_": ["C001", "C001", "C002", "C002"],
            "Customer Name": ["Customer 1", "Customer 1", "Customer 2", "Customer 2"],
            "Customer Posting Group": ["RETAIL", None, "WHOLESALE", pd.NA],
        }
    )

    bridge_amount, proof_df = calculate_customer_posting_group_bridge(df)

    assert bridge_amount == 0.0
    # Both customers should have only one non-null posting group
    assert proof_df.empty


def test_customer_posting_group_bridge_output_format():
    """Test that output DataFrame has the correct format"""
    df = pd.DataFrame(
        {
            "Customer No_": ["C001", "C001"],
            "Customer Name": ["Test Customer", "Test Customer"],
            "Customer Posting Group": ["GROUP_A", "GROUP_B"],
        }
    )

    bridge_amount, proof_df = calculate_customer_posting_group_bridge(df)

    assert bridge_amount == 0.0
    assert list(proof_df.columns) == [
        "Customer No_",
        "Customer Name",
        "Customer Posting Group",
    ]
    assert len(proof_df) == 1
    # Verify the posting groups are sorted and comma-separated
    assert proof_df.iloc[0]["Customer Posting Group"] == "GROUP_A, GROUP_B"


def test_calculate_vtc_adjustment_basic():
    """Test basic VTC adjustment calculation with unmatched vouchers."""
    # Create IPE_08 data with canceled refund vouchers
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 100.0,
            },
            {
                "id": "V002",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 200.0,
            },
            {
                "id": "V003",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 1,  # Active, should be excluded
                "Remaining Amount": 50.0,
            },
        ]
    )

    # Create CR_03 data with one cancellation entry
    cr_03_df = pd.DataFrame(
        [
            {"[Voucher No_]": "V001", "bridge_category": "Cancellation - Store Credit"},
        ]
    )

    adjustment, proof = calculate_vtc_adjustment(ipe_08_df, cr_03_df)

    # V002 should be unmatched (V001 matches, V003 is filtered out by is_active)
    assert adjustment == 200.0
    assert len(proof) == 1
    assert proof.iloc[0]["id"] == "V002"


def test_calculate_vtc_adjustment_all_matched():
    """Test VTC adjustment when all vouchers are matched in NAV."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 100.0,
            },
        ]
    )

    cr_03_df = pd.DataFrame(
        [
            {"[Voucher No_]": "V001", "bridge_category": "Cancellation - Refund"},
        ]
    )

    adjustment, proof = calculate_vtc_adjustment(ipe_08_df, cr_03_df)

    assert adjustment == 0.0
    assert len(proof) == 0


def test_calculate_vtc_adjustment_vtc_manual():
    """Test VTC adjustment recognizes 'VTC Manual' category."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 150.0,
            },
            {
                "id": "V002",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 250.0,
            },
        ]
    )

    cr_03_df = pd.DataFrame(
        [
            {"[Voucher No_]": "V001", "bridge_category": "VTC Manual"},
        ]
    )

    adjustment, proof = calculate_vtc_adjustment(ipe_08_df, cr_03_df)

    # Only V002 should be unmatched
    assert adjustment == 250.0
    assert len(proof) == 1
    assert proof.iloc[0]["id"] == "V002"


def test_calculate_vtc_adjustment_empty_nav():
    """Test VTC adjustment with empty NAV data (all vouchers unmatched)."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 100.0,
            },
            {
                "id": "V002",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 200.0,
            },
        ]
    )

    cr_03_df = pd.DataFrame()

    adjustment, proof = calculate_vtc_adjustment(ipe_08_df, cr_03_df)

    # All vouchers should be unmatched
    assert adjustment == 300.0
    assert len(proof) == 2


def test_calculate_vtc_adjustment_empty_bob():
    """Test VTC adjustment with empty BOB data."""
    ipe_08_df = pd.DataFrame()

    cr_03_df = pd.DataFrame(
        [
            {"[Voucher No_]": "V001", "bridge_category": "Cancellation - Refund"},
        ]
    )

    adjustment, proof = calculate_vtc_adjustment(ipe_08_df, cr_03_df)

    assert adjustment == 0.0
    assert len(proof) == 0


def test_calculate_vtc_adjustment_filters():
    """Test that VTC adjustment filters work correctly."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 100.0,
            },
            {
                "id": "V002",
                "business_use_formatted": "store_credit",  # Wrong business use
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 200.0,
            },
            {
                "id": "V003",
                "business_use_formatted": "refund",
                "is_valid": "invalid",  # Invalid
                "is_active": 0,
                "Remaining Amount": 300.0,
            },
            {
                "id": "V004",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 1,  # Still active
                "Remaining Amount": 400.0,
            },
            {
                "id": "V005",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 500.0,
            },
        ]
    )

    cr_03_df = pd.DataFrame(
        [
            {"[Voucher No_]": "V001", "bridge_category": "Cancellation - Refund"},
        ]
    )

    adjustment, proof = calculate_vtc_adjustment(ipe_08_df, cr_03_df)

    # Only V005 should pass filters and be unmatched
    # V001 matches in NAV, V002/V003/V004 are filtered out
    assert adjustment == 500.0
    assert len(proof) == 1
    assert proof.iloc[0]["id"] == "V005"


def test_calculate_vtc_adjustment_non_cancellation_categories():
    """Test that non-cancellation categories in NAV don't count as matches."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 100.0,
            },
            {
                "id": "V002",
                "business_use_formatted": "refund",
                "is_valid": "valid",
                "is_active": 0,
                "Remaining Amount": 200.0,
            },
        ]
    )

    cr_03_df = pd.DataFrame(
        [
            {"[Voucher No_]": "V001", "bridge_category": "Usage"},  # Not a cancellation
            {
                "[Voucher No_]": "V002",
                "bridge_category": "Issuance",  # Not a cancellation
            },
        ]
    )

    adjustment, proof = calculate_vtc_adjustment(ipe_08_df, cr_03_df)

    # Both vouchers should be unmatched since NAV entries are not cancellations
    assert adjustment == 300.0
    assert len(proof) == 2


def test_categorize_nav_vouchers_empty_df():
    """Test that empty DataFrames are handled correctly."""
    empty_df = pd.DataFrame()
    result = _categorize_nav_vouchers(empty_df)
    assert "bridge_category" in result.columns
    assert len(result) == 0


def test_categorize_nav_vouchers_none_df():
    """Test that None input is handled correctly."""
    result = _categorize_nav_vouchers(None)
    assert result is not None
    assert "bridge_category" in result.columns
    assert len(result) == 0


def test_categorize_nav_vouchers_rule1_vtc_manual():
    """Test Rule 1: VTC Manual - manual bank account transactions."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "Bal_ Account Type": "Bank Account",
                "User ID": "USER/01",
                "Document Description": "Manual voucher entry",
                "Document Type": "Payment",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 50.0,
                "Bal_ Account Type": "Bank Account",
                "User ID": "ADMIN/05",
                "Document Description": "Another manual entry",
                "Document Type": "Payment",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "VTC Manual"
    assert result.loc[1, "bridge_category"] == "VTC Manual"


def test_categorize_nav_vouchers_rule1_not_vtc_manual_nav13():
    """Test Rule 1: Should NOT be VTC Manual when user is NAV/13."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "Bal_ Account Type": "Bank Account",
                "User ID": "NAV/13",
                "Document Description": "Automated entry",
                "Document Type": "Payment",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    # Should not be VTC Manual since user is NAV/13
    assert result.loc[0, "bridge_category"] != "VTC Manual"


def test_categorize_nav_vouchers_rule2_usage():
    """Test Rule 2: Usage - voucher application by NAV/13."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 75.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "Item price credit applied",
                "Document Type": "Sales",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 50.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "Voucher application for order",
                "Document Type": "Sales",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 25.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "Item shipping fees discount",
                "Document Type": "Sales",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Usage"
    assert result.loc[1, "bridge_category"] == "Usage"
    assert result.loc[2, "bridge_category"] == "Usage"


def test_categorize_nav_vouchers_rule3_issuance_refund():
    """Test Rule 3.b.1: Issuance - Refund."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -100.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "Refund voucher issued",
                "Document Type": "Credit Memo",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": -50.0,
                "Bal_ Account Type": "Customer",
                "User ID": "USER/01",
                "Document Description": "RFN voucher for customer",
                "Document Type": "Credit Memo",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"
    assert result.loc[1, "bridge_category"] == "Issuance - Refund"


def test_categorize_nav_vouchers_rule3_issuance_apology():
    """Test Rule 3.b.2: Issuance - Apology."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -75.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "Commercial register voucher",
                "Document Type": "Credit Memo",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": -60.0,
                "Bal_ Account Type": "Customer",
                "User ID": "USER/02",
                "Document Description": "CXP apology voucher",
                "Document Type": "Credit Memo",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Apology"
    assert result.loc[1, "bridge_category"] == "Issuance - Apology"


def test_categorize_nav_vouchers_rule3_issuance_jforce():
    """Test Rule 3.b.3: Issuance - JForce."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -200.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "PYT_PF JForce payout voucher",
                "Document Type": "Payment",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - JForce"


def test_categorize_nav_vouchers_rule3_generic_issuance():
    """Test Rule 3: Generic Issuance when no sub-category matches."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -150.0,
                "Bal_ Account Type": "Customer",
                "User ID": "USER/03",
                "Document Description": "Some other voucher issuance",
                "Document Type": "Credit Memo",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance"


def test_categorize_nav_vouchers_rule4_cancellation_store_credit():
    """Test Rule 4.a: Cancellation - Store Credit."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 85.0,
                "Bal_ Account Type": "Customer",
                "User ID": "USER/04",
                "Document Description": "Store credit cancellation",
                "Document Type": "Credit Memo",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Cancellation - Store Credit"


def test_categorize_nav_vouchers_rule4_cancellation_apology():
    """Test Rule 4.b: Cancellation - Apology."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 45.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "Voucher occur",
                "Document Type": "Payment",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Cancellation - Apology"


def test_categorize_nav_vouchers_rule5_expired():
    """Test Rule 5: Expired vouchers."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 30.0,
                "Bal_ Account Type": "G/L Account",
                "User ID": "USER/05",
                "Document Description": "EXP-2024-001",
                "Document Type": "General Journal",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 20.0,
                "Bal_ Account Type": "G/L Account",
                "User ID": "ADMIN/02",
                "Document Description": "Expired voucher cleanup",
                "Document Type": "General Journal",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Expired"
    assert result.loc[1, "bridge_category"] == "Expired"


def test_categorize_nav_vouchers_non_18412_account():
    """Test that non-18412 accounts are not categorized."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18410",
                "Amount": 100.0,
                "Bal_ Account Type": "Bank Account",
                "User ID": "USER/01",
                "Document Description": "Different account",
                "Document Type": "Payment",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert (
        pd.isna(result.loc[0, "bridge_category"])
        or result.loc[0, "bridge_category"] is None
    )


def test_categorize_nav_vouchers_mixed_scenarios():
    """Test a mix of different categorization rules."""
    df = pd.DataFrame(
        [
            # VTC Manual
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "Bal_ Account Type": "Bank Account",
                "User ID": "USER/01",
                "Document Description": "Manual entry",
                "Document Type": "Payment",
            },
            # Usage
            {
                "Chart of Accounts No_": "18412",
                "Amount": 50.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "Item price credit",
                "Document Type": "Sales",
            },
            # Issuance - Refund
            {
                "Chart of Accounts No_": "18412",
                "Amount": -75.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "Refund voucher",
                "Document Type": "Credit Memo",
            },
            # Expired
            {
                "Chart of Accounts No_": "18412",
                "Amount": 25.0,
                "Bal_ Account Type": "G/L Account",
                "User ID": "USER/02",
                "Document Description": "EXP-2024-123",
                "Document Type": "General Journal",
            },
            # Non-18412 (should not be categorized)
            {
                "Chart of Accounts No_": "13011",
                "Amount": 200.0,
                "Bal_ Account Type": "Bank Account",
                "User ID": "USER/03",
                "Document Description": "Different account",
                "Document Type": "Payment",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "VTC Manual"
    assert result.loc[1, "bridge_category"] == "Usage"
    assert result.loc[2, "bridge_category"] == "Issuance - Refund"
    assert result.loc[3, "bridge_category"] == "Expired"
    assert (
        pd.isna(result.loc[4, "bridge_category"])
        or result.loc[4, "bridge_category"] is None
    )


def test_categorize_nav_vouchers_case_insensitivity():
    """Test that categorization is case-insensitive."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 50.0,
                "Bal_ Account Type": "BANK ACCOUNT",
                "User ID": "user/01",
                "Document Description": "MANUAL ENTRY",
                "Document Type": "PAYMENT",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": -100.0,
                "Bal_ Account Type": "Customer",
                "User ID": "NAV/13",
                "Document Description": "REFUND VOUCHER ISSUED",
                "Document Type": "CREDIT MEMO",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "VTC Manual"
    assert result.loc[1, "bridge_category"] == "Issuance - Refund"


# ========================================================================
# Tests for calculate_timing_difference_bridge
# ========================================================================


def test_calculate_timing_difference_bridge_basic():
    """Test basic timing difference bridge calculation with simple variance."""
    # Create Jdash data
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},
            {"Voucher Id": "V002", "Amount Used": 200.0},
            {"Voucher Id": "V003", "Amount Used": 150.0},
        ]
    )

    # Create Usage TV data
    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001", "TotalUsageAmount": 100.0},  # Matches exactly
            {"voucher_code": "V002", "TotalUsageAmount": 180.0},  # Variance of 20
            {"voucher_code": "V003", "TotalUsageAmount": 150.0},  # Matches exactly
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    # Only V002 should have a variance
    assert bridge_amount == 20.0
    assert len(proof_df) == 1
    assert proof_df.loc["V002", "variance"] == 20.0
    assert proof_df.loc["V002", "Amount Used"] == 200.0
    assert proof_df.loc["V002", "TotalUsageAmount"] == 180.0


def test_calculate_timing_difference_bridge_empty_inputs():
    """Test with both empty DataFrames."""
    jdash_df = pd.DataFrame()
    doc_voucher_usage_df = pd.DataFrame()

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    assert bridge_amount == 0.0
    assert proof_df.empty
    assert list(proof_df.columns) == ["Amount Used", "TotalUsageAmount", "variance"]


def test_calculate_timing_difference_bridge_none_inputs():
    """Test with None inputs."""
    bridge_amount, proof_df = calculate_timing_difference_bridge(None, None)

    assert bridge_amount == 0.0
    assert proof_df.empty
    assert list(proof_df.columns) == ["Amount Used", "TotalUsageAmount", "variance"]


def test_calculate_timing_difference_bridge_empty_jdash():
    """Test with empty Jdash data but populated Usage TV data."""
    jdash_df = pd.DataFrame()
    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001", "TotalUsageAmount": 100.0},
            {"voucher_code": "V002", "TotalUsageAmount": 200.0},
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    # All Usage TV amounts should appear as negative variances
    assert bridge_amount == -300.0
    assert len(proof_df) == 2
    assert proof_df.loc["V001", "variance"] == -100.0
    assert proof_df.loc["V002", "variance"] == -200.0


def test_calculate_timing_difference_bridge_empty_usage_tv():
    """Test with populated Jdash data but empty Usage TV data."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},
            {"Voucher Id": "V002", "Amount Used": 200.0},
        ]
    )
    doc_voucher_usage_df = pd.DataFrame()

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    # All Jdash amounts should appear as positive variances
    assert bridge_amount == 300.0
    assert len(proof_df) == 2
    assert proof_df.loc["V001", "variance"] == 100.0
    assert proof_df.loc["V002", "variance"] == 200.0


def test_calculate_timing_difference_bridge_unmatched_vouchers():
    """Test with vouchers appearing in only one source."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},
            {"Voucher Id": "V002", "Amount Used": 200.0},
            {"Voucher Id": "V003", "Amount Used": 150.0},
        ]
    )

    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V002", "TotalUsageAmount": 200.0},  # Matches
            {"voucher_code": "V004", "TotalUsageAmount": 300.0},  # Only in Usage TV
            {"voucher_code": "V005", "TotalUsageAmount": 250.0},  # Only in Usage TV
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    # V001: +100 (in Jdash only)
    # V002: 0 (matched)
    # V003: +150 (in Jdash only)
    # V004: -300 (in Usage TV only)
    # V005: -250 (in Usage TV only)
    # Total: 100 + 150 - 300 - 250 = -300
    assert bridge_amount == -300.0
    assert len(proof_df) == 4  # V002 matched, so not in proof
    assert "V002" not in proof_df.index


def test_calculate_timing_difference_bridge_aggregation():
    """Test that duplicate voucher IDs are properly aggregated."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 50.0},
            {"Voucher Id": "V001", "Amount Used": 50.0},  # Duplicate
            {"Voucher Id": "V002", "Amount Used": 100.0},
        ]
    )

    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001", "TotalUsageAmount": 80.0},
            {"voucher_code": "V001", "TotalUsageAmount": 20.0},  # Duplicate
            {"voucher_code": "V002", "TotalUsageAmount": 100.0},
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    # V001: (50+50) - (80+20) = 100 - 100 = 0 (matched after aggregation)
    # V002: 100 - 100 = 0 (matched)
    assert bridge_amount == 0.0
    assert len(proof_df) == 0


def test_calculate_timing_difference_bridge_negative_variance():
    """Test with Usage TV amounts exceeding Jdash amounts."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},
            {"Voucher Id": "V002", "Amount Used": 50.0},
        ]
    )

    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001", "TotalUsageAmount": 150.0},
            {"voucher_code": "V002", "TotalUsageAmount": 100.0},
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    # V001: 100 - 150 = -50
    # V002: 50 - 100 = -50
    # Total: -100
    assert bridge_amount == -100.0
    assert len(proof_df) == 2
    assert proof_df.loc["V001", "variance"] == -50.0
    assert proof_df.loc["V002", "variance"] == -50.0


def test_calculate_timing_difference_bridge_positive_variance():
    """Test with Jdash amounts exceeding Usage TV amounts."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 200.0},
            {"Voucher Id": "V002", "Amount Used": 150.0},
        ]
    )

    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001", "TotalUsageAmount": 100.0},
            {"voucher_code": "V002", "TotalUsageAmount": 50.0},
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    # V001: 200 - 100 = 100
    # V002: 150 - 50 = 100
    # Total: 200
    assert bridge_amount == 200.0
    assert len(proof_df) == 2
    assert proof_df.loc["V001", "variance"] == 100.0
    assert proof_df.loc["V002", "variance"] == 100.0


def test_calculate_timing_difference_bridge_mixed_variances():
    """Test with a mix of positive and negative variances."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},  # Positive variance
            {"Voucher Id": "V002", "Amount Used": 50.0},  # Negative variance
            {"Voucher Id": "V003", "Amount Used": 200.0},  # Exact match
        ]
    )

    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001", "TotalUsageAmount": 80.0},
            {"voucher_code": "V002", "TotalUsageAmount": 100.0},
            {"voucher_code": "V003", "TotalUsageAmount": 200.0},
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    # V001: 100 - 80 = +20
    # V002: 50 - 100 = -50
    # V003: 200 - 200 = 0 (excluded from proof)
    # Total: 20 - 50 = -30
    assert bridge_amount == -30.0
    assert len(proof_df) == 2
    assert proof_df.loc["V001", "variance"] == 20.0
    assert proof_df.loc["V002", "variance"] == -50.0
    assert "V003" not in proof_df.index


def test_calculate_timing_difference_bridge_missing_jdash_columns():
    """Test that missing required columns in jdash_df raise ValueError."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001"},  # Missing Amount Used
        ]
    )
    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001", "TotalUsageAmount": 100.0},
        ]
    )

    with pytest.raises(ValueError, match="jdash_df must contain"):
        calculate_timing_difference_bridge(jdash_df, doc_voucher_usage_df)


def test_calculate_timing_difference_bridge_missing_usage_tv_columns():
    """Test that missing required columns in doc_voucher_usage_df raise ValueError."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},
        ]
    )
    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001"},  # Missing TotalUsageAmount
        ]
    )

    with pytest.raises(ValueError, match="doc_voucher_usage_df must contain"):
        calculate_timing_difference_bridge(jdash_df, doc_voucher_usage_df)


def test_calculate_timing_difference_bridge_output_format():
    """Test that output DataFrame has the correct format and columns."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},
        ]
    )
    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001", "TotalUsageAmount": 80.0},
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    assert bridge_amount == 20.0
    assert list(proof_df.columns) == ["Amount Used", "TotalUsageAmount", "variance"]
    assert proof_df.index.name in [
        None,
        "Voucher Id",
        "voucher_code",
    ]  # Index from merge
    assert len(proof_df) == 1


def test_calculate_timing_difference_bridge_zero_amounts():
    """Test handling of zero amounts."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 0.0},
            {"Voucher Id": "V002", "Amount Used": 100.0},
        ]
    )
    doc_voucher_usage_df = pd.DataFrame(
        [
            {"voucher_code": "V001", "TotalUsageAmount": 0.0},
            {"voucher_code": "V002", "TotalUsageAmount": 0.0},
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, doc_voucher_usage_df
    )

    # V001: 0 - 0 = 0 (excluded)
    # V002: 100 - 0 = 100
    assert bridge_amount == 100.0
    assert len(proof_df) == 1
    assert proof_df.loc["V002", "variance"] == 100.0


# ========================================================================
# Tests for calculate_integration_error_adjustment
# ========================================================================


def test_calculate_integration_error_adjustment_basic():
    """Test basic integration error adjustment with simple error data."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Cash Deposits",
                "Amount": 100.0,
                "Integration_Status": "Error",
                "Transaction_ID": "T001",
            },
            {
                "Source_System": "Refunds",
                "Amount": 200.0,
                "Integration_Status": "Failed",
                "Transaction_ID": "T002",
            },
            {
                "Source_System": "JForce Payouts",
                "Amount": 150.0,
                "Integration_Status": "Pending",
                "Transaction_ID": "T003",
            },
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    # All three errors should be included
    assert adjustment_amount == 450.0
    assert len(proof_df) == 3
    assert "Target_GL" in proof_df.columns
    assert proof_df[proof_df["Source_System"] == "Cash Deposits"]["Target_GL"].iloc[
        0
    ] == "13012"
    assert proof_df[proof_df["Source_System"] == "Refunds"]["Target_GL"].iloc[
        0
    ] == "18412"
    assert proof_df[proof_df["Source_System"] == "JForce Payouts"]["Target_GL"].iloc[
        0
    ] == "18412"


def test_calculate_integration_error_adjustment_filters_posted():
    """Test that Posted and Integrated statuses are filtered out."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Cash Deposits",
                "Amount": 100.0,
                "Integration_Status": "Posted",
                "Transaction_ID": "T001",
            },
            {
                "Source_System": "Refunds",
                "Amount": 200.0,
                "Integration_Status": "Integrated",
                "Transaction_ID": "T002",
            },
            {
                "Source_System": "JForce Payouts",
                "Amount": 150.0,
                "Integration_Status": "Error",
                "Transaction_ID": "T003",
            },
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    # Only T003 should be included (Error status)
    assert adjustment_amount == 150.0
    assert len(proof_df) == 1
    assert proof_df.iloc[0]["Transaction_ID"] == "T003"


def test_calculate_integration_error_adjustment_unmapped_sources():
    """Test that unmapped source systems are excluded."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Cash Deposits",
                "Amount": 100.0,
                "Integration_Status": "Error",
                "Transaction_ID": "T001",
            },
            {
                "Source_System": "Unknown System",
                "Amount": 200.0,
                "Integration_Status": "Error",
                "Transaction_ID": "T002",
            },
            {
                "Source_System": "Another Unknown",
                "Amount": 300.0,
                "Integration_Status": "Failed",
                "Transaction_ID": "T003",
            },
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    # Only Cash Deposits should be included (mapped source)
    assert adjustment_amount == 100.0
    assert len(proof_df) == 1
    assert proof_df.iloc[0]["Source_System"] == "Cash Deposits"


def test_calculate_integration_error_adjustment_gl_mapping():
    """Test that all GL mappings are correct."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            # GL 13023 (Accrued MPL Revenue)
            {
                "Source_System": "SC Account Statement",
                "Amount": 100.0,
                "Integration_Status": "Error",
            },
            {
                "Source_System": "Seller Account Statements",
                "Amount": 200.0,
                "Integration_Status": "Error",
            },
            # GL 18412 (Voucher Accrual)
            {
                "Source_System": "JForce Payouts",
                "Amount": 300.0,
                "Integration_Status": "Error",
            },
            {"Source_System": "Refunds", "Amount": 400.0, "Integration_Status": "Error"},
            # GL 18314 (MPL Vendor Liability)
            {
                "Source_System": "Prepaid Deliveries",
                "Amount": 500.0,
                "Integration_Status": "Error",
            },
            # GL 13012 (PSP / Collection)
            {
                "Source_System": "Cash Deposits",
                "Amount": 600.0,
                "Integration_Status": "Error",
            },
            {
                "Source_System": "Cash Deposit Cancel",
                "Amount": 700.0,
                "Integration_Status": "Error",
            },
            {
                "Source_System": "Payment Reconciles",
                "Amount": 800.0,
                "Integration_Status": "Error",
            },
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    # All errors should be included
    assert adjustment_amount == 3600.0
    assert len(proof_df) == 8

    # Verify GL mappings
    gl_13023_sources = proof_df[proof_df["Target_GL"] == "13023"]["Source_System"]
    assert set(gl_13023_sources) == {"SC Account Statement", "Seller Account Statements"}

    gl_18412_sources = proof_df[proof_df["Target_GL"] == "18412"]["Source_System"]
    assert set(gl_18412_sources) == {"JForce Payouts", "Refunds"}

    gl_18314_sources = proof_df[proof_df["Target_GL"] == "18314"]["Source_System"]
    assert set(gl_18314_sources) == {"Prepaid Deliveries"}

    gl_13012_sources = proof_df[proof_df["Target_GL"] == "13012"]["Source_System"]
    assert set(gl_13012_sources) == {
        "Cash Deposits",
        "Cash Deposit Cancel",
        "Payment Reconciles",
    }


def test_calculate_integration_error_adjustment_empty_input():
    """Test with empty DataFrame."""
    empty_df = pd.DataFrame()
    adjustment_amount, proof_df = calculate_integration_error_adjustment(empty_df)

    assert adjustment_amount == 0.0
    assert proof_df.empty
    assert list(proof_df.columns) == [
        "Source_System",
        "Transaction_ID",
        "Amount",
        "Target_GL",
    ]


def test_calculate_integration_error_adjustment_none_input():
    """Test with None input."""
    adjustment_amount, proof_df = calculate_integration_error_adjustment(None)

    assert adjustment_amount == 0.0
    assert proof_df.empty
    assert list(proof_df.columns) == [
        "Source_System",
        "Transaction_ID",
        "Amount",
        "Target_GL",
    ]


def test_calculate_integration_error_adjustment_missing_columns():
    """Test that missing required columns raise ValueError."""
    df = pd.DataFrame(
        {
            "Source_System": ["Cash Deposits"],
            "Amount": [100.0],
            # Missing 'Integration_Status'
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_integration_error_adjustment(df)


def test_calculate_integration_error_adjustment_no_transaction_id():
    """Test that function works without Transaction_ID column."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Cash Deposits",
                "Amount": 100.0,
                "Integration_Status": "Error",
            },
            {"Source_System": "Refunds", "Amount": 200.0, "Integration_Status": "Error"},
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    assert adjustment_amount == 300.0
    assert len(proof_df) == 2
    assert "Transaction_ID" in proof_df.columns
    assert list(proof_df.columns) == ["Source_System", "Transaction_ID", "Amount", "Target_GL"]


def test_calculate_integration_error_adjustment_all_posted():
    """Test that returns empty when all statuses are Posted/Integrated."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Cash Deposits",
                "Amount": 100.0,
                "Integration_Status": "Posted",
            },
            {
                "Source_System": "Refunds",
                "Amount": 200.0,
                "Integration_Status": "Integrated",
            },
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    assert adjustment_amount == 0.0
    assert proof_df.empty


def test_calculate_integration_error_adjustment_all_unmapped():
    """Test that returns empty when all sources are unmapped."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Unknown Source 1",
                "Amount": 100.0,
                "Integration_Status": "Error",
            },
            {
                "Source_System": "Unknown Source 2",
                "Amount": 200.0,
                "Integration_Status": "Failed",
            },
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    assert adjustment_amount == 0.0
    assert proof_df.empty


def test_calculate_integration_error_adjustment_mixed_statuses():
    """Test with a mix of different integration statuses."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Cash Deposits",
                "Amount": 100.0,
                "Integration_Status": "Error",
                "Transaction_ID": "T001",
            },
            {
                "Source_System": "Refunds",
                "Amount": 200.0,
                "Integration_Status": "Posted",
                "Transaction_ID": "T002",
            },
            {
                "Source_System": "JForce Payouts",
                "Amount": 150.0,
                "Integration_Status": "Failed",
                "Transaction_ID": "T003",
            },
            {
                "Source_System": "Prepaid Deliveries",
                "Amount": 250.0,
                "Integration_Status": "Integrated",
                "Transaction_ID": "T004",
            },
            {
                "Source_System": "Payment Reconciles",
                "Amount": 300.0,
                "Integration_Status": "Pending",
                "Transaction_ID": "T005",
            },
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    # Only T001, T003, and T005 should be included (not Posted/Integrated)
    assert adjustment_amount == 550.0
    assert len(proof_df) == 3
    assert set(proof_df["Transaction_ID"]) == {"T001", "T003", "T005"}


def test_calculate_integration_error_adjustment_negative_amounts():
    """Test handling of negative amounts."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Cash Deposits",
                "Amount": -100.0,
                "Integration_Status": "Error",
            },
            {"Source_System": "Refunds", "Amount": 200.0, "Integration_Status": "Error"},
            {
                "Source_System": "JForce Payouts",
                "Amount": -50.0,
                "Integration_Status": "Failed",
            },
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    # Total: -100 + 200 - 50 = 50
    assert adjustment_amount == 50.0
    assert len(proof_df) == 3


def test_calculate_integration_error_adjustment_output_format():
    """Test that output DataFrame has the correct format and columns."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Cash Deposits",
                "Amount": 100.0,
                "Integration_Status": "Error",
                "Transaction_ID": "T001",
            }
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    assert adjustment_amount == 100.0
    assert list(proof_df.columns) == [
        "Source_System",
        "Transaction_ID",
        "Amount",
        "Target_GL",
    ]
    assert len(proof_df) == 1
    assert proof_df.iloc[0]["Source_System"] == "Cash Deposits"
    assert proof_df.iloc[0]["Transaction_ID"] == "T001"
    assert proof_df.iloc[0]["Amount"] == 100.0
    assert proof_df.iloc[0]["Target_GL"] == "13012"


def test_calculate_integration_error_adjustment_zero_amount():
    """Test handling of zero amounts."""
    ipe_rec_errors_df = pd.DataFrame(
        [
            {
                "Source_System": "Cash Deposits",
                "Amount": 0.0,
                "Integration_Status": "Error",
            },
            {"Source_System": "Refunds", "Amount": 100.0, "Integration_Status": "Error"},
        ]
    )

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df
    )

    # Both should be included (even zero amount)
    assert adjustment_amount == 100.0
    assert len(proof_df) == 2
