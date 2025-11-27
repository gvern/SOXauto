"""
Evidence Locator Module

Provides utilities for locating evidence packages (ZIP files) generated 
during IPE extractions.

This module is independent of Streamlit and returns standard Python types.
"""

import os
import glob
from typing import Optional


def get_latest_evidence_zip(item_id: str, evidence_root: Optional[str] = None) -> Optional[str]:
    """
    Finds the most recent ZIP evidence package generated for a given IPE item.
    
    This function searches the evidence directory for folders matching the item_id
    pattern and returns the path to the most recently created ZIP file.
    
    Args:
        item_id: The IPE or CR identifier (e.g., 'IPE_07', 'CR_03')
        evidence_root: Optional path to the evidence directory. If None, 
                       defaults to 'evidence/' relative to repository root.
    
    Returns:
        Full path to the most recent ZIP file, or None if no evidence found.
    
    Example:
        >>> zip_path = get_latest_evidence_zip('IPE_07')
        >>> if zip_path:
        ...     print(f"Found evidence: {zip_path}")
    """
    # Default evidence root relative to repository
    if evidence_root is None:
        # Navigate from this file's location to repo root
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        evidence_root = os.path.join(repo_root, "evidence")
    
    if not os.path.exists(evidence_root):
        return None
    
    # Search for folders starting with item_id
    candidates = []
    for folder_name in os.listdir(evidence_root):
        if folder_name.startswith(item_id):
            folder_path = os.path.join(evidence_root, folder_name)
            if os.path.isdir(folder_path):
                # Look for ZIP files inside the folder
                zip_files = glob.glob(os.path.join(folder_path, "*.zip"))
                if zip_files:
                    # Add (modification_time, zip_path) tuple
                    for zip_file in zip_files:
                        candidates.append((os.path.getmtime(zip_file), zip_file))
    
    if not candidates:
        return None
    
    # Sort by modification time (descending) and return the newest
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def find_evidence_packages(item_id: str, evidence_root: Optional[str] = None) -> list:
    """
    Find all evidence packages for a given IPE item.
    
    Args:
        item_id: The IPE or CR identifier (e.g., 'IPE_07', 'CR_03')
        evidence_root: Optional path to the evidence directory.
    
    Returns:
        List of tuples (modification_time, zip_path) sorted by time descending.
    """
    if evidence_root is None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        evidence_root = os.path.join(repo_root, "evidence")
    
    if not os.path.exists(evidence_root):
        return []
    
    candidates = []
    for folder_name in os.listdir(evidence_root):
        if folder_name.startswith(item_id):
            folder_path = os.path.join(evidence_root, folder_name)
            if os.path.isdir(folder_path):
                zip_files = glob.glob(os.path.join(folder_path, "*.zip"))
                for zip_file in zip_files:
                    candidates.append((os.path.getmtime(zip_file), zip_file))
    
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates


__all__ = [
    'get_latest_evidence_zip',
    'find_evidence_packages',
]
