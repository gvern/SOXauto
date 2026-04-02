# Architecture Decision Log

This document records key architectural decisions and pivots made during the SOXauto PG-01 project. Each entry explains what was decided, why, and what approach it replaced.

---

## ADR-001 — GCP/Cloud Run + Secret Manager (Initial, Oct 2024)

**Decision**: Deploy the pipeline as a Cloud Run service on GCP, with SQL Server credentials in GCP Secret Manager.

**Approach**:
- `gcp_utils.py` for Secret Manager access
- Credentials fetched at runtime from `DB_CREDENTIALS_NAV_BI`
- GCP environment variables: `GCP_PROJECT_ID`, `GCP_REGION`

**Outcome**: Abandoned. SQL Server (`fin-sql.jumia.local`) was on-prem and not accessible from GCP Cloud Run. Athena was investigated as an alternative.

**Archive**: `docs/archive/2026-03-obsolete-architecture/`, `docs/project-history/PHASE_COMPLETE_SUMMARY.md`

---

## ADR-002 — AWS Athena as Query Layer (Oct 2025, Abandoned)

**Decision**: Pivot from SQL Server via pyodbc to AWS Athena + S3 as the query engine.

**Rationale at the time**: AWS Athena had 148 databases visible, including `process_pg_bob`. Seemed cloud-native, scalable, IAM-based.

**Approach**:
- `src/core/runners/athena_runner.py` (`IPERunnerAthena`)
- `awswrangler` library for `wr.athena.read_sql_query()`
- Separate `config_athena.py` with `athena_database` / `athena_table` fields

**Why it was abandoned**: NAV_BI and FINREC tables (containing the GL entries, customer ledger entries, etc.) were not replicated to Athena. Only BOB tables were available. The Athena path would not have covered the core reconciliation data sources.

**Resolution**: Switched to direct SQL Server access via Teleport (see ADR-003).

**Archive**: `docs/archive/2026-03-obsolete-architecture/MIGRATION_SQL_TO_ATHENA.md`, `docs/project-history/ATHENA_ARCHITECTURE_DISCOVERY.md`, `docs/project-history/REFACTORING_COMPLETE.md`

---

## ADR-003 — SQL Server via Teleport (Nov 2025, Current)

**Decision**: Access SQL Server directly using a Teleport (`tsh`) tunnel + `pyodbc`.

**Approach**:
- Authenticate: `tsh login` → `tsh db proxy fin-sql.jumia.local`
- Execute via `pyodbc` ODBC connection to `fin-sql.jumia.local`
- No cloud credentials required; connection string set via env var `DB_CONNECTION_STRING`
- Runner: `src/core/runners/mssql_runner.py`

**Why**: Direct access to all required databases (NAV_BI, FINREC, BOB) via secure Teleport tunnel. No dependency on Athena availability. Lower latency and no S3 staging overhead.

**Orchestration impact**: Temporal orchestration was retired during this pivot (Nov 2025), in favor of simpler direct execution patterns.

**Current status**: Active. Documented in `docs/setup/DATABASE_CONNECTION.md` and `docs/setup/OKTA_AWS_SETUP.md`.

---

## ADR-004 — Apache Airflow Orchestration Trial (Jan-Feb 2026, Abandoned)

**Decision**: Introduce Apache Airflow as the orchestration layer for scheduled and repeatable reconciliation runs.

**Rationale at the time**: Airflow offered familiar DAG scheduling, retry policies, and operational visibility for batch workloads.

**Approach**:
- Airflow-oriented runtime and documentation for DAG/task execution
- SQL extraction tasks still executed against SQL Server via Teleport
- Intended use: scheduled monthly reconciliations with centralized monitoring

**Why it was abandoned**: The team's operating model remained primarily user-triggered (UI/CLI, on-demand runs). Airflow scheduling and infra management introduced overhead without delivering clear value over direct execution.

**Resolution**: Airflow orchestration was removed in favor of direct Python entry points (see ADR-005).

**Archive**: `docs/archive/2026-03-obsolete-architecture/`

---

## ADR-005 — Drop Airflow/Fargate Orchestration (Feb 2026)

**Decision**: Remove Apache Airflow and AWS Fargate from the architecture.

**Replaced**: Airflow runtime/scheduling layer and Fargate task definitions.

**Why**: The reconciliation pipeline is primarily user-triggered (UI/CLI, on-demand runs). Airflow scheduling and Fargate infra added operational overhead without clear value for this usage model.

**Timeline note**: Temporal had already been removed in Nov 2025 (ADR-003).

**Current approach**: Direct Python execution via:
- Streamlit UI: `src/frontend/app.py`
- CLI headless runner: `scripts/run_headless_test.py`

Both call the same `src/core/reconciliation/run_reconciliation.py` engine directly.

**Archive**: `docs/archive/2026-03-obsolete-architecture/temporal_worker_deploy.md`, `docs/development/archive/aws_deploy_FARGATE_OBSOLETE.md`

---

## ADR-006 — Schema Contract System (Jan 2026, Current)

**Decision**: Implement YAML-based schema contracts for all IPE/CR/DOC extractions.

**Problem solved**: Column names varied across SQL query outputs (e.g., `Customer No_`, `customer_no`, `CustomerNo`). Each bridge script had its own `_normalize_column_names()` function — fragile and inconsistent.

**Approach**:
- YAML contracts in `src/core/schema/contracts/*.yaml` (13 contracts)
- `apply_schema_contract()` normalizes columns after every SQL extraction
- Full transformation event tracking — lineage stored in evidence package (`08_schema_validation.json`, `09_transformations_log.json`)
- Auto-generates quality rules from contracts

**Current status**: Active. Fully integrated into `mssql_runner.py` and `evidence/manager.py`. Documented in `docs/development/SCHEMA_CONTRACTS_COMPLETE.md`.

---

## ADR-007 — src/core Package Refactoring (Jan 2026)

**Decision**: Reorganize flat `src/core/` structure into sub-packages.

**Before**: `ipe_runner.py`, `config.py`, `config_athena.py`, `evidence_manager.py` all at `src/core/` root.

**After**:
```
src/core/
├── catalog/cpg1.py       # single source of truth for IPE/CR definitions
├── runners/mssql_runner.py
├── evidence/manager.py
├── reconciliation/       # Phase 3 logic
└── schema/               # Schema contract system
```

**Note**: This refactoring initially also created `runners/athena_runner.py`, which was later removed when Athena was abandoned (see ADR-002).

**Archive**: `docs/project-history/REFACTORING_COMPLETE_V2.md`

---

## ADR-008 — Phase 3/4 Reconciliation Architecture (Jan 2026, Current)

**Decision**: Separate reconciliation concerns into Phase 3 (reconciliation + voucher classification) and Phase 4 (bridge analysis).

**Phase 3** (`src/core/reconciliation/`):
- Voucher lifecycle classification (manual vs integration, issuance/usage/VTC/expired)
- Variance analysis (NAV vs Target Values)

**Phase 4** (`src/bridges/`):
- Entity-level bridge calculations: timing difference, VTC adjustment, business line reclassification
- Each bridge returns: amount + proof DataFrame + metrics

**Why**: Separates "why is there variance" (reconciliation) from "how much variance does each category explain" (bridges). Auditors need both layers.

**Documented in**: `docs/architecture/reconciliation_phases.md`
