#!/usr/bin/env python3
"""
Generate Other AR related Accounts as CSV from contributing IPEs (e.g., IPE_10 prepayments, IPE_08 vouchers),
and produce SOX evidence for each contributing extraction.

Output: data/outputs/other_ar_related_accounts.csv (union of available contributing datasets)
Evidence: evidence/IPE_10/* and evidence/IPE_08/* (if queries exist); prints a manifest summary.

Notes:
- If a contributing IPE has no sql_query in the catalog, it is skipped with a warning.
- Union is column-wise (outer), with a 'source_i_item_id' column to indicate origin.
"""
import os
import sys
from typing import List, Tuple
import pandas as pd
import pyodbc
from datetime import datetime
import getpass
import socket

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.core.catalog.cpg1 import get_item_by_id  # noqa: E402
from src.core.evidence.manager import DigitalEvidenceManager, IPEEvidenceGenerator  # noqa: E402
from src.utils.sql_template import render_sql  # noqa: E402

CONTRIBUTORS = ["IPE_10", "IPE_08"]
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(REPO_ROOT, "data", "outputs"))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "other_ar_related_accounts.csv")


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


def run_contributor(ipe_id: str, conn: pyodbc.Connection) -> Tuple[str, pd.DataFrame, str]:
    item = get_item_by_id(ipe_id)
    if not item or not item.sql_query:
        print(f"[WARN] {ipe_id} missing sql_query; skipping")
        return ipe_id, pd.DataFrame(), ""

    evidence_manager = DigitalEvidenceManager("evidence")
    metadata = {
        "ipe_id": ipe_id,
        "description": item.title,
        "execution_start": datetime.now().isoformat(),
        "sox_compliance_required": True,
    }
    evidence_dir = evidence_manager.create_evidence_package(ipe_id, metadata)
    generator = IPEEvidenceGenerator(evidence_dir, ipe_id)

    cutoff_date = os.getenv("CUTOFF_DATE")
    rendered_query = render_sql(item.sql_query, {"cutoff_date": cutoff_date})
    generator.save_executed_query(
        rendered_query,
        parameters={
            "cutoff_date": cutoff_date,
            "contributor": ipe_id,
            "execution_context": {
                "user": getpass.getuser(),
                "host": socket.gethostname(),
            },
        },
    )
    df = pd.read_sql(rendered_query, conn)
    generator.save_data_snapshot(df)
    _ = generator.generate_integrity_hash(df)
    validations = {
        "completeness": {
            "expected_count": "> 0",
            "actual_count": int(len(df)),
            "status": "PASS" if len(df) > 0 else "FAIL",
        },
        "overall_status": "SUCCESS" if len(df) > 0 else "FAILED",
    }
    generator.save_validation_results(validations)
    zip_path = generator.finalize_evidence_package()
    return ipe_id, df, zip_path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cs = build_connection_string()
    combined: List[pd.DataFrame] = []
    manifest = []
    with pyodbc.connect(cs) as conn:
        for cid in CONTRIBUTORS:
            ipe_id, df, evidence_zip = run_contributor(cid, conn)
            if not df.empty:
                df = df.copy()
                df["source_item_id"] = ipe_id
                combined.append(df)
                manifest.append({"ipe_id": ipe_id, "rows": int(len(df)), "evidence": evidence_zip})

    if combined:
        final_df = pd.concat(combined, ignore_index=True, sort=True)
    else:
        final_df = pd.DataFrame()

    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Other AR related Accounts written: {OUTPUT_FILE} ({len(final_df)} rows)")
    print("Contributors:")
    for m in manifest:
        print(f"- {m['ipe_id']}: {m['rows']} rows; evidence: {m['evidence']}")


if __name__ == "__main__":
    main()
