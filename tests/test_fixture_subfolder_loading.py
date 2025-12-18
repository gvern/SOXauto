"""
Tests for company subfolder fixture loading.

Validates that the extraction pipeline and jdash loader correctly load
fixtures from company-specific subfolders with fallback to root fixtures.
"""

import shutil
import pandas as pd
import pytest

from src.core.extraction_pipeline import ExtractionPipeline
from src.core.jdash_loader import load_jdash_data


class TestExtractionPipelineSubfolderLoading:
    """Tests for ExtractionPipeline fixture loading with company subfolders."""

    def test_loads_from_company_subfolder_when_available(self, tmp_path):
        """Test that fixture is loaded from company subfolder when available."""
        # Setup: Create a company-specific fixture
        company = "EC_NG"
        item_id = "IPE_07"
        
        fixtures_dir = tmp_path / "tests" / "fixtures"
        company_dir = fixtures_dir / company
        company_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a company-specific fixture
        company_fixture_data = pd.DataFrame({
            'Customer No_': ['C001', 'C002'],
            'Amount': [100.0, 200.0],
        })
        company_fixture_path = company_dir / f"fixture_{item_id}.csv"
        company_fixture_data.to_csv(company_fixture_path, index=False)
        
        # Create pipeline with mocked REPO_ROOT
        params = {'cutoff_date': '2025-09-30', 'id_companies_active': f"('{company}')"}
        
        # Temporarily override REPO_ROOT for the test
        import src.core.extraction_pipeline as ep_module
        original_repo_root = ep_module.REPO_ROOT
        try:
            ep_module.REPO_ROOT = str(tmp_path)
            pipeline = ExtractionPipeline(params, company, "202509")
            
            # Act: Load fixture
            df = pipeline._load_fixture(item_id)
            
            # Assert: Should load from company subfolder
            assert not df.empty
            assert len(df) == 2
            assert 'Customer No_' in df.columns
        finally:
            ep_module.REPO_ROOT = original_repo_root

    def test_falls_back_to_root_fixtures_when_company_not_found(self, tmp_path):
        """Test fallback to root fixtures when company-specific file not found."""
        # Setup: Create only a root fixture
        company = "EC_NG"
        item_id = "CR_05"  # Shared FX rates
        
        fixtures_dir = tmp_path / "tests" / "fixtures"
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a root fixture (shared file)
        root_fixture_data = pd.DataFrame({
            'Company_Code': ['EC_NG', 'JD_GH'],
            'FX_rate': [1650.0, 15.5],
        })
        root_fixture_path = fixtures_dir / f"fixture_{item_id}.csv"
        root_fixture_data.to_csv(root_fixture_path, index=False)
        
        # Create pipeline
        params = {'cutoff_date': '2025-09-30', 'id_companies_active': f"('{company}')"}
        
        # Temporarily override REPO_ROOT
        import src.core.extraction_pipeline as ep_module
        original_repo_root = ep_module.REPO_ROOT
        try:
            ep_module.REPO_ROOT = str(tmp_path)
            pipeline = ExtractionPipeline(params, company, "202509")
            
            # Act: Load fixture
            df = pipeline._load_fixture(item_id)
            
            # Assert: Should load from root fixtures
            assert not df.empty
            assert len(df) == 2
            assert 'FX_rate' in df.columns
        finally:
            ep_module.REPO_ROOT = original_repo_root

    def test_returns_empty_when_no_fixture_found(self, tmp_path):
        """Test that empty DataFrame is returned when no fixture found."""
        # Setup: No fixtures created
        company = "EC_NG"
        item_id = "IPE_NONEXISTENT"
        
        fixtures_dir = tmp_path / "tests" / "fixtures"
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        
        # Create pipeline
        params = {'cutoff_date': '2025-09-30', 'id_companies_active': f"('{company}')"}
        
        # Temporarily override REPO_ROOT
        import src.core.extraction_pipeline as ep_module
        original_repo_root = ep_module.REPO_ROOT
        try:
            ep_module.REPO_ROOT = str(tmp_path)
            pipeline = ExtractionPipeline(params, company, "202509")
            
            # Act: Load fixture
            df = pipeline._load_fixture(item_id)
            
            # Assert: Should return empty DataFrame
            assert df.empty
        finally:
            ep_module.REPO_ROOT = original_repo_root

    def test_prefers_company_subfolder_over_root(self, tmp_path):
        """Test that company subfolder is preferred over root fixtures."""
        # Setup: Create both company and root fixtures
        company = "EC_NG"
        item_id = "IPE_08"
        
        fixtures_dir = tmp_path / "tests" / "fixtures"
        company_dir = fixtures_dir / company
        company_dir.mkdir(parents=True, exist_ok=True)
        
        # Create company-specific fixture
        company_fixture_data = pd.DataFrame({
            'id': ['V001', 'V002'],
            'TotalAmountUsed': [100.0, 200.0],
            'source': ['company_specific', 'company_specific'],
        })
        company_fixture_path = company_dir / f"fixture_{item_id}.csv"
        company_fixture_data.to_csv(company_fixture_path, index=False)
        
        # Create root fixture with different data
        root_fixture_data = pd.DataFrame({
            'id': ['V999'],
            'TotalAmountUsed': [999.0],
            'source': ['root'],
        })
        root_fixture_path = fixtures_dir / f"fixture_{item_id}.csv"
        root_fixture_data.to_csv(root_fixture_path, index=False)
        
        # Create pipeline
        params = {'cutoff_date': '2025-09-30', 'id_companies_active': f"('{company}')"}
        
        # Temporarily override REPO_ROOT
        import src.core.extraction_pipeline as ep_module
        original_repo_root = ep_module.REPO_ROOT
        try:
            ep_module.REPO_ROOT = str(tmp_path)
            pipeline = ExtractionPipeline(params, company, "202509")
            
            # Act: Load fixture
            df = pipeline._load_fixture(item_id)
            
            # Assert: Should load from company subfolder (not root)
            assert not df.empty
            assert len(df) == 2  # Company fixture has 2 rows
            assert all(df['source'] == 'company_specific')
        finally:
            ep_module.REPO_ROOT = original_repo_root


class TestJDashLoaderSubfolderLoading:
    """Tests for JDASH loader with company subfolder support."""

    def test_loads_jdash_from_company_subfolder(self, tmp_path):
        """Test that JDASH fixture is loaded from company subfolder when available."""
        # Setup: Create a company-specific JDASH fixture
        company = "EC_NG"
        
        fixtures_dir = tmp_path / "tests" / "fixtures"
        company_dir = fixtures_dir / company
        company_dir.mkdir(parents=True, exist_ok=True)
        
        # Create company-specific JDASH fixture
        jdash_data = pd.DataFrame({
            'Voucher Id': ['V001', 'V002'],
            'Amount Used': [100.0, 200.0],
        })
        jdash_fixture_path = company_dir / "fixture_JDASH.csv"
        jdash_data.to_csv(jdash_fixture_path, index=False)
        
        # Temporarily override REPO_ROOT
        import src.core.jdash_loader as jdash_module
        original_repo_root = jdash_module.REPO_ROOT
        try:
            jdash_module.REPO_ROOT = str(tmp_path)
            
            # Act: Load JDASH with company parameter
            df, source = load_jdash_data(company=company)
            
            # Assert: Should load from company subfolder
            assert not df.empty
            assert len(df) == 2
            assert 'Voucher Id' in df.columns
            assert 'Amount Used' in df.columns
            assert company in source
        finally:
            jdash_module.REPO_ROOT = original_repo_root

    def test_jdash_falls_back_to_root_fixtures(self, tmp_path):
        """Test JDASH fallback to root fixtures when company-specific not found."""
        # Setup: Create only a root JDASH fixture
        company = "EC_NG"
        
        fixtures_dir = tmp_path / "tests" / "fixtures"
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        
        # Create root JDASH fixture
        jdash_data = pd.DataFrame({
            'Voucher Id': ['V999'],
            'Amount Used': [999.0],
        })
        jdash_fixture_path = fixtures_dir / "fixture_JDASH.csv"
        jdash_data.to_csv(jdash_fixture_path, index=False)
        
        # Temporarily override REPO_ROOT
        import src.core.jdash_loader as jdash_module
        original_repo_root = jdash_module.REPO_ROOT
        try:
            jdash_module.REPO_ROOT = str(tmp_path)
            
            # Act: Load JDASH with company parameter
            df, source = load_jdash_data(company=company)
            
            # Assert: Should load from root fixtures
            assert not df.empty
            assert len(df) == 1
            assert source == "Local Fixture"
        finally:
            jdash_module.REPO_ROOT = original_repo_root

    def test_jdash_prefers_company_over_root(self, tmp_path):
        """Test that JDASH prefers company subfolder over root fixtures."""
        # Setup: Create both company and root fixtures
        company = "JD_GH"
        
        fixtures_dir = tmp_path / "tests" / "fixtures"
        company_dir = fixtures_dir / company
        company_dir.mkdir(parents=True, exist_ok=True)
        
        # Create company-specific JDASH fixture
        company_jdash = pd.DataFrame({
            'Voucher Id': ['V001', 'V002'],
            'Amount Used': [100.0, 200.0],
        })
        company_fixture_path = company_dir / "fixture_JDASH.csv"
        company_jdash.to_csv(company_fixture_path, index=False)
        
        # Create root JDASH fixture
        root_jdash = pd.DataFrame({
            'Voucher Id': ['V999'],
            'Amount Used': [999.0],
        })
        root_fixture_path = fixtures_dir / "fixture_JDASH.csv"
        root_jdash.to_csv(root_fixture_path, index=False)
        
        # Temporarily override REPO_ROOT
        import src.core.jdash_loader as jdash_module
        original_repo_root = jdash_module.REPO_ROOT
        try:
            jdash_module.REPO_ROOT = str(tmp_path)
            
            # Act: Load JDASH with company parameter
            df, source = load_jdash_data(company=company)
            
            # Assert: Should load from company subfolder
            assert not df.empty
            assert len(df) == 2  # Company fixture has 2 rows
            assert company in source
        finally:
            jdash_module.REPO_ROOT = original_repo_root
