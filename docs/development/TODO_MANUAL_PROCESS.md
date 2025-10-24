# PG-01 Manual Process Replication — To‑Do & Progress

Last updated: 2025-10-23
Scope: Reproduce the existing manual workflow via SQL Server (no Athena), generating intermediate files then a final consolidation.

---

## 🎯 Objectives

- Replace manual Power BI/PowerPivot exports with Python scripts that query SQL Server and write identical intermediate files.
- Keep the catalog (`src/core/catalog/cpg1.py`) as the single source of truth (queries + source mapping).
- Use the evidence system to capture executed queries, snapshots, and validation metadata.

---

## 🧭 High-level flow (target)

```mermaid
graph td
    subgraph "Data Source (SQL Server)"
        A[NAV BI / FINREC / BOB]
    end

    subgraph "Manual Step 1: Extractions via Power BI / Power Pivot"
        B1[IPE_07 Query]
        B2[IPE_31 Query]
        B3[IPE_10, IPE_08, etc. Queries]
        A --> B1
        A --> B2
        A --> B3
    end

    subgraph "Manual Step 2: Intermediate Files"
        C1[Customer Accounts.csv]
        C2[Collection Accounts.csv]
        C3[Other AR related Accounts.csv]
        B1 --> C1
        B2 --> C2
        B3 --> C3
    end

    subgraph "Manual Step 3: Final Consolidation"
        D[Consolidation.xlsx]
        C1 --> D
        C2 --> D
        C3 --> D
    end
```

---

## ✅ Status Dashboard

Legend: [ ] Not started · [~] In progress · [x] Done

- [x] Catalog pivot away from Athena (retain SQL queries/descriptions)
- [x] IPE_07 SQL present in catalog (restored)
- [x] Generic SQL→CSV runner in `scripts/run_sql_from_catalog.py`
- [~] Confirm SQL Server access path (Teleport/fin-sql.jumia.local) — connectivity script/docs in place; run pending
- [ ] Map exact content/columns for 3 intermediates
- [~] Implement Customer Accounts export (IPE_07) with evidence — script implemented; evidence package scaffolding present; awaiting live run
- [~] Implement Collection Accounts export (IPE_31) with evidence — script implemented; evidence package scaffolding present; awaiting live run
- [~] Implement Other AR related Accounts export (IPE_10, IPE_08, …) with evidence — umbrella generator implemented; IPE_08 query TBD
- [ ] Build Consolidation.xlsx (join + variances) with evidence
- [ ] Integrate Bridges/Timing Differences classification
- [x] Update DB connection docs and Dockerfile ODBC setup
- [x] Minimal smoke tests
- [ ] Optional: Google Sheets upload of outputs

---

## 📌 Immediate priorities (this sprint)

1. Access & Connectivity

- Decide on Teleport or direct connection; obtain a programmatic path to `fin-sql.jumia.local`.
- Set `DB_CONNECTION_STRING` for local/dev; mirror inside Docker.
- Install Microsoft ODBC Driver 18 for SQL Server (local + Docker).

1. Customer Accounts (IPE_07)

- Run `sql_query` from catalog and write `data/outputs/customer_accounts.csv`.
- Match manual columns and data types; confirm record counts.
- Generate evidence (executed query, snapshot, validation summary).

1. Collection Accounts (IPE_31)

- Execute the 7-table join; produce `collection_accounts.csv`.
- Validate joins/filters with a quick row-count/witness check.
- Evidence package.

---

## 🧩 Implementation notes

- Catalog: `src/core/catalog/cpg1.py` — contains `sql_query` for CR_05, CR_05a, IPE_10, IPE_31, CR_04, and IPE_07.
- Generic runner: `scripts/run_sql_from_catalog.py` — can export by `--only IPE_07,CR_04` to `data/outputs`.
- Evidence: `src/core/evidence/manager.py` — agnostic; integrate into per-file export scripts.
- SQL driver: prefer ODBC Driver 18; for dev, `TrustServerCertificate=yes` may be needed; remove in prod with proper CA.

---

## 📦 Deliverables per file

Each intermediate must include:

- Reproducible SQL (exact text saved in evidence)
- CSV export with expected columns/dtypes
- Evidence package (query + snapshot + validations)

### Customer Accounts.csv (IPE_07)

- Sources: NAV BI Detailed Customer Ledg. Entry, Customer Ledger Entries
- Output: `data/outputs/customer_accounts.csv`
- Acceptance: Row count ±1% vs manual; column parity; random spot checks.

### Collection Accounts.csv (IPE_31)

- Sources: RPT_CASHREC_\* tables, PACKLIST_\* tables, hubs mapping, IFRS mapping
- Output: `data/outputs/collection_accounts.csv`
- Acceptance: Row count parity; curated witness transactions present.

### Other AR related Accounts.csv

- Sources: IPE_10 (prepayments), IPE_08 (vouchers), others
- Output: `data/outputs/other_ar_related_accounts.csv`
- Acceptance: Aggregate totals match manual; specific filters replicated.

### Consolidation.xlsx

- Inputs: three intermediates + CR_04 (actuals)
- Output: `data/outputs/consolidation.xlsx`
- Acceptance: Variances identical to manual; bridges ready for classification.

---

## 🛠️ How to try the generic runner (dev)

Prereqs:

- Set `DB_CONNECTION_STRING` (ODBC) or MSSQL_* env vars
- Ensure msodbcsql18 is installed locally

Examples:

```bash
# Export just IPE_07 to CSV
python scripts/run_sql_from_catalog.py --only IPE_07 --outdir data/outputs

# Export multiple (e.g., IPE_07 and CR_04 actuals)
python scripts/run_sql_from_catalog.py --only IPE_07,CR_04 --outdir data/outputs
```

---

## 🧰 Per-file generators (with evidence)

- Customer Accounts: `scripts/generate_customer_accounts.py`
- Collection Accounts: `scripts/generate_collection_accounts.py`
- Other AR related Accounts: `scripts/generate_other_ar.py`

All scripts write to `data/outputs/` and produce evidence packages under `evidence/<IPE_ID>/`.

---

## 🔐 Open questions / blockers

- Programmatic access to `fin-sql.jumia.local` (Teleport path?)
- Required network/ports from dev/Docker to SQL Server
- Service account for optional Google Sheets upload (if used)

---

## 🧾 Change log (brief)

- 2025-10-23: Catalog de-Athena, added generic runner, defined manual replication plan
