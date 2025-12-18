"""
Tests for multi-entity fixture loading and VTC date wiring.

Verifies the QA requirements from the issue:
1. Multi-entity fixture loading from tests/fixtures/{company}/
2. VTC adjustment receives cutoff_date parameter
3. Company parameter flows correctly from script to orchestrator
"""

import os
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

from src.core.extraction_pipeline import ExtractionPipeline, load_all_data
from src.core.reconciliation.run_reconciliation import run_reconciliation


class TestMultiEntityFixtureLoading:
    """Test multi-entity fixture loading logic."""

    def test_fixture_loading_with_company_parameter(self, tmp_path):
        """Test that fixtures are loaded from company-specific directory when company is set."""
        # Setup: Create a mock fixture structure
        # tests/fixtures/EC_NG/fixture_IPE_07.csv
        company_dir = tmp_path / "tests" / "fixtures" / "EC_NG"
        company_dir.mkdir(parents=True, exist_ok=True)
        
        fixture_file = company_dir / "fixture_IPE_07.csv"
        test_data = pd.DataFrame({
            'Customer No_': ['C001', 'C002'],
            'Amount': [100.0, 200.0],
        })
        test_data.to_csv(fixture_file, index=False)
        
        # Create pipeline with company parameter
        params = {
            'company': 'EC_NG',
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
        }
        
        with patch('src.core.extraction_pipeline.REPO_ROOT', str(tmp_path)):
            pipeline = ExtractionPipeline(params)
            df = pipeline._load_fixture('IPE_07')
        
        # Verify data was loaded from company-specific directory
        assert not df.empty
        assert len(df) == 2
        assert 'Customer No_' in df.columns

    def test_fixture_loading_fallback_to_root(self, tmp_path):
        """Test that fixtures fall back to root directory when company-specific not found."""
        # Setup: Create root fixture only
        root_dir = tmp_path / "tests" / "fixtures"
        root_dir.mkdir(parents=True, exist_ok=True)
        
        fixture_file = root_dir / "fixture_IPE_07.csv"
        test_data = pd.DataFrame({
            'Customer No_': ['C001'],
            'Amount': [100.0],
        })
        test_data.to_csv(fixture_file, index=False)
        
        # Create pipeline with company parameter
        params = {
            'company': 'EC_NG',
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
        }
        
        with patch('src.core.extraction_pipeline.REPO_ROOT', str(tmp_path)):
            pipeline = ExtractionPipeline(params)
            df = pipeline._load_fixture('IPE_07')
        
        # Verify data was loaded from root fallback
        assert not df.empty
        assert len(df) == 1

    def test_country_code_extraction_from_company_param(self):
        """Test that country_code is correctly extracted from company parameter."""
        params = {
            'company': 'EC_NG',
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
        }
        
        pipeline = ExtractionPipeline(params)
        assert pipeline.country_code == 'EC_NG'

    def test_country_code_extraction_from_id_companies_active(self):
        """Test that country_code is extracted from id_companies_active when company not set."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_KE')",
        }
        
        pipeline = ExtractionPipeline(params)
        assert pipeline.country_code == 'EC_KE'


class TestVTCDateWiring:
    """Test that VTC adjustment receives cutoff_date parameter."""

    def test_vtc_receives_cutoff_date_in_reconciliation(self):
        """Test that run_reconciliation passes cutoff_date to calculate_vtc_adjustment."""
        params = {
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
            'run_bridges': True,
            'validate_quality': False,
        }
        
        # Create mock data with inactive vouchers
        mock_ipe_08 = pd.DataFrame({
            'id': ['V001', 'V002'],
            'business_use': ['refund', 'refund'],
            'is_valid': ['valid', 'valid'],
            'is_active': [0, 0],
            'inactive_at': ['2025-09-15', '2025-08-15'],  # One in cutoff month, one not
            'remaining_amount': [100.0, 50.0],
            'ID_COMPANY': ['EC_NG', 'EC_NG'],
        })
        
        mock_cr_03 = pd.DataFrame({
            'Chart of Accounts No_': ['18412'],
            'Amount': [-100.0],
            'User ID': ['JUMIA/NAV13AFR.BATCH.SRVC'],
            'Document Description': ['Test'],
        })
        
        mock_data_store = {
            'CR_03': mock_cr_03,
            'IPE_08': mock_ipe_08,
        }
        
        # Mock calculate_vtc_adjustment to verify it receives cutoff_date
        with patch('src.core.reconciliation.run_reconciliation.load_all_data') as mock_load:
            with patch('src.core.reconciliation.run_reconciliation.calculate_vtc_adjustment') as mock_vtc:
                mock_load.return_value = (mock_data_store, {}, {'CR_03': 'Mock', 'IPE_08': 'Mock'})
                mock_vtc.return_value = (100.0, pd.DataFrame(), {'total_count': 1})
                
                result = run_reconciliation(params)
                
                # Verify calculate_vtc_adjustment was called with cutoff_date
                assert mock_vtc.called
                call_kwargs = mock_vtc.call_args[1]
                assert 'cutoff_date' in call_kwargs
                assert call_kwargs['cutoff_date'] == '2025-09-30'


class TestScriptParameterFlow:
    """Test that --company parameter flows correctly through the system."""

    def test_company_param_in_load_all_data(self):
        """Test that company parameter is used in load_all_data."""
        params = {
            'company': 'EC_NG',
            'cutoff_date': '2025-09-30',
            'id_companies_active': "('EC_NG')",
        }
        
        with patch('src.core.extraction_pipeline.ExtractionPipeline') as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline_class.return_value = mock_pipeline
            mock_pipeline._load_fixture.return_value = pd.DataFrame()
            mock_pipeline.filter_by_country.return_value = pd.DataFrame()
            
            # Mock asyncio.run to avoid actual async execution
            with patch('src.core.extraction_pipeline.asyncio.run') as mock_async:
                mock_async.return_value = (pd.DataFrame(), None)
                
                data_store, evidence_store, source_store = load_all_data(
                    params=params,
                    required_ipes=['IPE_07'],
                )
                
                # Verify pipeline was created with correct params
                mock_pipeline_class.assert_called_once()
                call_args = mock_pipeline_class.call_args
                assert call_args[0][0] == params  # First positional arg is params
                # The country_code should be extracted from 'company' param
                assert call_args[0][1] == 'EC_NG'  # Second positional arg is country_code
