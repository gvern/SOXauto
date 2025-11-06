#!/usr/bin/env python3
"""
Standalone classifier test script.

This script runs the entire classification logic offline using local CSV files
from tests/fixtures/. It does not depend on temporalio or mssql_runner, only
on pandas and the classifier module.

Usage:
    python scripts/run_classifier_test.py
"""

import os
import sys
import pandas as pd

# Add the repository root to the Python path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Import classifier functions
from src.bridges.classifier import (
    _categorize_nav_vouchers,
    calculate_vtc_adjustment,
    calculate_customer_posting_group_bridge,
    calculate_timing_difference_bridge,
)


def load_fixtures():
    """Load all required fixture files from tests/fixtures/."""
    fixtures_dir = os.path.join(REPO_ROOT, "tests", "fixtures")

    fixtures = {}
    fixture_files = {
        "CR_03": "fixture_CR_03.csv",
        "IPE_08": "fixture_IPE_08.csv",
        "IPE_07": "fixture_IPE_07.csv",
        "JDASH": "fixture_JDASH.csv",
        "DOC_VOUCHER_USAGE": "fixture_DOC_VOUCHER_USAGE.csv",
    }

    print("=" * 80)
    print("LOADING FIXTURES")
    print("=" * 80)

    for name, filename in fixture_files.items():
        filepath = os.path.join(fixtures_dir, filename)
        if not os.path.exists(filepath):
            print(f"❌ ERROR: Fixture file not found: {filepath}")
            sys.exit(1)

        fixtures[name] = pd.read_csv(filepath)
        print(f"✓ Loaded {name}: {len(fixtures[name])} rows from {filename}")

    print()
    return fixtures


def run_task2_vtc(fixtures):
    """
    Task 2: VTC (Voucher to Cash) Reconciliation

    Steps:
    1. Categorize NAV vouchers from CR_03
    2. Calculate VTC adjustment using IPE_08 and categorized CR_03
    """
    print("=" * 80)
    print("TASK 2: VTC (VOUCHER TO CASH) RECONCILIATION")
    print("=" * 80)

    # Step 1: Categorize NAV vouchers
    print("\n[Step 1] Categorizing NAV vouchers from CR_03...")
    categorized_cr_03 = _categorize_nav_vouchers(fixtures["CR_03"])
    print(f"✓ Categorized {len(categorized_cr_03)} voucher entries")
    print("\nCategorization Results:")
    print(
        categorized_cr_03[
            ["Chart of Accounts No_", "Amount", "[Voucher No_]", "bridge_category"]
        ].to_string()
    )

    # Step 2: Calculate VTC adjustment
    print("\n[Step 2] Calculating VTC adjustment...")
    adjustment_amount, proof_df = calculate_vtc_adjustment(
        fixtures["IPE_08"], categorized_cr_03
    )

    print(f"\n✓ VTC Adjustment Amount: ${adjustment_amount:,.2f}")
    print(f"✓ Number of unmatched vouchers: {len(proof_df)}")

    if not proof_df.empty:
        print("\nUnmatched Vouchers (proof_df.head()):")
        print(proof_df.head().to_string())
    else:
        print("\nNo unmatched vouchers found.")

    print()
    return adjustment_amount, proof_df


def run_task4_customer_reclass(fixtures):
    """
    Task 4: Customer Posting Group Reclassification

    Identifies customers with multiple posting groups for manual review.
    """
    print("=" * 80)
    print("TASK 4: CUSTOMER POSTING GROUP RECLASSIFICATION")
    print("=" * 80)

    print("\nCalculating customer posting group bridge...")
    bridge_amount, proof_df = calculate_customer_posting_group_bridge(
        fixtures["IPE_07"]
    )

    print(
        f"\n✓ Bridge Amount: ${bridge_amount:,.2f} (always 0 for identification tasks)"
    )
    print(f"✓ Number of customers with multiple posting groups: {len(proof_df)}")

    if not proof_df.empty:
        print("\nCustomers with Multiple Posting Groups (proof_df.head()):")
        print(proof_df.head().to_string())
    else:
        print("\nNo customers with multiple posting groups found.")

    print()
    return bridge_amount, proof_df


def run_task1_timing_diff(fixtures):
    """
    Task 1: Timing Difference Bridge

    Calculates timing differences between Jdash and Usage TV Extract.
    """
    print("=" * 80)
    print("TASK 1: TIMING DIFFERENCE BRIDGE")
    print("=" * 80)

    print("\nCalculating timing difference bridge...")
    bridge_amount, proof_df = calculate_timing_difference_bridge(
        fixtures["JDASH"], fixtures["DOC_VOUCHER_USAGE"]
    )

    print(f"\n✓ Bridge Amount: ${bridge_amount:,.2f}")
    print(f"✓ Number of vouchers with variances: {len(proof_df)}")

    if not proof_df.empty:
        print("\nVouchers with Variances (proof_df.head()):")
        print(proof_df.head().to_string())
    else:
        print("\nNo timing differences found.")

    print()
    return bridge_amount, proof_df


def print_summary(task2_result, task4_result, task1_result):
    """Print final summary of all bridges/adjustments."""
    print("=" * 80)
    print("SUMMARY OF ALL BRIDGES/ADJUSTMENTS")
    print("=" * 80)

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│ Task 2: VTC (Voucher to Cash) Reconciliation               │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│ Adjustment Amount:      ${task2_result[0]:>16,.2f}            │")
    print(
        f"│ Unmatched Vouchers:     {task2_result[1].__len__():>6} items                    │"
    )
    print("└─────────────────────────────────────────────────────────────┘")

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│ Task 4: Customer Posting Group Reclassification             │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│ Bridge Amount:          ${task4_result[0]:>16,.2f}            │")
    print(
        f"│ Problem Customers:      {task4_result[1].__len__():>6} items                    │"
    )
    print("└─────────────────────────────────────────────────────────────┘")

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│ Task 1: Timing Difference Bridge                            │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│ Bridge Amount:          ${task1_result[0]:>16,.2f}            │")
    print(
        f"│ Vouchers w/ Variance:   {task1_result[1].__len__():>6} items                    │"
    )
    print("└─────────────────────────────────────────────────────────────┘")

    total_bridges = task2_result[0] + task4_result[0] + task1_result[0]
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│ TOTAL BRIDGES/ADJUSTMENTS                                   │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│ Total Amount:           ${total_bridges:>16,.2f}            │")
    print("└─────────────────────────────────────────────────────────────┘")
    print()


def main():
    """Main entry point for the classifier test script."""
    print("\n" + "=" * 80)
    print("CLASSIFIER TEST SCRIPT")
    print("Testing classification logic offline using local fixtures")
    print("=" * 80 + "\n")

    # Load fixtures
    fixtures = load_fixtures()

    # Run Task 2: VTC
    task2_result = run_task2_vtc(fixtures)

    # Run Task 4: Customer Reclass
    task4_result = run_task4_customer_reclass(fixtures)

    # Run Task 1: Timing Diff
    task1_result = run_task1_timing_diff(fixtures)

    # Print summary
    print_summary(task2_result, task4_result, task1_result)

    print("✓ Test completed successfully!")
    print()


if __name__ == "__main__":
    main()
