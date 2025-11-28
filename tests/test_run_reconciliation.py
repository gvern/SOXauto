"""
Tests for the headless reconciliation engine (run_reconciliation).

Tests the main reconciliation orchestration function that chains:
Extraction -> Preprocessing -> Categorization -> Bridges
"""

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from src.core.recon.run_reconciliation import (
    run_reconciliation,
    _validate_params,
    _get_dataframe_summary,
    _get_default_ipes,
)


class TestValidateParams:
    """Tests for parameter validation."""

    def test_missing_cutoff_date(self):
        """Test that missing cutoff_date is reported as error."""
        params = {'id_companies_active': "('EC_NG')"}
        errors = _validate_params(params)
        assert any('cutoff_date' in err for err in errors)

    def test_missing_company(self):
        """Test that missing id_companies_active is reported as error."""
        params = {'cutoff_date': '2025-09-30'}
        errors = _validate_params(params)
        assert any('id_companies_active' in err for err in errors)

    def test_invalid_date_format(self):
        """Test that invalid date format is reported as error."""
        params = {
            'cutoff_date': '30-09-2025',  # Wrong format
            'id_companies_active': "('EC_NG')",
        }
        errors = _validate_params(params)
        assert any('YYYY-MM-DD' in err for err in errors)

    def test_valid_params(self):
        """Test that valid params return no errors."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
        }
        errors = _validate_params(params)
        assert len(errors) == 0


class TestGetDataframeSummary:
    """Tests for DataFrame summary generation."""

    def test_empty_dataframe(self):
        """Test summary of empty DataFrame."""
        df = pd.DataFrame()
        summary = _get_dataframe_summary(df)
        assert summary['row_count'] == 0
        assert summary['column_count'] == 0

    def test_none_dataframe(self):
        """Test summary of None DataFrame."""
        summary = _get_dataframe_summary(None)
        assert summary['row_count'] == 0
        assert summary['column_count'] == 0

    def test_normal_dataframe(self):
        """Test summary of normal DataFrame."""
        df = pd.DataFrame({
            'col_a': [1, 2, 3],
            'col_b': ['a', 'b', 'c'],
        })
        summary = _get_dataframe_summary(df)
        assert summary['row_count'] == 3
        assert summary['column_count'] == 2
        assert 'col_a' in summary['columns']
        assert 'col_b' in summary['columns']


class TestGetDefaultIpes:
    """Tests for default IPE list."""

    def test_default_ipes_not_empty(self):
        """Test that default IPEs list is not empty."""
        ipes = _get_default_ipes()
        assert len(ipes) > 0

    def test_default_ipes_contains_critical_items(self):
        """Test that default IPEs contain critical reconciliation items."""
        ipes = _get_default_ipes()
        # CR_04 is the Actuals (GL Balances) - critical
        assert 'CR_04' in ipes
        # CR_03 is needed for categorization
        assert 'CR_03' in ipes


class TestRunReconciliation:
    """Tests for the main run_reconciliation function."""

    def test_returns_required_keys(self):
        """Test that result contains all required keys."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
        }
        
        # Mock load_all_data to avoid actual extraction
        with patch('src.core.recon.run_reconciliation.load_all_data') as mock_load:
            mock_load.return_value = ({}, {}, {})
            
            result = run_reconciliation(params)
        
        # Check all required keys are present
        required_keys = [
            'status', 'timestamp', 'params', 'dataframes',
            'dataframe_summaries', 'evidence_paths', 'data_sources',
            'quality_reports', 'categorization', 'bridges',
            'reconciliation', 'errors', 'warnings',
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_error_status_on_missing_params(self):
        """Test that error status is returned for missing params."""
        params = {}  # Missing required params
        
        result = run_reconciliation(params)
        
        assert result['status'] == 'ERROR'
        assert len(result['errors']) > 0

    def test_timestamp_is_iso_format(self):
        """Test that timestamp is in ISO format."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
        }
        
        with patch('src.core.recon.run_reconciliation.load_all_data') as mock_load:
            mock_load.return_value = ({}, {}, {})
            
            result = run_reconciliation(params)
        
        # Should be able to parse the timestamp
        from datetime import datetime
        timestamp = result['timestamp']
        assert 'T' in timestamp
        assert timestamp.endswith('Z')

    def test_params_echoed_in_result(self):
        """Test that input params are echoed in result."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
        }
        
        with patch('src.core.recon.run_reconciliation.load_all_data') as mock_load:
            mock_load.return_value = ({}, {}, {})
            
            result = run_reconciliation(params)
        
        assert result['params']['cutoff_date'] == '2025-09-30'
        assert result['params']['id_companies_active'] == "('EC_NG')"

    def test_with_mock_data(self):
        """Test reconciliation with mock data."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': False,  # Skip bridges for faster test
            'validate_quality': False,  # Skip quality checks
        }
        
        # Create mock DataFrames
        mock_cr_03 = pd.DataFrame({
            'Chart of Accounts No_': ['18412', '18412', '13003'],
            'Amount': [-100.0, 50.0, 200.0],
            'User ID': ['JUMIA/NAV13AFR.BATCH.SRVC', 'USER/01', 'USER/02'],
            'Document Description': ['Refund voucher', 'Manual entry', 'Customer payment'],
        })
        
        mock_cr_04 = pd.DataFrame({
            'BALANCE_AT_DATE': [1000.0, 2000.0, 500.0],
            'GROUP_COA_ACCOUNT_NO': ['18412', '13003', '18350'],
        })
        
        mock_data_store = {
            'CR_03': mock_cr_03,
            'CR_04': mock_cr_04,
        }
        
        with patch('src.core.recon.run_reconciliation.load_all_data') as mock_load:
            mock_load.return_value = (mock_data_store, {}, {'CR_03': 'Mock', 'CR_04': 'Mock'})
            
            result = run_reconciliation(params)
        
        # Should process without error
        assert result['status'] in ['SUCCESS', 'WARNING']
        
        # Should have DataFrame summaries
        assert 'CR_03' in result['dataframe_summaries']
        assert result['dataframe_summaries']['CR_03']['row_count'] == 3

    def test_categorization_with_mock_data(self):
        """Test that categorization runs on CR_03 data."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': False,
            'validate_quality': False,
        }
        
        # Create mock CR_03 data with categorizable entries
        mock_cr_03 = pd.DataFrame({
            'Chart of Accounts No_': ['18412', '18412'],
            'Amount': [-100.0, 50.0],
            'User ID': ['JUMIA/NAV13AFR.BATCH.SRVC', 'JUMIA/NAV13AFR.BATCH.SRVC'],
            'Document Description': ['Refund voucher', 'Item price credit'],
        })
        
        mock_data_store = {'CR_03': mock_cr_03}
        
        with patch('src.core.recon.run_reconciliation.load_all_data') as mock_load:
            mock_load.return_value = (mock_data_store, {}, {'CR_03': 'Mock'})
            
            result = run_reconciliation(params)
        
        # Should have categorization summary
        assert 'categorization' in result
        assert 'summary' in result['categorization']

    def test_json_serializable_output(self):
        """Test that result is JSON serializable."""
        import json
        
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': False,
            'validate_quality': False,
        }
        
        with patch('src.core.recon.run_reconciliation.load_all_data') as mock_load:
            mock_load.return_value = ({}, {}, {})
            
            result = run_reconciliation(params)
        
        # Should be JSON serializable
        json_str = json.dumps(result, default=str)
        assert json_str is not None
        assert len(json_str) > 0


class TestReconciliationIntegration:
    """Integration tests for the reconciliation pipeline."""

    def test_full_pipeline_with_fixtures(self):
        """Test full pipeline with fixture data if available."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': True,
            'validate_quality': True,
        }
        
        # Create comprehensive mock data
        mock_cr_03 = pd.DataFrame({
            'Chart of Accounts No_': ['18412', '18412', '18412', '18412'],
            'Amount': [-100.0, 50.0, -75.0, 25.0],
            'User ID': [
                'JUMIA/NAV13AFR.BATCH.SRVC',
                'JUMIA/NAV13AFR.BATCH.SRVC',
                'USER/01',
                'USER/02',
            ],
            'Document Description': [
                'Refund voucher',
                'Item price credit',
                'Manual RND entry',
                'EXPR_APLGY-2024-123',
            ],
        })
        
        mock_ipe_08 = pd.DataFrame({
            'id': ['V001', 'V002'],
            'business_use': ['refund', 'apology_v2'],
            'remaining_amount': [100.0, 50.0],
            'is_active': [0, 1],
        })
        
        mock_ipe_07 = pd.DataFrame({
            'Customer No_': ['C001', 'C002'],
            'Customer Name': ['Customer 1', 'Customer 2'],
            'Customer Posting Group': ['DOMESTIC', 'DOMESTIC'],
            'Amount': [1000.0, 2000.0],
        })
        
        mock_cr_04 = pd.DataFrame({
            'BALANCE_AT_DATE': [5000.0],
            'GROUP_COA_ACCOUNT_NO': ['18412'],
        })
        
        mock_data_store = {
            'CR_03': mock_cr_03,
            'CR_04': mock_cr_04,
            'IPE_07': mock_ipe_07,
            'IPE_08': mock_ipe_08,
        }
        
        mock_source_store = {
            'CR_03': 'Mock',
            'CR_04': 'Mock',
            'IPE_07': 'Mock',
            'IPE_08': 'Mock',
        }
        
        with patch('src.core.recon.run_reconciliation.load_all_data') as mock_load:
            mock_load.return_value = (mock_data_store, {}, mock_source_store)
            
            result = run_reconciliation(params)
        
        # Verify pipeline completed
        assert result['status'] in ['SUCCESS', 'WARNING']
        
        # Verify categorization ran
        assert 'categorization' in result
        if 'summary' in result['categorization']:
            summary = result['categorization']['summary']
            assert summary['total_rows'] == 4
        
        # Verify bridges ran (may have errors due to missing data)
        assert 'bridges' in result
