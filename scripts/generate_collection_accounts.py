#!/usr/bin/env python3
"""
Generate Collection Accounts (from IPE_31) as CSV and produce SOX evidence.

Output: data/outputs/collection_accounts.csv
Evidence: evidence/IPE_31/<timestamp>/*

Assertions:
- Non-empty result
- Key columns exist: ID_Company, Event_date, Amount
"""
import os
import sys
import pandas as pd
import pyodbc
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.core.catalog.cpg1 import get_item_by_id  # noqa: E402
from src.core.evidence.manager import DigitalEvidenceManager, IPEEvidenceGenerator  # noqa: E402

ITEM_ID = "IPE_31"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(REPO_ROOT, "data", "outputs"))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "collection_accounts.csv")
KEY_COLUMNS = ["ID_Company", "Event_date", "Amount"]


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
    results = {
        "completeness": {
            "expected_count": "> 0",
            "actual_count": int(len(df)),
            "status": "PASS" if len(df) > 0 else "FAIL",
        }
    }
    missing = [c for c in KEY_COLUMNS if c not in df.columns]
    results["key_columns"] = {
        "required": KEY_COLUMNS,
        "missing": missing,
        "status": "PASS" if not missing else "FAIL",
    }
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
        generator.save_executed_query(item.sql_query)
        df = pd.read_sql(item.sql_query, conn)

    df.to_csv(OUTPUT_FILE, index=False)

    generator.save_data_snapshot(df)
    _ = generator.generate_integrity_hash(df)
    validations = validate_output(df)
    generator.save_validation_results(validations)
    zip_path = generator.finalize_evidence_package()

    print(f"Collection Accounts written: {OUTPUT_FILE}")
    print(f"Evidence: {zip_path}")


if __name__ == "__main__":
    main()
