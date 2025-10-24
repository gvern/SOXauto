# PROJECT DASHBOARD — SOXauto PG-01

> Source of truth for current priorities, status, and links. Updated: 2025-10-24

## Objectives

- Phase 1 (priority): Replicate the manual reconciliation process via MSSQL as described in `docs/development/TODO_MANUAL_PROCESS.md`.
- Phase 2 (target): Gradually migrate eligible IPEs to the AWS Athena architecture.

## Recent decisions

- Use a read-only MSSQL service account for direct access to the Data Warehouse (no intermediate ETL). Athena ingestion returns as a phase 2 target.
- While credentials are pending, progress in “offline mode” with a mocked MSSQL runner returning a test DataFrame and integrate the Digital Evidence Manager end to end.
- Orchestrate via `scripts/run_full_reconciliation.py` driven by the catalog.

## IPE progress status

| IPE | Summary | Source | Status | Owner |
|-----|---------|--------|--------|-------|
| IPE_07 | Customer balances (monthly balances) | MSSQL | To do | - |
| IPE_09 | BOB Sales Orders | MSSQL | To do | - |
| IPE_31 | PG detailed TV extraction | MSSQL | To do | - |

Notes:

- Statuses above describe the MSSQL phase replicating the manual process. The Athena target will follow.
- Update as work progresses (In progress, Blocked, Done) and add the owner.

## Current blockers (top-1)

- Waiting for read-only MSSQL service account credentials. On receipt: validate via `scripts/check_mssql_connection.py`.

## Plan while waiting for access — Parallel workstreams

Track progress with the checkboxes below. Goal: be plug-and-play when credentials arrive.

### Axis 1 — Application core (offline mode)

- [ ] Finalize `src/core/runners/mssql_runner.py` driven by the catalog (`src/core/catalog/cpg1.py`)
  - [ ] Load a catalog item by `item_id` and extract `sql_query`
  - [ ] Parameter handling (placeholders `{...}` via env/kwargs)
  - [ ] `_execute_mock_query()` returning a DataFrame from a CSV in `tests/fixtures/`
- [ ] Full Digital Evidence Manager integration
  - [ ] Pre-execution: create evidence folder
  - [ ] Save `01_executed_query.sql`
  - [ ] After mock: `03_data_snapshot.csv`, `04_data_summary.json`, `05_integrity_hash.json`
  - [ ] `06_validation_results.json` dummy (e.g., {"status": "PASS"})
  - [ ] `07_execution_log.json`
- [ ] Orchestrator `scripts/run_full_reconciliation.py` (loop IPEs, mock mode by default)

### Axis 2 — Tests (offline strategy)

- [ ] Unit tests for catalog `cpg1.py` (load by ID, missing ID → None, non-empty query)
- [ ] Integration tests with mocked runner
  - [ ] Orchestrator test: evidence folder creation
  - [ ] Evidence test: 7 files generated + SHA-256 check

### Axis 3 — Post-extraction business logic

- [ ] “Bridges & Adjustments” classifier module `src/agents/classifier.py`
  - [ ] Implement rules from `docs/development/BRIDGES_RULES.md`
  - [ ] Unit tests on small DataFrames
- [ ] Final visualization file generator (CSV/Excel) from results

### Axis 4 — Cleanup & documentation

- [ ] Clear docstrings in `cpg1.py`, `mssql_runner.py`, Evidence Manager
- [ ] Update this dashboard (Decisions, Next actions)
- [ ] Align `docs/development/TODO_MANUAL_PROCESS.md` as a checklist

## Key links

- Manual process to replicate: `docs/development/TODO_MANUAL_PROCESS.md`
- IPE catalog (definitions): `src/core/catalog/cpg1.py`
- Generated evidence folders: `evidence/`
- MSSQL connectivity scripts: `scripts/check_mssql_connection.py`

## Next actions (Phase 1)

1. Offline mode: complete Axis 1 (mocked runner + Evidence) and Axis 2 (tests)
2. Run `scripts/run_full_reconciliation.py` in mock mode on 1–2 IPEs (e.g., IPE_07)
3. Start Axis 3 (classifier + final export)
4. When MSSQL credentials arrive: switch to “live” execution (replace `_execute_mock_query()` with DB call)

## Progress indicators

- Axis 1: 0/6 | Axis 2: 0/3 | Axis 3: 0/3 | Axis 4: 0/3 (update as you go)

## Notes

- README is the target vision. This dashboard reflects the operational reality and should be the primary reference.
- Please archive obsolete docs under `docs/development/archive/` to reduce noise.
