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
)


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
# Tests for calculate_timing_difference_bridge (Month N vs N+1 logic)
# ========================================================================


def test_calculate_timing_difference_bridge_basic():
    """Test basic timing difference bridge calculation with Month N vs N+1 logic."""
    # Create IPE_08 data with vouchers used in September, delivered/canceled in October
    ipe_08_df = pd.DataFrame(
        [
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-15",
                "Order_Delivery_Date": "2025-10-05",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 100.0,
            },
            {
                "Business_Use": "apology_v2",
                "Order_Creation_Date": "2025-09-20",
                "Order_Delivery_Date": pd.NaT,
                "Order_Cancellation_Date": "2025-10-10",
                "remaining_amount": 200.0,
            },
            {
                "Business_Use": "store_credit",
                "Order_Creation_Date": "2025-09-25",
                "Order_Delivery_Date": "2025-09-28",  # Delivered in same month
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 150.0,
            },
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        ipe_08_df, "2025-09-30"
    )

    # Only first two vouchers should be included (delivered/canceled in Oct)
    assert bridge_amount == 300.0
    assert len(proof_df) == 2


def test_calculate_timing_difference_bridge_empty_input():
    """Test with empty DataFrame."""
    ipe_08_df = pd.DataFrame()

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        ipe_08_df, "2025-09-30"
    )

    assert bridge_amount == 0.0
    assert proof_df.empty


def test_calculate_timing_difference_bridge_none_input():
    """Test with None input."""
    bridge_amount, proof_df = calculate_timing_difference_bridge(None, "2025-09-30")

    assert bridge_amount == 0.0
    assert proof_df.empty


def test_calculate_timing_difference_bridge_filters_marketing():
    """Test that marketing vouchers are excluded."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "Business_Use": "marketing",
                "Order_Creation_Date": "2025-09-15",
                "Order_Delivery_Date": "2025-10-05",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 100.0,
            },
            {
                "Business_Use": "marketing_campaign",
                "Order_Creation_Date": "2025-09-20",
                "Order_Delivery_Date": "2025-10-10",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 200.0,
            },
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-25",
                "Order_Delivery_Date": "2025-10-15",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 150.0,
            },
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        ipe_08_df, "2025-09-30"
    )

    # Only the refund voucher should be included
    assert bridge_amount == 150.0
    assert len(proof_df) == 1
    assert proof_df.iloc[0]["Business_Use"] == "refund"


def test_calculate_timing_difference_bridge_filters_by_month():
    """Test that only vouchers created in Month N and delivered/canceled in Month N+1 are included."""
    ipe_08_df = pd.DataFrame(
        [
            # Created in Sep, delivered in Oct - INCLUDE
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-15",
                "Order_Delivery_Date": "2025-10-05",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 100.0,
            },
            # Created in Aug, delivered in Oct - EXCLUDE (wrong creation month)
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-08-15",
                "Order_Delivery_Date": "2025-10-05",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 200.0,
            },
            # Created in Sep, delivered in Sep - EXCLUDE (same month)
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-15",
                "Order_Delivery_Date": "2025-09-25",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 150.0,
            },
            # Created in Sep, delivered in Nov - EXCLUDE (wrong delivery month)
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-15",
                "Order_Delivery_Date": "2025-11-05",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 300.0,
            },
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        ipe_08_df, "2025-09-30"
    )

    # Only the first voucher should be included
    assert bridge_amount == 100.0
    assert len(proof_df) == 1


def test_calculate_timing_difference_bridge_cancellation_date():
    """Test that cancellation dates are properly handled."""
    ipe_08_df = pd.DataFrame(
        [
            # Canceled in Month N+1
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-15",
                "Order_Delivery_Date": pd.NaT,
                "Order_Cancellation_Date": "2025-10-05",
                "remaining_amount": 100.0,
            },
            # Delivered in Month N+1
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-20",
                "Order_Delivery_Date": "2025-10-10",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 200.0,
            },
            # Both delivery and cancellation in Month N+1 (should count once)
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-25",
                "Order_Delivery_Date": "2025-10-15",
                "Order_Cancellation_Date": "2025-10-20",
                "remaining_amount": 150.0,
            },
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        ipe_08_df, "2025-09-30"
    )

    # All three vouchers should be included
    assert bridge_amount == 450.0
    assert len(proof_df) == 3


def test_calculate_timing_difference_bridge_missing_columns():
    """Test that missing required columns raise ValueError."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-15",
                # Missing Order_Delivery_Date and other columns
            }
        ]
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_timing_difference_bridge(ipe_08_df, "2025-09-30")


def test_calculate_timing_difference_bridge_invalid_cutoff_date():
    """Test that invalid cutoff_date raises ValueError."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-15",
                "Order_Delivery_Date": "2025-10-05",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 100.0,
            }
        ]
    )

    with pytest.raises(ValueError, match="Invalid cutoff_date format"):
        calculate_timing_difference_bridge(ipe_08_df, "invalid-date")


def test_calculate_timing_difference_bridge_business_use_types():
    """Test that correct non-marketing business use types are included."""
    ipe_08_df = pd.DataFrame(
        [
            # Non-marketing types that should be INCLUDED
            {
                "Business_Use": "apology_v2",
                "Order_Creation_Date": "2025-09-15",
                "Order_Delivery_Date": "2025-10-05",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 100.0,
            },
            {
                "Business_Use": "jforce",
                "Order_Creation_Date": "2025-09-16",
                "Order_Delivery_Date": "2025-10-06",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 200.0,
            },
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-17",
                "Order_Delivery_Date": "2025-10-07",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 150.0,
            },
            {
                "Business_Use": "store_credit",
                "Order_Creation_Date": "2025-09-18",
                "Order_Delivery_Date": "2025-10-08",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 250.0,
            },
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        ipe_08_df, "2025-09-30"
    )

    # All non-marketing vouchers should be included
    assert bridge_amount == 700.0
    assert len(proof_df) == 4


def test_calculate_timing_difference_bridge_date_parsing():
    """Test that various date formats are parsed correctly."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "Business_Use": "refund",
                "Order_Creation_Date": pd.Timestamp("2025-09-15"),
                "Order_Delivery_Date": pd.Timestamp("2025-10-05"),
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 100.0,
            },
            {
                "Business_Use": "refund",
                "Order_Creation_Date": "2025-09-20T10:30:00",
                "Order_Delivery_Date": "2025-10-10T15:45:00",
                "Order_Cancellation_Date": pd.NaT,
                "remaining_amount": 200.0,
            },
        ]
    )

    bridge_amount, proof_df = calculate_timing_difference_bridge(
        ipe_08_df, "2025-09-30"
    )

    assert bridge_amount == 300.0
    assert len(proof_df) == 2
