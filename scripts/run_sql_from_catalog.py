#!/usr/bin/env python3
"""
Manual extractor: Run SQL Server queries from catalog and export CSVs for intermediate Google Sheets.

- Reads items from src.core.catalog.cpg1.CPG1_CATALOG
- Filters items with sql_query defined
- Executes queries against SQL Server via pyodbc
- Writes results to data/outputs/{item_id}.csv

Usage:
  python scripts/run_sql_from_catalog.py [--only IPE_07,CR_04] [--outdir data/outputs]

DB connection:
  Use DB_CONNECTION_STRING env var (recommended). Example:
    Driver={ODBC Driver 18 for SQL Server};Server=server;Database=db;UID=user;PWD=pass;TrustServerCertificate=yes;

  Or provide components via env:
    MSSQL_DRIVER, MSSQL_SERVER, MSSQL_DATABASE, MSSQL_USER, MSSQL_PASSWORD

Notes:
  - This script does NOT upload to Google Sheets. After CSVs are written, you can import them manually to Google Sheets,
    or we can wire up pygsheets in a follow-up once service account creds are available.
"""
import argparse
import os
import sys
import time
from typing import List, Optional

import pandas as pd
import pyodbc

# Add repo root for imports when running directly
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.core.catalog.cpg1 import CPG1_CATALOG  # noqa: E402
from src.utils.sql_template import render_sql  # noqa: E402


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
    # TrustServerCertificate helps with local/dev TLS; can be removed in prod with proper CA
    return (
        f"Driver={{{{ {driver} }}}};"
        f"Server={server};Database={database};"
        f"UID={user};PWD={password};TrustServerCertificate=yes;"
    )


def get_items_to_run(only_ids: Optional[List[str]]) -> List:
    items = [it for it in CPG1_CATALOG if it.sql_query]
    if only_ids:
        wanted = set(x.strip() for x in only_ids)
        items = [it for it in items if it.item_id in wanted]
    return items


def run_query_to_csv(conn: pyodbc.Connection, item, outdir: str) -> str:
    params = {
        "cutoff_date": os.getenv("CUTOFF_DATE"),
        "year_start": os.getenv("YEAR_START"),
        "year_end": os.getenv("YEAR_END"),
        "fx_date": os.getenv("FX_DATE"),
    }
    rendered = render_sql(item.sql_query, params)
    df = pd.read_sql(rendered, conn)
    os.makedirs(outdir, exist_ok=True)
    out_path = os.path.join(outdir, f"{item.item_id}.csv")
    df.to_csv(out_path, index=False)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Run catalog SQL items and export to CSV")
    ap.add_argument("--only", help="Comma-separated item_ids to run (e.g., IPE_07,CR_04)")
    ap.add_argument("--outdir", default="data/outputs", help="Output directory for CSVs")
    args = ap.parse_args()

    only_ids = args.only.split(",") if args.only else None
    items = get_items_to_run(only_ids)

    if not items:
        print("No items with sql_query found to run.")
        sys.exit(0)

    cs = build_connection_string()
    print(f"Connecting to SQL Server...")
    with pyodbc.connect(cs) as conn:
        print(f"Connected. Running {len(items)} item(s)...")
        results = []
        for it in items:
            t0 = time.time()
            print(f"- {it.item_id}: {it.title}")
            try:
                out_path = run_query_to_csv(conn, it, args.outdir)
                elapsed = time.time() - t0
                results.append((it.item_id, out_path, elapsed))
                print(f"  -> OK: {out_path} ({elapsed:.1f}s)")
            except Exception as e:
                print(f"  -> ERROR: {e}")
    print("Done.")


if __name__ == "__main__":
    main()
