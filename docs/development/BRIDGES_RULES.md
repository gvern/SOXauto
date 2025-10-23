# Bridges and Adjustments Rules (Phase 2)

This document captures the business rules extracted from the provided table and how they map into our rule engine.

## High-level

- Source datasets: IPE_31 (Collections open items), IPE_10 (Prepayments TV), IPE_07 (Customer balances), and related CRs.
- Output: Classified variances with `bridge_key`, GL expectations (Dr/Cr), and required enrichment hints.

## Rules Summary

- CASH_DEPOSITS
  - Triggers: Transaction_Type in [Transfer to, Third Party Collection, Payment - Rev, Translist in progress, Payment, Transfer]
  - GL: Dr 100XX, Cr 13011/13012/10590
  - Enrich: bank_posting_group (NAV Bank Accounts + Posting Group join)
  - Priority: High

- CASH_DEPOSITS_CANCEL
  - Triggers: [Payment Charges Rev, Transfer From, Reallocation From]
  - GL: Dr 13011/13012/10590, Cr 100XX

- JFORCE_PAYOUTS
  - Triggers: [JForce Payout, Payment]
  - GL: Dr 18307, Cr 18412
  - Enrich: jforce_voucher_only (only when voucher is the payment method)

- PAYMENT_RECONCILES
  - Triggers: [Payment, Transfer to, Third Party Collection]
  - GL: Dr 13024, Cr 13011/13012/10590

- PREPAID_DELIVERIES / PREPAYMENTS
  - Trigger: IS_PREPAYMENT = 1
  - GL: Prepaid deliveries Dr 18350 Cr 18314; Prepayments Dr 13012/13030 Cr 18350

- REFUNDS
  - Triggers: [Refund]
  - GL: Retail -> Cr 13005; MPL -> Cr 18317; Dr side varies by refund method (100XX, 18412, JPay, etc.)
  - Enrich: refund_channel (Retail vs MPL)

- SALES_CREDIT_MEMOS
  - Triggers: [Sales Credit Memo]
  - GL: Dr 30101/30102, Cr 13005
  - Enrich: customer_type_flag (individual vs corporate)

- SALES_DELIVERIES
  - Triggers: [Delivery, DELIVERED]
  - GL: Dr 13005, Cr 300XX
  - Priority: High

- SC_ACCOUNT_STATEMENT / SELLER_ACCOUNT_STATEMENTS
  - GL: Dr 18314, Cr 13023

## Enrichment Notes

- bank_posting_group
  - We expose both `G_L Bank Account No_` and `Bank_Account_Posting_Group` in `IPE_31` SQL.
- refund_channel
  - Stub in `src/utils/sql_enrichment.py` using `RPT_SOI` (MPL flag). Wire in as needed.
- customer_type_flag
  - Source TBD (customer master) to distinguish 30101 (individual) vs 30102 (corporate).

## How to run

1. Generate inputs (CSV) via the existing scripts (pending DB connectivity):
   - `scripts/generate_collection_accounts.py` (IPE_31)
   - `scripts/generate_customer_accounts.py` (IPE_07)
   - `scripts/generate_other_ar.py` (includes IPE_10)
2. Classify bridges offline:
   - `python scripts/classify_bridges.py`
   - Output: `data/outputs/bridges_classified.csv`

## Next steps

- Connect enrichment functions to live DB and add an optional `--enrich` mode performing lookups.
- Add consolidation with CR_04 actuals and compute variance by GL & company.
- Extend rules based on reviewers' feedback.
