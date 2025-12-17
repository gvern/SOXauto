"""
Tests for the debug_probe module.

Run with: pytest tests/test_debug_probe.py -v
"""

import os
import sys
import json
import pandas as pd
import pytest
from pathlib import Path

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.core.debug_probe import DFProbe, probe_df


# =======================
# DFProbe Dataclass Tests
# =======================

def test_dfprobe_basic_instantiation():
    """Test DFProbe can be instantiated with basic fields."""
    probe = DFProbe(
        name="test_probe",
        rows=100,
        cols=5,
        nulls_total=10,
        duplicated_rows=2
    )
    
    assert probe.name == "test_probe"
    assert probe.rows == 100
    assert probe.cols == 5
    assert probe.nulls_total == 10
    assert probe.duplicated_rows == 2
    assert probe.amount_sum is None
    assert probe.amount_col is None
    assert probe.min_date is None
    assert probe.max_date is None
    assert probe.unique_keys is None


def test_dfprobe_full_instantiation():
    """Test DFProbe with all optional fields."""
    probe = DFProbe(
        name="full_probe",
        rows=50,
        cols=3,
        nulls_total=5,
        duplicated_rows=1,
        amount_sum=1500.50,
        amount_col="amount",
        min_date="2024-01-01",
        max_date="2024-12-31",
        unique_keys={"customer_id": 25, "order_id": 50}
    )
    
    assert probe.amount_sum == 1500.50
    assert probe.amount_col == "amount"
    assert probe.min_date == "2024-01-01"
    assert probe.max_date == "2024-12-31"
    assert probe.unique_keys == {"customer_id": 25, "order_id": 50}


# =======================
# probe_df Basic Tests
# =======================

def test_probe_df_basic(tmp_path):
    """Test basic probe_df functionality."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "value": [10, 20, 30, 40, 50]
    })
    
    probe = probe_df(df, "test_basic", tmp_path)
    
    assert probe.name == "test_basic"
    assert probe.rows == 5
    assert probe.cols == 2
    assert probe.nulls_total == 0
    assert probe.duplicated_rows == 0


def test_probe_df_with_nulls(tmp_path):
    """Test probe_df correctly counts null values."""
    df = pd.DataFrame({
        "id": [1, 2, None, 4, 5],
        "value": [10, None, 30, None, 50],
        "name": ["A", "B", "C", None, "E"]
    })
    
    probe = probe_df(df, "test_nulls", tmp_path)
    
    assert probe.rows == 5
    assert probe.cols == 3
    assert probe.nulls_total == 4  # 1 + 2 + 1


def test_probe_df_with_duplicates(tmp_path):
    """Test probe_df correctly counts duplicated rows."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 2, 3],
        "value": [10, 20, 30, 20, 30]
    })
    
    probe = probe_df(df, "test_duplicates", tmp_path)
    
    assert probe.duplicated_rows == 2


def test_probe_df_empty_dataframe(tmp_path):
    """Test probe_df handles empty DataFrames."""
    df = pd.DataFrame()
    
    probe = probe_df(df, "test_empty", tmp_path)
    
    assert probe.rows == 0
    assert probe.cols == 0
    assert probe.nulls_total == 0
    assert probe.duplicated_rows == 0


# =======================
# probe_df Amount Column Tests
# =======================

def test_probe_df_with_amount_col(tmp_path):
    """Test probe_df with amount column."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "amount": [100.50, 200.75, 300.25]
    })
    
    probe = probe_df(df, "test_amount", tmp_path, amount_col="amount")
    
    assert probe.amount_col == "amount"
    assert probe.amount_sum == pytest.approx(601.50)


def test_probe_df_amount_col_with_nulls(tmp_path):
    """Test probe_df amount calculation with null values."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "amount": [100.0, None, 200.0, 50.0]
    })
    
    probe = probe_df(df, "test_amount_nulls", tmp_path, amount_col="amount")
    
    # pandas.sum() ignores NaN values by default
    assert probe.amount_sum == pytest.approx(350.0)


def test_probe_df_amount_col_missing(tmp_path):
    """Test probe_df handles missing amount column gracefully."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "value": [100, 200, 300]
    })
    
    probe = probe_df(df, "test_missing_amount", tmp_path, amount_col="amount")
    
    # Should not raise error, just log warning
    assert probe.amount_col == "amount"
    assert probe.amount_sum is None


def test_probe_df_amount_col_non_numeric(tmp_path):
    """Test probe_df handles non-numeric amount column."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "amount": ["A", "B", "C"]
    })
    
    probe = probe_df(df, "test_non_numeric_amount", tmp_path, amount_col="amount")
    
    # Should not raise error, just log warning
    assert probe.amount_col == "amount"
    assert probe.amount_sum is None


# =======================
# probe_df Date Column Tests
# =======================

def test_probe_df_with_date_col(tmp_path):
    """Test probe_df with date column."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "posting_date": ["2024-01-15", "2024-06-20", "2024-12-31"]
    })
    
    probe = probe_df(df, "test_dates", tmp_path, date_col="posting_date")
    
    assert probe.min_date == "2024-01-15"
    assert probe.max_date == "2024-12-31"


def test_probe_df_date_col_with_datetime(tmp_path):
    """Test probe_df with datetime objects."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "posting_date": pd.to_datetime(["2024-01-15", "2024-06-20", "2024-12-31"])
    })
    
    probe = probe_df(df, "test_datetime", tmp_path, date_col="posting_date")
    
    assert probe.min_date == "2024-01-15"
    assert probe.max_date == "2024-12-31"


def test_probe_df_date_col_with_nulls(tmp_path):
    """Test probe_df date calculation with null values."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "posting_date": ["2024-01-01", None, "2024-12-31", None]
    })
    
    probe = probe_df(df, "test_date_nulls", tmp_path, date_col="posting_date")
    
    assert probe.min_date == "2024-01-01"
    assert probe.max_date == "2024-12-31"


def test_probe_df_date_col_missing(tmp_path):
    """Test probe_df handles missing date column gracefully."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "value": [100, 200, 300]
    })
    
    probe = probe_df(df, "test_missing_date", tmp_path, date_col="posting_date")
    
    # Should not raise error, just log warning
    assert probe.min_date is None
    assert probe.max_date is None


def test_probe_df_date_col_invalid_dates(tmp_path):
    """Test probe_df handles invalid dates gracefully."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "posting_date": ["not-a-date", "invalid", "2024-12-31"]
    })
    
    probe = probe_df(df, "test_invalid_dates", tmp_path, date_col="posting_date")
    
    # Should process the valid date
    assert probe.min_date == "2024-12-31"
    assert probe.max_date == "2024-12-31"


# =======================
# probe_df Key Columns Tests
# =======================

def test_probe_df_with_key_cols(tmp_path):
    """Test probe_df with key columns."""
    df = pd.DataFrame({
        "customer_id": [1, 1, 2, 3, 3],
        "order_id": [101, 102, 103, 104, 105],
        "value": [100, 200, 300, 400, 500]
    })
    
    probe = probe_df(
        df, "test_keys", tmp_path, 
        key_cols=["customer_id", "order_id"]
    )
    
    assert probe.unique_keys is not None
    assert probe.unique_keys["customer_id"] == 3
    assert probe.unique_keys["order_id"] == 5


def test_probe_df_key_cols_missing(tmp_path):
    """Test probe_df handles missing key columns gracefully."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "value": [100, 200, 300]
    })
    
    probe = probe_df(
        df, "test_missing_keys", tmp_path, 
        key_cols=["customer_id", "order_id"]
    )
    
    # Should not raise error, just log warnings
    assert probe.unique_keys is None


def test_probe_df_key_cols_partial_missing(tmp_path):
    """Test probe_df with some key columns missing."""
    df = pd.DataFrame({
        "customer_id": [1, 1, 2, 3],
        "value": [100, 200, 300, 400]
    })
    
    probe = probe_df(
        df, "test_partial_keys", tmp_path, 
        key_cols=["customer_id", "order_id"]
    )
    
    # Should process the available column
    assert probe.unique_keys is not None
    assert probe.unique_keys["customer_id"] == 3


# =======================
# probe_df Directory Creation Tests
# =======================

def test_probe_df_creates_directory(tmp_path):
    """Test probe_df creates output directory if it doesn't exist."""
    out_dir = tmp_path / "nested" / "path" / "probes"
    
    df = pd.DataFrame({"id": [1, 2, 3]})
    probe_df(df, "test_dir", out_dir)
    
    assert out_dir.exists()
    assert out_dir.is_dir()


def test_probe_df_with_string_path(tmp_path):
    """Test probe_df works with string paths."""
    out_dir_str = str(tmp_path / "string_path")
    
    df = pd.DataFrame({"id": [1, 2, 3]})
    probe_df(df, "test_string", out_dir_str)
    
    assert Path(out_dir_str).exists()


# =======================
# probe_df Logging Tests
# =======================

def test_probe_df_creates_log_file(tmp_path):
    """Test probe_df creates probes.log file."""
    df = pd.DataFrame({"id": [1, 2, 3]})
    probe_df(df, "test_log", tmp_path)
    
    log_file = tmp_path / "probes.log"
    assert log_file.exists()


def test_probe_df_log_format(tmp_path):
    """Test probe_df log file has correct JSON format."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "amount": [100, 200, 300]
    })
    probe_df(df, "test_format", tmp_path, amount_col="amount")
    
    log_file = tmp_path / "probes.log"
    
    with open(log_file, 'r') as f:
        log_line = f.readline()
    
    log_entry = json.loads(log_line)
    
    assert "timestamp" in log_entry
    assert "probe" in log_entry
    assert log_entry["probe"]["name"] == "test_format"
    assert log_entry["probe"]["rows"] == 3
    assert log_entry["probe"]["amount_sum"] == pytest.approx(600.0)


def test_probe_df_appends_to_log(tmp_path):
    """Test probe_df appends to existing log file."""
    df1 = pd.DataFrame({"id": [1, 2]})
    df2 = pd.DataFrame({"id": [3, 4, 5]})
    
    probe_df(df1, "probe1", tmp_path)
    probe_df(df2, "probe2", tmp_path)
    
    log_file = tmp_path / "probes.log"
    
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    assert len(lines) == 2
    
    entry1 = json.loads(lines[0])
    entry2 = json.loads(lines[1])
    
    assert entry1["probe"]["name"] == "probe1"
    assert entry1["probe"]["rows"] == 2
    assert entry2["probe"]["name"] == "probe2"
    assert entry2["probe"]["rows"] == 3


# =======================
# probe_df Snapshot Tests
# =======================

def test_probe_df_snapshot_basic(tmp_path):
    """Test probe_df creates CSV snapshot."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "value": [100, 200, 300]
    })
    
    probe_df(df, "test_snapshot", tmp_path, snapshot=True)
    
    # Check if snapshot file was created
    snapshot_files = list(tmp_path.glob("snapshot_test_snapshot_*.csv"))
    assert len(snapshot_files) == 1
    
    # Verify snapshot content
    snapshot_df = pd.read_csv(snapshot_files[0])
    assert len(snapshot_df) == 3
    assert list(snapshot_df.columns) == ["id", "value"]


def test_probe_df_snapshot_with_cols(tmp_path):
    """Test probe_df snapshot with specific columns."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "value": [100, 200, 300],
        "name": ["A", "B", "C"]
    })
    
    probe_df(
        df, "test_snapshot_cols", tmp_path, 
        snapshot=True, 
        snapshot_cols=["id", "value"]
    )
    
    snapshot_files = list(tmp_path.glob("snapshot_test_snapshot_cols_*.csv"))
    assert len(snapshot_files) == 1
    
    snapshot_df = pd.read_csv(snapshot_files[0])
    assert list(snapshot_df.columns) == ["id", "value"]


def test_probe_df_snapshot_missing_cols(tmp_path):
    """Test probe_df snapshot handles missing columns gracefully."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "value": [100, 200, 300]
    })
    
    # Request columns that don't exist
    probe_df(
        df, "test_snapshot_missing", tmp_path, 
        snapshot=True, 
        snapshot_cols=["id", "missing_col"]
    )
    
    # Should create snapshot with available columns
    snapshot_files = list(tmp_path.glob("snapshot_test_snapshot_missing_*.csv"))
    assert len(snapshot_files) == 1
    
    snapshot_df = pd.read_csv(snapshot_files[0])
    assert "id" in snapshot_df.columns


def test_probe_df_no_snapshot_by_default(tmp_path):
    """Test probe_df doesn't create snapshot by default."""
    df = pd.DataFrame({"id": [1, 2, 3]})
    probe_df(df, "test_no_snapshot", tmp_path)
    
    snapshot_files = list(tmp_path.glob("snapshot_*.csv"))
    assert len(snapshot_files) == 0


# =======================
# Integration Tests
# =======================

def test_probe_df_complete_workflow(tmp_path):
    """Test complete probe_df workflow with all features."""
    df = pd.DataFrame({
        "customer_id": [1, 1, 2, 3, 3, 3],
        "order_id": [101, 102, 103, 104, 105, 106],
        "amount": [100.50, 200.75, None, 300.25, 150.00, 75.50],
        "posting_date": ["2024-01-15", "2024-02-20", "2024-03-10", 
                         "2024-06-15", "2024-09-01", "2024-12-31"],
        "status": ["completed", "completed", "pending", "completed", 
                   "completed", "pending"]
    })
    
    probe = probe_df(
        df, "complete_test", tmp_path,
        amount_col="amount",
        date_col="posting_date",
        key_cols=["customer_id", "order_id"],
        snapshot=True,
        snapshot_cols=["customer_id", "order_id", "amount"]
    )
    
    # Verify probe data
    assert probe.name == "complete_test"
    assert probe.rows == 6
    assert probe.cols == 5
    assert probe.nulls_total == 1  # One None in amount
    # Business rule: null amounts are excluded from the sum (not treated as zero).
    assert probe.amount_sum == pytest.approx(826.00)
    assert probe.min_date == "2024-01-15"
    assert probe.max_date == "2024-12-31"
    assert probe.unique_keys["customer_id"] == 3
    assert probe.unique_keys["order_id"] == 6
    
    # Verify log file
    log_file = tmp_path / "probes.log"
    assert log_file.exists()
    
    # Verify snapshot
    snapshot_files = list(tmp_path.glob("snapshot_complete_test_*.csv"))
    assert len(snapshot_files) == 1
    snapshot_df = pd.read_csv(snapshot_files[0])
    assert len(snapshot_df) == 6
    assert set(snapshot_df.columns) == {"customer_id", "order_id", "amount"}


def test_probe_df_handles_nan_and_infinity(tmp_path):
    """Test probe_df handles NaN and Infinity values in financial data."""
    import numpy as np
    
    # Create DataFrame with NaN and Infinity values
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "amount": [100.0, float('nan'), float('inf'), float('-inf'), 200.0]
    })
    
    probe = probe_df(df, "test_nan_inf", tmp_path, amount_col="amount")
    
    # The sum of [100, nan, inf, -inf, 200] should result in nan or inf
    # Verify probe was created (exact value depends on pandas behavior)
    assert probe.name == "test_nan_inf"
    assert probe.rows == 5
    
    # Verify log file was created and can be read
    log_file = tmp_path / "probes.log"
    assert log_file.exists()
    
    # Verify the log entry can be parsed as JSON (no serialization errors)
    with open(log_file, 'r') as f:
        log_line = f.readline()
    
    # This should not raise an error even with NaN/Inf values
    log_entry = json.loads(log_line)
    
    assert "timestamp" in log_entry
    assert "probe" in log_entry
    assert log_entry["probe"]["name"] == "test_nan_inf"
    
    # NaN and Infinity should be converted to None for JSON serialization
    # (the exact behavior depends on how pandas.sum() handles these values)
    amount_sum_logged = log_entry["probe"]["amount_sum"]
    # Should be None (converted from NaN/Inf) or a valid number
    assert amount_sum_logged is None or isinstance(amount_sum_logged, (int, float))


def test_probe_df_handles_decimal_types(tmp_path):
    """Test probe_df handles Decimal types in financial data."""
    from decimal import Decimal
    
    # Create DataFrame with Decimal values (common in financial datasets)
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "amount": [Decimal("100.50"), Decimal("200.75"), Decimal("300.25")]
    })
    
    probe = probe_df(df, "test_decimal", tmp_path, amount_col="amount")
    
    # Verify probe was created
    assert probe.name == "test_decimal"
    assert probe.rows == 3
    
    # Verify log file was created and can be read
    log_file = tmp_path / "probes.log"
    assert log_file.exists()
    
    # Verify the log entry can be parsed as JSON (no serialization errors)
    with open(log_file, 'r') as f:
        log_line = f.readline()
    
    # This should not raise an error even with Decimal values
    log_entry = json.loads(log_line)
    
    assert "timestamp" in log_entry
    assert "probe" in log_entry
    assert log_entry["probe"]["name"] == "test_decimal"
    
    # Decimal values should be converted to float for JSON serialization
    amount_sum_logged = log_entry["probe"]["amount_sum"]
    assert isinstance(amount_sum_logged, (int, float))


def test_probe_df_snapshot_max_rows(tmp_path):
    """Test probe_df limits snapshot rows to prevent massive disk writes."""
    # Create a large DataFrame
    df = pd.DataFrame({
        "id": range(15000),
        "value": range(15000)
    })
    
    # Default max_rows is 10000
    probe_df(df, "test_large", tmp_path, snapshot=True)
    
    # Verify snapshot was created with limited rows
    snapshot_files = list(tmp_path.glob("snapshot_test_large_*.csv"))
    assert len(snapshot_files) == 1
    
    snapshot_df = pd.read_csv(snapshot_files[0])
    assert len(snapshot_df) == 10000  # Default limit
    
    # Test with custom max_rows
    probe_df(df, "test_custom", tmp_path, snapshot=True, snapshot_max_rows=5000)
    
    snapshot_files = list(tmp_path.glob("snapshot_test_custom_*.csv"))
    assert len(snapshot_files) == 1
    
    snapshot_df = pd.read_csv(snapshot_files[0])
    assert len(snapshot_df) == 5000  # Custom limit


def test_probe_df_snapshot_small_dataframe(tmp_path):
    """Test probe_df doesn't limit snapshot for small DataFrames."""
    # Create a small DataFrame
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "value": [100, 200, 300]
    })
    
    # Should save all rows since it's under the limit
    probe_df(df, "test_small", tmp_path, snapshot=True, snapshot_max_rows=10000)
    
    snapshot_files = list(tmp_path.glob("snapshot_test_small_*.csv"))
    assert len(snapshot_files) == 1
    
    snapshot_df = pd.read_csv(snapshot_files[0])
    assert len(snapshot_df) == 3  # All rows saved
