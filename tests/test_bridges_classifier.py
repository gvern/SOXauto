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


def test_calculate_vtc_adjustment_vtc_category():
    """Test VTC adjustment recognizes 'VTC' category (new categorization)."""
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
            {"[Voucher No_]": "V001", "bridge_category": "VTC"},
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
    assert "voucher_type" in result.columns
    assert "Integration_Type" in result.columns
    assert len(result) == 0


def test_categorize_nav_vouchers_none_df():
    """Test that None input is handled correctly."""
    result = _categorize_nav_vouchers(None)
    assert result is not None
    assert "bridge_category" in result.columns
    assert "voucher_type" in result.columns
    assert "Integration_Type" in result.columns
    assert len(result) == 0


# ========================================================================
# Step 1: Integration_Type Tests
# ========================================================================


def test_categorize_nav_vouchers_step1_integration_type():
    """Test Step 1: Integration_Type detection (Manual vs Integration).

    New logic: If User ID contains "NAV" AND ("BATCH" OR "SRVC"), treat as Integration.
    """
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "User ID": "JUMIA/NAV31AFR.BATCH.SRVC",
                "Document Description": "Test entry",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "User ID": "NAV/13",  # Contains NAV but not BATCH or SRVC -> Manual
                "Document Description": "Test entry",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "User ID": "USER/01",
                "Document Description": "Test entry",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "User ID": "NAV13AFR.BATCH.SRVC",
                "Document Description": "Test entry",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "Integration_Type"] == "Integration"
    assert (
        result.loc[1, "Integration_Type"] == "Manual"
    )  # Updated: NAV/13 without BATCH/SRVC is now Manual
    assert result.loc[2, "Integration_Type"] == "Manual"
    assert result.loc[3, "Integration_Type"] == "Integration"


# ========================================================================
# Step 2: Issuance (Negative Amounts) Tests
# ========================================================================


def test_categorize_nav_vouchers_step2_issuance_integrated_refund():
    """Test Step 2: Integrated Issuance - Refund (description contains 'Refund')."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -100.0,
                "User ID": "JUMIA/NAV31AFR.BATCH.SRVC",
                "Document Description": "Refund voucher issued for order 12345",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"
    assert result.loc[0, "voucher_type"] == "Refund"
    assert result.loc[0, "Integration_Type"] == "Integration"


def test_categorize_nav_vouchers_step2_issuance_integrated_apology():
    """Test Step 2: Integrated Issuance - Apology (COMMERCIAL GESTURE)."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -75.0,
                "User ID": "JUMIA/NAV31AFR.BATCH.SRVC",
                "Document Description": "COMMERCIAL GESTURE voucher for customer",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Apology"
    assert result.loc[0, "voucher_type"] == "Apology"
    assert result.loc[0, "Integration_Type"] == "Integration"


def test_categorize_nav_vouchers_step2_issuance_integrated_jforce():
    """Test Step 2: Integrated Issuance - JForce (PYT_PF)."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -200.0,
                "User ID": "JUMIA/NAV31AFR.BATCH.SRVC",
                "Document Description": "PYT_PF JForce payout voucher",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - JForce"
    assert result.loc[0, "voucher_type"] == "JForce"


def test_categorize_nav_vouchers_step2_issuance_manual_store_credit():
    """Test Step 2: Manual Issuance - Store Credit (Doc No starts with country code)."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -150.0,
                "User ID": "USER/03",
                "Document Description": "Store credit issued",
                "Document No": "NG-SC-2024-001",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": -100.0,
                "User ID": "ADMIN/01",
                "Document Description": "Store credit issued",
                "Document No": "EG-SC-2024-002",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Store Credit"
    assert result.loc[0, "voucher_type"] == "Store Credit"
    assert result.loc[0, "Integration_Type"] == "Manual"
    assert result.loc[1, "bridge_category"] == "Issuance - Store Credit"
    assert result.loc[1, "voucher_type"] == "Store Credit"


def test_categorize_nav_vouchers_step2_issuance_manual_refund():
    """Test Step 2: Manual Issuance - Refund."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -50.0,
                "User ID": "USER/01",
                "Document Description": "RFN voucher for customer",
                "Document No": "INV-001",  # Does not start with country code
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"
    assert result.loc[0, "voucher_type"] == "Refund"
    assert result.loc[0, "Integration_Type"] == "Manual"


def test_categorize_nav_vouchers_step2_issuance_generic():
    """Test Step 2: Generic Issuance when no sub-category matches."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -150.0,
                "User ID": "USER/03",
                "Document Description": "Some other voucher issuance",
                "Document No": "INV-002",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance"
    assert result.loc[0, "Integration_Type"] == "Manual"


# ========================================================================
# Step 3: Usage (Positive Amounts + Integrated) Tests
# ========================================================================


def test_categorize_nav_vouchers_step3_usage_integrated():
    """Test Step 3: Usage - Integrated transactions."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 75.0,
                "User ID": "JUMIA/NAV13AFR.BATCH.SRVC",
                "Document Description": "Item price credit applied",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 50.0,
                "User ID": "JUMIA/NAV31AFR.BATCH.SRVC",
                "Document Description": "Voucher application for order",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Usage"
    assert result.loc[0, "Integration_Type"] == "Integration"
    assert result.loc[1, "bridge_category"] == "Usage"
    assert result.loc[1, "Integration_Type"] == "Integration"


def test_categorize_nav_vouchers_step3_cancellation_apology_voucher_accrual():
    """Test Step 3: Cancellation - Apology (Voucher Accrual description)."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 45.0,
                "User ID": "JUMIA/NAV13AFR.BATCH.SRVC",
                "Document Description": "Voucher Accrual reversal",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Cancellation - Apology"
    assert result.loc[0, "voucher_type"] == "Apology"


def test_categorize_nav_vouchers_step3_usage_with_voucher_lookup():
    """Test Step 3: Usage with voucher type lookup from IPE_08."""
    cr_03_df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 75.0,
                "User ID": "JUMIA/NAV13AFR.BATCH.SRVC",
                "Document Description": "Item price credit applied",
                "[Voucher No_]": "V001",
            },
        ]
    )
    ipe_08_df = pd.DataFrame(
        [
            {"id": "V001", "business_use": "refund"},
            {"id": "V002", "business_use": "apology"},
        ]
    )
    result = _categorize_nav_vouchers(cr_03_df, ipe_08_df=ipe_08_df)
    assert result.loc[0, "bridge_category"] == "Usage"
    assert result.loc[0, "voucher_type"] == "refund"


def test_categorize_nav_vouchers_step3_usage_fallback_doc_no():
    """Test Step 3: Usage with fallback lookup via Document No to Transaction_No."""
    cr_03_df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 75.0,
                "User ID": "JUMIA/NAV13AFR.BATCH.SRVC",
                "Document Description": "Item price credit applied",
                "[Voucher No_]": "",  # Empty voucher no
                "Document No": "TXN001",
            },
        ]
    )
    doc_voucher_usage_df = pd.DataFrame(
        [
            {"id": "V001", "business_use": "store_credit", "Transaction_No": "TXN001"},
        ]
    )
    result = _categorize_nav_vouchers(
        cr_03_df, doc_voucher_usage_df=doc_voucher_usage_df
    )
    assert result.loc[0, "bridge_category"] == "Usage"
    assert result.loc[0, "voucher_type"] == "store_credit"


# ========================================================================
# Step 4: Expired (Manual + Positive + 'EXPR') Tests
# ========================================================================


def test_categorize_nav_vouchers_step4_expired_apology():
    """Test Step 4: Expired - Apology (EXPR_APLGY)."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 30.0,
                "User ID": "USER/05",
                "Document Description": "EXPR_APLGY voucher cleanup",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Expired - Apology"
    assert result.loc[0, "voucher_type"] == "Apology"
    assert result.loc[0, "Integration_Type"] == "Manual"


def test_categorize_nav_vouchers_step4_expired_refund():
    """Test Step 4: Expired - Refund (EXPR_JFORCE)."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 25.0,
                "User ID": "ADMIN/02",
                "Document Description": "EXPR_JFORCE voucher expiry",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Expired - Refund"
    assert result.loc[0, "voucher_type"] == "Refund"


def test_categorize_nav_vouchers_step4_expired_store_credit():
    """Test Step 4: Expired - Store Credit (EXPR_STR CRDT)."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 20.0,
                "User ID": "USER/06",
                "Document Description": "EXPR_STR CRDT voucher",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": 15.0,
                "User ID": "USER/06",
                "Document Description": "EXPR_STR_CRDT voucher",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Expired - Store Credit"
    assert result.loc[0, "voucher_type"] == "Store Credit"
    assert result.loc[1, "bridge_category"] == "Expired - Store Credit"


def test_categorize_nav_vouchers_step4_expired_generic():
    """Test Step 4: Generic Expired (EXPR without sub-type)."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 35.0,
                "User ID": "USER/07",
                "Document Description": "EXPR-2024-001 cleanup",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Expired"


# ========================================================================
# Step 5: VTC (Manual + Positive + 'RND'/'PYT') Tests
# ========================================================================


def test_categorize_nav_vouchers_step5_vtc_manual_rnd():
    """Test Step 5: VTC - Manual RND."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "User ID": "USER/01",
                "Document Description": "Manual RND voucher entry",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "VTC"
    assert result.loc[0, "voucher_type"] == "Refund"
    assert result.loc[0, "Integration_Type"] == "Manual"


def test_categorize_nav_vouchers_step5_vtc_pyt_gtb():
    """Test Step 5: VTC - PYT_ with GTB in Comment."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 150.0,
                "User ID": "USER/02",
                "Document Description": "PYT_123 voucher",
                "Comment": "GTB bank transfer",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "VTC"
    assert result.loc[0, "voucher_type"] == "Refund"


# ========================================================================
# Step 6: Manual Cancellation (Manual + Positive + Credit Memo) Tests
# ========================================================================


def test_categorize_nav_vouchers_step6_manual_cancellation():
    """Test Step 6: Manual Cancellation - Store Credit via Credit Memo."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 85.0,
                "User ID": "USER/04",
                "Document Description": "Store credit cancellation",
                "Document Type": "Credit Memo",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Cancellation - Store Credit"
    assert result.loc[0, "voucher_type"] == "Store Credit"
    assert result.loc[0, "Integration_Type"] == "Manual"


# ========================================================================
# Step 7: Manual Usage (Nigeria Exception) Tests
# ========================================================================


def test_categorize_nav_vouchers_step7_manual_usage_itempricecredit():
    """Test Step 7: Manual Usage - ITEMPRICECREDIT (Nigeria exception)."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 60.0,
                "User ID": "USER/08",
                "Document Description": "ITEMPRICECREDIT adjustment",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Usage"
    assert result.loc[0, "Integration_Type"] == "Manual"


def test_categorize_nav_vouchers_step7_manual_usage_with_voucher_lookup():
    """Test Step 7: Manual Usage with voucher type lookup."""
    cr_03_df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 60.0,
                "User ID": "USER/08",
                "Document Description": "ITEMPRICECREDIT adjustment",
                "[Voucher No_]": "V003",
            },
        ]
    )
    ipe_08_df = pd.DataFrame(
        [
            {"id": "V003", "business_use": "store_credit"},
        ]
    )
    result = _categorize_nav_vouchers(cr_03_df, ipe_08_df=ipe_08_df)
    assert result.loc[0, "bridge_category"] == "Usage"
    assert result.loc[0, "voucher_type"] == "store_credit"


# ========================================================================
# General Tests
# ========================================================================


def test_categorize_nav_vouchers_non_18412_account():
    """Test that non-18412 accounts are not categorized."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18410",
                "Amount": 100.0,
                "User ID": "USER/01",
                "Document Description": "Different account",
            }
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert (
        pd.isna(result.loc[0, "bridge_category"])
        or result.loc[0, "bridge_category"] is None
    )
    # Integration_Type should still be set
    assert result.loc[0, "Integration_Type"] == "Manual"


def test_categorize_nav_vouchers_mixed_scenarios():
    """Test a mix of different categorization rules."""
    df = pd.DataFrame(
        [
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
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"
    assert result.loc[1, "bridge_category"] == "Usage"
    assert result.loc[2, "bridge_category"] == "VTC"
    assert result.loc[3, "bridge_category"] == "Expired - Apology"
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
                "User ID": "user/01",
                "Document Description": "manual rnd ENTRY",
            },
            {
                "Chart of Accounts No_": "18412",
                "Amount": -100.0,
                "User ID": "jumia/nav13afr.batch.srvc",
                "Document Description": "refund voucher issued",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "VTC"
    assert result.loc[1, "bridge_category"] == "Issuance - Refund"


def test_categorize_nav_vouchers_returns_enriched_columns():
    """Test that the function returns all three required columns."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 100.0,
                "User ID": "JUMIA/NAV13AFR.BATCH.SRVC",
                "Document Description": "Test",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert "bridge_category" in result.columns
    assert "voucher_type" in result.columns
    assert "Integration_Type" in result.columns


# ========================================================================
# Tests for calculate_timing_difference_bridge (Issuance vs Jdash Reconciliation)
# ========================================================================


def test_calculate_timing_difference_bridge_basic():
    """Test basic timing difference bridge comparing Jdash vs IPE_08 amounts."""
    # Create IPE_08 data (Issuance) with inactive vouchers
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,  # Inactive
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "apology_v2",
                "is_active": 0,  # Inactive
                "TotalAmountUsed": 200.0,
                "created_at": "2024-10-20",
            },
        ]
    )

    # Create Jdash data with ordered amounts
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 150.0},  # Ordered > Delivered
            {"Voucher Id": "V002", "Amount Used": 180.0},  # Ordered < Delivered
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    # Variance = Jdash['Amount Used'] - IPE_08['TotalAmountUsed']
    # V001: 150 - 100 = 50
    # V002: 180 - 200 = -20
    # Total: 50 + (-20) = 30
    assert variance_sum == 30.0
    assert len(proof_df) == 2
    assert "V001" in proof_df["id"].values
    assert "V002" in proof_df["id"].values


def test_calculate_timing_difference_bridge_empty_ipe08_input():
    """Test with empty IPE_08 DataFrame."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},
        ]
    )
    ipe_08_df = pd.DataFrame()

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    assert variance_sum == 0.0
    assert proof_df.empty


def test_calculate_timing_difference_bridge_none_ipe08_input():
    """Test with None IPE_08 input."""
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, None, "2024-10-31"
    )

    assert variance_sum == 0.0
    assert proof_df.empty


def test_calculate_timing_difference_bridge_empty_jdash():
    """Test with empty Jdash DataFrame - all IPE amounts become negative variance."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "apology_v2",
                "is_active": 0,
                "TotalAmountUsed": 200.0,
                "created_at": "2024-10-20",
            },
        ]
    )
    jdash_df = pd.DataFrame()

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    # Variance = 0 - IPE amount for each unmatched voucher
    # V001: 0 - 100 = -100
    # V002: 0 - 200 = -200
    # Total: -300
    assert variance_sum == -300.0
    assert len(proof_df) == 2


def test_calculate_timing_difference_bridge_filter_active_vouchers():
    """Test that only inactive vouchers (is_active == 0) are included."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,  # Inactive - included
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "refund",
                "is_active": 1,  # Active - excluded
                "TotalAmountUsed": 200.0,
                "created_at": "2024-10-15",
            },
        ]
    )

    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 150.0},
            {"Voucher Id": "V002", "Amount Used": 250.0},
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    # Only V001 should be included (is_active == 0)
    # Variance = 150 - 100 = 50
    assert variance_sum == 50.0
    assert len(proof_df) == 1
    assert proof_df.iloc[0]["id"] == "V001"


def test_calculate_timing_difference_bridge_filter_non_marketing():
    """Test that only non-marketing vouchers are included."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",  # Non-marketing
                "is_active": 0,
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "marketing",  # Marketing - excluded
                "is_active": 0,
                "TotalAmountUsed": 200.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V003",
                "business_use": "jforce",  # Non-marketing
                "is_active": 0,
                "TotalAmountUsed": 150.0,
                "created_at": "2024-10-15",
            },
        ]
    )

    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 120.0},
            {"Voucher Id": "V002", "Amount Used": 220.0},
            {"Voucher Id": "V003", "Amount Used": 160.0},
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    # Only V001 and V003 should be included
    # V001: 120 - 100 = 20
    # V003: 160 - 150 = 10
    # Total: 30
    assert variance_sum == 30.0
    assert len(proof_df) == 2
    assert "V002" not in proof_df["id"].values


def test_calculate_timing_difference_bridge_filter_one_year():
    """Test that only vouchers created within 1 year of cutoff are included."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",  # Within 1 year
            },
            {
                "id": "V002",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 200.0,
                "created_at": "2023-10-30",  # Just within 1 year (1 day before cutoff - 1 year)
            },
            {
                "id": "V003",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 150.0,
                "created_at": "2023-10-01",  # More than 1 year ago - excluded
            },
        ]
    )

    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 120.0},
            {"Voucher Id": "V002", "Amount Used": 220.0},
            {"Voucher Id": "V003", "Amount Used": 160.0},
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    # V001 and V002 should be included
    # V001: 120 - 100 = 20
    # V002: 220 - 200 = 20
    # Total: 40
    assert variance_sum == 40.0
    assert len(proof_df) == 2
    assert set(proof_df["id"].values) == {"V001", "V002"}


def test_calculate_timing_difference_bridge_jdash_aggregation():
    """Test that Jdash amounts are aggregated by Voucher Id."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",
            },
        ]
    )

    # Multiple Jdash entries for same voucher
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 50.0},
            {"Voucher Id": "V001", "Amount Used": 30.0},
            {"Voucher Id": "V001", "Amount Used": 40.0},  # Total: 120
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    # Jdash aggregated: 50 + 30 + 40 = 120
    # Variance = 120 - 100 = 20
    assert variance_sum == 20.0
    assert len(proof_df) == 1


def test_calculate_timing_difference_bridge_unmatched_vouchers():
    """Test vouchers in IPE_08 without matching Jdash entries get 0 Jdash amount."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 200.0,
                "created_at": "2024-10-20",
            },
        ]
    )

    # Only V001 has Jdash entry
    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 150.0},
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    # V001: 150 - 100 = 50
    # V002: 0 - 200 = -200 (no Jdash match, filled with 0)
    # Total: 50 + (-200) = -150
    assert variance_sum == -150.0
    assert len(proof_df) == 2


def test_calculate_timing_difference_bridge_all_non_marketing_types():
    """Test that all non-marketing types are included."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "apology_v2",
                "is_active": 0,
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "jforce",
                "is_active": 0,
                "TotalAmountUsed": 200.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V003",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 150.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V004",
                "business_use": "store_credit",
                "is_active": 0,
                "TotalAmountUsed": 50.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V005",
                "business_use": "Jpay store_credit",
                "is_active": 0,
                "TotalAmountUsed": 75.0,
                "created_at": "2024-10-15",
            },
        ]
    )

    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 100.0},
            {"Voucher Id": "V002", "Amount Used": 200.0},
            {"Voucher Id": "V003", "Amount Used": 150.0},
            {"Voucher Id": "V004", "Amount Used": 50.0},
            {"Voucher Id": "V005", "Amount Used": 75.0},
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    # All have matching amounts, so variance = 0 for each
    assert variance_sum == 0.0
    assert len(proof_df) == 5


def test_calculate_timing_difference_bridge_output_format():
    """Test that output DataFrame has the correct columns."""
    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",
            },
        ]
    )

    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 150.0},
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    assert variance_sum == 50.0
    # Check required columns are present
    assert "id" in proof_df.columns
    assert "business_use" in proof_df.columns
    assert "TotalAmountUsed" in proof_df.columns
    assert "Jdash_Amount_Used" in proof_df.columns
    assert "Variance" in proof_df.columns
    assert len(proof_df) == 1


def test_calculate_timing_difference_bridge_comprehensive():
    """Test comprehensive scenario with multiple filters and reconciliation cases."""
    ipe_08_df = pd.DataFrame(
        [
            # Included: inactive, non-marketing, within 1 year
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "TotalAmountUsed": 100.0,
                "created_at": "2024-10-15",
            },
            # Excluded: active
            {
                "id": "V002",
                "business_use": "refund",
                "is_active": 1,
                "TotalAmountUsed": 200.0,
                "created_at": "2024-10-15",
            },
            # Excluded: marketing
            {
                "id": "V003",
                "business_use": "marketing",
                "is_active": 0,
                "TotalAmountUsed": 300.0,
                "created_at": "2024-10-15",
            },
            # Included: inactive, non-marketing, within 1 year
            {
                "id": "V004",
                "business_use": "apology_v2",
                "is_active": 0,
                "TotalAmountUsed": 150.0,
                "created_at": "2024-06-01",
            },
            # Included but no Jdash match
            {
                "id": "V005",
                "business_use": "store_credit",
                "is_active": 0,
                "TotalAmountUsed": 75.0,
                "created_at": "2024-09-01",
            },
        ]
    )

    jdash_df = pd.DataFrame(
        [
            {"Voucher Id": "V001", "Amount Used": 120.0},
            {"Voucher Id": "V002", "Amount Used": 220.0},  # Will be ignored (V002 excluded)
            {"Voucher Id": "V003", "Amount Used": 320.0},  # Will be ignored (V003 excluded)
            {"Voucher Id": "V004", "Amount Used": 140.0},
            # V005 has no Jdash entry
        ]
    )

    variance_sum, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, "2024-10-31"
    )

    # Included vouchers: V001, V004, V005
    # V001: 120 - 100 = 20
    # V004: 140 - 150 = -10
    # V005: 0 - 75 = -75 (no Jdash match)
    # Total: 20 + (-10) + (-75) = -65
    assert variance_sum == -65.0
    assert len(proof_df) == 3
    
    included_ids = set(proof_df["id"].values)
    assert included_ids == {"V001", "V004", "V005"}
    
    # Verify excluded vouchers
    assert "V002" not in included_ids
    assert "V003" not in included_ids


# ========================================================================
# Tests for Production Data Patterns (Ghana CR_03 Issue Fix)
# ========================================================================


def test_categorize_nav_vouchers_production_integration_user_nav13():
    """Test production data pattern: JUMIA\\NAV13AFR.BATCH.SRVC as Integration user."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -100.0,
                "User ID": "JUMIA\\NAV13AFR.BATCH.SRVC",
                "Document Description": "RF_317489956_0925",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "Integration_Type"] == "Integration"
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"
    assert result.loc[0, "voucher_type"] == "Refund"


def test_categorize_nav_vouchers_production_rf_prefix_pattern():
    """Test production data pattern: RF_317... description for refunds."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -5437.00,
                "User ID": "JUMIA\\NAV13AFR.BATCH.SRVC",
                "Document Description": "RF_317489956_0925",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"
    assert result.loc[0, "voucher_type"] == "Refund"


def test_categorize_nav_vouchers_production_vtc_bank_account_negative():
    """Test production data pattern: VTC via Bank Account with negative amount."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -5437.00,
                "User ID": "JUMIA\\ABIR.OUALI",
                "Document Description": "Customer refund payment",
                "Bal_ Account Type": "Bank Account",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "Integration_Type"] == "Manual"
    assert result.loc[0, "bridge_category"] == "VTC"
    assert result.loc[0, "voucher_type"] == "Refund"


def test_categorize_nav_vouchers_production_vtc_bank_account_positive():
    """Test production data pattern: VTC via Bank Account with positive amount."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": 5437.00,
                "User ID": "JUMIA\\ABIR.OUALI",
                "Document Description": "Customer refund adjustment",
                "Bal_ Account Type": "Bank Account",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "Integration_Type"] == "Manual"
    assert result.loc[0, "bridge_category"] == "VTC"
    assert result.loc[0, "voucher_type"] == "Refund"


def test_categorize_nav_vouchers_production_pyt_jforce():
    """Test production data pattern: PYT_ pattern for JForce."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -200.0,
                "User ID": "JUMIA\\NAV13AFR.BATCH.SRVC",
                "Document Description": "PYT_123456_0925",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - JForce"
    assert result.loc[0, "voucher_type"] == "JForce"


def test_categorize_nav_vouchers_production_case_insensitivity():
    """Test production data pattern: Case insensitivity for all inputs."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -100.0,
                "User ID": "jumia\\nav13afr.batch.srvc",
                "Document Description": "rf_317489956_0925",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "Integration_Type"] == "Integration"
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"


def test_categorize_nav_vouchers_production_combined_scenario():
    """Test production data patterns: Combined scenario with multiple row types."""
    df = pd.DataFrame(
        [
            # Integration user with RF_ prefix (refund issuance)
            {
                "Chart of Accounts No_": "18412",
                "Amount": -5437.00,
                "User ID": "JUMIA\\NAV13AFR.BATCH.SRVC",
                "Document Description": "RF_317489956_0925",
            },
            # Manual user with Bank Account (VTC negative)
            {
                "Chart of Accounts No_": "18412",
                "Amount": -3250.00,
                "User ID": "JUMIA\\ABIR.OUALI",
                "Document Description": "Payment to customer",
                "Bal_ Account Type": "Bank Account",
            },
            # Integration user with PYT_ prefix (JForce)
            {
                "Chart of Accounts No_": "18412",
                "Amount": -1500.00,
                "User ID": "JUMIA\\NAV13AFR.BATCH.SRVC",
                "Document Description": "PYT_789012_0925",
            },
            # Manual user without Bank Account (generic issuance)
            {
                "Chart of Accounts No_": "18412",
                "Amount": -500.00,
                "User ID": "JUMIA\\REGULAR.USER",
                "Document Description": "Some other voucher",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)

    # Row 0: Integration + RF_ = Issuance - Refund
    assert result.loc[0, "Integration_Type"] == "Integration"
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"

    # Row 1: Manual + Bank Account = VTC
    assert result.loc[1, "Integration_Type"] == "Manual"
    assert result.loc[1, "bridge_category"] == "VTC"

    # Row 2: Integration + PYT_ = Issuance - JForce
    assert result.loc[2, "Integration_Type"] == "Integration"
    assert result.loc[2, "bridge_category"] == "Issuance - JForce"

    # Row 3: Manual without Bank Account = generic Issuance
    assert result.loc[3, "Integration_Type"] == "Manual"
    assert result.loc[3, "bridge_category"] == "Issuance"


def test_categorize_nav_vouchers_production_rf_space_pattern():
    """Test production data pattern: RF with space (RF ) pattern for refunds."""
    df = pd.DataFrame(
        [
            {
                "Chart of Accounts No_": "18412",
                "Amount": -100.0,
                "User ID": "JUMIA\\NAV13AFR.BATCH.SRVC",
                "Document Description": "RF 317489956 0925",
            },
        ]
    )
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"
    assert result.loc[0, "voucher_type"] == "Refund"


# ========================================================================
# Tests for _filter_ipe08_scope Helper Function
# ========================================================================


def test_filter_ipe08_scope_basic():
    """Test basic filtering of IPE_08 with non-marketing vouchers."""
    from src.bridges.classifier import _filter_ipe08_scope

    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "Order_Creation_Date": "2024-10-15",
                "remaining_amount": 100.0,
            },
            {
                "id": "V002",
                "business_use": "marketing",  # Should be filtered out
                "Order_Creation_Date": "2024-10-15",
                "remaining_amount": 200.0,
            },
            {
                "id": "V003",
                "business_use": "apology_v2",
                "Order_Creation_Date": "2024-10-15",
                "remaining_amount": 150.0,
            },
        ]
    )

    result = _filter_ipe08_scope(ipe_08_df)

    # Only V001 and V003 should remain (non-marketing)
    assert len(result) == 2
    assert "V001" in result["id"].values
    assert "V003" in result["id"].values
    assert "V002" not in result["id"].values


def test_filter_ipe08_scope_all_non_marketing_types():
    """Test that all non-marketing types are retained."""
    from src.bridges.classifier import _filter_ipe08_scope

    ipe_08_df = pd.DataFrame(
        [
            {"id": "V001", "business_use": "apology_v2", "remaining_amount": 100.0},
            {"id": "V002", "business_use": "jforce", "remaining_amount": 200.0},
            {"id": "V003", "business_use": "refund", "remaining_amount": 150.0},
            {"id": "V004", "business_use": "store_credit", "remaining_amount": 50.0},
            {
                "id": "V005",
                "business_use": "Jpay store_credit",
                "remaining_amount": 75.0,
            },
        ]
    )

    result = _filter_ipe08_scope(ipe_08_df)

    # All should be retained
    assert len(result) == 5
    assert set(result["id"].values) == {"V001", "V002", "V003", "V004", "V005"}


def test_filter_ipe08_scope_date_conversion():
    """Test that date columns are converted to datetime."""
    from src.bridges.classifier import _filter_ipe08_scope

    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "Order_Creation_Date": "2024-10-15",
                "Order_Delivery_Date": "2024-10-20",
                "Order_Cancellation_Date": "2024-10-25",
                "remaining_amount": 100.0,
            },
        ]
    )

    result = _filter_ipe08_scope(ipe_08_df)

    # Check that dates are datetime objects
    assert pd.api.types.is_datetime64_any_dtype(result["Order_Creation_Date"])
    assert pd.api.types.is_datetime64_any_dtype(result["Order_Delivery_Date"])
    assert pd.api.types.is_datetime64_any_dtype(result["Order_Cancellation_Date"])


def test_filter_ipe08_scope_empty_input():
    """Test that empty DataFrame is handled correctly."""
    from src.bridges.classifier import _filter_ipe08_scope

    ipe_08_df = pd.DataFrame()
    result = _filter_ipe08_scope(ipe_08_df)

    assert result.empty


def test_filter_ipe08_scope_none_input():
    """Test that None input is handled correctly."""
    from src.bridges.classifier import _filter_ipe08_scope

    result = _filter_ipe08_scope(None)

    assert result.empty


def test_filter_ipe08_scope_missing_business_use_column():
    """Test handling when business_use column is missing."""
    from src.bridges.classifier import _filter_ipe08_scope

    ipe_08_df = pd.DataFrame(
        [
            {"id": "V001", "remaining_amount": 100.0},
            {"id": "V002", "remaining_amount": 200.0},
        ]
    )

    result = _filter_ipe08_scope(ipe_08_df)

    # All rows retained when column is missing
    assert len(result) == 2  # All rows retained when column is missing


def test_filter_ipe08_scope_date_columns_missing():
    """Test that missing date columns don't cause errors."""
    from src.bridges.classifier import _filter_ipe08_scope

    ipe_08_df = pd.DataFrame(
        [
            {"id": "V001", "business_use": "refund", "remaining_amount": 100.0},
            {"id": "V002", "business_use": "apology_v2", "remaining_amount": 200.0},
        ]
    )

    result = _filter_ipe08_scope(ipe_08_df)

    # Should work fine without date columns
    assert len(result) == 2


def test_filter_ipe08_scope_preserves_other_columns():
    """Test that other columns are preserved after filtering."""
    from src.bridges.classifier import _filter_ipe08_scope

    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use": "refund",
                "remaining_amount": 100.0,
                "ID_COMPANY": "NG",
                "custom_field": "value1",
            },
            {
                "id": "V002",
                "business_use": "jforce",
                "remaining_amount": 200.0,
                "ID_COMPANY": "EG",
                "custom_field": "value2",
            },
        ]
    )

    result = _filter_ipe08_scope(ipe_08_df)

    # All columns should be preserved
    assert "id" in result.columns
    assert "business_use" in result.columns
    assert "remaining_amount" in result.columns
    assert "ID_COMPANY" in result.columns
    assert "custom_field" in result.columns
    assert len(result) == 2


def test_filter_ipe08_scope_business_use_formatted_column():
    """Test that business_use_formatted column is also supported for backward compatibility."""
    from src.bridges.classifier import _filter_ipe08_scope

    ipe_08_df = pd.DataFrame(
        [
            {
                "id": "V001",
                "business_use_formatted": "refund",
                "remaining_amount": 100.0,
            },
            {
                "id": "V002",
                "business_use_formatted": "marketing",  # Should be filtered out
                "remaining_amount": 200.0,
            },
            {
                "id": "V003",
                "business_use_formatted": "apology_v2",
                "remaining_amount": 150.0,
            },
        ]
    )

    result = _filter_ipe08_scope(ipe_08_df)

    # Only V001 and V003 should remain (non-marketing)
    assert len(result) == 2
    assert "V001" in result["id"].values
    assert "V003" in result["id"].values
    assert "V002" not in result["id"].values
