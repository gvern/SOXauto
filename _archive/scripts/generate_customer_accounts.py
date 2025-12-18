#!/usr/bin/env python3
"""
Generate Customer Accounts (IPE_07) as CSV and produce SOX evidence.

Output: data/outputs/customer_accounts.csv
Evidence: evidence/IPE_07/<timestamp>/* (executed query, snapshot, hash, validations, log)

Connection:
- Uses DB_CONNECTION_STRING env var (ODBC) OR MSSQL_* components.

Assertions:
- Non-empty result
- Optional: expected columns check (add to EXPECTED_COLUMNS if needed)
"""
import os
import sys
from typing import List, Optional
import pandas as pd
import pyodbc
from datetime import datetime
import getpass
import socket

# Make repo importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.core.catalog.cpg1 import get_item_by_id  # noqa: E402
from src.core.evidence.manager import DigitalEvidenceManager, IPEEvidenceGenerator  # noqa: E402
from src.utils.sql_template import render_sql  # noqa: E402

ITEM_ID = "IPE_07"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(REPO_ROOT, "data", "outputs"))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "customer_accounts.csv")
EXPECTED_COLUMNS: Optional[List[str]] = None  # e.g., ["Customer_No", "Remaining Amount_LCY"]


def build_connection_string() -> str:
    cs = os.getenv("DB_CONNECTION_STRING")
    if cs:
        return cs
    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("MSSQL_SERVER")
    database = os.getenv("MSSQL_DATABASE")
    user = os.getenv("MSSQL_USER")
    password = os.getenv("MSSQL_PASSWORD")
    if not (server and database and user and password):
        raise RuntimeError(
            "Missing DB connection details. Set DB_CONNECTION_STRING or MSSQL_SERVER, MSSQL_DATABASE, MSSQL_USER, MSSQL_PASSWORD"
        )
    return (
        f"Driver={{{{ {driver} }}}};Server={server};Database={database};"
        f"UID={user};PWD={password};TrustServerCertificate=yes;"
    )


def validate_output(df: pd.DataFrame) -> dict:
    results = {}
    # Completeness: non-empty
    results["completeness"] = {
        "expected_count": "> 0",
        "actual_count": int(len(df)),
        "status": "PASS" if len(df) > 0 else "FAIL",
    }
    # Positive accuracy (placeholder): at least one numeric column present
    numeric_cols = list(df.select_dtypes(include=["number"]).columns)
    results["accuracy_positive"] = {
        "numeric_columns_present": len(numeric_cols),
        "status": "PASS" if len(numeric_cols) > 0 else "WARN",
    }
    # Negative accuracy (placeholder): no obvious null-only columns
    null_only = [c for c in df.columns if df[c].isna().all()]
    results["accuracy_negative"] = {
        "null_only_columns": null_only,
        "status": "PASS" if len(null_only) == 0 else "WARN",
    }
    # Expected columns if defined
    if EXPECTED_COLUMNS:
        missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        results["expected_columns"] = {
            "expected": EXPECTED_COLUMNS,
            "missing": missing,
            "status": "PASS" if not missing else "FAIL",
        }
    # Overall
    statuses = [v.get("status") for v in results.values()]
    results["overall_status"] = "SUCCESS" if ("FAIL" not in statuses) else "FAILED"
    return results


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    item = get_item_by_id(ITEM_ID)
    if not item or not item.sql_query:
        raise SystemExit(f"Catalog item {ITEM_ID} not found or has no sql_query.")

    evidence_manager = DigitalEvidenceManager("evidence")
    metadata = {
        "ipe_id": ITEM_ID,
        "description": item.title,
        "execution_start": datetime.now().isoformat(),
        "sox_compliance_required": True,
        "output_file": OUTPUT_FILE,
    }
    evidence_dir = evidence_manager.create_evidence_package(ITEM_ID, metadata)
    generator = IPEEvidenceGenerator(evidence_dir, ITEM_ID)

    cs = build_connection_string()
    with pyodbc.connect(cs) as conn:
        # Prepare parameters and render query
        cutoff_date = os.getenv("CUTOFF_DATE")
        rendered_query = render_sql(item.sql_query, {"cutoff_date": cutoff_date})
        # Save executed query with parameters/context (ensures 02_query_parameters.json is created)
        generator.save_executed_query(
            rendered_query,
            parameters={
                "cutoff_date": cutoff_date,
                "execution_context": {
                    "user": getpass.getuser(),
                    "host": socket.gethostname(),
                },
            },
        )
        # Run query
        df = pd.read_sql(rendered_query, conn)

    # Save CSV
    df.to_csv(OUTPUT_FILE, index=False)

    # Evidence: snapshot, hash, validations
    generator.save_data_snapshot(df, snapshot_rows=100)
    data_hash = generator.generate_integrity_hash(df)
    validations = validate_output(df)
    generator.save_validation_results(validations)
    zip_path = generator.finalize_evidence_package()

    print(f"Customer Accounts written: {OUTPUT_FILE}")
    print(f"Evidence: {zip_path}")


if __name__ == "__main__":
    main()
