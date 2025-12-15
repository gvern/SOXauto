"""
Unit tests for SummaryBuilder module.

Tests the financial reconciliation summary calculation logic:
- Actuals calculation from CR_04 (NAV GL Balances)
- Target values calculation from component IPEs
- Variance calculation and status determination
"""

import pandas as pd
import pytest

from src.core.recon.summary_builder import SummaryBuilder, calculate_reconciliation_metrics


class TestSummaryBuilder:
    """Tests for SummaryBuilder class."""

    def test_empty_data_store(self):
        """Test with completely empty data store."""
        builder = SummaryBuilder({})
        metrics = builder.build()
        
        assert metrics['actuals'] is None
        assert metrics['target_values'] == 0.0
        assert metrics['variance'] is None
        assert metrics['status'] is None

    def test_calculate_actuals_with_valid_data(self):
        """Test actuals calculation with valid CR_04 data."""
        cr_04_df = pd.DataFrame({
            'BALANCE_AT_DATE': [1000.0, 2000.0, 500.0],
            'GROUP_COA_ACCOUNT_NO': ['18412', '13003', '18350'],
        })
        
        builder = SummaryBuilder({'CR_04': cr_04_df})
        actuals = builder._calculate_actuals()
        
        assert actuals == 3500.0

    def test_calculate_actuals_with_alternative_column_name(self):
        """Test actuals calculation with alternative column names."""
        cr_04_df = pd.DataFrame({
            'Balance_At_Date': [1500.0, 2500.0],
            'Account': ['18412', '13003'],
        })
        
        builder = SummaryBuilder({'CR_04': cr_04_df})
        actuals = builder._calculate_actuals()
        
        assert actuals == 4000.0

    def test_calculate_actuals_missing_cr04(self):
        """Test actuals calculation when CR_04 is missing."""
        builder = SummaryBuilder({})
        actuals = builder._calculate_actuals()
        
        assert actuals is None

    def test_calculate_actuals_empty_cr04(self):
        """Test actuals calculation when CR_04 is empty."""
        cr_04_df = pd.DataFrame()
        
        builder = SummaryBuilder({'CR_04': cr_04_df})
        actuals = builder._calculate_actuals()
        
        assert actuals is None

    def test_calculate_actuals_no_amount_column(self):
        """Test actuals calculation when no amount column is found."""
        cr_04_df = pd.DataFrame({
            'ACCOUNT_NO': ['18412', '13003'],
            'DESCRIPTION': ['GL1', 'GL2'],
        })
        
        builder = SummaryBuilder({'CR_04': cr_04_df})
        actuals = builder._calculate_actuals()
        
        assert actuals is None

    def test_calculate_target_values_with_valid_data(self):
        """Test target values calculation with valid component IPEs."""
        data_store = {
            'IPE_07': pd.DataFrame({'Amount': [1000.0, 500.0]}),
            'IPE_10': pd.DataFrame({'remaining_amount': [300.0, 200.0]}),
            'IPE_08': pd.DataFrame({'remaining_amount': [150.0]}),
        }
        
        builder = SummaryBuilder(data_store)
        target_sum, component_totals = builder._calculate_target_values()
        
        assert target_sum == 2150.0
        assert component_totals['IPE_07'] == 1500.0
        assert component_totals['IPE_10'] == 500.0
        assert component_totals['IPE_08'] == 150.0

    def test_calculate_target_values_partial_data(self):
        """Test target values calculation with only some components available."""
        data_store = {
            'IPE_07': pd.DataFrame({'Amount': [1000.0]}),
            # IPE_10 is missing
            'IPE_08': pd.DataFrame({'remaining_amount': [150.0]}),
        }
        
        builder = SummaryBuilder(data_store)
        target_sum, component_totals = builder._calculate_target_values()
        
        assert target_sum == 1150.0
        assert 'IPE_07' in component_totals
        assert 'IPE_08' in component_totals
        assert 'IPE_10' not in component_totals

    def test_calculate_target_values_empty_dataframes(self):
        """Test target values calculation with empty DataFrames."""
        data_store = {
            'IPE_07': pd.DataFrame(),
            'IPE_10': pd.DataFrame(),
        }
        
        builder = SummaryBuilder(data_store)
        target_sum, component_totals = builder._calculate_target_values()
        
        assert target_sum == 0.0
        assert component_totals == {}

    def test_calculate_target_values_invalid_column_data(self):
        """Test target values calculation with invalid data types in columns."""
        data_store = {
            'IPE_07': pd.DataFrame({'Amount': ['invalid', 'data', 'here']}),
        }
        
        builder = SummaryBuilder(data_store)
        target_sum, component_totals = builder._calculate_target_values()
        
        # Should handle exception gracefully and skip invalid data
        assert target_sum == 0.0
        assert 'IPE_07' not in component_totals

    def test_build_complete_reconciliation(self):
        """Test complete reconciliation with actuals and targets."""
        data_store = {
            'CR_04': pd.DataFrame({'BALANCE_AT_DATE': [10000.0]}),
            'IPE_07': pd.DataFrame({'Amount': [8000.0]}),
            'IPE_08': pd.DataFrame({'remaining_amount': [2000.0]}),
        }
        
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        assert metrics['actuals'] == 10000.0
        assert metrics['target_values'] == 10000.0
        assert metrics['variance'] == 0.0
        assert metrics['status'] == 'RECONCILED'
        assert metrics['is_reconciled'] is True

    def test_build_with_variance(self):
        """Test reconciliation with variance exceeding threshold."""
        data_store = {
            'CR_04': pd.DataFrame({'BALANCE_AT_DATE': [10000.0]}),
            'IPE_07': pd.DataFrame({'Amount': [8000.0]}),
            'IPE_08': pd.DataFrame({'remaining_amount': [500.0]}),  # Missing 1500
        }
        
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        assert metrics['actuals'] == 10000.0
        assert metrics['target_values'] == 8500.0
        assert metrics['variance'] == 1500.0
        assert metrics['status'] == 'VARIANCE_DETECTED'
        assert metrics['is_reconciled'] is False

    def test_build_with_missing_actuals(self):
        """Test reconciliation when actuals cannot be calculated."""
        data_store = {
            'IPE_07': pd.DataFrame({'Amount': [8000.0]}),
            'IPE_08': pd.DataFrame({'remaining_amount': [2000.0]}),
        }
        
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        assert metrics['actuals'] is None
        assert metrics['target_values'] == 10000.0
        assert metrics['variance'] is None
        assert metrics['status'] is None

    def test_build_with_missing_targets(self):
        """Test reconciliation when targets cannot be calculated."""
        data_store = {
            'CR_04': pd.DataFrame({'BALANCE_AT_DATE': [10000.0]}),
        }
        
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        assert metrics['actuals'] == 10000.0
        assert metrics['target_values'] == 0.0
        # Variance should still be calculated
        assert metrics['variance'] == 10000.0
        assert metrics['status'] == 'VARIANCE_DETECTED'

    def test_variance_at_threshold_boundary(self):
        """Test variance calculation at the threshold boundary (1000)."""
        # Variance of exactly 999 should be RECONCILED
        data_store = {
            'CR_04': pd.DataFrame({'BALANCE_AT_DATE': [10999.0]}),
            'IPE_07': pd.DataFrame({'Amount': [10000.0]}),
        }
        
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        assert metrics['variance'] == 999.0
        assert metrics['status'] == 'RECONCILED'
        
        # Variance of exactly 1000 should be VARIANCE_DETECTED
        data_store['CR_04'] = pd.DataFrame({'BALANCE_AT_DATE': [11000.0]})
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        assert metrics['variance'] == 1000.0
        assert metrics['status'] == 'VARIANCE_DETECTED'


class TestCalculateReconciliationMetrics:
    """Tests for the convenience function."""

    def test_convenience_function(self):
        """Test the convenience function wrapper."""
        data_store = {
            'CR_04': pd.DataFrame({'BALANCE_AT_DATE': [5000.0]}),
            'IPE_07': pd.DataFrame({'Amount': [5000.0]}),
        }
        
        metrics = calculate_reconciliation_metrics(data_store)
        
        assert metrics['actuals'] == 5000.0
        assert metrics['target_values'] == 5000.0
        assert metrics['status'] == 'RECONCILED'

    def test_convenience_function_empty_data(self):
        """Test convenience function with empty data."""
        metrics = calculate_reconciliation_metrics({})
        
        assert metrics['actuals'] is None
        assert metrics['target_values'] == 0.0
        assert metrics['status'] is None


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_negative_amounts(self):
        """Test handling of negative amounts in actuals."""
        data_store = {
            'CR_04': pd.DataFrame({'BALANCE_AT_DATE': [-1000.0, 2000.0]}),
            'IPE_07': pd.DataFrame({'Amount': [1000.0]}),
        }
        
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        # Should handle negative values correctly
        assert metrics['actuals'] == 1000.0
        assert metrics['variance'] == 0.0

    def test_very_large_numbers(self):
        """Test handling of very large financial amounts."""
        data_store = {
            'CR_04': pd.DataFrame({'BALANCE_AT_DATE': [1e12]}),  # 1 trillion
            'IPE_07': pd.DataFrame({'Amount': [1e12]}),
        }
        
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        assert metrics['actuals'] == 1e12
        assert metrics['target_values'] == 1e12
        assert metrics['status'] == 'RECONCILED'

    def test_zero_amounts(self):
        """Test handling of zero amounts."""
        data_store = {
            'CR_04': pd.DataFrame({'BALANCE_AT_DATE': [0.0]}),
            'IPE_07': pd.DataFrame({'Amount': [0.0]}),
        }
        
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        assert metrics['actuals'] == 0.0
        assert metrics['target_values'] == 0.0
        assert metrics['variance'] == 0.0
        assert metrics['status'] == 'RECONCILED'

    def test_mixed_column_types(self):
        """Test with different column name variations across IPEs."""
        data_store = {
            'CR_04': pd.DataFrame({'Balance_At_Date': [10000.0]}),
            'IPE_07': pd.DataFrame({'Amount': [5000.0]}),
            'IPE_10': pd.DataFrame({'remaining_amount': [2500.0]}),
            'IPE_08': pd.DataFrame({'Remaining Amount': [2500.0]}),
        }
        
        builder = SummaryBuilder(data_store)
        metrics = builder.build()
        
        assert metrics['actuals'] == 10000.0
        assert metrics['target_values'] == 10000.0
        assert metrics['status'] == 'RECONCILED'
