#!/usr/bin/env python3
"""
Temporal Workflow Starter for C-PG-1 Reconciliation.

This script starts the C-PG-1 reconciliation workflow on the Temporal server.
It replaces the old script-based orchestration with a robust Temporal workflow.

Usage:
    python scripts/run_full_reconciliation.py [--cutoff-date YYYY-MM-DD]

Environment Variables:
    TEMPORAL_HOST: Temporal server host (default: localhost:7233)
    TEMPORAL_NAMESPACE: Temporal namespace (default: default)
    TEMPORAL_TASK_QUEUE: Task queue name (default: cpg1-task-queue)
    CUTOFF_DATE: Cutoff date for reconciliation (default: first day of current month)
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from temporalio.client import Client


async def start_workflow(
    cutoff_date: str,
    gl_accounts: list[str],
    year_start: str,
    year_end: str,
) -> Dict[str, Any]:
    """
    Start the C-PG-1 reconciliation workflow.
    
    Args:
        cutoff_date: Cutoff date for reconciliation (YYYY-MM-DD)
        gl_accounts: List of GL accounts to reconcile
        year_start: Start of year for GL entries (YYYY-MM-DD)
        year_end: End of year for GL entries (YYYY-MM-DD)
        
    Returns:
        Workflow execution result
    """
    # Get configuration from environment
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "cpg1-task-queue")
    
    print(f"Connecting to Temporal server at {temporal_host}")
    print(f"Namespace: {temporal_namespace}")
    print(f"Task queue: {task_queue}")
    
    try:
        # Connect to Temporal server
        client = await Client.connect(
            temporal_host,
            namespace=temporal_namespace,
        )
        
        print("Connected to Temporal server")
        
        # Prepare workflow input
        workflow_input = {
            "cutoff_date": cutoff_date,
            "gl_accounts": gl_accounts,
            "year_start": year_start,
            "year_end": year_end,
        }
        
        # Generate workflow ID
        workflow_id = f"cpg1-reconciliation-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\nStarting C-PG-1 Reconciliation Workflow")
        print(f"Workflow ID: {workflow_id}")
        print(f"Cutoff Date: {cutoff_date}")
        print(f"GL Accounts: {', '.join(gl_accounts)}")
        print(f"Year Range: {year_start} to {year_end}")
        print()
        
        # Start workflow
        handle = await client.start_workflow(
            "Cpg1Workflow",
            workflow_input,
            id=workflow_id,
            task_queue=task_queue,
            execution_timeout=timedelta(hours=2),
        )
        
        print(f"Workflow started successfully!")
        print(f"Workflow ID: {handle.id}")
        print(f"Run ID: {handle.result_run_id}")
        print()
        print("Waiting for workflow to complete...")
        print("(You can safely Ctrl+C to stop waiting - the workflow will continue running)")
        print()
        
        # Wait for workflow to complete
        result = await handle.result()
        
        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETED")
        print("=" * 80)
        print(f"Status: {result.get('status')}")
        print(f"\nIPE Results:")
        for ipe_id, ipe_result in result.get("ipe_results", {}).items():
            print(f"  - {ipe_id}: {ipe_result.get('rows_extracted', 0)} rows extracted")
        
        print(f"\nCR Results:")
        for cr_id, cr_result in result.get("cr_results", {}).items():
            print(f"  - {cr_id}: {cr_result.get('rows_extracted', 0)} rows extracted")
        
        print(f"\nBridge Calculations:")
        for bridge_name, bridge_result in result.get("bridge_calculations", {}).items():
            if "bridge_amount" in bridge_result:
                print(f"  - {bridge_name}: ${bridge_result['bridge_amount']:,.2f}")
            elif "adjustment_amount" in bridge_result:
                print(f"  - {bridge_name}: ${bridge_result['adjustment_amount']:,.2f}")
            elif "total_rows" in bridge_result:
                print(f"  - {bridge_name}: {bridge_result['total_rows']} rows classified")
        
        print(f"\nEvidence saved to:")
        for evidence_path in result.get("evidence_paths", []):
            print(f"  - {evidence_path}")
        
        print("\n" + "=" * 80)
        
        return result
        
    except KeyboardInterrupt:
        print("\n\nStopped waiting for workflow (workflow continues running on server)")
        print(f"You can check workflow status using workflow ID: {workflow_id}")
        return {}
    except Exception as e:
        print(f"\nError starting workflow: {e}", file=sys.stderr)
        raise


def main():
    """
    Parse arguments and start the workflow.
    """
    parser = argparse.ArgumentParser(
        description="Start C-PG-1 Reconciliation Workflow on Temporal"
    )
    parser.add_argument(
        "--cutoff-date",
        type=str,
        help="Cutoff date for reconciliation (YYYY-MM-DD). Defaults to first day of current month.",
    )
    parser.add_argument(
        "--gl-accounts",
        type=str,
        nargs="+",
        default=[
            "13001", "13002", "13003", "13004", "13005", "13009", "13024",
            "18304", "18317", "18350", "18397", "18412", "18650",
        ],
        help="List of GL accounts to reconcile",
    )
    parser.add_argument(
        "--year-start",
        type=str,
        help="Start of year for GL entries (YYYY-MM-DD). Defaults to Jan 1 of current year.",
    )
    parser.add_argument(
        "--year-end",
        type=str,
        help="End of year for GL entries (YYYY-MM-DD). Defaults to Dec 31 of current year.",
    )
    
    args = parser.parse_args()
    
    # Determine dates
    today = datetime.now()
    
    # Default cutoff_date: first day of current month
    if args.cutoff_date:
        cutoff_date = args.cutoff_date
    else:
        cutoff_date = os.getenv("CUTOFF_DATE")
        if not cutoff_date:
            first_day = today.replace(day=1)
            cutoff_date = first_day.strftime("%Y-%m-%d")
    
    # Default year_start: Jan 1 of current year
    if args.year_start:
        year_start = args.year_start
    else:
        year_start = today.replace(month=1, day=1).strftime("%Y-%m-%d")
    
    # Default year_end: Dec 31 of current year
    if args.year_end:
        year_end = args.year_end
    else:
        year_end = today.replace(month=12, day=31).strftime("%Y-%m-%d")
    
    # Start workflow
    asyncio.run(start_workflow(cutoff_date, args.gl_accounts, year_start, year_end))


if __name__ == "__main__":
    main()
