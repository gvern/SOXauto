"""
Tests for debug probe instrumentation in run_reconciliation.

Validates that probes are correctly placed and called during reconciliation.
"""

import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from src.core.reconciliation.run_reconciliation import run_reconciliation


class TestDebugProbeInstrumentation:
    """Tests for debug probe calls in run_reconciliation."""

    def test_probe_df_called_for_cr03_load(self):
        """Test that probe_df is called for CR_03 after loading."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': False,
            'validate_quality': False,
        }
        
        mock_cr_03 = pd.DataFrame({
            'Chart of Accounts No_': ['18412'],
            'Amount': [100.0],
        })
        
        mock_data_store = {'CR_03': mock_cr_03}
        
        with patch('src.core.reconciliation.run_reconciliation.load_all_data') as mock_load, \
             patch('src.core.reconciliation.run_reconciliation.probe_df') as mock_probe:
            mock_load.return_value = (mock_data_store, {}, {'CR_03': 'Mock'})
            
            run_reconciliation(params)
            
            # Verify probe_df was called for CR_03 raw load
            probe_calls = [call for call in mock_probe.call_args_list 
                          if len(call[0]) > 1 and call[0][1] == "NAV_raw_load_CR03"]
            assert len(probe_calls) > 0, "probe_df should be called for NAV_raw_load_CR03"

    def test_probe_df_called_for_ipe08_load(self):
        """Test that probe_df is called for IPE_08 after loading."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': False,
            'validate_quality': False,
        }
        
        mock_ipe_08 = pd.DataFrame({
            'VoucherId': ['V001'],
            'TotalAmountUsed': [100.0],
        })
        
        mock_data_store = {'IPE_08': mock_ipe_08}
        
        with patch('src.core.reconciliation.run_reconciliation.load_all_data') as mock_load, \
             patch('src.core.reconciliation.run_reconciliation.probe_df') as mock_probe:
            mock_load.return_value = (mock_data_store, {}, {'IPE_08': 'Mock'})
            
            run_reconciliation(params)
            
            # Verify probe_df was called for IPE_08 load
            probe_calls = [call for call in mock_probe.call_args_list 
                          if len(call[0]) > 1 and call[0][1] == "IPE08_load"]
            assert len(probe_calls) > 0, "probe_df should be called for IPE08_load"

    def test_probe_df_called_for_scope_filtering(self):
        """Test that probe_df is called after IPE_08 scope filtering."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': False,
            'validate_quality': False,
        }
        
        mock_ipe_08 = pd.DataFrame({
            'VoucherId': ['V001'],
            'TotalAmountUsed': [100.0],
            'business_use': ['refund'],
        })
        
        mock_data_store = {'IPE_08': mock_ipe_08}
        
        with patch('src.core.reconciliation.run_reconciliation.load_all_data') as mock_load, \
             patch('src.core.reconciliation.run_reconciliation.probe_df') as mock_probe:
            mock_load.return_value = (mock_data_store, {}, {'IPE_08': 'Mock'})
            
            run_reconciliation(params)
            
            # Verify probe_df was called for IPE_08 scope filtering
            probe_calls = [call for call in mock_probe.call_args_list 
                          if len(call[0]) > 1 and call[0][1] == "IPE08_scope_filtered"]
            assert len(probe_calls) > 0, "probe_df should be called for IPE08_scope_filtered"

    def test_probe_df_called_for_categorization(self):
        """Test that probe_df is called after NAV categorization."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': False,
            'validate_quality': False,
        }
        
        mock_cr_03 = pd.DataFrame({
            'Chart of Accounts No_': ['18412'],
            'Amount': [-100.0],
            'User ID': ['JUMIA/NAV13AFR.BATCH.SRVC'],
            'Document Description': ['Refund voucher'],
            'Bal_ Account Type': ['Customer'],
            'Document Type': ['Invoice'],
            'Document No': ['INV001'],
        })
        
        mock_data_store = {'CR_03': mock_cr_03}
        
        with patch('src.core.reconciliation.run_reconciliation.load_all_data') as mock_load, \
             patch('src.core.reconciliation.run_reconciliation.probe_df') as mock_probe:
            mock_load.return_value = (mock_data_store, {}, {'CR_03': 'Mock'})
            
            run_reconciliation(params)
            
            # Verify probe_df was called for NAV categorization
            probe_calls = [call for call in mock_probe.call_args_list 
                          if len(call[0]) > 1 and call[0][1] == "NAV_categorization_with_bridge"]
            assert len(probe_calls) > 0, "probe_df should be called for NAV_categorization_with_bridge"

    def test_audit_merge_called_for_timing_diff(self):
        """Test that audit_merge is called before timing difference calculation."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': True,
            'validate_quality': False,
        }
        
        mock_jdash = pd.DataFrame({
            'OrderId': ['O001', 'O002'],
            'OrderedAmount': [100.0, 200.0],
        })
        
        mock_ipe_08 = pd.DataFrame({
            'OrderId': ['O001', 'O003'],
            'TotalAmountUsed': [100.0, 150.0],
            'business_use': ['refund', 'store_credit'],
        })
        
        mock_data_store = {
            'JDASH': mock_jdash,
            'IPE_08': mock_ipe_08,
        }
        
        with patch('src.core.reconciliation.run_reconciliation.load_all_data') as mock_load, \
             patch('src.core.reconciliation.run_reconciliation.audit_merge') as mock_audit, \
             patch('src.core.reconciliation.run_reconciliation.calculate_timing_difference_bridge') as mock_calc:
            mock_load.return_value = (mock_data_store, {}, {'JDASH': 'Mock', 'IPE_08': 'Mock'})
            mock_calc.return_value = (0.0, pd.DataFrame())
            
            run_reconciliation(params)
            
            # Verify audit_merge was called
            assert mock_audit.called, "audit_merge should be called for timing difference merge"

    def test_no_probe_for_empty_dataframes(self):
        """Test that probes are not called for empty DataFrames."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': False,
            'validate_quality': False,
        }
        
        # Empty DataFrames
        mock_data_store = {
            'CR_03': pd.DataFrame(),
            'IPE_08': pd.DataFrame(),
        }
        
        with patch('src.core.reconciliation.run_reconciliation.load_all_data') as mock_load, \
             patch('src.core.reconciliation.run_reconciliation.probe_df') as mock_probe:
            mock_load.return_value = (mock_data_store, {}, {})
            
            run_reconciliation(params)
            
            # Verify probe_df was not called for empty DataFrames
            assert mock_probe.call_count == 0, "probe_df should not be called for empty DataFrames"

    def test_debug_output_directory_constant(self):
        """Test that DEBUG_OUTPUT_DIR constant is defined."""
        from src.core.reconciliation.run_reconciliation import DEBUG_OUTPUT_DIR
        
        assert DEBUG_OUTPUT_DIR == "outputs/_debug_sep2025_ng"
