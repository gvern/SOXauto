import os
import sys
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.bridges.catalog import load_rules  # noqa: E402
from src.bridges.classifier import (
    classify_bridges,
    calculate_customer_posting_group_bridge,
)  # noqa: E402


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
