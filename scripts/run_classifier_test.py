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
    calculate_integration_error_adjustment,
)
from src.utils.fx_utils import FXConverter

# === CONFIGURATION ===
PARAMS = {
    "cutoff_date": "2025-09-30",
    "country": "EC_NG",  # Pour le filtrage par défaut
}


# -------------------------------
# Console rendering utilities
# -------------------------------
class Box:
    def __init__(self, title: str, width: int = 61):
        self.title = title
        self.width = max(width, len(title) + 4)

    def header(self):
        return (
            "\n"
            + "┌"
            + "─" * (self.width - 2)
            + "┐\n"
            + f"│ {self.title.ljust(self.width - 3)}│\n"
            + "├"
            + "─" * (self.width - 2)
            + "┤"
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
        "display.max_rows",
        limit,
        "display.max_columns",
        12,
        "display.max_colwidth",
        80,
        "display.width",
        120,
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
        "CR_05": "fixture_CR_05.csv",
        "IPE_08": "fixture_IPE_08.csv",
        "IPE_07": "fixture_IPE_07.csv",
        "JDASH": "fixture_JDASH.csv",
        "DOC_VOUCHER_USAGE": "fixture_DOC_VOUCHER_USAGE.csv",
    }

    hr("LOADING FIXTURES")

    fixtures = {}
    for name, filename in fixture_files.items():
        path = os.path.join(fixtures_dir, filename)
        if not os.path.exists(path):
            print(f"❌ ERROR: Fixture file not found: {path}")
            sys.exit(1)
        # Réduit les DtypeWarning bruyants
        df = pd.read_csv(path, low_memory=False)
        fixtures[name] = df
        print(f"Colonnes pour {name}: {list(df.columns)}")
        print(f"✓ Loaded {name}: {len(df)} rows from {filename}")

    # Filter by country
    hr(f"FILTERING FIXTURES FOR A SINGLE COUNTRY ({country_code})")
    try:
        rows_before = len(fixtures["CR_03"])
        fixtures["CR_03"] = fixtures["CR_03"][
            fixtures["CR_03"]["id_company"] == country_code
        ].copy()
        print(f"✓ Filtered CR_03: {rows_before} -> {len(fixtures['CR_03'])}")

        rows_before = len(fixtures["IPE_08"])
        fixtures["IPE_08"] = fixtures["IPE_08"][
            fixtures["IPE_08"]["ID_COMPANY"] == country_code
        ].copy()
        print(f"✓ Filtered IPE_08: {rows_before} -> {len(fixtures['IPE_08'])}")

        rows_before = len(fixtures["IPE_07"])
        fixtures["IPE_07"] = fixtures["IPE_07"][
            fixtures["IPE_07"]["id_company"] == country_code
        ].copy()
        print(f"✓ Filtered IPE_07: {rows_before} -> {len(fixtures['IPE_07'])}")

        rows_before = len(fixtures["DOC_VOUCHER_USAGE"])
        fixtures["DOC_VOUCHER_USAGE"] = fixtures["DOC_VOUCHER_USAGE"][
            fixtures["DOC_VOUCHER_USAGE"]["ID_Company"] == country_code
        ].copy()
        print(
            f"✓ Filtered DOC_VOUCHER_USAGE: {rows_before} -> {len(fixtures['DOC_VOUCHER_USAGE'])}"
        )

        print(
            f"✓ Kept JDASH: {len(fixtures['JDASH'])} rows (already filtered or global)"
        )

    except KeyError as e:
        print(
            "\n❌ ERREUR DE FILTRAGE: colonne manquante (id_company / ID_COMPANY / ID_Company)."
        )
        print(f"Erreur: {e}")
        sys.exit(1)

    # DATA QUALITY PRE-CHECKS
    hr(f"DATA QUALITY PRE-CHECKS ({country_code} ONLY)")
    print(
        f"✓ CR_03 (NAV): {len(fixtures['CR_03'])} rows. Total Amount: {fixtures['CR_03']['Amount'].sum():,.2f}"
    )
    print(
        f"✓ IPE_08 (Issuance): {len(fixtures['IPE_08'])} rows. Total Remaining: {fixtures['IPE_08']['remaining_amount'].sum():,.2f}"
    )
    print(f"✓ IPE_07 (Customers): {len(fixtures['IPE_07'])} rows.")
    print(
        f"✓ DOC_VOUCHER_USAGE (Usage TV): {len(fixtures['DOC_VOUCHER_USAGE'])} rows. Total Usage: {fixtures['DOC_VOUCHER_USAGE']['TotalAmountUsed'].sum():,.2f}"
    )
    print(
        f"✓ JDASH (Jdash): {len(fixtures['JDASH'])} rows. Total Amount Used: {fixtures['JDASH']['Amount Used'].sum():,.2f}"
    )

    return fixtures


# -------------------------------
# Tasks
# -------------------------------
def run_task2_vtc(fixtures, fx_converter=None, quiet=False, limit=10):
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
        fixtures["IPE_08"], categorized, fx_converter=fx_converter
    )

    # Save evidence
    evidence_dir = os.path.join(REPO_ROOT, "evidence_output")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "TASK_2_VTC_PROOF.csv")
    proof_df.to_csv(evidence_path, index=False)
    print(f"✓ Evidence saved to 'evidence_output/TASK_2_VTC_PROOF.csv'")

    if not quiet:
        print(f"\n✓ VTC Adjustment Amount: ${adjustment_amount:,.2f}")
        print(f"✓ Number of unmatched vouchers: {len(proof_df)}")
        print_df(proof_df, "Unmatched Vouchers (proof_df)", limit)

    return adjustment_amount, proof_df


def run_task3_integration(fixtures, fx_converter=None, quiet=False, limit=10):
    hr("TASK 3: INTEGRATION ERRORS ADJUSTMENT")

    if "IPE_REC_ERRORS" not in fixtures:
        print("⚠️ Fixture IPE_REC_ERRORS not found. Skipping Task 3.")
        return 0.0, pd.DataFrame()

    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        fixtures["IPE_REC_ERRORS"], fx_converter=fx_converter
    )

    # Save evidence
    evidence_dir = os.path.join(REPO_ROOT, "evidence_output")
    os.makedirs(evidence_dir, exist_ok=True)
    proof_df.to_csv(
        os.path.join(evidence_dir, "TASK_3_INTEGRATION_PROOF.csv"), index=False
    )
    print(f"✓ Evidence saved to 'evidence_output/TASK_3_INTEGRATION_PROOF.csv'")

    if not quiet:
        print(f"\n✓ Integration Adjustment Amount: ${adjustment_amount:,.2f}")
        print(f"✓ Number of error transactions: {len(proof_df)}")
        print_df(proof_df, "Integration Errors (proof_df)", limit)

        # Show breakdown by GL
        print("\nBreakdown by Target GL:")
        print(proof_df.groupby("Target_GL")["Amount"].sum())

    return adjustment_amount, proof_df


def run_task4_customer_reclass(fixtures, quiet=False, limit=10):
    hr("TASK 4: CUSTOMER POSTING GROUP RECLASSIFICATION")
    bridge_amount, proof_df = calculate_customer_posting_group_bridge(
        fixtures["IPE_07"]
    )

    # Save evidence
    evidence_dir = os.path.join(REPO_ROOT, "evidence_output")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "TASK_4_RECLASS_PROOF.csv")
    proof_df.to_csv(evidence_path, index=False)
    print(f"✓ Evidence saved to 'evidence_output/TASK_4_RECLASS_PROOF.csv'")

    if not quiet:
        print(
            f"\n✓ Bridge Amount: ${bridge_amount:,.2f} (always 0 for identification tasks)"
        )
        print(f"✓ Number of customers with multiple posting groups: {len(proof_df)}")
        print_df(proof_df, "Customers with Multiple Posting Groups (proof_df)", limit)
    return bridge_amount, proof_df


def run_task1_timing_diff(
    fixtures, cutoff_date=None, fx_converter=None, quiet=False, limit=10
):
    hr("TASK 1: TIMING DIFFERENCE BRIDGE")
    bridge_amount, proof_df = calculate_timing_difference_bridge(
        fixtures["IPE_08"], cutoff_date=cutoff_date, fx_converter=fx_converter
    )

    # Save evidence
    evidence_dir = os.path.join(REPO_ROOT, "evidence_output")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "TASK_1_TIMING_DIFF_PROOF.csv")
    proof_df.to_csv(evidence_path, index=False)
    print(f"✓ Evidence saved to 'evidence_output/TASK_1_TIMING_DIFF_PROOF.csv'")

    if not quiet:
        print(f"\n✓ Bridge Amount: ${bridge_amount:,.2f}")
        print(f"✓ Number of vouchers with variances: {len(proof_df)}")
        print_df(proof_df, "Vouchers with Variances (proof_df)", limit)
    return bridge_amount, proof_df


# -------------------------------
# Summary
# -------------------------------
def print_summary(task1, task2, task3, task4):
    b1 = Box("Task 1: Timing Difference Bridge")
    b2 = Box("Task 2: VTC (Voucher to Cash) Reconciliation")
    b3 = Box("Task 3: Integration Errors Adjustment")
    b4 = Box("Task 4: Customer Posting Group Reclassification")
    bt = Box("TOTAL BRIDGES/ADJUSTMENTS")

    # Task 1
    print(b1.header())
    print(b1.line(f"Bridge Amount:          ${task1[0]:>16,.2f}"))
    print(b1.line(f"Vouchers w/ Variance:   {len(task1[1]):>6} items"))
    print(b1.footer())
    # Task 2
    print(b2.header())
    print(b2.line(f"Adjustment Amount:      ${task2[0]:>16,.2f}"))
    print(b2.line(f"Unmatched Vouchers:     {len(task2[1]):>6} items"))
    print(b2.footer())

    # Task 3
    print(b3.header())
    print(b3.line(f"Adjustment Amount:      ${task3[0]:>16,.2f}"))
    print(b3.line(f"Error Transactions:     {len(task3[1]):>6} items"))
    print(b3.footer())

    # Task 4
    print(b4.header())
    print(b4.line(f"Bridge Amount:          ${task4[0]:>16,.2f}"))
    print(b4.line(f"Problem Customers:      {len(task4[1]):>6} items"))
    print(b4.footer())

    total = task2[0] + task4[0] + task1[0]
    print(bt.header())
    print(bt.line(f"Total Amount:           ${total:>16,.2f}"))
    print(bt.footer())


# -------------------------------
# Main
# -------------------------------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--country",
        default="EC_NG",
        help="ID_COMPANY / id_company code to filter (default: EC_NG)",
    )
    p.add_argument(
        "--cutoff-date",
        default=None,
        help="Reconciliation cutoff date (YYYY-MM-DD)",
    )
    p.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only the final summary (no step details)",
    )
    p.add_argument(
        "--quiet", action="store_true", help="Hide intermediate DataFrame heads"
    )
    p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max rows to display in DataFrame previews",
    )
    return p.parse_args()


def main():
    args = parse_args()
    cutoff_date = args.cutoff_date or PARAMS["cutoff_date"]
    country = args.country or PARAMS["country"]

    print(f"Running analysis for: {country} (Cutoff: {cutoff_date})")

    fixtures = load_fixtures(country)
    hr("CLASSIFIER TEST SCRIPT")
    print("Testing classification logic offline using local fixtures")

    # Initialize FX Converter
    hr("INITIALIZING FX CONVERTER")
    try:
        fx_converter = FXConverter(fixtures["CR_05"])
        print(
            f"✓ FX Converter initialized with {len(fx_converter.rates_dict)} exchange rates"
        )
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize FX Converter: {e}")
        print("   Continuing with local currency calculations...")
        fx_converter = None

    # 1. TASK 1: Timing Difference (L'analyse temporelle globale)
    task1 = run_task1_timing_diff(
        fixtures,
        cutoff_date=cutoff_date,
        fx_converter=fx_converter,
        quiet=args.summary_only or args.quiet,
        limit=args.limit,
    )

    # 2. TASK 2: VTC Adjustment (L'analyse spécifique des remboursements)
    task2 = run_task2_vtc(
        fixtures,
        fx_converter=fx_converter,
        quiet=args.summary_only or args.quiet,
        limit=args.limit,
    )

    # 3. TASK 3: Integration Errors (Les erreurs techniques - NOUVEAU)
    # (Nous allons implémenter cette fonction juste après)
    task3 = run_task3_integration(
        fixtures,
        fx_converter=fx_converter,
        quiet=args.summary_only or args.quiet,
        limit=args.limit,
    )

    # 4. TASK 4: Customer Reclass (L'hygiène des tiers)
    task4 = run_task4_customer_reclass(
        fixtures, quiet=args.summary_only or args.quiet, limit=args.limit
    )

    # Résumé
    hr("SUMMARY OF ALL BRIDGES/ADJUSTMENTS")
    print_summary(task1, task2, task3, task4)

    print("\n✓ Test completed successfully!\n")


if __name__ == "__main__":
    main()
