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
    assert result.loc[1, "Integration_Type"] == "Manual"  # Updated: NAV/13 without BATCH/SRVC is now Manual
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
