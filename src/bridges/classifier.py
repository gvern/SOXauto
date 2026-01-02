"""
Rule-based classifier for PG-1 reconciliation bridges.

Takes input DataFrames (e.g., IPE_31 open items, IPE_10 prepayments) and applies
BridgeRule triggers to produce a standardized classification with GL expectations.

For NAV voucher categorization, use the modular pipeline from src.bridges.categorization:
- cat_nav_classifier: Integration type detection (Manual vs Integration)
- cat_issuance_classifier: Issuance categorization rules
- cat_usage_classifier: Usage categorization rules
- cat_vtc_classifier: VTC (Voucher to Cash) categorization rules
- cat_expired_classifier: Expired voucher categorization rules
- cat_pipeline: Main categorization pipeline (use categorize_nav_vouchers from src.bridges)
"""

from __future__ import annotations
from typing import List
import pandas as pd

from src.bridges.catalog import BridgeRule


def _row_matches_rule(row: pd.Series, rule: BridgeRule) -> bool:
    for col, values in rule.triggers.items():
        if col not in row.index:
            # If the column isn't present, this rule can't fire on this row
            return False
        val = row[col]
        if pd.isna(val):
            return False
        sval = str(val)
        if not any(sval == v or sval.lower() == str(v).lower() for v in values):
            return False
    return True


def classify_bridges(df: pd.DataFrame, rules: List[BridgeRule]) -> pd.DataFrame:
    """Return a copy of df with added classification columns:
    - bridge_key
    - bridge_title
    - dr_gl_accounts (comma string)
    - cr_gl_accounts (comma string)
    - required_enrichments (comma string)

    If multiple rules match, the first in the list wins (order defines priority).
    """
    if df is None or df.empty:
        return df.copy()

    out = df.copy()
    out["bridge_key"] = None
    out["bridge_title"] = None
    out["dr_gl_accounts"] = None
    out["cr_gl_accounts"] = None
    out["required_enrichments"] = None

    # Sort rules by explicit priority rank (lower is higher priority)
    rules_sorted = sorted(rules, key=lambda r: getattr(r, "priority_rank", 2))

    for idx, row in out.iterrows():
        for rule in rules_sorted:
            if _row_matches_rule(row, rule):
                out.at[idx, "bridge_key"] = rule.key
                out.at[idx, "bridge_title"] = rule.title
                out.at[idx, "dr_gl_accounts"] = ",".join(rule.dr_gl_accounts)
                out.at[idx, "cr_gl_accounts"] = ",".join(rule.cr_gl_accounts)
                out.at[idx, "required_enrichments"] = ",".join(
                    rule.required_enrichments
                )
                break

    return out


__all__ = [
    "classify_bridges",
]