#!/usr/bin/env python3
"""
Test enhanced evidence package functionality.

This test verifies:
1. System context generation (git commit, hostname, Python version)
2. Evidence package folder naming with country and period
3. Full parameter logging in evidence files
4. Tail snapshot instead of head snapshot

Run:
    python3 tests/test_evidence_enhancements.py
    or
    pytest tests/test_evidence_enhancements.py -v
"""
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.system_utils import (
    get_git_commit_hash,
    get_execution_host,
    get_python_version,
    get_system_context
)
from src.core.evidence.manager import (
    DigitalEvidenceManager,
    IPEEvidenceGenerator
)


class TestSystemUtils:
    """Test system utility functions."""
    
    def test_get_git_commit_hash(self):
        """Test git commit hash retrieval."""
        commit_hash = get_git_commit_hash()
        assert commit_hash is not None
        assert isinstance(commit_hash, str)
        # Should be 7 characters for short hash or 'unknown' if not in git repo
        assert len(commit_hash) == 7 or commit_hash == 'unknown'
    
    def test_get_execution_host(self):
        """Test hostname retrieval."""
        hostname = get_execution_host()
        assert hostname is not None
        assert isinstance(hostname, str)
        assert len(hostname) > 0
    
    def test_get_python_version(self):
        """Test Python version retrieval."""
        version = get_python_version()
        assert version is not None
        assert isinstance(version, str)
        assert 'Python' in version or '3.' in version
    
    def test_get_system_context(self):
        """Test complete system context retrieval."""
        context = get_system_context()
        assert context is not None
        assert isinstance(context, dict)
        assert 'git_commit_id' in context
        assert 'execution_host' in context
        assert 'python_version' in context
        assert 'runner_version' in context
        assert context['runner_version'] == 'SOXauto v1.0'


class TestEvidenceManagerEnhancements:
    """Test enhanced evidence manager functionality."""
    
    @pytest.fixture
    def temp_evidence_dir(self):
        """Create a temporary evidence directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_evidence_package_with_country_and_period(self, temp_evidence_dir):
        """Test evidence package creation with country and period."""
        manager = DigitalEvidenceManager(base_evidence_dir=temp_evidence_dir)
        
        ipe_id = "IPE_08"
        country = "NG"
        period = "202509"
        metadata = {
            'ipe_id': ipe_id,
            'description': 'Test IPE',
            'cutoff_date': '2025-09-30'
        }
        
        evidence_dir = manager.create_evidence_package(
            ipe_id=ipe_id,
            execution_metadata=metadata,
            country=country,
            period=period
        )
        
        # Verify folder name format: {ipe_id}_{country}_{period}_{timestamp}
        folder_name = Path(evidence_dir).name
        assert folder_name.startswith(f"{ipe_id}_{country}_{period}_")
        
        # Verify folder exists
        assert os.path.exists(evidence_dir)
        
        # Verify 00_system_context.json exists
        context_file = Path(evidence_dir) / "00_system_context.json"
        assert context_file.exists()
        
        # Verify system context content
        with open(context_file, 'r') as f:
            context = json.load(f)
        
        assert 'git_commit_id' in context
        assert 'execution_host' in context
        assert 'python_version' in context
        assert 'runner_version' in context
        assert context['runner_version'] == 'SOXauto v1.0'
        
        # Verify execution metadata file exists
        metadata_file = Path(evidence_dir) / "execution_metadata.json"
        assert metadata_file.exists()
    
    def test_evidence_package_without_country_and_period(self, temp_evidence_dir):
        """Test evidence package creation without country and period (fallback)."""
        manager = DigitalEvidenceManager(base_evidence_dir=temp_evidence_dir)
        
        ipe_id = "IPE_07"
        metadata = {
            'ipe_id': ipe_id,
            'description': 'Test IPE',
            'cutoff_date': '2025-09-30'
        }
        
        evidence_dir = manager.create_evidence_package(
            ipe_id=ipe_id,
            execution_metadata=metadata
        )
        
        # Verify folder name format: {ipe_id}_{timestamp} (fallback)
        folder_name = Path(evidence_dir).name
        assert folder_name.startswith(f"{ipe_id}_")
        
        # Verify folder exists
        assert os.path.exists(evidence_dir)


class TestDataSnapshotEnhancements:
    """Test data snapshot enhancements (tail instead of head)."""
    
    @pytest.fixture
    def temp_evidence_dir(self):
        """Create a temporary evidence directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_snapshot_uses_tail(self, temp_evidence_dir):
        """Test that data snapshot uses tail instead of head."""
        # Create evidence generator
        evidence_dir = Path(temp_evidence_dir) / "test_evidence"
        evidence_dir.mkdir(parents=True)
        generator = IPEEvidenceGenerator(str(evidence_dir), "IPE_TEST")
        
        # Create a test DataFrame with 2000 rows
        test_data = pd.DataFrame({
            'id': range(1, 2001),
            'value': range(2001, 4001)
        })
        
        # Save snapshot
        generator.save_data_snapshot(test_data, snapshot_rows=100)
        
        # Verify snapshot file exists
        snapshot_file = evidence_dir / "03_data_snapshot.csv"
        assert snapshot_file.exists()
        
        # Read the snapshot (skip comment lines)
        snapshot_df = pd.read_csv(snapshot_file, comment='#')
        
        # Verify it contains 1000 rows (because len(df) > 1000)
        assert len(snapshot_df) == 1000
        
        # Verify it contains the LAST rows (tail)
        # The last row should have id=2000
        assert snapshot_df['id'].iloc[-1] == 2000
        # The first row should have id=1001 (2000-1000+1)
        assert snapshot_df['id'].iloc[0] == 1001
        
        # Verify summary file includes snapshot_type
        summary_file = evidence_dir / "04_data_summary.json"
        assert summary_file.exists()
        
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        
        assert summary['snapshot_type'] == 'tail'
        assert summary['snapshot_rows'] == 1000
        assert summary['total_rows'] == 2000
    
    def test_snapshot_small_dataframe(self, temp_evidence_dir):
        """Test snapshot with DataFrame smaller than 1000 rows."""
        # Create evidence generator
        evidence_dir = Path(temp_evidence_dir) / "test_evidence"
        evidence_dir.mkdir(parents=True)
        generator = IPEEvidenceGenerator(str(evidence_dir), "IPE_TEST")
        
        # Create a small test DataFrame with 50 rows
        test_data = pd.DataFrame({
            'id': range(1, 51),
            'value': range(51, 101)
        })
        
        # Save snapshot
        generator.save_data_snapshot(test_data, snapshot_rows=100)
        
        # Read the snapshot
        snapshot_file = evidence_dir / "03_data_snapshot.csv"
        snapshot_df = pd.read_csv(snapshot_file, comment='#')
        
        # Verify it contains all 50 rows
        assert len(snapshot_df) == 50
        
        # Verify it's the tail (in this case, all data)
        assert snapshot_df['id'].iloc[-1] == 50
        assert snapshot_df['id'].iloc[0] == 1


class TestFullParameterLogging:
    """Test full parameter logging in evidence."""
    
    @pytest.fixture
    def temp_evidence_dir(self):
        """Create a temporary evidence directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_full_params_logged(self, temp_evidence_dir):
        """Test that all parameters are logged in 02_query_parameters.json."""
        # Create evidence generator
        evidence_dir = Path(temp_evidence_dir) / "test_evidence"
        evidence_dir.mkdir(parents=True)
        generator = IPEEvidenceGenerator(str(evidence_dir), "IPE_08")
        
        # Test query with parameters
        test_query = "SELECT * FROM table WHERE date = ?"
        test_params = {
            'cutoff_date': '2025-09-30',
            'gl_accounts': '13003,13011',
            'id_companies_active': '1,2,3,4,5',
            'year': '2025',
            'month': '09',
            'parameters': ['2025-09-30']
        }
        
        # Save query with full parameters
        generator.save_executed_query(test_query, test_params)
        
        # Verify parameters file exists
        params_file = evidence_dir / "02_query_parameters.json"
        assert params_file.exists()
        
        # Verify all parameters are saved
        with open(params_file, 'r') as f:
            saved_params = json.load(f)
        
        assert saved_params['cutoff_date'] == '2025-09-30'
        assert saved_params['gl_accounts'] == '13003,13011'
        assert saved_params['id_companies_active'] == '1,2,3,4,5'
        assert saved_params['year'] == '2025'
        assert saved_params['month'] == '09'


def run_all_tests():
    """Run all tests manually."""
    print("=" * 70)
    print("EVIDENCE PACKAGE ENHANCEMENT TESTS")
    print("=" * 70)
    
    # Test system utils
    print("\n--- Testing System Utils ---")
    test_utils = TestSystemUtils()
    test_utils.test_get_git_commit_hash()
    print("✅ Git commit hash retrieval works")
    
    test_utils.test_get_execution_host()
    print("✅ Hostname retrieval works")
    
    test_utils.test_get_python_version()
    print("✅ Python version retrieval works")
    
    test_utils.test_get_system_context()
    print("✅ System context retrieval works")
    
    # Test evidence manager enhancements
    print("\n--- Testing Evidence Manager Enhancements ---")
    temp_dir = tempfile.mkdtemp()
    try:
        test_manager = TestEvidenceManagerEnhancements()
        test_manager.test_evidence_package_with_country_and_period(temp_dir)
        print("✅ Evidence package with country and period works")
        
        test_manager.test_evidence_package_without_country_and_period(temp_dir)
        print("✅ Evidence package fallback (without country/period) works")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Test snapshot enhancements
    print("\n--- Testing Data Snapshot Enhancements ---")
    temp_dir = tempfile.mkdtemp()
    try:
        test_snapshot = TestDataSnapshotEnhancements()
        test_snapshot.test_snapshot_uses_tail(temp_dir)
        print("✅ Tail snapshot works correctly")
        
        test_snapshot.test_snapshot_small_dataframe(temp_dir)
        print("✅ Snapshot with small DataFrame works correctly")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Test parameter logging
    print("\n--- Testing Full Parameter Logging ---")
    temp_dir = tempfile.mkdtemp()
    try:
        test_params = TestFullParameterLogging()
        test_params.test_full_params_logged(temp_dir)
        print("✅ Full parameter logging works")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    return True


if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
