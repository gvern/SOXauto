#!/usr/bin/env python3
"""
Apply bridge classification rules to extracted CSVs and produce a consolidated labeled output.

Inputs (from data/outputs):
- IPE_31.csv (Collection Accounts open items) — recommended
- IPE_10.csv (Prepayments TV) — optional
- IPE_07.csv (Customer balances) — optional

Output:
- data/outputs/bridges_classified.csv

Notes:
- This script operates offline on CSVs. For DB-driven enrichment, wire in sql_enrichment when connectivity is ready.
"""
import os
import sys
import pandas as pd
from typing import List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.bridges.catalog import load_rules
from src.bridges.classifier import classify_bridges


INPUT_FILES_CANDIDATES = [
    os.path.join(REPO_ROOT, "data", "outputs", "IPE_31.csv"),
    os.path.join(REPO_ROOT, "data", "outputs", "IPE_10.csv"),
    os.path.join(REPO_ROOT, "data", "outputs", "IPE_07.csv"),
]
OUTPUT_FILE = os.path.join(REPO_ROOT, "data", "outputs", "bridges_classified.csv")


def load_inputs(paths: List[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p)
                df["_source_file"] = os.path.basename(p)
                frames.append(df)
                print(f"Loaded: {p} ({len(df)} rows)")
            except Exception as e:
                print(f"[WARN] Failed to read {p}: {e}")
        else:
            print(f"[INFO] Missing optional input: {p}")
    if frames:
        return pd.concat(frames, ignore_index=True, sort=False)
    return pd.DataFrame()


def main():
    rules = load_rules()
    df = load_inputs(INPUT_FILES_CANDIDATES)
    if df.empty:
        print("No input CSVs found — nothing to classify.")
        sys.exit(0)

    classified = classify_bridges(df, rules)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    classified.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote: {OUTPUT_FILE} ({len(classified)} rows)")

    counts = classified["bridge_key"].value_counts(dropna=False)
    print("Bridge distribution:")
    for k, v in counts.items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()
