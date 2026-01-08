"""
Tests for Timing Difference Bridge calculation.

Tests both pure helper functions and full bridge integration logic.
Ensures robustness against edge cases and column name variants.
"""

import pandas as pd
import pytest
from src.bridges.calculations.timing import (
    calculate_timing_difference_bridge,
    compute_rolling_window,
    _normalize_column_names,
)


# =============================================================================
# Tests for Pure Functions (High Priority - Reduce Fragility)
# =============================================================================


class TestComputeRollingWindow:
    """Test rolling window calculation independently (pure function)."""

    def test_september_cutoff_returns_october_to_september_window(self):
        """Test standard month-end cutoff (September 30)."""
        start, end = compute_rolling_window("2025-09-30")
        
        assert start == pd.Timestamp("2024-10-01"), "Start should be Oct 1st of previous year"
        assert end == pd.Timestamp("2025-09-30"), "End should be cutoff date"

    def test_october_cutoff_returns_november_to_october_window(self):
        """Test cutoff on different month (October 31)."""
        start, end = compute_rolling_window("2024-10-31")
        
        assert start == pd.Timestamp("2023-11-01"), "Start should be Nov 1st of previous year"
        assert end == pd.Timestamp("2024-10-31"), "End should be cutoff date"

    def test_december_cutoff_handles_year_boundary(self):
        """Test year boundary handling for December cutoff."""
        start, end = compute_rolling_window("2024-12-31")
        
        assert start == pd.Timestamp("2024-01-01"), "Start should be Jan 1st of same year"
        assert end == pd.Timestamp("2024-12-31"), "End should be cutoff date"

    def test_mid_month_cutoff(self):
        """Test non-month-end cutoff date."""
        start, end = compute_rolling_window("2025-09-15")
        
        # Should still use 1st of (month + 1) - 1 year logic
        assert start == pd.Timestamp("2024-10-01"), "Start should be Oct 1st of previous year"
        assert end == pd.Timestamp("2025-09-15"), "End should be exact cutoff date"


class TestNormalizeColumnNames:
    """Test column name adapter for various naming conventions."""

    def test_normalize_jdash_columns_with_spaces(self):
        """Test normalization of Jdash export with spaces in column names."""
        df = pd.DataFrame({
            "Voucher Id": ["V001", "V002"],
            "Amount Used": [100.0, 200.0]
        })
        
        mapping = {
            "voucher_id": ["Voucher Id", "Voucher_Id", "voucher_id"],
            "amount_used": ["Amount Used", "Amount_Used", "amount_used"]
        }
        
        result = _normalize_column_names(df, mapping)
        
        assert "voucher_id" in result.columns, "Should have normalized voucher_id column"
        assert "amount_used" in result.columns, "Should have normalized amount_used column"
        assert result["voucher_id"].tolist() == ["V001", "V002"]
        assert result["amount_used"].tolist() == [100.0, 200.0]

    def test_normalize_jdash_columns_with_underscores(self):
        """Test normalization of Jdash export with underscores."""
        df = pd.DataFrame({
            "Voucher_Id": ["V001"],
            "Amount_Used": [150.0]
        })
        
        mapping = {
            "voucher_id": ["Voucher Id", "Voucher_Id", "voucher_id"],
            "amount_used": ["Amount Used", "Amount_Used", "amount_used"]
        }
        
        result = _normalize_column_names(df, mapping)
        
        assert "voucher_id" in result.columns
        assert "amount_used" in result.columns
        assert result["voucher_id"].iloc[0] == "V001"

    def test_normalize_preserves_unmapped_columns(self):
        """Test that columns not in mapping are preserved."""
        df = pd.DataFrame({
            "Voucher Id": ["V001"],
            "Extra_Column": ["value"]
        })
        
        mapping = {
            "voucher_id": ["Voucher Id"]
        }
        
        result = _normalize_column_names(df, mapping)
        
        assert "voucher_id" in result.columns, "Should normalize mapped column"
        assert "Extra_Column" in result.columns, "Should preserve unmapped column"

    def test_normalize_priority_order_uses_first_match(self):
        """Test that priority order in variants matters (first match wins)."""
        df = pd.DataFrame({
            "Voucher_Id": ["V001"],  # Second variant in list
            "voucher_id": ["V002"]   # Third variant in list
        })
        
        # Priority order: "Voucher Id" > "Voucher_Id" > "voucher_id"
        mapping = {
            "canonical_id": ["Voucher Id", "Voucher_Id", "voucher_id"]
        }
        
        result = _normalize_column_names(df, mapping)
        
        # Should use "Voucher_Id" (first match in priority order)
        assert "canonical_id" in result.columns
        assert result["canonical_id"].iloc[0] == "V001"
        # Original "voucher_id" column should still exist (not matched)
        assert "voucher_id" in result.columns

    def test_normalize_empty_dataframe(self):
        """Test normalization handles empty DataFrame gracefully."""
        df = pd.DataFrame()
        mapping = {"voucher_id": ["Voucher Id"]}
        
        result = _normalize_column_names(df, mapping)
        
        assert result.empty


# =============================================================================
# Integration Tests for Full Bridge Calculation
# =============================================================================


class TestTimingDifferenceBridgeIntegration:
    """Integration tests for calculate_timing_difference_bridge."""

    def test_nominal_case_with_matching_vouchers(self):
        """Test standard reconciliation with matching data."""
        # Setup IPE_08 data (Accounting baseline)
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",  # Within window for cutoff 2025-09-30
            },
            {
                "id": "V002",
                "business_use": "store_credit",
                "is_active": 0,
                "Total Amount Used": 200.0,
                "created_at": "2024-11-20",
            },
        ])
        
        # Setup Jdash data (Ops perspective)
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 120.0},  # +20 variance
            {"Voucher Id": "V002", "Amount Used": 180.0},  # -20 variance
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Variance = Jdash - IPE = (120 - 100) + (180 - 200) = 20 - 20 = 0
        assert variance_sum == 0.0, f"Expected 0.0, got {variance_sum}"
        assert len(proof_df) == 2, "Should have 2 vouchers in proof"
        assert "Variance" in proof_df.columns
        assert "Jdash_Amount_Used" in proof_df.columns

    def test_empty_ipe_08_returns_zero_variance(self):
        """Test that empty IPE_08 returns 0 variance and empty proof."""
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 100.0}
        ])
        
        ipe_08_df = pd.DataFrame()  # Empty
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        assert variance_sum == 0.0
        assert proof_df.empty

    def test_empty_jdash_creates_negative_variance(self):
        """Test that empty Jdash creates negative variance (unmatched IPE amounts)."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "jforce",
                "is_active": 0,
                "Total Amount Used": 50.0,
                "created_at": "2024-11-01",
            },
        ])
        
        jdash_df = pd.DataFrame()  # Empty
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Variance = 0 - 100 + 0 - 50 = -150
        assert variance_sum == -150.0, f"Expected -150.0, got {variance_sum}"
        assert len(proof_df) == 2
        assert all(proof_df["Jdash_Amount_Used"] == 0.0)

    def test_date_filtering_uses_rolling_window(self):
        """Test that date filtering correctly uses 1-year rolling window."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",  # Within window [2024-10-01, 2025-09-30]
            },
            {
                "id": "V002",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 200.0,
                "created_at": "2024-09-30",  # BEFORE window start - excluded
            },
            {
                "id": "V003",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 150.0,
                "created_at": "2025-09-30",  # At cutoff - included
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 120.0},
            {"Voucher Id": "V003", "Amount Used": 170.0},
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Only V001 and V003 should be included (V002 excluded by date filter)
        # Variance = (120 - 100) + (170 - 150) = 20 + 20 = 40
        assert variance_sum == 40.0, f"Expected 40.0, got {variance_sum}"
        assert len(proof_df) == 2, "Should have 2 vouchers (V002 filtered out)"
        assert "V002" not in proof_df["id"].values

    def test_column_variants_jdash_with_spaces(self):
        """Test handling of Jdash with space-separated column names."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",
            },
        ])
        
        # Jdash with spaces (most common export format)
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 150.0}
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Should successfully normalize and calculate
        assert variance_sum == 50.0, f"Expected 50.0, got {variance_sum}"
        assert len(proof_df) == 1

    def test_column_variants_jdash_with_underscores(self):
        """Test handling of Jdash with underscore-separated column names."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "store_credit",
                "is_active": 0,
                "Total Amount Used": 200.0,
                "created_at": "2024-10-15",
            },
        ])
        
        # Jdash with underscores
        jdash_df = pd.DataFrame([
            {"Voucher_Id": "V001", "Amount_Used": 180.0}
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Variance = 180 - 200 = -20
        assert variance_sum == -20.0, f"Expected -20.0, got {variance_sum}"

    def test_non_marketing_filter_excludes_marketing_vouchers(self):
        """Test that marketing vouchers are excluded from calculation."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",  # Non-marketing - included
                "is_active": 0,
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "marketing",  # Marketing - excluded
                "is_active": 0,
                "Total Amount Used": 500.0,
                "created_at": "2024-10-20",
            },
            {
                "id": "V003",
                "business_use": "jforce",  # Non-marketing - included
                "is_active": 0,
                "Total Amount Used": 80.0,
                "created_at": "2024-11-01",
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 110.0},
            {"Voucher Id": "V003", "Amount Used": 90.0},
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Only V001 and V003 should be included (V002 excluded by business_use filter)
        # Variance = (110 - 100) + (90 - 80) = 10 + 10 = 20
        assert variance_sum == 20.0, f"Expected 20.0, got {variance_sum}"
        assert len(proof_df) == 2
        assert "V002" not in proof_df["id"].values

    def test_active_vouchers_excluded(self):
        """Test that active vouchers (is_active=1) are excluded."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,  # Inactive - included
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "refund",
                "is_active": 1,  # Active - excluded
                "Total Amount Used": 300.0,
                "created_at": "2024-10-20",
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 120.0},
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Only V001 included (V002 excluded by is_active filter)
        assert variance_sum == 20.0, f"Expected 20.0, got {variance_sum}"
        assert len(proof_df) == 1

    def test_multiple_jdash_entries_for_same_voucher_aggregated(self):
        """Test that multiple Jdash entries for same voucher are summed correctly."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",
            },
        ])
        
        # Multiple Jdash entries for V001 (should be aggregated)
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 50.0},
            {"Voucher Id": "V001", "Amount Used": 30.0},
            {"Voucher Id": "V001", "Amount Used": 20.0},
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Jdash total = 50 + 30 + 20 = 100
        # Variance = 100 - 100 = 0
        assert variance_sum == 0.0, f"Expected 0.0, got {variance_sum}"
        assert len(proof_df) == 1
        assert proof_df.iloc[0]["Jdash_Amount_Used"] == 100.0

    def test_voucher_in_jdash_but_not_ipe_ignored(self):
        """Test that vouchers in Jdash but not in IPE_08 are ignored (left join)."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 110.0},
            {"Voucher Id": "V999", "Amount Used": 500.0},  # Not in IPE_08
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Only V001 should be in result (left join from IPE_08)
        assert variance_sum == 10.0, f"Expected 10.0, got {variance_sum}"
        assert len(proof_df) == 1
        assert "V999" not in proof_df["id"].values

    def test_missing_created_at_column_logs_warning(self, caplog):
        """Test that missing created_at column triggers warning but doesn't crash."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 100.0,
                # No created_at column
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 120.0}
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Should still work (no date filter applied)
        assert variance_sum == 20.0
        assert len(proof_df) == 1

    def test_missing_jdash_columns_logs_warning_and_treats_as_empty(self, caplog):
        """Test that invalid Jdash columns trigger warning and treat as empty."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",
            },
        ])
        
        # Jdash with wrong column names
        jdash_df = pd.DataFrame([
            {"WrongCol1": "V001", "WrongCol2": 120.0}
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Should treat as empty Jdash (warning logged)
        assert variance_sum == -100.0, "Should have negative variance (unmatched IPE)"
        assert len(proof_df) == 1
        assert proof_df.iloc[0]["Jdash_Amount_Used"] == 0.0


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestTimingBridgeEdgeCases:
    """Edge case tests for robustness."""

    def test_none_ipe_08_returns_zero(self):
        """Test None IPE_08 DataFrame."""
        jdash_df = pd.DataFrame([{"Voucher Id": "V001", "Amount Used": 100.0}])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, None, "2025-09-30"
        )
        
        assert variance_sum == 0.0
        assert proof_df.empty

    def test_none_jdash_creates_negative_variance(self):
        """Test None Jdash DataFrame."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 100.0,
                "created_at": "2024-10-15",
            },
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            None, ipe_08_df, "2025-09-30"
        )
        
        assert variance_sum == -100.0
        assert len(proof_df) == 1

    def test_zero_amounts(self):
        """Test handling of zero amounts."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 0.0,
                "created_at": "2024-10-15",
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 0.0}
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        assert variance_sum == 0.0
        assert len(proof_df) == 1

    def test_negative_amounts_in_source_data(self):
        """Test handling of negative amounts (edge case in data)."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": -50.0,  # Negative (data anomaly)
                "created_at": "2024-10-15",
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 100.0}
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Variance = 100 - (-50) = 150
        assert variance_sum == 150.0
        assert len(proof_df) == 1
    
    def test_string_amounts_with_commas(self):
        """Test handling of string amounts with commas (CSV upload scenario)."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": "1,234.56",  # String with commas
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "jforce",
                "is_active": 0,
                "Total Amount Used": "2,000",  # String with commas
                "created_at": "2024-11-01",
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": "1,500"},
            {"Voucher Id": "V002", "Amount Used": "2,100.50"},
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Should handle comma-separated strings correctly
        # Variance = (1500 - 1234.56) + (2100.50 - 2000) = 265.44 + 100.50 = 365.94
        assert variance_sum == pytest.approx(365.94, rel=1e-5)
        assert len(proof_df) == 2
    
    def test_mixed_numeric_and_string_amounts(self):
        """Test handling of mixed numeric and string amounts."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": 1000.0,  # Numeric
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "jforce",
                "is_active": 0,
                "Total Amount Used": "2,500",  # String
                "created_at": "2024-11-01",
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": "1,100"},  # String
            {"Voucher Id": "V002", "Amount Used": 2600.0},  # Numeric
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Variance = (1100 - 1000) + (2600 - 2500) = 100 + 100 = 200
        assert variance_sum == 200.0
        assert len(proof_df) == 2
    
    def test_empty_strings_and_nans(self):
        """Test handling of empty strings and NaN values."""
        ipe_08_df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "is_active": 0,
                "Total Amount Used": "",  # Empty string
                "created_at": "2024-10-15",
            },
            {
                "id": "V002",
                "business_use": "jforce",
                "is_active": 0,
                "Total Amount Used": None,  # NaN
                "created_at": "2024-11-01",
            },
        ])
        
        jdash_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 100.0},
            {"Voucher Id": "V002", "Amount Used": ""},  # Empty string
        ])
        
        variance_sum, proof_df = calculate_timing_difference_bridge(
            jdash_df, ipe_08_df, "2025-09-30"
        )
        
        # Empty strings and NaN should be treated as 0.0
        # Variance = (100 - 0) + (0 - 0) = 100
        assert variance_sum == 100.0
        assert len(proof_df) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/bridges/calculations/timing"])
