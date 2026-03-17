# SOXauto PG-01 — Project Dashboard

> **Last Updated**: 16 March 2026
> **Branch**: `restore-queries-9c5e338`
> **Sprint Period**: Q1 2026

---

## Current Architecture

| Layer | Component | Status |
|-------|-----------|--------|
| **UI** | Streamlit (`src/frontend/app.py`) | ✅ Operational |
| **CLI** | `scripts/run_headless_test.py` | ✅ Operational |
| **Extraction** | `src/core/extraction_pipeline.py` | ✅ Operational |
| **DB Connection** | `src/core/runners/mssql_runner.py` + Teleport (`tsh`) | ✅ Operational |
| **Reconciliation** | `src/core/reconciliation/run_reconciliation.py` | ✅ Operational |
| **Evidence** | `src/core/evidence/manager.py` (SHA-256) | ✅ Operational |
| **Schema Validation** | `src/core/schema/` (YAML contracts) | ✅ Operational |
| **Bridge Analysis** | `src/bridges/` | ✅ Operational |
| **Orchestration** | Direct pipeline (no Airflow/Temporal) | ✅ Operational |

---

## IPE / CR Status

| ID | Description | SQL Query | Schema Contract | Status |
|----|-------------|-----------|-----------------|--------|
| IPE_07 | Customer balances | ✅ | ✅ | Complete |
| IPE_08 | Store credit vouchers TV | ✅ | ✅ | Complete |
| IPE_09 | BOB Sales Orders | ✅ | ✅ | Complete |
| IPE_10 | Customer prepayments TV | ✅ | ✅ | In Progress |
| IPE_11 | Seller Center Liability | ✅ | ✅ | Complete |
| IPE_12 | TV - Packages delivered not reconciled | ✅ | ✅ | In Progress |
| IPE_31 | PG detailed TV extraction | ✅ | ✅ | In Progress |
| IPE_34 | Marketplace refund liability | ✅ | ✅ | In Progress |
| CR_03 | CR reconciliation | ✅ | ✅ | Complete |
| CR_04 | CR reconciliation | ✅ | ✅ | Complete |
| CR_05 | CR reconciliation | ✅ | ✅ | Complete |
| DOC_VOUCHER_USAGE | Voucher usage documentation | ✅ | ✅ | Complete |

---

## Recent Completions

- ✅ Multi-entity VTC (Voucher Type Classification) support — `--company` param wiring
- ✅ `cutoff_date` param propagation fix in `calculate_vtc_adjustment`
- ✅ Multi-entity fixture loading for tests
- ✅ Schema contract system (14 contracts, YAML-based)
- ✅ Variance threshold catalog (YAML, per-country precedence)
- ✅ Debug probe instrumentation in `run_reconciliation.py`
- ✅ `build_nav_pivot()` implementation in `src/core/reconciliation/analysis/pivots.py`

---

## Known Issues / In Progress

| Issue | Owner | Priority |
|-------|-------|----------|
| IPE_10, IPE_12, IPE_31, IPE_34 SQL queries to validate on live DB | — | 🟠 Medium |
| FX conversion (`fx_utils.py`) integration into reconciliation pipeline | — | 🟠 Medium |
| Streamlit UI: add export to PDF for evidence packages | — | 🟡 Low |

---

## How to Run

```bash
# Streamlit UI (interactive)
streamlit run src/frontend/app.py

# CLI / headless (batch or CI)
python scripts/run_headless_test.py --cutoff-date 2025-09-30 --company EC_NG

# Offline demo (no DB required)
python scripts/run_demo.py --ipe IPE_07

# Full test suite
pytest tests/ -v
```

---

## Infrastructure

| Resource | Value |
|----------|-------|
| DB Server | `fin-sql.jumia.local` |
| Access Method | Teleport (`tsh login --proxy=teleport.jumia.com`) |
| AWS Account | `007809111365` (Data-Prod) |
| AWS Region | `eu-west-1` |
| S3 Evidence Bucket | `S3_BUCKET_EVIDENCE` env var |
| Auth | Okta SSO → AWS IAM Role → Secrets Manager |
