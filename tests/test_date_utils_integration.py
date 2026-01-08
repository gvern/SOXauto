"""
Integration tests for date_utils refactoring.

These tests verify that the refactored modules (timing.py, vtc.py, etc.)
work correctly with the centralized date utilities.

Run with: pytest tests/test_date_utils_integration.py -v
"""

import os
import sys
import pandas as pd
import pytest

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.bridges.calculations.timing import compute_rolling_window
from src.bridges.calculations.vtc import calculate_vtc_adjustment
from src.core.reconciliation.run_reconciliation import _validate_params
from src.utils.date_utils import normalize_date, month_start, month_end


class TestTimingBridgeIntegration:
    """Test that timing.py uses date_utils correctly."""
    
    def test_compute_rolling_window_uses_normalize_date(self):
        """Verify compute_rolling_window returns normalized timestamps."""
        start_dt, end_dt = compute_rolling_window("2024-10-31")
        
        # Should be normalized (midnight)
        assert start_dt.hour == 0
        assert start_dt.minute == 0
        assert start_dt.second == 0
        
        assert end_dt.hour == 0
        assert end_dt.minute == 0
        assert end_dt.second == 0
    
    def test_compute_rolling_window_consistency(self):
        """Verify compute_rolling_window produces same result as manual calculation."""
        cutoff_date = "2025-09-30"
        
        # Using the function
        start_dt, end_dt = compute_rolling_window(cutoff_date)
        
        # Manual calculation using date_utils
        cutoff_dt = normalize_date(cutoff_date)
        next_month_first = (cutoff_dt.replace(day=1) + pd.DateOffset(months=1))
        expected_start = next_month_first - pd.DateOffset(years=1)
        
        assert start_dt == expected_start
        assert end_dt == cutoff_dt


class TestVTCBridgeIntegration:
    """Test that vtc.py uses date_utils correctly."""
    
    def test_vtc_with_cutoff_date_filters_correctly(self):
        """Verify VTC adjustment uses month_start/month_end correctly."""
        # Create sample data with inactive dates in and out of range
        cutoff_date = "2024-09-30"
        
        ipe_08_data = pd.DataFrame({
            'id': ['V001', 'V002', 'V003'],
            'business_use': ['refund', 'refund', 'refund'],
            'is_active': [0, 0, 0],
            'is_valid': ['valid', 'valid', 'valid'],
            'inactive_at': [
                '2024-09-15',  # In range
                '2024-08-31',  # Out of range (before)
                '2024-10-01',  # Out of range (after)
            ],
            'remaining_amount': [100, 200, 300],
        })
        
        # No NAV entries (all should be unmatched)
        categorized_cr_03 = pd.DataFrame({
            'Voucher No_': [],
            'bridge_category': [],
        })
        
        # Call VTC adjustment
        amount, proof_df, metrics = calculate_vtc_adjustment(
            ipe_08_df=ipe_08_data,
            categorized_cr_03_df=categorized_cr_03,
            cutoff_date=cutoff_date,
        )
        
        # Should only include V001 (inactive in September)
        assert len(proof_df) == 1
        assert proof_df.iloc[0]['id'] == 'V001'
        assert amount == 100
    
    def test_vtc_without_cutoff_date_includes_all(self):
        """Verify VTC without cutoff_date doesn't filter by date."""
        ipe_08_data = pd.DataFrame({
            'id': ['V001', 'V002'],
            'business_use': ['refund', 'refund'],
            'is_active': [0, 0],
            'is_valid': ['valid', 'valid'],
            'inactive_at': ['2024-09-15', '2024-08-31'],
            'remaining_amount': [100, 200],
        })
        
        categorized_cr_03 = pd.DataFrame({
            'Voucher No_': [],
            'bridge_category': [],
        })
        
        # Call without cutoff_date
        amount, proof_df, metrics = calculate_vtc_adjustment(
            ipe_08_df=ipe_08_data,
            categorized_cr_03_df=categorized_cr_03,
            cutoff_date=None,
        )
        
        # Should include both vouchers
        assert len(proof_df) == 2
        assert amount == 300


class TestReconciliationValidation:
    """Test that run_reconciliation.py uses validate_yyyy_mm_dd correctly."""
    
    def test_validate_params_accepts_valid_date(self):
        """Verify valid YYYY-MM-DD date is accepted."""
        params = {
            'cutoff_date': '2024-10-31',
            'id_companies_active': "('EC_NG')",
        }
        
        errors = _validate_params(params)
        assert len(errors) == 0
    
    def test_validate_params_rejects_invalid_format(self):
        """Verify invalid date format is rejected."""
        params = {
            'cutoff_date': '2024/10/31',  # Wrong separator
            'id_companies_active': "('EC_NG')",
        }
        
        errors = _validate_params(params)
        assert len(errors) == 1
        assert 'Invalid cutoff_date' in errors[0]
    
    def test_validate_params_rejects_invalid_date(self):
        """Verify invalid date (e.g., Feb 30) is rejected."""
        params = {
            'cutoff_date': '2024-02-30',  # Invalid day
            'id_companies_active': "('EC_NG')",
        }
        
        errors = _validate_params(params)
        assert len(errors) == 1
        assert 'Invalid cutoff_date' in errors[0]
    
    def test_validate_params_rejects_non_leap_year_feb_29(self):
        """Verify Feb 29 in non-leap year is rejected."""
        params = {
            'cutoff_date': '2023-02-29',  # Not a leap year
            'id_companies_active': "('EC_NG')",
        }
        
        errors = _validate_params(params)
        assert len(errors) == 1
        assert 'Invalid cutoff_date' in errors[0]


class TestCrossModuleConsistency:
    """Test that date handling is consistent across modules."""
    
    def test_month_boundaries_consistency(self):
        """Verify month_start and month_end work consistently."""
        test_dates = [
            "2024-01-15",
            "2024-02-29",  # Leap year
            "2024-10-31",
            "2024-12-25",
        ]
        
        for date_str in test_dates:
            start = month_start(date_str)
            end = month_end(date_str)
            
            # Start should be 1st of month
            assert start.day == 1
            
            # End should be last day of month
            # Verify it's actually the last day by adding one day and checking it's next month
            next_day = end + pd.Timedelta(days=1)
            assert next_day.month != end.month or next_day.year != end.year
            
            # Start should be before end
            assert start <= end
    
    def test_all_date_functions_return_timezone_naive(self):
        """Verify all date functions return timezone-naive timestamps by default."""
        date_str = "2024-10-31"
        
        # Test each function
        from src.utils.date_utils import parse_date, normalize_date, month_start, month_end
        
        parsed = parse_date(date_str)
        assert parsed.tz is None
        
        normalized = normalize_date(date_str)
        assert normalized.tz is None
        
        start = month_start(date_str)
        assert start.tz is None
        
        end = month_end(date_str)
        assert end.tz is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
