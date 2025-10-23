"""
Bridge rules catalog for classifying reconciliation variances (PG-1).

Each rule maps business transaction signals (e.g., Transaction_Type, source system fields)
into a canonical "bridge_type" with expected GL accounts (Dr/Cr) and required enrichments.

This is phase 2 of the pipeline and complements the raw extractions (IPE_07, IPE_31, IPE_10, etc.).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class BridgeRule:
    key: str  # e.g., CASH_DEPOSITS, REFUNDS
    title: str
    triggers: Dict[str, List[str]]  # column_name -> list of values (any match triggers)
    dr_gl_accounts: List[str] = field(default_factory=list)
    cr_gl_accounts: List[str] = field(default_factory=list)
    required_enrichments: List[str] = field(default_factory=list)  # e.g., ["bank_posting_group", "refund_channel"]
    notes: Optional[str] = None
    priority: str = "medium"  # label for docs: low | medium | high
    priority_rank: int = 2     # explicit ordering used by classifier: 1=high,2=medium,3=low


def load_rules() -> List[BridgeRule]:
    """Return the initial set of bridge rules distilled from the provided business table.

    Notes on enrichments:
    - bank_posting_group: Requires joining NAV Bank Accounts + Bank Account Posting Group by Service Provider No.
    - refund_channel: Requires OMS fields to distinguish Retail vs MPL; may use existing flags in RPT_SOI or related.
    - jforce_voucher_only: Consider only payments by voucher when evaluating JForce payouts.
    """
    rules: List[BridgeRule] = [
        BridgeRule(
            key="CASH_DEPOSITS",
            title="Cash deposits pending application",
            triggers={"Transaction_Type": ["Transfer to", "Third Party Collection", "Payment - Rev", "Translist in progress", "Payment", "Transfer"]},
            dr_gl_accounts=["100XX"],
            cr_gl_accounts=["13011", "13012", "10590"],
            required_enrichments=["bank_posting_group"],
            notes=(
                "We only have Service Provider No. in extract (IPE_31). Join NAV bank accounts to fetch Bank Account Posting Group and G/L Bank Account."
            ),
            priority="high",
            priority_rank=1,
        ),
        BridgeRule(
            key="CASH_DEPOSITS_CANCEL",
            title="Cash deposit cancellations",
            triggers={"Transaction_Type": ["Payment Charges Rev", "Transfer From", "Reallocation From"]},
            dr_gl_accounts=["13011", "13012", "10590"],
            cr_gl_accounts=["100XX"],
            required_enrichments=["bank_posting_group"],
            priority="medium",
            priority_rank=2,
        ),
        BridgeRule(
            key="JFORCE_PAYOUTS",
            title="JForce payouts by voucher",
            triggers={"Transaction_Type": ["JForce Payout", "Jforce Payouts", "Payment"]},
            dr_gl_accounts=["18307"],
            cr_gl_accounts=["18412"],
            required_enrichments=["jforce_voucher_only"],
            notes="Only consider when payment method is voucher; other methods handled by other controls.",
            priority="medium",
            priority_rank=2,
        ),
        BridgeRule(
            key="PAYMENT_RECONCILES",
            title="Payments reconciled timing differences",
            triggers={"Transaction_Type": ["Payment", "Transfer to", "Third Party Collection"]},
            dr_gl_accounts=["13024"],
            cr_gl_accounts=["13011", "13012", "10590"],
            required_enrichments=["bank_posting_group"],
            priority="medium",
            priority_rank=2,
        ),
        BridgeRule(
            key="PREPAID_DELIVERIES",
            title="Prepaid deliveries in transit",
            triggers={"IS_PREPAYMENT": ["1", "True", "true", "YES", "Yes"]},
            dr_gl_accounts=["18350"],
            cr_gl_accounts=["18314"],
            required_enrichments=[],
            priority="low",
            priority_rank=3,
        ),
        BridgeRule(
            key="PREPAYMENTS",
            title="Customer prepayments (TV)",
            triggers={"IS_PREPAYMENT": ["1", "True", "true", "YES", "Yes"]},
            dr_gl_accounts=["13012", "13030"],
            cr_gl_accounts=["18350"],
            required_enrichments=["payment_provider_channel_optional"],
            priority="medium",
            priority_rank=2,
        ),
        BridgeRule(
            key="REFUNDS",
            title="Refunds - retail vs MPL",
            triggers={"Transaction_Type": ["Refund", "REFUND", "Refunds"]},
            dr_gl_accounts=["100XX", "18412"],
            cr_gl_accounts=["13005", "18317"],
            required_enrichments=["refund_channel"],
            notes="Need a flag to identify retail (B2C) vs MPL; use OMS/RPT_SOI fields or joins.",
            priority="medium",
            priority_rank=2,
        ),
        BridgeRule(
            key="SALES_CREDIT_MEMOS",
            title="Sales credit memos",
            triggers={"Transaction_Type": ["Sales Credit Memo"]},
            dr_gl_accounts=["30101", "30102"],
            cr_gl_accounts=["13005"],
            required_enrichments=["customer_type_flag"],
            priority="low",
            priority_rank=3,
        ),
        BridgeRule(
            key="SALES_DELIVERIES",
            title="Sales deliveries not posted",
            triggers={"Transaction_Type": ["Delivery", "DELIVERED"]},
            dr_gl_accounts=["13005"],
            cr_gl_accounts=["300XX"],
            required_enrichments=[],
            notes="High financial impact; prioritize.",
            priority="high",
            priority_rank=1,
        ),
        BridgeRule(
            key="SC_ACCOUNT_STATEMENT",
            title="Seller Center account statements",
            triggers={"Source": ["Seller Center", "SC"], "Entity": ["Account Statement"]},
            dr_gl_accounts=["18314"],
            cr_gl_accounts=["13023"],
            required_enrichments=[],
            priority="medium",
            priority_rank=2,
        ),
        BridgeRule(
            key="SELLER_ACCOUNT_STATEMENTS",
            title="Seller account statements",
            triggers={"Source": ["Seller", "MPL"], "Entity": ["Account Statement"]},
            dr_gl_accounts=["18314"],
            cr_gl_accounts=["13023"],
            required_enrichments=[],
            priority="medium",
            priority_rank=2,
        ),
    ]
    return rules


__all__ = ["BridgeRule", "load_rules"]
