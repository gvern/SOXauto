"""
Integration tests for Business Line Reclass bridge calculation.

Tests the full end-to-end flow with realistic CLE data scenarios,
ensuring output schema stability and deterministic behavior.
"""

import pandas as pd
import pytest
from src.bridges.calculations.business_line_reclass import (
    identify_business_line_reclass_candidates,
)


class TestBusinessLineReclassIntegration:
    """Integration tests simulating realistic CLE extraction scenarios."""

    def test_realistic_cle_scenario_multiple_customers(self):
        """Test realistic scenario with multiple customers and various BL patterns."""
        # Simulate NAV Customer Ledger Entries extract
        cle_df = pd.DataFrame([
            # Customer C001: Multiple BLs (BL01 dominant)
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 15000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 500.0},
            {"customer_id": "C001", "business_line_code": "BL03", "amount_lcy": -100.0},
            
            # Customer C002: Single BL (no reclass needed)
            {"customer_id": "C002", "business_line_code": "BL01", "amount_lcy": 10000.0},
            
            # Customer C003: Two BLs with similar balances
            {"customer_id": "C003", "business_line_code": "BL01", "amount_lcy": 5000.0},
            {"customer_id": "C003", "business_line_code": "BL02", "amount_lcy": 4800.0},
            
            # Customer C004: Multiple entries same customer+BL (should aggregate)
            {"customer_id": "C004", "business_line_code": "BL01", "amount_lcy": 3000.0},
            {"customer_id": "C004", "business_line_code": "BL01", "amount_lcy": 2000.0},
            {"customer_id": "C004", "business_line_code": "BL02", "amount_lcy": 1000.0},
            
            # Customer C005: All negative balances
            {"customer_id": "C005", "business_line_code": "BL01", "amount_lcy": -2000.0},
            {"customer_id": "C005", "business_line_code": "BL02", "amount_lcy": -500.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Validation: Only multi-BL customers (C001, C003, C004, C005)
        assert set(result["customer_id"].unique()) == {"C001", "C003", "C004", "C005"}
        
        # C001: 3 rows (BL01, BL02, BL03)
        c001_rows = result[result["customer_id"] == "C001"]
        assert len(c001_rows) == 3
        assert (c001_rows["proposed_primary_business_line"] == "BL01").all()
        
        # C003: 2 rows (BL01, BL02)
        c003_rows = result[result["customer_id"] == "C003"]
        assert len(c003_rows) == 2
        assert (c003_rows["proposed_primary_business_line"] == "BL01").all()  # 5000 > 4800
        
        # C004: 2 rows (BL01 aggregated to 5000, BL02)
        c004_rows = result[result["customer_id"] == "C004"]
        assert len(c004_rows) == 2
        assert (c004_rows["proposed_primary_business_line"] == "BL01").all()  # 5000 > 1000
        bl01_balance = c004_rows[c004_rows["business_line_code"] == "BL01"]["balance_lcy"].iloc[0]
        assert bl01_balance == 5000.0  # 3000 + 2000
        
        # C005: 2 rows (BL01, BL02), BL01 primary (abs(-2000) > abs(-500))
        c005_rows = result[result["customer_id"] == "C005"]
        assert len(c005_rows) == 2
        assert (c005_rows["proposed_primary_business_line"] == "BL01").all()

    def test_output_schema_stability(self):
        """Test that output schema is stable and matches specification."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 200.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Expected columns in exact order
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

        # Verify column types
        assert result["customer_id"].dtype == "object"
        assert result["business_line_code"].dtype == "object"
        assert result["balance_lcy"].dtype == "float64"
        assert result["num_business_lines_for_customer"].dtype in ["int64", "Int64"]
        assert result["proposed_primary_business_line"].dtype == "object"
        assert result["proposed_reclass_amount_lcy"].dtype == "float64"
        assert result["reasoning"].dtype == "object"
        assert result["review_required"].dtype == "bool"

    def test_deterministic_output_order(self):
        """Test that output order is deterministic across multiple runs."""
        cle_df = pd.DataFrame([
            {"customer_id": "C003", "business_line_code": "BL02", "amount_lcy": 300.0},
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C002", "business_line_code": "BL03", "amount_lcy": 500.0},
            {"customer_id": "C001", "business_line_code": "BL03", "amount_lcy": 200.0},
            {"customer_id": "C002", "business_line_code": "BL01", "amount_lcy": 400.0},
            {"customer_id": "C003", "business_line_code": "BL01", "amount_lcy": 250.0},
        ])

        # Run twice
        result1 = identify_business_line_reclass_candidates(cle_df, "2025-09-30")
        result2 = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Results should be identical
        pd.testing.assert_frame_equal(result1, result2)

        # Order should be: C001-BL01, C001-BL03, C002-BL01, C002-BL03, C003-BL01, C003-BL02
        expected_order = [
            ("C001", "BL01"),
            ("C001", "BL03"),
            ("C002", "BL01"),
            ("C002", "BL03"),
            ("C003", "BL01"),
            ("C003", "BL02"),
        ]
        actual_order = list(zip(result1["customer_id"], result1["business_line_code"]))
        assert actual_order == expected_order

    def test_csv_upload_scenario_with_messy_data(self):
        """Test realistic CSV upload scenario with mixed types and formatting."""
        # Simulate CSV data with various formatting issues
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": "1,234.56"},  # String with comma
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 500},  # Integer
            {"customer_id": "C002", "business_line_code": "BL01", "amount_lcy": "2,000.00"},  # String
            {"customer_id": "C002", "business_line_code": "BL03", "amount_lcy": 1500.5},  # Float
            {"customer_id": "C003", "business_line_code": "BL02", "amount_lcy": ""},  # Empty string
            {"customer_id": "C003", "business_line_code": "BL01", "amount_lcy": "750"},  # String without comma
            {"customer_id": "C004", "business_line_code": "BL01", "amount_lcy": None},  # None/NaN
            {"customer_id": "C004", "business_line_code": "BL02", "amount_lcy": "   100.5   "},  # Spaces
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Should handle all formatting gracefully
        assert len(result) > 0

        # C001: BL01 (1234.56) vs BL02 (500) - BL01 should be primary
        c001_rows = result[result["customer_id"] == "C001"]
        assert len(c001_rows) == 2
        assert (c001_rows["proposed_primary_business_line"] == "BL01").all()

        # C002: BL01 (2000) vs BL03 (1500.5) - BL01 should be primary
        c002_rows = result[result["customer_id"] == "C002"]
        assert len(c002_rows) == 2
        assert (c002_rows["proposed_primary_business_line"] == "BL01").all()

    def test_large_dataset_performance(self):
        """Test performance with larger dataset (1000+ rows)."""
        # Generate 100 customers, each with 2-5 business lines
        import numpy as np
        np.random.seed(42)

        rows = []
        for cust_num in range(100):
            customer_id = f"C{cust_num:04d}"
            num_bls = np.random.randint(2, 6)  # 2-5 business lines
            for bl_num in range(num_bls):
                business_line = f"BL{bl_num:02d}"
                amount = np.random.uniform(-10000, 10000)
                rows.append({
                    "customer_id": customer_id,
                    "business_line_code": business_line,
                    "amount_lcy": amount,
                })

        cle_df = pd.DataFrame(rows)

        # Should complete without error
        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # All 100 customers should have candidates (all have 2+ BLs)
        assert result["customer_id"].nunique() == 100

        # Each customer should have 2-5 rows
        for customer_id in result["customer_id"].unique():
            customer_rows = result[result["customer_id"] == customer_id]
            assert 2 <= len(customer_rows) <= 5

    def test_integration_with_custom_column_names(self):
        """Test integration with custom column name mapping."""
        # Simulate CLE extract with different column names
        cle_df = pd.DataFrame([
            {"cust_no": "C001", "bl_code": "RETAIL", "balance": 15000.0},
            {"cust_no": "C001", "bl_code": "WHOLESALE", "balance": 2000.0},
            {"cust_no": "C002", "bl_code": "RETAIL", "balance": 8000.0},
            {"cust_no": "C002", "bl_code": "ECOMMERCE", "balance": 9500.0},
        ])

        result = identify_business_line_reclass_candidates(
            cle_df,
            "2025-09-30",
            customer_id_col="cust_no",
            business_line_col="bl_code",
            amount_col="balance",
        )

        # Should process correctly
        assert len(result) == 4

        # C001: RETAIL (15000) should be primary
        c001_rows = result[result["customer_id"] == "C001"]
        assert (c001_rows["proposed_primary_business_line"] == "RETAIL").all()

        # C002: ECOMMERCE (9500) should be primary
        c002_rows = result[result["customer_id"] == "C002"]
        assert (c002_rows["proposed_primary_business_line"] == "ECOMMERCE").all()

    def test_reclass_amount_calculations_end_to_end(self):
        """Test end-to-end reclass amount calculations are correct."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 10000.0},  # Primary
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 2500.0},  # Reclass 2500
            {"customer_id": "C001", "business_line_code": "BL03", "amount_lcy": -500.0},  # Reclass -500
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # BL01 (primary): no reclass
        bl01_row = result[result["business_line_code"] == "BL01"].iloc[0]
        assert bl01_row["proposed_reclass_amount_lcy"] == 0.0

        # BL02 (non-primary): full balance reclass
        bl02_row = result[result["business_line_code"] == "BL02"].iloc[0]
        assert bl02_row["proposed_reclass_amount_lcy"] == 2500.0

        # BL03 (non-primary): full balance reclass (negative)
        bl03_row = result[result["business_line_code"] == "BL03"].iloc[0]
        assert bl03_row["proposed_reclass_amount_lcy"] == -500.0

        # Sum of non-primary reclass amounts
        non_primary_reclass = result[
            result["business_line_code"] != result["proposed_primary_business_line"]
        ]["proposed_reclass_amount_lcy"].sum()
        assert non_primary_reclass == 2000.0  # 2500 + (-500)


class TestBusinessLineReclassRobustness:
    """Test robustness and error handling in integration scenarios."""

    def test_empty_cle_dataframe_returns_empty_gracefully(self):
        """Test empty CLE DataFrame is handled gracefully."""
        cle_df = pd.DataFrame(columns=["customer_id", "business_line_code", "amount_lcy"])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert result.empty
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

    def test_all_customers_single_bl_returns_empty(self):
        """Test scenario where all customers have single BL."""
        cle_df = pd.DataFrame([
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 10000.0},
            {"customer_id": "C002", "business_line_code": "BL02", "amount_lcy": 5000.0},
            {"customer_id": "C003", "business_line_code": "BL01", "amount_lcy": 7500.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        assert result.empty

    def test_data_quality_issues_handled(self):
        """Test various data quality issues are handled gracefully."""
        cle_df = pd.DataFrame([
            # Valid multi-BL customer
            {"customer_id": "C001", "business_line_code": "BL01", "amount_lcy": 1000.0},
            {"customer_id": "C001", "business_line_code": "BL02", "amount_lcy": 500.0},
            
            # Missing customer_id (should be dropped)
            {"customer_id": None, "business_line_code": "BL01", "amount_lcy": 200.0},
            
            # Missing business_line_code (should be dropped)
            {"customer_id": "C002", "business_line_code": None, "amount_lcy": 300.0},
            
            # Invalid amount (empty string - treated as 0)
            {"customer_id": "C003", "business_line_code": "BL01", "amount_lcy": ""},
            {"customer_id": "C003", "business_line_code": "BL02", "amount_lcy": 400.0},
        ])

        result = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

        # Should only have C001 (valid multi-BL customer)
        # C003 has only 1 valid BL after empty string filtered out
        assert result["customer_id"].unique().tolist() == ["C001"]
        assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
