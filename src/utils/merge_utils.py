"""
Merge utilities for detecting Cartesian products and other merge anomalies.

This module provides tools to audit DataFrame merges before they happen,
helping prevent "exploding joins" (many-to-many relationships) that can
duplicate amount lines and cause financial discrepancies.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Union, List
import pandas as pd


def audit_merge(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: Union[str, List[str]],
    name: str,
    out_dir: Union[str, Path],
) -> dict:
    """
    Audit a DataFrame merge operation to detect potential Cartesian products.
    
    This function counts duplicates on the join keys in both left and right
    dataframes before performing the merge. If duplicates are found, it exports
    the problematic keys to CSV files for inspection.
    
    Args:
        left: Left DataFrame for the merge
        right: Right DataFrame for the merge
        on: Column name(s) to join on. Can be a single string or list of strings
        name: Name identifier for this merge operation (used in log messages and file names)
        out_dir: Directory path where audit outputs will be saved
        
    Returns:
        dict: Audit results containing:
            - left_duplicates: Number of duplicate keys in left DataFrame
            - right_duplicates: Number of duplicate keys in right DataFrame
            - left_duplicates: Number of duplicate key occurrences in the left DataFrame
            - right_duplicates: Number of duplicate key occurrences in the right DataFrame
            - left_total_rows: Total rows in the left DataFrame
            - right_total_rows: Total rows in the right DataFrame
            - has_duplicates: Boolean indicating if any duplicates were found in either DataFrame
            - left_unique_dup_keys: Number of distinct join-key combinations that are duplicated in the left DataFrame
            - right_unique_dup_keys: Number of distinct join-key combinations that are duplicated in the right DataFrame
            - left_dup_keys_file: Optional path (as str or Path) to a CSV file with duplicated join keys from the left DataFrame;
              present only when left-side duplicates are found and export succeeds
            - right_dup_keys_file: Optional path (as str or Path) to a CSV file with duplicated join keys from the right DataFrame;
              present only when right-side duplicates are found and export succeeds
            - left_duplicates_path: Optional path to CSV with left duplicate keys (or None)
            - right_duplicates_path: Optional path to CSV with right duplicate keys (or None)

    Example:
        >>> left_df = pd.DataFrame({'id': [1, 1, 2], 'value': [10, 20, 30]})
        >>> right_df = pd.DataFrame({'id': [1, 2, 2], 'amount': [100, 200, 300]})
        >>> audit_merge(left_df, right_df, on='id', name='test_merge', out_dir='./output')
        {
        ...     'left_duplicates': 1,
        ...     'right_duplicates': 1,
        ...     'left_total_rows': 3,
        ...     'right_total_rows': 3,
        ...     'left_unique_dup_keys': 1,
        ...     'right_unique_dup_keys': 1,
        ...     'has_duplicates': True,
        ...     'left_duplicates_path': '<out_dir>/test_merge_left_duplicates.csv',
        ...     'right_duplicates_path': '<out_dir>/test_merge_right_duplicates.csv',
        ... }
    """
    # Convert on to list if it's a single string
    if isinstance(on, str):
        on = [on]
    
    # Ensure out_dir is a Path object
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up logging to both file and console
    log_file = out_dir / "merge_audit.log"
    logger = logging.getLogger("merge_audit")
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Log the start of the audit
    logger.info(f"=== Merge Audit: {name} ===")
    logger.info(f"Join keys: {on}")
    logger.info(f"Left DataFrame shape: {left.shape}")
    logger.info(f"Right DataFrame shape: {right.shape}")
    
    # Validate that join columns exist
    missing_left = [col for col in on if col not in left.columns]
    missing_right = [col for col in on if col not in right.columns]
    
    if missing_left:
        logger.error(f"Missing columns in left DataFrame: {missing_left}")
        raise ValueError(f"Missing columns in left DataFrame: {missing_left}")
    
    if missing_right:
        logger.error(f"Missing columns in right DataFrame: {missing_right}")
        raise ValueError(f"Missing columns in right DataFrame: {missing_right}")
    
    # Count duplicates on join keys in left DataFrame
    left_dup_mask = left.duplicated(subset=on, keep=False)
    left_duplicates = left_dup_mask.sum()
    left_unique_dup_keys = left[left_dup_mask][on].drop_duplicates().shape[0]
    
    # Count duplicates on join keys in right DataFrame
    right_dup_mask = right.duplicated(subset=on, keep=False)
    right_duplicates = right_dup_mask.sum()
    right_unique_dup_keys = right[right_dup_mask][on].drop_duplicates().shape[0]
    
    # Log the statistics
    logger.info(f"Left DataFrame: {left_duplicates} duplicate rows across {left_unique_dup_keys} unique keys")
    logger.info(f"Right DataFrame: {right_duplicates} duplicate rows across {right_unique_dup_keys} unique keys")
    
    # Prepare audit results
    audit_results = {
        'left_duplicates': int(left_duplicates),
        'right_duplicates': int(right_duplicates),
        'left_total_rows': len(left),
        'right_total_rows': len(right),
        'left_unique_dup_keys': int(left_unique_dup_keys),
        'right_unique_dup_keys': int(right_unique_dup_keys),
        'has_duplicates': left_duplicates > 0 or right_duplicates > 0,
    }
    
    # If duplicates found, export problematic keys to CSV
    if left_duplicates > 0:
        left_dup_keys_file = out_dir / f"{name}.left_dup_keys.csv"
        left_dup_rows = left[left_dup_mask].copy()
        left_dup_rows.to_csv(left_dup_keys_file, index=False)
        logger.warning(f"⚠️  Left duplicates found! Exported to: {left_dup_keys_file}")
        audit_results['left_dup_keys_file'] = str(left_dup_keys_file)
    
    if right_duplicates > 0:
        right_dup_keys_file = out_dir / f"{name}.right_dup_keys.csv"
        right_dup_rows = right[right_dup_mask].copy()
        right_dup_rows.to_csv(right_dup_keys_file, index=False)
        logger.warning(f"⚠️  Right duplicates found! Exported to: {right_dup_keys_file}")
        audit_results['right_dup_keys_file'] = str(right_dup_keys_file)
    
    # Estimate potential explosion factor
    if left_duplicates > 0 and right_duplicates > 0:
        # Calculate worst-case scenario: if both sides have duplicates on overlapping keys
        # This is a rough estimate of potential Cartesian product
        logger.warning(
            f"⚠️  CARTESIAN PRODUCT RISK: Both sides have duplicates on join keys!"
        )
        logger.warning(
            f"    Potential merge explosion if keys overlap."
        )
    
    if audit_results['has_duplicates']:
        logger.warning(f"✗ Merge audit FAILED: Duplicates detected")
    else:
        logger.info(f"✓ Merge audit PASSED: No duplicates on join keys")
    
    logger.info(f"=== End Merge Audit: {name} ===\n")
    
    return audit_results
