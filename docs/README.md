# Documentation Index

Active documentation for SOXauto PG-01.

**Runtime**: Streamlit UI (`src/frontend/app.py`) and CLI (`scripts/run_headless_test.py`)
**Database**: SQL Server via Teleport (`tsh`)
**Pipeline**: Python extraction → reconciliation → evidence generation

---

## Architecture

- [DATA_ARCHITECTURE.md](architecture/DATA_ARCHITECTURE.md) — Current runtime architecture overview
- [reconciliation_phases.md](architecture/reconciliation_phases.md) — Phase 3 (reconciliation) and Phase 4 (bridges) design
- [ARCHITECTURE_DECISION_LOG.md](architecture/ARCHITECTURE_DECISION_LOG.md) — Key architectural decisions and pivots (ADR log)
- [NEW_ARCHITECTURE.mmd](architecture/NEW_ARCHITECTURE.mmd) — Architecture diagram (Mermaid)

## Setup

- [DATABASE_CONNECTION.md](setup/DATABASE_CONNECTION.md) — SQL Server connection via env vars and Teleport
- [OKTA_AWS_SETUP.md](setup/OKTA_AWS_SETUP.md) — AWS Okta SSO configuration
- [OKTA_QUICK_REFERENCE.md](setup/OKTA_QUICK_REFERENCE.md) — Quick Okta auth reference

## Deployment

- [sql_server_prerequisites.sql](deployment/sql_server_prerequisites.sql) — SQL Server prerequisites

## Development

- [ENTRY_POINTS.md](development/ENTRY_POINTS.md) — How to run the pipeline (UI, CLI, demos)
- [RUNNING_EXTRACTIONS.md](development/RUNNING_EXTRACTIONS.md) — SQL parameter execution guide
- [TESTING_GUIDE.md](development/TESTING_GUIDE.md) — Testing procedures
- [RECONCILIATION_FLOW.md](development/RECONCILIATION_FLOW.md) — End-to-end pipeline flow
- [evidence_documentation.md](development/evidence_documentation.md) — Digital evidence system specification
- [BRIDGES_RULES.md](development/BRIDGES_RULES.md) — Bridge classification rules
- [BUSINESS_LINE_RECLASS.md](development/BUSINESS_LINE_RECLASS.md) — Business line reclassification bridge
- [SCHEMA_CONTRACTS_COMPLETE.md](development/SCHEMA_CONTRACTS_COMPLETE.md) — Schema contract system (all 13 contracts)
- [THRESHOLD_CATALOG.md](development/THRESHOLD_CATALOG.md) — Variance threshold catalog
- [DATE_UTILS.md](development/DATE_UTILS.md) — Date normalization utilities
- [PANDAS_UTILS.md](development/PANDAS_UTILS.md) — Pandas type casting utilities
- [DEBUG_MAP.md](development/DEBUG_MAP.md) — Pipeline mental model and debug probe map
- [DEBUG_PROBE.md](development/DEBUG_PROBE.md) — Debug probe utility API reference
- [MERGE_AUDIT_GUIDE.md](development/MERGE_AUDIT_GUIDE.md) — Merge audit utility (Cartesian product detection)
- [QA_VERIFICATION_MULTI_ENTITY_VTC.md](development/QA_VERIFICATION_MULTI_ENTITY_VTC.md) — Multi-entity fixture and VTC date wiring QA

## Project History

- [project-history/ATHENA_ARCHITECTURE_DISCOVERY.md](project-history/ATHENA_ARCHITECTURE_DISCOVERY.md) — Athena exploration (Oct 2025, subsequently abandoned — see ADR-002)
- [project-history/REFACTORING_COMPLETE.md](project-history/REFACTORING_COMPLETE.md) — Jan 2025 core refactoring (Athena runner era, subsequently replaced)
- [project-history/REFACTORING_COMPLETE_V2.md](project-history/REFACTORING_COMPLETE_V2.md) — Final core package restructuring

## Archive

- [archive/2026-03-obsolete-architecture/](archive/2026-03-obsolete-architecture/) — Legacy Temporal/Athena/GCP/Fargate docs
- [development/archive/](development/archive/) — Historical working notes, migration drafts, prior iterations
