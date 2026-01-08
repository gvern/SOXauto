"""
Unit tests for Business Line Reclass bridge calculation.

Tests the identify_business_line_reclass_candidates() function with various
scenarios including single/multiple business lines per customer, numeric
casting edge cases, and heuristic selection logic.
"""

import pandas as pd
import pytest
from src.bridges.categorization.business_line_reclass import (
    identify_business_line_reclass_candidates,
)


class TestSingleBusinessLinePerCustomer:
    """Test cases where customers have only one business line (no candidates)."""

    def test_single_customer_single_bl_returns_empty(self):
        """Test customer with single business line - no reclass candidates."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert result.empty, "Should return empty DataFrame for single BL per customer"
        assert list(result.columns) == [
            "customer_id",
            "business_line_code",
            "balance_lcy",
            "num_business_lines_for_customer",
            "proposed_primary_business_line",
            "proposed_reclass_amount_lcy",
            "reasoning",
            "review_required",
        ]

    def test_multiple_customers_single_bl_each_returns_empty(self):
        """Test multiple customers, each with single business line."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C002", "business_line_code": "BL02", "amount_lcy": 500.0},
            {"customer_id": "C003", "business_line_code": "BL01", "amount_lcy": 750.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert result.empty, "Should return empty when no customer has multiple BLs"

    def test_same_customer_multiple_entries_same_bl_aggregated(self):
        """Test same customer with multiple entries in same BL - should aggregate."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 500.0},
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": -200.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Should aggregate to single BL (1000 + 500 - 200 = 1300), no candidates
        assert result.empty


class TestMultipleBusinessLinesPerCustomer:
    """Test cases where customers have multiple business lines (candidates generated)."""

    def test_customer_with_two_bls_generates_candidates(self):
        """Test customer with two business lines - generates 2 candidate rows."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert len(result) == 2, "Should generate 2 rows (one per BL)"
        assert result["customer_id"].unique().tolist() == ["C001"]
        assert result["num_business_lines_for_customer"].iloc[0] == 2

    def test_customer_with_three_bls_generates_candidates(self):
        """Test customer with three business lines."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
            {"customer_id": "C001", "business_line_code": "BL03", "amount_lcy": -50.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert len(result) == 3, "Should generate 3 rows (one per BL)"
        assert result["num_business_lines_for_customer"].iloc[0] == 3

    def test_mixed_customers_some_single_some_multiple_bls(self):
        """Test mix of customers: some with single BL, some with multiple."""
        cle_df = pd.DataFrame([
            # C001: single BL - no candidates
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            # C002: two BLs - candidates
            {"customer_id": "C002", "business_line_code": "BL01", "amount_lcy": 500.0},
            {"customer_id": "C002", "business_line_code": "BL02", "amount_lcy": 300.0},
            # C003: single BL - no candidates
            {"customer_id": "C003", "business_line_code": "BL03", "amount_lcy": 750.0},
            # C004: three BLs - candidates
            {"customer_id": "C004", "business_line_code": "BL01", "amount_lcy": 100.0},
            {"customer_id": "C004", "business_line_code": "BL02", "amount_lcy": 50.0},
            {"customer_id": "C004", "business_line_code": "BL03", "amount_lcy": 25.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Should only have C002 (2 rows) and C004 (3 rows) = 5 total
        assert len(result) == 5
        assert set(result["customer_id"].unique()) == {"C002", "C004"}


class TestPrimaryBusinessLineHeuristic:
    """Test heuristic for selecting proposed primary business line."""

    def test_largest_absolute_balance_selected_as_primary(self):
        """Test that BL with largest absolute balance is selected as primary."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
            {"customer_id": "C001", "business_line_code": "BL03", "amount_lcy": 50.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL01 has largest balance (1000), should be primary for all rows
        assert (result["proposed_primary_business_line"] == "BL01").all()

    def test_negative_balance_with_largest_absolute_selected(self):
        """Test that negative balance with largest absolute value is selected."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 100.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": -1500.0},  # Largest abs
            {"customer_id": "C001", "business_line_code": "BL03", "amount_lcy": 50.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL02 has largest absolute balance (1500), should be primary
        assert (result["proposed_primary_business_line"] == "BL02").all()

    def test_tie_breaker_alphabetical_order(self):
        """Test tie-breaker when multiple BLs have same absolute balance."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL03", "amount_lcy": 500.0},
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 500.0},  # Same abs, comes first alphabetically
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": -500.0},  # Same abs (negative)
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL01 should be selected (alphabetically first among ties)
        assert (result["proposed_primary_business_line"] == "BL01").all()


class TestReclassAmountCalculation:
    """Test calculation of proposed reclass amounts."""

    def test_non_primary_bl_has_full_balance_as_reclass_amount(self):
        """Test that non-primary BL has its full balance as reclass amount."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},  # Primary
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},  # Non-primary
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL01 is primary - no reclass needed
        bl01_row = result[result["business_line_code"] == "BL01"].iloc[0]
        assert bl01_row["proposed_reclass_amount_lcy"] == 0.0

        # BL02 is non-primary - full balance should reclass
        bl02_row = result[result["business_line_code"] == "BL02"].iloc[0]
        assert bl02_row["proposed_reclass_amount_lcy"] == 200.0

    def test_negative_balance_reclass_amount(self):
        """Test reclass amount calculation for negative balances."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},  # Primary
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": -150.0},  # Non-primary, negative
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL02 should have -150 as reclass amount (full balance)
        bl02_row = result[result["business_line_code"] == "BL02"].iloc[0]
        assert bl02_row["proposed_reclass_amount_lcy"] == -150.0


class TestNumericCasting:
    """Test numeric casting of amount column (mixed types, commas, NaN)."""

    def test_string_amounts_with_commas_parsed_correctly(self):
        """Test string amounts with commas are parsed correctly."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": "1,234.56"},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": "2,000"},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert len(result) == 2
        # BL02 should be primary (2000 > 1234.56)
        assert (result["proposed_primary_business_line"] == "BL02").all()

    def test_mixed_numeric_and_string_amounts(self):
        """Test mixed numeric and string amounts."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},  # Numeric
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": "2,500"},  # String
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL02 should be primary (2500 > 1000)
        assert (result["proposed_primary_business_line"] == "BL02").all()

    def test_empty_strings_treated_as_zero(self):
        """Test empty strings are treated as 0.0."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": ""},  # Empty string
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL02 should have 0.0 balance after casting
        # But should still be filtered out by min_abs_amount (default 0.01)
        # So only 1 row left, not a multi-BL customer anymore
        assert result.empty

    def test_nan_values_treated_as_zero(self):
        """Test NaN values are treated as 0.0."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": None},  # NaN
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # NaN treated as 0.0, filtered out by min_abs_amount
        assert result.empty


class TestNegativeAmounts:
    """Test handling of negative amounts."""

    def test_negative_amounts_work_correctly(self):
        """Test negative amounts are handled correctly in all calculations."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": -1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL01 should be primary (abs(-1000) = 1000 > 200)
        assert (result["proposed_primary_business_line"] == "BL01").all()

        # BL02 should reclass 200 to BL01
        bl02_row = result[result["business_line_code"] == "BL02"].iloc[0]
        assert bl02_row["proposed_reclass_amount_lcy"] == 200.0

    def test_all_negative_amounts(self):
        """Test customer with all negative balances."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": -500.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": -1500.0},  # Largest abs
            {"customer_id": "C001", "business_line_code": "BL03", "amount_lcy": -100.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL02 should be primary (abs(-1500) = 1500)
        assert (result["proposed_primary_business_line"] == "BL02").all()


class TestMinimumAbsoluteAmountFilter:
    """Test min_abs_amount parameter filtering."""

    def test_default_min_abs_amount_filters_negligible_balances(self):
        """Test default min_abs_amount (0.01) filters out negligible balances."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 0.005},  # Below 0.01
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL02 filtered out, only BL01 left - no longer multi-BL customer
        assert result.empty

    def test_custom_min_abs_amount_parameter(self):
        """Test custom min_abs_amount parameter."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 50.0},
        ])

        # With min_abs_amount=100, BL02 should be filtered out
        result = identify_business_line_reclass_candidates(
            cle_df, "2025-09-30", min_abs_amount=100.0
        )

        assert result.empty


class TestColumnValidation:
    """Test column validation and error messages."""

    def test_missing_customer_id_column_raises_error(self):
        """Test missing customer_id column raises clear error."""
        cle_df = pd.DataFrame([
            {"business_line_code": "BL01", "amount_lcy": 1000.0},
        ])

        with pytest.raises(ValueError, match="Required columns missing"):
            identify_business_line_reclass_candidates(cle_df, "2025-09-30")

    def test_missing_business_line_column_raises_error(self):
        """Test missing business_line_code column raises clear error."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "amount_lcy": 1000.0},
        ])

        with pytest.raises(ValueError, match="Required columns missing"):
            identify_business_line_reclass_candidates(cle_df, "2025-09-30")

    def test_missing_amount_column_raises_error(self):
        """Test missing amount_lcy column raises clear error."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01"},
        ])

        with pytest.raises(ValueError, match="Required columns missing"):
            identify_business_line_reclass_candidates(cle_df, "2025-09-30")

    def test_custom_column_names_work(self):
        """Test custom column name parameters work correctly."""
        cle_df = pd.DataFrame([
            {"cust_id": "C001", "bl_code": "BL01", "balance": 1000.0},
            {"cust_id": "C001", "bl_code": "BL02", "balance": 200.0},
        ])

        result = identify_business_line_reclass_candidates(
            cle_df,
            "2025-09-30",
            customer_id_col="cust_id",
            business_line_col="bl_code",
            amount_col="balance",
        )

        assert len(result) == 2
        assert "customer_id" in result.columns  # Output uses standard names


class TestCutoffDateValidation:
    """Test cutoff_date parameter validation."""

    def test_invalid_cutoff_date_format_raises_error(self):
        """Test invalid cutoff_date format raises error."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
        ])

        with pytest.raises(ValueError, match="Invalid cutoff_date"):
            identify_business_line_reclass_candidates(cle_df, "2025/09/30")  # Wrong separator

    def test_valid_cutoff_date_accepted(self):
        """Test valid YYYY-MM-DD cutoff_date is accepted."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
        ])

        # Should not raise
        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")
        assert len(result) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe_returns_empty_result(self):
        """Test empty input DataFrame returns empty result."""
        cle_df = pd.DataFrame(columns=["customer_id", "business_line_code", "amount_lcy"])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert result.empty

    def test_non_dataframe_input_raises_typeerror(self):
        """Test non-DataFrame input raises TypeError."""
        with pytest.raises(TypeError, match="cle_df must be a pandas DataFrame"):
            identify_business_line_reclass_candidates(
                [{"customer_id": "C001"}],  # List, not DataFrame
                "2025-09-30"
            )

    def test_rows_with_missing_customer_id_dropped(self):
        """Test rows with missing customer_id are dropped with warning."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": None, "business_line_code": "BL02", "amount_lcy": 200.0},  # Missing customer_id
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 300.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Should process C001 with 2 BLs (BL01 and BL02)
        assert len(result) == 2

    def test_rows_with_missing_business_line_dropped(self):
        """Test rows with missing business_line_code are dropped."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": None, "amount_lcy": 200.0},  # Missing BL
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 300.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Should process C001 with 2 BLs (BL01 and BL02)
        assert len(result) == 2


class TestOutputSchema:
    """Test output DataFrame schema and formatting."""

    def test_output_has_required_columns(self):
        """Test output has all required columns."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        expected_columns = [
            "customer_id",
            "business_line_code",
            "balance_lcy",
            "num_business_lines_for_customer",
            "proposed_primary_business_line",
            "proposed_reclass_amount_lcy",
            "reasoning",
            "review_required",
        ]
        assert list(result.columns) == expected_columns

    def test_review_required_always_true(self):
        """Test review_required column is always True."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert (result["review_required"] == True).all()

    def test_reasoning_column_populated(self):
        """Test reasoning column is populated with human-readable text."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert (result["reasoning"].str.len() > 0).all()
        assert "Customer C001" in result["reasoning"].iloc[0]

    def test_output_sorted_deterministically(self):
        """Test output is sorted deterministically by customer_id and business_line_code."""
        cle_df = pd.DataFrame([
            {"customer_id": "C002", "business_line_code": "BL03", "amount_lcy": 100.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C002", "business_line_code": "BL01", "amount_lcy": 500.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Should be sorted: C001-BL01, C001-BL02, C002-BL01, C002-BL03
        assert result["customer_id"].tolist() == ["C001", "C001", "C002", "C002"]
        assert result["business_line_code"].tolist() == ["BL01", "BL02", "BL01", "BL03"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
