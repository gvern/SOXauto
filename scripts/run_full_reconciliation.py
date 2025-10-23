#!/usr/bin/env python3
"""
Run the full manual-process replication pipeline in order:

1) Customer Accounts (IPE_07)
2) Collection Accounts (IPE_31)
3) Other AR related Accounts (IPE_10, IPE_08, ...)

Assumes DB connectivity is already working (see scripts/check_mssql_connection.py).
"""
import subprocess
import sys


def run(step_name: str, cmd: list[str]):
    print(f"\n=== {step_name} ===")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR in {step_name}: {e}")
        sys.exit(e.returncode)


def main():
    run("Step 1: Customer Accounts (IPE_07)", [sys.executable, "scripts/generate_customer_accounts.py"]) 
    run("Step 2: Collection Accounts (IPE_31)", [sys.executable, "scripts/generate_collection_accounts.py"]) 
    run("Step 3: Other AR related Accounts", [sys.executable, "scripts/generate_other_ar.py"]) 
    run("Step 4: Classify Bridges & Adjustments", [sys.executable, "scripts/classify_bridges.py"]) 
    print("\nAll steps completed. You can proceed to consolidation.")


if __name__ == "__main__":
    main()
