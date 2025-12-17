"""
Debug probe utility for pipeline instrumentation.

This module provides lightweight utilities to log statistics (rows, sums, nulls) 
and snapshot data at various steps of the reconciliation pipeline without 
refactoring the entire codebase.

Usage:
    from src.core.debug_probe import probe_df
    
    # Basic usage
    probe = probe_df(df, "after_merge", "/tmp/probes")
    
    # With amount tracking
    probe = probe_df(df, "balance_check", "/tmp/probes", 
                     amount_col="amount", snapshot=True)
    
    # With date range and key columns
    probe = probe_df(df, "final_output", "/tmp/probes",
                     amount_col="total", date_col="posting_date",
                     key_cols=["customer_no", "document_no"])
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd
import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DFProbe:
    """
    Dataclass representing DataFrame probe statistics.
    
    Attributes:
        name: Name/identifier for this probe point
        rows: Number of rows in the DataFrame
        cols: Number of columns in the DataFrame
        nulls_total: Total null values across all columns
        duplicated_rows: Number of duplicated rows
        amount_sum: Sum of amount column (if specified)
        amount_col: Name of the amount column (if specified)
        min_date: Minimum date value (if date_col specified)
        max_date: Maximum date value (if date_col specified)
        unique_keys: Dictionary of unique value counts for key columns
    """
    name: str
    rows: int
    cols: int
    nulls_total: int
    duplicated_rows: int
    amount_sum: float | None = None
    amount_col: str | None = None
    min_date: str | None = None
    max_date: str | None = None
    unique_keys: dict[str, int] | None = None


def probe_df(
    df: pd.DataFrame,
    name: str,
    out_dir: str | Path,
    *,
    amount_col: str | None = None,
    date_col: str | None = None,
    key_cols: list[str] | None = None,
    snapshot: bool = False,
    snapshot_cols: list[str] | None = None,
) -> DFProbe:
    """
    Probe a DataFrame and collect statistics for pipeline instrumentation.
    
    This function collects comprehensive statistics about a DataFrame at a specific
    point in the pipeline, logs them to a file, and optionally saves a CSV snapshot.
    
    Args:
        df: The DataFrame to probe
        name: Identifier for this probe point (e.g., "after_merge", "final_output")
        out_dir: Directory path where logs and snapshots will be saved
        amount_col: Optional column name for amount/value summation
        date_col: Optional column name for date range calculation
        key_cols: Optional list of column names to count unique values
        snapshot: If True, save a CSV snapshot of the DataFrame
        snapshot_cols: Optional list of columns to include in snapshot (None = all)
        
    Returns:
        DFProbe: A dataclass containing all collected statistics

    Notes:
        If any of ``amount_col``, ``date_col``, ``key_cols``, or ``snapshot_cols``
        refer to columns that are not present in ``df``, those metrics are skipped
        and a warning is logged. No exception is raised for missing columns.
    Example:
        >>> import pandas as pd
        >>> from src.core.debug_probe import probe_df
        >>> df = pd.DataFrame({"id": [1, 2, 3], "amount": [100, 200, 300]})
        >>> probe = probe_df(df, "test", "/tmp/probes", amount_col="amount")
        >>> probe.amount_sum
        600.0
    """
    # Ensure output directory exists
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Collect basic statistics
    rows = len(df)
    cols = len(df.columns)
    nulls_total = int(df.isnull().sum().sum())
    duplicated_rows = int(df.duplicated().sum())
    
    # Initialize optional fields
    amount_sum = None
    min_date = None
    max_date = None
    unique_keys = None
    
    # Handle amount column
    if amount_col is not None:
        if amount_col not in df.columns:
            logger.warning(
                f"Amount column '{amount_col}' not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )
        else:
            try:
                amount_sum = float(df[amount_col].sum())
            except (TypeError, ValueError) as e:
                logger.warning(
                    f"Could not sum column '{amount_col}': {e}. "
                    f"Column dtype: {df[amount_col].dtype}"
                )
    
    # Handle date column
    if date_col is not None:
        if date_col not in df.columns:
            logger.warning(
                f"Date column '{date_col}' not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )
        else:
            try:
                # Try to convert to datetime if not already
                date_series = pd.to_datetime(df[date_col], errors='coerce')
                non_null_dates = date_series.dropna()
                
                if len(non_null_dates) > 0:
                    min_date = non_null_dates.min().strftime('%Y-%m-%d')
                    max_date = non_null_dates.max().strftime('%Y-%m-%d')
                else:
                    logger.warning(
                        f"Date column '{date_col}' contains no valid dates"
                    )
            except Exception as e:
                logger.warning(
                    f"Could not process date column '{date_col}': {e}"
                )
    
    # Handle key columns
    if key_cols is not None:
        unique_keys = {}
        for key_col in key_cols:
            if key_col not in df.columns:
                logger.warning(
                    f"Key column '{key_col}' not found in DataFrame. "
                    f"Available columns: {list(df.columns)}"
                )
            else:
                try:
                    unique_keys[key_col] = int(df[key_col].nunique())
                except Exception as e:
                    logger.warning(
                        f"Could not count unique values in '{key_col}': {e}"
                    )
        
        # Only keep unique_keys if we successfully processed at least one column
        if not unique_keys:
            unique_keys = None
    
    # Create probe dataclass
    probe = DFProbe(
        name=name,
        rows=rows,
        cols=cols,
        nulls_total=nulls_total,
        duplicated_rows=duplicated_rows,
        amount_sum=amount_sum,
        amount_col=amount_col,
        min_date=min_date,
        max_date=max_date,
        unique_keys=unique_keys,
    )
    
    # Log to probes.log file in JSON-like format
    log_file = out_path / "probes.log"
    try:
        log_entry = {
            "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            "probe": asdict(probe),
        }
        
        # Append to log file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, indent=None) + '\n')
        
        logger.debug(f"Probe '{name}' logged to {log_file}")
    except Exception as e:
        logger.error(f"Failed to write probe log to {log_file}: {e}")
    
    # Save CSV snapshot if requested
    if snapshot:
        try:
            # Use snapshot_cols if provided, otherwise use all columns
            df_to_save = df[snapshot_cols] if snapshot_cols is not None else df
            
            # Validate snapshot_cols exist
            if snapshot_cols is not None:
                missing_cols = set(snapshot_cols) - set(df.columns)
                if missing_cols:
                    logger.warning(
                        f"Snapshot columns {missing_cols} not found in DataFrame. "
                        f"Saving with available columns only."
                    )
                    available_cols = [col for col in snapshot_cols if col in df.columns]
                    df_to_save = df[available_cols] if available_cols else df
            
            # Create snapshot filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            snapshot_file = out_path / f"snapshot_{name}_{timestamp}.csv"
            
            df_to_save.to_csv(snapshot_file, index=False)
            logger.debug(f"Snapshot saved to {snapshot_file}")
        except Exception as e:
            logger.error(f"Failed to save snapshot for probe '{name}': {e}")
    
    return probe
