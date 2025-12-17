"""
Tests for debug probe utilities.

Validates that probe_df and audit_merge work correctly and produce
expected debug output files.
"""

import pandas as pd
from pathlib import Path

from src.utils.debug_probes import probe_df, audit_merge


class TestProbeDF:
    """Tests for the probe_df function."""

    def test_probe_df_creates_log_file(self, tmp_path):
        """Test that probe_df creates a log file."""
        df = pd.DataFrame({
            'col_a': [1, 2, 3],
            'col_b': [10.5, 20.5, 30.5],
        })
        
        debug_dir = str(tmp_path / "test_debug")
        probe_df(df, "test_checkpoint", debug_dir=debug_dir)
        
        log_file = Path(debug_dir) / "probe_log.txt"
        assert log_file.exists()
        
        # Check log file content
        with open(log_file, 'r') as f:
            content = f.read()
            assert "test_checkpoint" in content
            assert "Row Count: 3" in content
            assert "Column Count: 2" in content

    def test_probe_df_creates_sample_file(self, tmp_path):
        """Test that probe_df creates a sample CSV file."""
        df = pd.DataFrame({
            'col_a': [1, 2, 3],
            'col_b': [10.5, 20.5, 30.5],
        })
        
        debug_dir = str(tmp_path / "test_debug")
        probe_df(df, "test_checkpoint", debug_dir=debug_dir)
        
        # Check that a sample CSV file was created
        sample_files = list(Path(debug_dir).glob("test_checkpoint_*_sample.csv"))
        assert len(sample_files) == 1
        
        # Verify the sample file contains data
        sample_df = pd.read_csv(sample_files[0])
        assert len(sample_df) == 3

    def test_probe_df_with_metrics(self, tmp_path):
        """Test that probe_df calculates metrics correctly."""
        df = pd.DataFrame({
            'Amount': [100.0, 200.0, 300.0],
            'Category': ['A', 'B', 'A'],
        })
        
        debug_dir = str(tmp_path / "test_debug")
        probe_df(df, "test_with_metrics", debug_dir=debug_dir, metrics=['Amount', 'Category'])
        
        log_file = Path(debug_dir) / "probe_log.txt"
        with open(log_file, 'r') as f:
            content = f.read()
            # Numeric column should have sum and mean
            assert "Amount_sum: 600.00" in content
            assert "Amount_mean: 200.00" in content
            # String column should have unique count
            assert "Category_unique_count: 2" in content

    def test_probe_df_with_empty_dataframe(self, tmp_path):
        """Test that probe_df handles empty DataFrame gracefully."""
        df = pd.DataFrame()
        
        debug_dir = str(tmp_path / "test_debug")
        probe_df(df, "empty_checkpoint", debug_dir=debug_dir)
        
        log_file = Path(debug_dir) / "probe_log.txt"
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Row Count: 0" in content


class TestAuditMerge:
    """Tests for the audit_merge function."""

    def test_audit_merge_creates_log_file(self, tmp_path):
        """Test that audit_merge creates a log file."""
        left_df = pd.DataFrame({
            'key': [1, 2, 3],
            'value_left': ['a', 'b', 'c'],
        })
        right_df = pd.DataFrame({
            'key': [2, 3, 4],
            'value_right': ['x', 'y', 'z'],
        })
        
        debug_dir = str(tmp_path / "test_debug")
        audit_merge(left_df, right_df, on='key', merge_name="test_merge", debug_dir=debug_dir)
        
        log_file = Path(debug_dir) / "merge_audit_log.txt"
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            content = f.read()
            assert "test_merge" in content
            assert "Left DataFrame" in content
            assert "Right DataFrame" in content

    def test_audit_merge_analyzes_keys(self, tmp_path):
        """Test that audit_merge analyzes key uniqueness."""
        left_df = pd.DataFrame({
            'key': [1, 2, 3, 1],  # Duplicate key
            'value': ['a', 'b', 'c', 'd'],
        })
        right_df = pd.DataFrame({
            'key': [2, 3, 4],
            'value': ['x', 'y', 'z'],
        })
        
        debug_dir = str(tmp_path / "test_debug")
        audit_merge(left_df, right_df, on='key', merge_name="duplicate_test", debug_dir=debug_dir)
        
        log_file = Path(debug_dir) / "merge_audit_log.txt"
        with open(log_file, 'r') as f:
            content = f.read()
            # Should report duplicate keys
            assert "Unique Keys: 3" in content
            assert "Duplicate Keys: 1" in content

    def test_audit_merge_with_missing_keys(self, tmp_path):
        """Test that audit_merge handles missing keys."""
        left_df = pd.DataFrame({
            'key_left': [1, 2, 3],
            'value': ['a', 'b', 'c'],
        })
        right_df = pd.DataFrame({
            'key_right': [2, 3, 4],
            'value': ['x', 'y', 'z'],
        })
        
        debug_dir = str(tmp_path / "test_debug")
        audit_merge(left_df, right_df, on='nonexistent_key', 
                   merge_name="missing_key_test", debug_dir=debug_dir)
        
        log_file = Path(debug_dir) / "merge_audit_log.txt"
        with open(log_file, 'r') as f:
            content = f.read()
            assert "ERROR: Missing merge keys!" in content

    def test_audit_merge_match_rate(self, tmp_path):
        """Test that audit_merge calculates match rate."""
        left_df = pd.DataFrame({
            'key': [1, 2, 3, 4],
            'value': ['a', 'b', 'c', 'd'],
        })
        right_df = pd.DataFrame({
            'key': [3, 4, 5, 6],
            'value': ['x', 'y', 'z', 'w'],
        })
        
        debug_dir = str(tmp_path / "test_debug")
        audit_merge(left_df, right_df, on='key', merge_name="match_rate_test", debug_dir=debug_dir)
        
        log_file = Path(debug_dir) / "merge_audit_log.txt"
        with open(log_file, 'r') as f:
            content = f.read()
            # 2 out of 4 keys match on left (50%)
            assert "Left Match Rate: 50.0%" in content
            # 2 out of 4 keys match on right (50%)
            assert "Right Match Rate: 50.0%" in content
            # Should report matching and non-matching keys
            assert "Matching Keys: 2" in content
            assert "Left-Only Keys: 2" in content
            assert "Right-Only Keys: 2" in content

    def test_audit_merge_with_multiple_keys(self, tmp_path):
        """Test that audit_merge handles multiple merge keys."""
        left_df = pd.DataFrame({
            'key1': [1, 2, 3],
            'key2': ['a', 'b', 'c'],
            'value': [10, 20, 30],
        })
        right_df = pd.DataFrame({
            'key1': [2, 3, 4],
            'key2': ['b', 'c', 'd'],
            'value': [100, 200, 300],
        })
        
        debug_dir = str(tmp_path / "test_debug")
        audit_merge(left_df, right_df, on=['key1', 'key2'], 
                   merge_name="multi_key_test", debug_dir=debug_dir)
        
        log_file = Path(debug_dir) / "merge_audit_log.txt"
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            content = f.read()
            assert "key1, key2" in content
