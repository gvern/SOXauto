import os
import sys
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.bridges.catalog import load_rules
from src.bridges.classifier import classify_bridges, _categorize_nav_vouchers


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
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": 100.0,
            "Bal_ Account Type": "Bank Account",
            "User ID": "USER/01",
            "Document Description": "Manual voucher entry",
            "Document Type": "Payment"
        },
        {
            "Chart of Accounts No_": "18412",
            "Amount": 50.0,
            "Bal_ Account Type": "Bank Account",
            "User ID": "ADMIN/05",
            "Document Description": "Another manual entry",
            "Document Type": "Payment"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "VTC Manual"
    assert result.loc[1, "bridge_category"] == "VTC Manual"


def test_categorize_nav_vouchers_rule1_not_vtc_manual_nav13():
    """Test Rule 1: Should NOT be VTC Manual when user is NAV/13."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": 100.0,
            "Bal_ Account Type": "Bank Account",
            "User ID": "NAV/13",
            "Document Description": "Automated entry",
            "Document Type": "Payment"
        }
    ])
    result = _categorize_nav_vouchers(df)
    # Should not be VTC Manual since user is NAV/13
    assert result.loc[0, "bridge_category"] != "VTC Manual"


def test_categorize_nav_vouchers_rule2_usage():
    """Test Rule 2: Usage - voucher application by NAV/13."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": 75.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "Item price credit applied",
            "Document Type": "Sales"
        },
        {
            "Chart of Accounts No_": "18412",
            "Amount": 50.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "Voucher application for order",
            "Document Type": "Sales"
        },
        {
            "Chart of Accounts No_": "18412",
            "Amount": 25.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "Item shipping fees discount",
            "Document Type": "Sales"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Usage"
    assert result.loc[1, "bridge_category"] == "Usage"
    assert result.loc[2, "bridge_category"] == "Usage"


def test_categorize_nav_vouchers_rule3_issuance_refund():
    """Test Rule 3.b.1: Issuance - Refund."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": -100.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "Refund voucher issued",
            "Document Type": "Credit Memo"
        },
        {
            "Chart of Accounts No_": "18412",
            "Amount": -50.0,
            "Bal_ Account Type": "Customer",
            "User ID": "USER/01",
            "Document Description": "RFN voucher for customer",
            "Document Type": "Credit Memo"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Refund"
    assert result.loc[1, "bridge_category"] == "Issuance - Refund"


def test_categorize_nav_vouchers_rule3_issuance_apology():
    """Test Rule 3.b.2: Issuance - Apology."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": -75.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "Commercial register voucher",
            "Document Type": "Credit Memo"
        },
        {
            "Chart of Accounts No_": "18412",
            "Amount": -60.0,
            "Bal_ Account Type": "Customer",
            "User ID": "USER/02",
            "Document Description": "CXP apology voucher",
            "Document Type": "Credit Memo"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - Apology"
    assert result.loc[1, "bridge_category"] == "Issuance - Apology"


def test_categorize_nav_vouchers_rule3_issuance_jforce():
    """Test Rule 3.b.3: Issuance - JForce."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": -200.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "PYT_PF JForce payout voucher",
            "Document Type": "Payment"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance - JForce"


def test_categorize_nav_vouchers_rule3_generic_issuance():
    """Test Rule 3: Generic Issuance when no sub-category matches."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": -150.0,
            "Bal_ Account Type": "Customer",
            "User ID": "USER/03",
            "Document Description": "Some other voucher issuance",
            "Document Type": "Credit Memo"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Issuance"


def test_categorize_nav_vouchers_rule4_cancellation_store_credit():
    """Test Rule 4.a: Cancellation - Store Credit."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": 85.0,
            "Bal_ Account Type": "Customer",
            "User ID": "USER/04",
            "Document Description": "Store credit cancellation",
            "Document Type": "Credit Memo"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Cancellation - Store Credit"


def test_categorize_nav_vouchers_rule4_cancellation_apology():
    """Test Rule 4.b: Cancellation - Apology."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": 45.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "Voucher occur",
            "Document Type": "Payment"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Cancellation - Apology"


def test_categorize_nav_vouchers_rule5_expired():
    """Test Rule 5: Expired vouchers."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": 30.0,
            "Bal_ Account Type": "G/L Account",
            "User ID": "USER/05",
            "Document Description": "EXP-2024-001",
            "Document Type": "General Journal"
        },
        {
            "Chart of Accounts No_": "18412",
            "Amount": 20.0,
            "Bal_ Account Type": "G/L Account",
            "User ID": "ADMIN/02",
            "Document Description": "Expired voucher cleanup",
            "Document Type": "General Journal"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "Expired"
    assert result.loc[1, "bridge_category"] == "Expired"


def test_categorize_nav_vouchers_non_18412_account():
    """Test that non-18412 accounts are not categorized."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18410",
            "Amount": 100.0,
            "Bal_ Account Type": "Bank Account",
            "User ID": "USER/01",
            "Document Description": "Different account",
            "Document Type": "Payment"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert pd.isna(result.loc[0, "bridge_category"]) or result.loc[0, "bridge_category"] is None


def test_categorize_nav_vouchers_mixed_scenarios():
    """Test a mix of different categorization rules."""
    df = pd.DataFrame([
        # VTC Manual
        {
            "Chart of Accounts No_": "18412",
            "Amount": 100.0,
            "Bal_ Account Type": "Bank Account",
            "User ID": "USER/01",
            "Document Description": "Manual entry",
            "Document Type": "Payment"
        },
        # Usage
        {
            "Chart of Accounts No_": "18412",
            "Amount": 50.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "Item price credit",
            "Document Type": "Sales"
        },
        # Issuance - Refund
        {
            "Chart of Accounts No_": "18412",
            "Amount": -75.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "Refund voucher",
            "Document Type": "Credit Memo"
        },
        # Expired
        {
            "Chart of Accounts No_": "18412",
            "Amount": 25.0,
            "Bal_ Account Type": "G/L Account",
            "User ID": "USER/02",
            "Document Description": "EXP-2024-123",
            "Document Type": "General Journal"
        },
        # Non-18412 (should not be categorized)
        {
            "Chart of Accounts No_": "13011",
            "Amount": 200.0,
            "Bal_ Account Type": "Bank Account",
            "User ID": "USER/03",
            "Document Description": "Different account",
            "Document Type": "Payment"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "VTC Manual"
    assert result.loc[1, "bridge_category"] == "Usage"
    assert result.loc[2, "bridge_category"] == "Issuance - Refund"
    assert result.loc[3, "bridge_category"] == "Expired"
    assert pd.isna(result.loc[4, "bridge_category"]) or result.loc[4, "bridge_category"] is None


def test_categorize_nav_vouchers_case_insensitivity():
    """Test that categorization is case-insensitive."""
    df = pd.DataFrame([
        {
            "Chart of Accounts No_": "18412",
            "Amount": 50.0,
            "Bal_ Account Type": "BANK ACCOUNT",
            "User ID": "user/01",
            "Document Description": "MANUAL ENTRY",
            "Document Type": "PAYMENT"
        },
        {
            "Chart of Accounts No_": "18412",
            "Amount": -100.0,
            "Bal_ Account Type": "Customer",
            "User ID": "NAV/13",
            "Document Description": "REFUND VOUCHER ISSUED",
            "Document Type": "CREDIT MEMO"
        }
    ])
    result = _categorize_nav_vouchers(df)
    assert result.loc[0, "bridge_category"] == "VTC Manual"
    assert result.loc[1, "bridge_category"] == "Issuance - Refund"
