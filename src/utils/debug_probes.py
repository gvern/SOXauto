"""
Debug Probe Utilities for Reconciliation Data Flow Tracing

This module provides lightweight debugging tools to trace data flow through
the reconciliation engine. These probes are designed to be inserted at key
checkpoints to understand data transformations during the "September NG" run.

Usage:
    from src.utils.debug_probes import probe_df, audit_merge
    
    # Probe a DataFrame at a checkpoint
    probe_df(df, "NAV_raw_load", debug_dir="outputs/_debug_sep2025_ng")
    
    # Audit a merge operation
    audit_merge(left_df, right_df, on=['key_col'], 
                merge_name="JDash_IPE_timing", 
                debug_dir="outputs/_debug_sep2025_ng")
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, List


def probe_df(
    df: pd.DataFrame,
    checkpoint_name: str,
    debug_dir: str = "outputs/_debug_sep2025_ng",
    metrics: Optional[List[str]] = None,
) -> None:
    """
    Probe a DataFrame at a specific checkpoint in the reconciliation flow.
    
    Captures key metrics and writes them to a debug log file. This is a 
    lightweight inspection tool that doesn't modify the DataFrame.
    
    Args:
        df: The DataFrame to inspect
        checkpoint_name: Descriptive name for this checkpoint (e.g., "NAV_raw_load")
        debug_dir: Directory to write debug logs (created if not exists)
        metrics: Optional list of column names to calculate sum/count for
    
    Example:
        >>> probe_df(nav_df, "NAV_raw_load", metrics=["Amount"])
        >>> probe_df(ipe08_df, "IPE08_scope_filtered", metrics=["TotalAmountUsed"])
    """
    # Create debug directory if it doesn't exist
    debug_path = Path(debug_dir)
    debug_path.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Build probe log entry
    log_entry = {
        'timestamp': timestamp,
        'checkpoint': checkpoint_name,
        'row_count': len(df),
        'column_count': len(df.columns),
        'columns': list(df.columns),
        'memory_mb': round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
    }
    
    # Add metric calculations if specified
    if metrics:
        log_entry['metrics'] = {}
        for metric_col in metrics:
            if metric_col in df.columns:
                # Calculate sum if numeric
                if pd.api.types.is_numeric_dtype(df[metric_col]):
                    log_entry['metrics'][f'{metric_col}_sum'] = float(df[metric_col].sum())
                    log_entry['metrics'][f'{metric_col}_mean'] = float(df[metric_col].mean())
                    log_entry['metrics'][f'{metric_col}_non_null_count'] = int(df[metric_col].notna().sum())
                else:
                    log_entry['metrics'][f'{metric_col}_unique_count'] = int(df[metric_col].nunique())
                    log_entry['metrics'][f'{metric_col}_non_null_count'] = int(df[metric_col].notna().sum())
    
    # Write to debug log file (append mode)
    log_file = debug_path / "probe_log.txt"
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"PROBE: {checkpoint_name}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Row Count: {log_entry['row_count']:,}\n")
        f.write(f"Column Count: {log_entry['column_count']}\n")
        f.write(f"Columns: {', '.join(log_entry['columns'])}\n")
        f.write(f"Memory: {log_entry['memory_mb']} MB\n")
        
        if 'metrics' in log_entry:
            f.write("\nMetrics:\n")
            for metric_name, metric_value in log_entry['metrics'].items():
                if isinstance(metric_value, float):
                    f.write(f"  {metric_name}: {metric_value:,.2f}\n")
                else:
                    f.write(f"  {metric_name}: {metric_value:,}\n")
        
        f.write(f"{'='*80}\n")
    
    # Also save a sample of the DataFrame (first 100 rows)
    sample_file = debug_path / f"{checkpoint_name}_{timestamp}_sample.csv"
    df.head(100).to_csv(sample_file, index=False)
    
    print(f"[DEBUG PROBE] {checkpoint_name}: {len(df):,} rows | Logged to {log_file}")


def audit_merge(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    on: Union[str, List[str]],
    merge_name: str,
    debug_dir: str = "outputs/_debug_sep2025_ng",
    how: str = "inner",
) -> None:
    """
    Audit a merge operation before it happens.
    
    This function analyzes the keys used for merging and reports:
    - Key uniqueness on both sides
    - Expected match rate
    - Potential data loss from the merge
    
    Args:
        left_df: Left DataFrame for merge
        right_df: Right DataFrame for merge
        on: Column(s) to merge on
        merge_name: Descriptive name for this merge (e.g., "JDash_IPE_timing")
        debug_dir: Directory to write debug logs
        how: Type of merge ('inner', 'left', 'right', 'outer')
    
    Example:
        >>> audit_merge(jdash_df, ipe_df, on=['OrderId'], 
        ...             merge_name="Timing_Diff_Merge", how="inner")
    """
    # Create debug directory if it doesn't exist
    debug_path = Path(debug_dir)
    debug_path.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Normalize 'on' to a list
    merge_keys = [on] if isinstance(on, str) else on
    
    # Analyze key uniqueness
    audit_results = {
        'timestamp': timestamp,
        'merge_name': merge_name,
        'merge_type': how,
        'left_rows': len(left_df),
        'right_rows': len(right_df),
        'merge_keys': merge_keys,
    }
    
    # Check if all merge keys exist in both DataFrames
    missing_keys_left = [k for k in merge_keys if k not in left_df.columns]
    missing_keys_right = [k for k in merge_keys if k not in right_df.columns]
    
    if missing_keys_left or missing_keys_right:
        audit_results['error'] = {
            'missing_in_left': missing_keys_left,
            'missing_in_right': missing_keys_right,
        }
    else:
        # Analyze key uniqueness
        left_unique = left_df[merge_keys].drop_duplicates()
        right_unique = right_df[merge_keys].drop_duplicates()
        
        audit_results['left_unique_keys'] = len(left_unique)
        audit_results['right_unique_keys'] = len(right_unique)
        audit_results['left_duplicate_keys'] = len(left_df) - len(left_unique)
        audit_results['right_duplicate_keys'] = len(right_df) - len(right_unique)
        
        # Check for null values in merge keys
        left_nulls = left_df[merge_keys].isnull().any(axis=1).sum()
        right_nulls = right_df[merge_keys].isnull().any(axis=1).sum()
        
        audit_results['left_null_keys'] = left_nulls
        audit_results['right_null_keys'] = right_nulls
        
        # Estimate match rate (simplified - doesn't account for duplicates)
        # Find intersection of unique keys
        left_key_set = set(left_unique.apply(tuple, axis=1))
        right_key_set = set(right_unique.apply(tuple, axis=1))
        common_keys = left_key_set & right_key_set
        
        audit_results['matching_keys'] = len(common_keys)
        audit_results['left_only_keys'] = len(left_key_set - right_key_set)
        audit_results['right_only_keys'] = len(right_key_set - left_key_set)
        
        if len(left_unique) > 0:
            audit_results['left_match_rate'] = round(len(common_keys) / len(left_unique) * 100, 2)
        if len(right_unique) > 0:
            audit_results['right_match_rate'] = round(len(common_keys) / len(right_unique) * 100, 2)
    
    # Write to audit log file
    log_file = debug_path / "merge_audit_log.txt"
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"MERGE AUDIT: {merge_name}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Merge Type: {how}\n")
        f.write(f"Merge Keys: {', '.join(merge_keys)}\n")
        f.write(f"\nLeft DataFrame:\n")
        f.write(f"  Total Rows: {audit_results['left_rows']:,}\n")
        
        if 'error' not in audit_results:
            f.write(f"  Unique Keys: {audit_results['left_unique_keys']:,}\n")
            f.write(f"  Duplicate Keys: {audit_results['left_duplicate_keys']:,}\n")
            f.write(f"  Null Keys: {audit_results['left_null_keys']:,}\n")
            
            f.write(f"\nRight DataFrame:\n")
            f.write(f"  Total Rows: {audit_results['right_rows']:,}\n")
            f.write(f"  Unique Keys: {audit_results['right_unique_keys']:,}\n")
            f.write(f"  Duplicate Keys: {audit_results['right_duplicate_keys']:,}\n")
            f.write(f"  Null Keys: {audit_results['right_null_keys']:,}\n")
            
            f.write(f"\nMerge Analysis:\n")
            f.write(f"  Matching Keys: {audit_results['matching_keys']:,}\n")
            f.write(f"  Left-Only Keys: {audit_results['left_only_keys']:,}\n")
            f.write(f"  Right-Only Keys: {audit_results['right_only_keys']:,}\n")
            if 'left_match_rate' in audit_results:
                f.write(f"  Left Match Rate: {audit_results['left_match_rate']}%\n")
            if 'right_match_rate' in audit_results:
                f.write(f"  Right Match Rate: {audit_results['right_match_rate']}%\n")
        else:
            f.write(f"\nERROR: Missing merge keys!\n")
            f.write(f"  Missing in Left: {audit_results['error']['missing_in_left']}\n")
            f.write(f"  Missing in Right: {audit_results['error']['missing_in_right']}\n")
        
        f.write(f"{'='*80}\n")
    
    print(f"[MERGE AUDIT] {merge_name}: L={len(left_df):,} R={len(right_df):,} | "
          f"Keys={', '.join(merge_keys)} | Logged to {log_file}")


__all__ = ['probe_df', 'audit_merge']
