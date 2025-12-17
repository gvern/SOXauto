#!/usr/bin/env python3
"""
Demonstration script for debug_probe.py usage.

This script shows how to use the debug_probe module to instrument
your data processing pipeline.
"""

import sys
import os
from pathlib import Path

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pandas as pd
from src.core.debug_probe import probe_df

def main():
    """Demonstrate debug_probe usage."""
    print("=" * 70)
    print("Debug Probe Demonstration")
    print("=" * 70)
    
    # Create sample data simulating a reconciliation pipeline
    print("\n1. Creating sample data...")
    df_transactions = pd.DataFrame({
        "customer_id": [1, 1, 2, 3, 3, 3, 4, 5],
        "transaction_id": [101, 102, 103, 104, 105, 106, 107, 108],
        "amount": [100.50, 200.75, -50.00, 300.25, 150.00, 75.50, -25.00, 500.00],
        "posting_date": [
            "2024-01-15", "2024-02-20", "2024-03-10", 
            "2024-06-15", "2024-09-01", "2024-12-31",
            "2024-11-15", "2024-12-25"
        ],
        "status": [
            "completed", "completed", "refund", "completed", 
            "completed", "pending", "refund", "completed"
        ]
    })
    
    print(f"   Created {len(df_transactions)} transactions")
    
    # Set up output directory
    out_dir = Path("/tmp/probe_demo")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n2. Output directory: {out_dir}")
    
    # Probe 1: Initial data load
    print("\n3. Probe 1: After data load (basic stats)")
    probe1 = probe_df(df_transactions, "01_initial_load", out_dir)
    print(f"   Rows: {probe1.rows}")
    print(f"   Columns: {probe1.cols}")
    print(f"   Nulls: {probe1.nulls_total}")
    print(f"   Duplicates: {probe1.duplicated_rows}")
    
    # Probe 2: With amount tracking
    print("\n4. Probe 2: After data load (with amount tracking)")
    probe2 = probe_df(
        df_transactions, 
        "02_load_with_amounts", 
        out_dir,
        amount_col="amount"
    )
    print(f"   Total amount: {probe2.amount_sum:.2f}")
    
    # Filter to completed transactions only
    print("\n5. Filtering to completed transactions only...")
    df_completed = df_transactions[df_transactions["status"] == "completed"].copy()
    
    # Probe 3: After filtering with all features
    print("\n6. Probe 3: After filtering (full probe)")
    probe3 = probe_df(
        df_completed,
        "03_completed_only",
        out_dir,
        amount_col="amount",
        date_col="posting_date",
        key_cols=["customer_id", "transaction_id"],
        snapshot=True
    )
    print(f"   Rows: {probe3.rows}")
    print(f"   Total amount: {probe3.amount_sum:.2f}")
    print(f"   Date range: {probe3.min_date} to {probe3.max_date}")
    print(f"   Unique customers: {probe3.unique_keys['customer_id']}")
    print(f"   Unique transactions: {probe3.unique_keys['transaction_id']}")
    
    # Add some nulls for demonstration
    print("\n7. Creating data with nulls...")
    df_with_nulls = df_transactions.copy()
    df_with_nulls.loc[2, "amount"] = None
    df_with_nulls.loc[5, "customer_id"] = None
    
    # Probe 4: Data quality check
    print("\n8. Probe 4: Data quality check")
    probe4 = probe_df(
        df_with_nulls,
        "04_quality_check",
        out_dir,
        amount_col="amount",
        key_cols=["customer_id"]
    )
    print(f"   Nulls found: {probe4.nulls_total}")
    print(f"   Amount sum (nulls ignored): {probe4.amount_sum:.2f}")
    
    # Show log file contents
    print("\n9. Checking probes.log file...")
    log_file = out_dir / "probes.log"
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
        print(f"   Log file has {len(lines)} entries")
        
        # Show the last entry
        if lines:
            import json
            last_entry = json.loads(lines[-1])
            print(f"   Last probe: {last_entry['probe']['name']}")
            print(f"   Timestamp: {last_entry['timestamp']}")
    
    # Show snapshot files
    print("\n10. Checking snapshot files...")
    snapshot_files = list(out_dir.glob("snapshot_*.csv"))
    print(f"   Found {len(snapshot_files)} snapshot(s)")
    for snapshot in snapshot_files:
        print(f"   - {snapshot.name}")
    
    print("\n" + "=" * 70)
    print("Demonstration complete!")
    print(f"All output saved to: {out_dir}")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
