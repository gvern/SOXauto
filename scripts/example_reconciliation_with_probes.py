"""
Example integration of debug_probe into existing reconciliation workflow.

This script demonstrates how to add debug probes to an existing
data processing pipeline without refactoring.
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


def simulate_reconciliation_workflow():
    """
    Simulate a typical reconciliation workflow with debug probes.
    
    This shows how to instrument an existing workflow without refactoring.
    """
    print("=" * 70)
    print("Reconciliation Workflow with Debug Probes")
    print("=" * 70)
    
    # Setup probe output directory
    probe_dir = Path("/tmp/reconciliation_probes")
    probe_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nProbe output: {probe_dir}")
    
    # Step 1: Extract IPE data (simulated)
    print("\n[Step 1] Extracting IPE data...")
    df_ipe = pd.DataFrame({
        "customer_no": ["C001", "C002", "C003", "C004", "C005"],
        "document_no": ["D101", "D102", "D103", "D104", "D105"],
        "amount": [1000.00, 2000.00, 1500.00, 3000.00, 2500.00],
        "posting_date": ["2024-01-15", "2024-01-20", "2024-01-25", 
                         "2024-02-01", "2024-02-15"],
        "status": ["posted", "posted", "posted", "posted", "posted"]
    })
    
    # Add probe after IPE extraction
    probe = probe_df(
        df_ipe, 
        "01_ipe_extracted", 
        probe_dir,
        amount_col="amount",
        date_col="posting_date",
        key_cols=["customer_no", "document_no"],
        snapshot=True
    )
    print(f"   IPE extracted: {probe.rows} rows, total amount: {probe.amount_sum:.2f}")
    print(f"   Date range: {probe.min_date} to {probe.max_date}")
    
    # Step 2: Extract GL data (simulated)
    print("\n[Step 2] Extracting GL data...")
    df_gl = pd.DataFrame({
        "account_no": ["GL001", "GL002", "GL003", "GL004"],
        "amount": [1000.00, 2000.00, 1500.00, 3000.00],
        "posting_date": ["2024-01-15", "2024-01-20", "2024-01-25", "2024-02-01"],
        "description": ["Payment", "Invoice", "Credit", "Invoice"]
    })
    
    # Add probe after GL extraction
    probe = probe_df(
        df_gl, 
        "02_gl_extracted", 
        probe_dir,
        amount_col="amount",
        date_col="posting_date",
        snapshot=True
    )
    print(f"   GL extracted: {probe.rows} rows, total amount: {probe.amount_sum:.2f}")
    
    # Step 3: Apply business rules / filters
    print("\n[Step 3] Applying business rules...")
    df_ipe_filtered = df_ipe[df_ipe["status"] == "posted"].copy()
    
    # Add probe after filtering
    probe = probe_df(
        df_ipe_filtered, 
        "03_ipe_filtered", 
        probe_dir,
        amount_col="amount",
        key_cols=["customer_no"]
    )
    print(f"   After filtering: {probe.rows} rows")
    print(f"   Unique customers: {probe.unique_keys['customer_no']}")
    
    # Step 4: Calculate differences (simulated)
    print("\n[Step 4] Calculating differences...")
    
    # Aggregate IPE by date
    df_ipe_agg = df_ipe_filtered.groupby("posting_date").agg({
        "amount": "sum"
    }).reset_index()
    df_ipe_agg.rename(columns={"amount": "ipe_amount"}, inplace=True)
    
    # Aggregate GL by date
    df_gl_agg = df_gl.groupby("posting_date").agg({
        "amount": "sum"
    }).reset_index()
    df_gl_agg.rename(columns={"amount": "gl_amount"}, inplace=True)
    
    # Merge
    df_comparison = pd.merge(
        df_ipe_agg, 
        df_gl_agg, 
        on="posting_date", 
        how="outer"
    )
    df_comparison.fillna(0, inplace=True)
    df_comparison["difference"] = df_comparison["ipe_amount"] - df_comparison["gl_amount"]
    
    # Add probe for comparison
    probe = probe_df(
        df_comparison, 
        "04_comparison", 
        probe_dir,
        amount_col="difference",
        date_col="posting_date",
        snapshot=True,
        snapshot_cols=["posting_date", "ipe_amount", "gl_amount", "difference"]
    )
    print(f"   Comparison: {probe.rows} dates")
    print(f"   Total difference: {probe.amount_sum:.2f}")
    
    # Step 5: Identify reconciliation issues
    print("\n[Step 5] Identifying issues...")
    df_issues = df_comparison[df_comparison["difference"].abs() > 0].copy()
    
    # Add probe for issues
    probe = probe_df(
        df_issues, 
        "05_issues_found", 
        probe_dir,
        amount_col="difference",
        snapshot=True
    )
    
    if probe.rows > 0:
        print(f"   ⚠️  Found {probe.rows} dates with differences")
        print(f"   Total unreconciled amount: {probe.amount_sum:.2f}")
    else:
        print(f"   ✓ No differences found - fully reconciled!")
    
    # Summary
    print("\n" + "=" * 70)
    print("Workflow complete!")
    print(f"Probe logs: {probe_dir / 'probes.log'}")
    print(f"Snapshots: {len(list(probe_dir.glob('snapshot_*.csv')))} files")
    print("=" * 70)
    
    # Show probe log summary
    print("\n[Probe Log Summary]")
    log_file = probe_dir / "probes.log"
    if log_file.exists():
        import json
        with open(log_file, 'r') as f:
            for i, line in enumerate(f, 1):
                entry = json.loads(line)
                probe_data = entry["probe"]
                print(f"{i}. {probe_data['name']}: "
                      f"{probe_data['rows']} rows, "
                      f"{probe_data['cols']} cols, "
                      f"{probe_data['nulls_total']} nulls")


def main():
    """Run the integration example."""
    try:
        simulate_reconciliation_workflow()
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
