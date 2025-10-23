"""
SQL-based enrichment helpers (stubs) for bridge classification.

These functions are thin wrappers around SQL Server lookups to add business flags
needed for classification. They are intentionally simple and can be optimized later.
"""
from __future__ import annotations
from typing import Optional
import pandas as pd
import pyodbc


def get_bank_posting_group(conn: pyodbc.Connection, service_provider_no: str, id_company: Optional[str] = None) -> Optional[str]:
    """Return the Bank Account Posting Group code for a given Service Provider No_.

    If multiple matches, returns an arbitrary first; callers may need to disambiguate by company.
    """
    q = """
    SELECT TOP 1 bapg.[Code]
    FROM [AIG_Nav_DW].[dbo].[Bank Accounts] b
    LEFT JOIN [AIG_Nav_DW].[dbo].[Bank Account Posting Group] bapg
      ON bapg.[ID_Company] = b.[ID_Company] AND bapg.[Code] = b.[Bank Account Posting Group]
    WHERE b.[Service Provider No_] = ?
    {company_filter}
    """.format(company_filter=("AND b.[ID_Company] = ?" if id_company else ""))
    params = [service_provider_no]
    if id_company:
        params.append(id_company)
    try:
        cur = conn.cursor()
        row = cur.execute(q, params).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def get_refund_channel(conn: pyodbc.Connection, order_nr: str) -> Optional[str]:
    """Return refund channel for an order (e.g., 'Retail' or 'MPL'), derived from OMS records.

    This is a stub: adapt the FROM/WHERE to the canonical OMS source used for refunds.
    """
    q = """
    SELECT TOP 1 CASE WHEN IS_MARKETPLACE = 1 THEN 'MPL' ELSE 'Retail' END AS channel
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
    WHERE [ORDER_NR] = ?
    """
    try:
        cur = conn.cursor()
        row = cur.execute(q, [order_nr]).fetchone()
        return row[0] if row else None
    except Exception:
        return None


__all__ = ["get_bank_posting_group", "get_refund_channel"]
