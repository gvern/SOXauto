#!/usr/bin/env python3
"""
Standalone classifier test script (clean output).

Usage:
  python scripts/run_classifier_test.py [--country JD_GH] [--summary-only] [--quiet] [--limit 10]
"""

import os
import sys
import argparse
import pandas as pd

# Add the repository root to the Python path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.bridges.classifier import (
    _categorize_nav_vouchers,
    calculate_vtc_adjustment,
    calculate_customer_posting_group_bridge,
    calculate_timing_difference_bridge,
)

# -------------------------------
# Console rendering utilities
# -------------------------------
class Box:
    def __init__(self, title: str, width: int = 61):
        self.title = title
        self.width = max(width, len(title) + 4)

    def header(self):
        return (
            "\n" +
            "┌" + "─" * (self.width - 2) + "┐\n" +
            f"│ {self.title.ljust(self.width - 3)}│\n" +
            "├" + "─" * (self.width - 2) + "┤"
        )

    def line(self, text: str):
        return f"\n│ {text.ljust(self.width - 3)}│"

    def footer(self):
        return "\n" + "└" + "─" * (self.width - 2) + "┘"

def print_df(df: pd.DataFrame, title: str, limit: int = 10):
    if df is None or df.empty:
        print(f"\n{title}: <empty>")
        return
    print(f"\n{title}:")
    # affichage stable / non verbeux
    with pd.option_context(
        "display.max_rows", limit,
        "display.max_columns", 12,
        "display.max_colwidth", 80,
        "display.width", 120
    ):
        print(df.head(limit).to_string(index=False))

def hr(title: str):
    bar = "=" * 80
    print(f"\n{bar}\n{title}\n{bar}")

# -------------------------------
# Data loading
# -------------------------------
def load_fixtures(country_code: str):
    fixtures_dir = os.path.join(REPO_ROOT, "tests", "fixtures")
    fixture_files = {
        "CR_03": "fixture_CR_03.csv",
        "IPE_08": "fixture_IPE_08.csv",
        "IPE_07": "fixture_IPE_07.csv",
    }

    hr("LOADING FIXTURES")

    fixtures = {}
    for name, filename in fixture_files.items():
        path = os.path.join(fixtures_dir, filename)
        if not os.path.exists(path):
            print(f"❌ ERROR: Fixture file not found: {path}")
            print(f"   Note: Task 1 (Timing Difference) now uses IPE_08 instead of JDASH/DOC_VOUCHER_USAGE")
            sys.exit(1)
        # Réduit les DtypeWarning bruyants
        df = pd.read_csv(path, low_memory=False)
        fixtures[name] = df
        print(f"Colonnes pour {name}: {list(df.columns)}")
        print(f"✓ Loaded {name}: {len(df)} rows from {filename}")

    # Filter by country
    hr(f"FILTERING FIXTURES FOR A SINGLE COUNTRY ({country_code})")
    try:
        rows_before = len(fixtures['CR_03'])
        fixtures['CR_03'] = fixtures['CR_03'][fixtures['CR_03']['id_company'] == country_code].copy()
        print(f"✓ Filtered CR_03: {rows_before} -> {len(fixtures['CR_03'])}")

        rows_before = len(fixtures['IPE_08'])
        fixtures['IPE_08'] = fixtures['IPE_08'][fixtures['IPE_08']['ID_COMPANY'] == country_code].copy()
        print(f"✓ Filtered IPE_08: {rows_before} -> {len(fixtures['IPE_08'])}")

        rows_before = len(fixtures['IPE_07'])
        fixtures['IPE_07'] = fixtures['IPE_07'][fixtures['IPE_07']['id_company'] == country_code].copy()
        print(f"✓ Filtered IPE_07: {rows_before} -> {len(fixtures['IPE_07'])}")

    except KeyError as e:
        print("\n❌ ERREUR DE FILTRAGE: colonne manquante (id_company / ID_COMPANY / ID_Company).")
        print(f"Erreur: {e}")
        sys.exit(1)

    return fixtures

# -------------------------------
# Tasks
# -------------------------------
def run_task2_vtc(fixtures, quiet=False, limit=10):
    hr("TASK 2: VTC (VOUCHER TO CASH) RECONCILIATION")
    if not quiet:
        print("\n[Step 1] Categorizing NAV vouchers from CR_03...")
    categorized = _categorize_nav_vouchers(fixtures["CR_03"])
    if not quiet:
        print(f"✓ Categorized {len(categorized)} voucher entries")
        print_df(categorized, "Categorization Results", limit)

    if not quiet:
        print("\n[Step 2] Calculating VTC adjustment...")
    adjustment_amount, proof_df = calculate_vtc_adjustment(
        fixtures["IPE_08"], categorized
    )

    if not quiet:
        print(f"\n✓ VTC Adjustment Amount: ${adjustment_amount:,.2f}")
        print(f"✓ Number of unmatched vouchers: {len(proof_df)}")
        print_df(proof_df, "Unmatched Vouchers (proof_df)", limit)

    return adjustment_amount, proof_df

def run_task4_customer_reclass(fixtures, quiet=False, limit=10):
    hr("TASK 4: CUSTOMER POSTING GROUP RECLASSIFICATION")
    bridge_amount, proof_df = calculate_customer_posting_group_bridge(fixtures["IPE_07"])
    if not quiet:
        print(f"\n✓ Bridge Amount: ${bridge_amount:,.2f} (always 0 for identification tasks)")
        print(f"✓ Number of customers with multiple posting groups: {len(proof_df)}")
        print_df(proof_df, "Customers with Multiple Posting Groups (proof_df)", limit)
    return bridge_amount, proof_df

def run_task1_timing_diff(fixtures, cutoff_date="2025-09-30", quiet=False, limit=10):
    hr("TASK 1: TIMING DIFFERENCE BRIDGE")
    bridge_amount, proof_df = calculate_timing_difference_bridge(
        fixtures["IPE_08"], cutoff_date
    )
    if not quiet:
        print(f"\n✓ Bridge Amount: ${bridge_amount:,.2f}")
        print(f"✓ Number of vouchers with timing differences: {len(proof_df)}")
        print_df(proof_df, "Vouchers with Timing Differences (proof_df)", limit)
    return bridge_amount, proof_df

# -------------------------------
# Summary
# -------------------------------
def print_summary(task2, task4, task1):
    b1 = Box("Task 2: VTC (Voucher to Cash) Reconciliation")
    b2 = Box("Task 4: Customer Posting Group Reclassification")
    b3 = Box("Task 1: Timing Difference Bridge")
    bt = Box("TOTAL BRIDGES/ADJUSTMENTS")

    # Task 2
    print(b1.header())
    print(b1.line(f"Adjustment Amount:      ${task2[0]:>16,.2f}"))
    print(b1.line(f"Unmatched Vouchers:     {len(task2[1]):>6} items"))
    print(b1.footer())

    # Task 4
    print(b2.header())
    print(b2.line(f"Bridge Amount:          ${task4[0]:>16,.2f}"))
    print(b2.line(f"Problem Customers:      {len(task4[1]):>6} items"))
    print(b2.footer())

    # Task 1
    print(b3.header())
    print(b3.line(f"Bridge Amount:          ${task1[0]:>16,.2f}"))
    print(b3.line(f"Vouchers w/ Variance:   {len(task1[1]):>6} items"))
    print(b3.footer())

    total = task2[0] + task4[0] + task1[0]
    print(bt.header())
    print(bt.line(f"Total Amount:           ${total:>16,.2f}"))
    print(bt.footer())

# -------------------------------
# Main
# -------------------------------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--country", default="JD_GH", help="ID_COMPANY / id_company code to filter (default: JD_GH)")
    p.add_argument("--cutoff-date", default="2025-09-30", help="Cutoff date for Task 1 timing difference bridge (default: 2025-09-30)")
    p.add_argument("--summary-only", action="store_true", help="Print only the final summary (no step details)")
    p.add_argument("--quiet", action="store_true", help="Hide intermediate DataFrame heads")
    p.add_argument("--limit", type=int, default=10, help="Max rows to display in DataFrame previews")
    return p.parse_args()

def main():
    args = parse_args()

    hr("CLASSIFIER TEST SCRIPT")
    print("Testing classification logic offline using local fixtures")

    fixtures = load_fixtures(args.country)

    # Steps
    task2 = run_task2_vtc(fixtures, quiet=args.summary_only or args.quiet, limit=args.limit)
    task4 = run_task4_customer_reclass(fixtures, quiet=args.summary_only or args.quiet, limit=args.limit)
    task1 = run_task1_timing_diff(fixtures, cutoff_date=args.cutoff_date, quiet=args.summary_only or args.quiet, limit=args.limit)

    # Single, clean summary
    hr("SUMMARY OF ALL BRIDGES/ADJUSTMENTS")
    print_summary(task2, task4, task1)

    print("\n✓ Test completed successfully!\n")

if __name__ == "__main__":
    main()
