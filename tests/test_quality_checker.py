"""
Tests for the Data Quality Checker module.
"""

import pandas as pd
import sys
import os

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.core.quality_checker import (
    RowCountCheck,
    ColumnExistsCheck,
    NumericSumCheck,
    NoNullsCheck,
    DataQualityEngine,
    QualityReport,
)


# =======================
# RowCountCheck Tests
# =======================

def test_row_count_check_pass_min_only():
    """Test RowCountCheck passes with minimum row count."""
    df = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
    rule = RowCountCheck(min_rows=3)
    passed, message = rule.check(df)

    assert passed is True
    assert "PASS" in message
    assert "5 rows" in message


def test_row_count_check_pass_with_max():
    """Test RowCountCheck passes when within min and max bounds."""
    df = pd.DataFrame({"A": [1, 2, 3]})
    rule = RowCountCheck(min_rows=2, max_rows=5)
    passed, message = rule.check(df)

    assert passed is True
    assert "PASS" in message
    assert "3 rows" in message


def test_row_count_check_fail_too_few():
    """Test RowCountCheck fails with too few rows."""
    df = pd.DataFrame({"A": [1, 2]})
    rule = RowCountCheck(min_rows=5)
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "2 rows" in message
    assert ">= 5" in message


def test_row_count_check_fail_too_many():
    """Test RowCountCheck fails with too many rows."""
    df = pd.DataFrame({"A": range(20)})
    rule = RowCountCheck(min_rows=1, max_rows=10)
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "20 rows" in message


def test_row_count_check_empty_dataframe():
    """Test RowCountCheck with empty DataFrame."""
    df = pd.DataFrame()
    rule = RowCountCheck(min_rows=1)
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "0 rows" in message


# =======================
# ColumnExistsCheck Tests
# =======================

def test_column_exists_check_pass():
    """Test ColumnExistsCheck passes when column exists."""
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
    rule = ColumnExistsCheck(column_name="B")
    passed, message = rule.check(df)

    assert passed is True
    assert "PASS" in message
    assert "B" in message


def test_column_exists_check_fail():
    """Test ColumnExistsCheck fails when column missing."""
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    rule = ColumnExistsCheck(column_name="C")
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "C" in message
    assert "not found" in message


def test_column_exists_check_empty_dataframe():
    """Test ColumnExistsCheck with empty DataFrame."""
    df = pd.DataFrame()
    rule = ColumnExistsCheck(column_name="A")
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message


# =======================
# NumericSumCheck Tests
# =======================

def test_numeric_sum_check_pass_zero():
    """Test NumericSumCheck passes when sum is zero and should be."""
    df = pd.DataFrame({"values": [1, -1, 2, -2, 0]})
    rule = NumericSumCheck(column_name="values", should_be_zero=True)
    passed, message = rule.check(df)

    assert passed is True
    assert "PASS" in message
    assert "sum of 'values' is 0" in message


def test_numeric_sum_check_fail_not_zero():
    """Test NumericSumCheck fails when sum is not zero but should be."""
    df = pd.DataFrame({"values": [1, 2, 3]})
    rule = NumericSumCheck(column_name="values", should_be_zero=True)
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "expected 0" in message


def test_numeric_sum_check_pass_non_zero():
    """Test NumericSumCheck passes when sum is non-zero and should be."""
    df = pd.DataFrame({"values": [1, 2, 3]})
    rule = NumericSumCheck(column_name="values", should_be_zero=False)
    passed, message = rule.check(df)

    assert passed is True
    assert "PASS" in message
    assert "expected non-zero" in message


def test_numeric_sum_check_fail_zero_when_nonzero_expected():
    """Test NumericSumCheck fails when sum is zero but should be non-zero."""
    df = pd.DataFrame({"values": [0, 0, 0]})
    rule = NumericSumCheck(column_name="values", should_be_zero=False)
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "expected non-zero" in message


def test_numeric_sum_check_column_not_found():
    """Test NumericSumCheck fails when column doesn't exist."""
    df = pd.DataFrame({"A": [1, 2, 3]})
    rule = NumericSumCheck(column_name="B", should_be_zero=True)
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "not found" in message


def test_numeric_sum_check_non_numeric_column():
    """Test NumericSumCheck fails gracefully with non-numeric data."""
    df = pd.DataFrame({"text": ["a", "b", "c"]})
    rule = NumericSumCheck(column_name="text", should_be_zero=True)
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message


# =======================
# NoNullsCheck Tests
# =======================

def test_no_nulls_check_pass():
    """Test NoNullsCheck passes when no nulls present."""
    df = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
    rule = NoNullsCheck(column_name="A")
    passed, message = rule.check(df)

    assert passed is True
    assert "PASS" in message
    assert "no nulls" in message


def test_no_nulls_check_fail_with_nulls():
    """Test NoNullsCheck fails when nulls present."""
    df = pd.DataFrame({"A": [1, None, 3, None, 5]})
    rule = NoNullsCheck(column_name="A")
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "2 null values" in message
    assert "out of 5 rows" in message


def test_no_nulls_check_column_not_found():
    """Test NoNullsCheck fails when column doesn't exist."""
    df = pd.DataFrame({"A": [1, 2, 3]})
    rule = NoNullsCheck(column_name="B")
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "not found" in message


def test_no_nulls_check_with_nan():
    """Test NoNullsCheck detects NaN values."""
    df = pd.DataFrame({"A": [1.0, float('nan'), 3.0]})
    rule = NoNullsCheck(column_name="A")
    passed, message = rule.check(df)

    assert passed is False
    assert "FAIL" in message
    assert "1 null value" in message


# =======================
# DataQualityEngine Tests
# =======================

def test_quality_engine_all_pass():
    """Test DataQualityEngine with all checks passing."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "amount": [10, 20, 30, 40, 50],
        "balance": [5, -5, 10, -10, 0]
    })

    rules = [
        RowCountCheck(min_rows=3, max_rows=10),
        ColumnExistsCheck(column_name="id"),
        ColumnExistsCheck(column_name="amount"),
        NumericSumCheck(column_name="balance", should_be_zero=True),
        NoNullsCheck(column_name="id"),
    ]

    engine = DataQualityEngine()
    report = engine.run_checks(df, rules)

    assert report.status == "PASS"
    assert len(report.details) == 5
    assert all("PASS" in detail for detail in report.details)


def test_quality_engine_some_fail():
    """Test DataQualityEngine with some checks failing."""
    df = pd.DataFrame({
        "id": [1, None, 3],  # Has null
        "amount": [10, 20, 30]
    })

    rules = [
        RowCountCheck(min_rows=5),  # Will fail
        ColumnExistsCheck(column_name="id"),  # Will pass
        ColumnExistsCheck(column_name="missing"),  # Will fail
        NoNullsCheck(column_name="id"),  # Will fail
    ]

    engine = DataQualityEngine()
    report = engine.run_checks(df, rules)

    assert report.status == "FAIL"
    assert len(report.details) == 4
    # Count failures
    failures = [d for d in report.details if "FAIL" in d]
    assert len(failures) == 3


def test_quality_engine_empty_rules():
    """Test DataQualityEngine with no rules."""
    df = pd.DataFrame({"A": [1, 2, 3]})
    engine = DataQualityEngine()
    report = engine.run_checks(df, [])

    assert report.status == "PASS"
    assert len(report.details) == 1
    assert "No rules to check" in report.details[0]


def test_quality_engine_empty_dataframe():
    """Test DataQualityEngine with empty DataFrame."""
    df = pd.DataFrame()

    rules = [
        RowCountCheck(min_rows=1),
        ColumnExistsCheck(column_name="A"),
    ]

    engine = DataQualityEngine()
    report = engine.run_checks(df, rules)

    assert report.status == "FAIL"
    assert all("FAIL" in detail for detail in report.details)


def test_quality_report_string_representation():
    """Test QualityReport string formatting."""
    report = QualityReport(
        status="PASS",
        details=[
            "RowCountCheck: PASS (5 rows)",
            "ColumnExistsCheck: PASS (column 'A' exists)"
        ]
    )

    report_str = str(report)
    assert "Quality Report: PASS" in report_str
    assert "RowCountCheck: PASS" in report_str
    assert "ColumnExistsCheck: PASS" in report_str


# =======================
# Integration Tests
# =======================

def test_integration_realistic_scenario():
    """Test a realistic scenario with multiple quality checks."""
    # Simulate an extracted IPE dataframe
    df = pd.DataFrame({
        "Company": ["JM_EG", "JM_EG", "JM_KE", "JM_KE", "JM_NG"],
        "GL_Account": ["13003", "13004", "13003", "13009", "13003"],
        "Amount": [1000.0, -500.0, 2000.0, -1000.0, 3000.0],
        "Currency": ["EGP", "EGP", "KES", "KES", "NGN"],
        "Period": ["2025-06", "2025-06", "2025-06", "2025-06", "2025-06"]
    })

    rules = [
        RowCountCheck(min_rows=1, max_rows=1000),
        ColumnExistsCheck(column_name="Company"),
        ColumnExistsCheck(column_name="GL_Account"),
        ColumnExistsCheck(column_name="Amount"),
        ColumnExistsCheck(column_name="Currency"),
        NoNullsCheck(column_name="Company"),
        NoNullsCheck(column_name="GL_Account"),
    ]

    engine = DataQualityEngine()
    report = engine.run_checks(df, rules)

    assert report.status == "PASS"
    assert len(report.details) == 7


def test_integration_failing_scenario():
    """Test a scenario where extracted data has quality issues."""
    # Simulate problematic extracted data
    df = pd.DataFrame({
        "Company": ["JM_EG", None, "JM_KE"],  # Missing company
        "GL_Account": ["13003", "13004", "13003"],
        "Amount": [100.0, 200.0, 300.0]
        # Missing required "Currency" column
    })

    rules = [
        RowCountCheck(min_rows=5),  # Too few rows
        ColumnExistsCheck(column_name="Currency"),  # Missing column
        NoNullsCheck(column_name="Company"),  # Has null
    ]

    engine = DataQualityEngine()
    report = engine.run_checks(df, rules)

    assert report.status == "FAIL"
    assert len(report.details) == 3
    assert all("FAIL" in detail for detail in report.details)
