"""
Unit tests for merge_utils module.

Tests the audit_merge function's ability to detect Cartesian products
and other merge anomalies.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.utils.merge_utils import audit_merge


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary directory for test outputs."""
    return tmp_path / "test_output"


class TestAuditMerge:
    """Test suite for audit_merge function."""

    def test_no_duplicates_clean_merge(self, temp_output_dir):
        """Test audit_merge with clean data (no duplicates)."""
        # Create clean test data
        left = pd.DataFrame({
            'id': [1, 2, 3],
            'value': [10, 20, 30]
        })
        right = pd.DataFrame({
            'id': [1, 2, 3],
            'amount': [100, 200, 300]
        })
        
        # Run audit
        result = audit_merge(left, right, on='id', name='clean_merge', out_dir=temp_output_dir)
        
        # Verify results
        assert result['left_duplicates'] == 0
        assert result['right_duplicates'] == 0
        assert result['has_duplicates'] is False
        assert result['left_total_rows'] == 3
        assert result['right_total_rows'] == 3
        
        # Verify no CSV files were created
        assert not (temp_output_dir / 'clean_merge.left_dup_keys.csv').exists()
        assert not (temp_output_dir / 'clean_merge.right_dup_keys.csv').exists()
        
        # Verify log file was created
        assert (temp_output_dir / 'merge_audit.log').exists()

    def test_left_duplicates_only(self, temp_output_dir):
        """Test audit_merge with duplicates in left DataFrame only."""
        left = pd.DataFrame({
            'id': [1, 1, 2, 3],  # ID 1 appears twice
            'value': [10, 15, 20, 30]
        })
        right = pd.DataFrame({
            'id': [1, 2, 3],
            'amount': [100, 200, 300]
        })
        
        result = audit_merge(left, right, on='id', name='left_dup', out_dir=temp_output_dir)
        
        assert result['left_duplicates'] == 2  # Two rows with duplicate ID
        assert result['right_duplicates'] == 0
        assert result['has_duplicates'] is True
        assert result['left_unique_dup_keys'] == 1  # One unique duplicate key
        
        # Verify CSV file was created for left duplicates
        left_dup_file = temp_output_dir / 'left_dup.left_dup_keys.csv'
        assert left_dup_file.exists()
        
        # Verify CSV content
        dup_df = pd.read_csv(left_dup_file)
        assert len(dup_df) == 2
        assert all(dup_df['id'] == 1)

    def test_right_duplicates_only(self, temp_output_dir):
        """Test audit_merge with duplicates in right DataFrame only."""
        left = pd.DataFrame({
            'id': [1, 2, 3],
            'value': [10, 20, 30]
        })
        right = pd.DataFrame({
            'id': [1, 2, 2, 3],  # ID 2 appears twice
            'amount': [100, 200, 250, 300]
        })
        
        result = audit_merge(left, right, on='id', name='right_dup', out_dir=temp_output_dir)
        
        assert result['left_duplicates'] == 0
        assert result['right_duplicates'] == 2
        assert result['has_duplicates'] is True
        assert result['right_unique_dup_keys'] == 1
        
        # Verify CSV file was created for right duplicates
        right_dup_file = temp_output_dir / 'right_dup.right_dup_keys.csv'
        assert right_dup_file.exists()
        
        # Verify CSV content
        dup_df = pd.read_csv(right_dup_file)
        assert len(dup_df) == 2
        assert all(dup_df['id'] == 2)

    def test_both_sides_duplicates_cartesian_risk(self, temp_output_dir):
        """Test audit_merge with duplicates on both sides (Cartesian product risk)."""
        left = pd.DataFrame({
            'id': [1, 1, 2, 3],  # ID 1 duplicated
            'value': [10, 15, 20, 30]
        })
        right = pd.DataFrame({
            'id': [1, 1, 2, 3],  # ID 1 duplicated
            'amount': [100, 150, 200, 300]
        })
        
        result = audit_merge(left, right, on='id', name='cartesian', out_dir=temp_output_dir)
        
        assert result['left_duplicates'] == 2
        assert result['right_duplicates'] == 2
        assert result['has_duplicates'] is True
        
        # Both CSV files should be created
        assert (temp_output_dir / 'cartesian.left_dup_keys.csv').exists()
        assert (temp_output_dir / 'cartesian.right_dup_keys.csv').exists()

    def test_multiple_join_keys(self, temp_output_dir):
        """Test audit_merge with multiple join columns."""
        left = pd.DataFrame({
            'customer_id': [1, 1, 2, 3],
            'product_id': ['A', 'A', 'B', 'C'],  # (1, 'A') duplicated
            'value': [10, 15, 20, 30]
        })
        right = pd.DataFrame({
            'customer_id': [1, 2, 3],
            'product_id': ['A', 'B', 'C'],
            'amount': [100, 200, 300]
        })
        
        result = audit_merge(
            left, right, 
            on=['customer_id', 'product_id'], 
            name='multi_key', 
            out_dir=temp_output_dir
        )
        
        assert result['left_duplicates'] == 2  # (1, 'A') appears twice
        assert result['right_duplicates'] == 0
        assert result['has_duplicates'] is True

    def test_single_key_as_string(self, temp_output_dir):
        """Test that single key can be passed as string (not list)."""
        left = pd.DataFrame({'id': [1, 2], 'value': [10, 20]})
        right = pd.DataFrame({'id': [1, 2], 'amount': [100, 200]})
        
        # Should work with string
        result = audit_merge(left, right, on='id', name='string_key', out_dir=temp_output_dir)
        
        assert result['has_duplicates'] is False

    def test_missing_column_in_left(self, temp_output_dir):
        """Test error handling when join column is missing in left DataFrame."""
        left = pd.DataFrame({'id': [1, 2], 'value': [10, 20]})
        right = pd.DataFrame({'customer_id': [1, 2], 'amount': [100, 200]})
        
        with pytest.raises(ValueError, match="Missing columns in left DataFrame"):
            audit_merge(left, right, on='customer_id', name='missing_left', out_dir=temp_output_dir)

    def test_missing_column_in_right(self, temp_output_dir):
        """Test error handling when join column is missing in right DataFrame."""
        left = pd.DataFrame({'customer_id': [1, 2], 'value': [10, 20]})
        right = pd.DataFrame({'id': [1, 2], 'amount': [100, 200]})
        
        with pytest.raises(ValueError, match="Missing columns in right DataFrame"):
            audit_merge(left, right, on='customer_id', name='missing_right', out_dir=temp_output_dir)

    def test_empty_dataframes(self, temp_output_dir):
        """Test audit_merge with empty DataFrames."""
        left = pd.DataFrame({'id': [], 'value': []})
        right = pd.DataFrame({'id': [], 'amount': []})
        
        result = audit_merge(left, right, on='id', name='empty', out_dir=temp_output_dir)
        
        assert result['left_duplicates'] == 0
        assert result['right_duplicates'] == 0
        assert result['has_duplicates'] is False
        assert result['left_total_rows'] == 0
        assert result['right_total_rows'] == 0

    def test_output_directory_creation(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        new_dir = tmp_path / 'nested' / 'output' / 'dir'
        assert not new_dir.exists()
        
        left = pd.DataFrame({'id': [1, 2], 'value': [10, 20]})
        right = pd.DataFrame({'id': [1, 2], 'amount': [100, 200]})
        
        audit_merge(left, right, on='id', name='test', out_dir=new_dir)
        
        # Directory should now exist
        assert new_dir.exists()
        assert (new_dir / 'merge_audit.log').exists()

    def test_many_duplicates(self, temp_output_dir):
        """Test with many duplicate keys to verify counting logic."""
        # Create data with ID 1 appearing 5 times, ID 2 appearing 3 times
        left = pd.DataFrame({
            'id': [1, 1, 1, 1, 1, 2, 2, 2, 3],
            'value': range(9)
        })
        right = pd.DataFrame({
            'id': [1, 2, 3],
            'amount': [100, 200, 300]
        })
        
        result = audit_merge(left, right, on='id', name='many_dup', out_dir=temp_output_dir)
        
        # 5 rows with ID 1 + 3 rows with ID 2 = 8 duplicate rows
        assert result['left_duplicates'] == 8
        # 2 unique keys that have duplicates (ID 1 and ID 2)
        assert result['left_unique_dup_keys'] == 2
        
        # Verify CSV contains all duplicate rows
        dup_df = pd.read_csv(temp_output_dir / 'many_dup.left_dup_keys.csv')
        assert len(dup_df) == 8

    def test_real_world_financial_scenario(self, temp_output_dir):
        """Test with realistic financial data scenario."""
        # IPE data with duplicate customer entries (problematic)
        ipe_data = pd.DataFrame({
            'customer_no': ['C001', 'C001', 'C002', 'C003'],
            'document_no': ['D1', 'D2', 'D3', 'D4'],
            'amount': [1000.0, 1500.0, 2000.0, 3000.0]
        })
        
        # GL data
        gl_data = pd.DataFrame({
            'customer_no': ['C001', 'C002', 'C003'],
            'gl_amount': [2500.0, 2000.0, 3000.0]
        })
        
        result = audit_merge(
            ipe_data, gl_data, 
            on='customer_no', 
            name='financial_recon',
            out_dir=temp_output_dir
        )
        
        # Customer C001 appears twice in IPE data
        assert result['left_duplicates'] == 2
        assert result['right_duplicates'] == 0
        assert result['has_duplicates'] is True
        
        # Verify the duplicate customer is exported
        dup_df = pd.read_csv(temp_output_dir / 'financial_recon.left_dup_keys.csv')
        assert all(dup_df['customer_no'] == 'C001')
        assert len(dup_df) == 2

    def test_log_file_append_mode(self, temp_output_dir):
        """Test that multiple audits append to the same log file."""
        left = pd.DataFrame({'id': [1, 2], 'value': [10, 20]})
        right = pd.DataFrame({'id': [1, 2], 'amount': [100, 200]})
        
        # First audit
        audit_merge(left, right, on='id', name='audit1', out_dir=temp_output_dir)
        
        # Second audit
        audit_merge(left, right, on='id', name='audit2', out_dir=temp_output_dir)
        
        # Log file should contain both audits
        log_file = temp_output_dir / 'merge_audit.log'
        with open(log_file, 'r') as f:
            log_content = f.read()
        
        assert 'audit1' in log_content
        assert 'audit2' in log_content
        # Should appear twice (start and end markers)
        assert log_content.count('audit1') >= 2
        assert log_content.count('audit2') >= 2
