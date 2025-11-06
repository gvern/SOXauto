# Documentation Audit — 2025-11-06

This audit classifies all project documentation based on the final architecture pivot (Temporal.io orchestration + Teleport `tsh` to on‑prem MSSQL). It flags outdated content (Athena, Lambda/Fargate, GCP), misplaced files, and proposes a cleanup plan.

Legend

- KEEP: Current and aligned
- UPDATE: Still relevant but needs edits
- ARCHIVE: Move to docs/development/archive/ (historical)
- DELETE: Remove if duplicated/obsolete

## Top-Level

- README.md — UPDATE
  - Issues: Mentions Flask orchestrator and script entrypoints; current orchestration is Temporal.
  - Action: Add a “Current Architecture” section explicitly stating Temporal workflow (src/orchestrators/*) and that scripts/ are starters only. Keep demo instructions.
- PROJECT_DASHBOARD.md — KEEP
  - Up to date with Temporal + Teleport and current blockers.
- AUDIT_SUMMARY.md — REVIEW LATER
  - Depends on how you want to present to auditors; ensure it references the Digital Evidence package spec and Temporal run IDs.
- IMPLEMENTATION_SUMMARY.md — REVIEW LATER
  - Confirm alignment with final architecture; otherwise mark UPDATE.
- OBSOLETE_SCRIPTS.md — KEEP
  - Ensure it lists any scripts deprecated by Temporal pivot.

## Architecture

- docs/architecture/DATA_ARCHITECTURE.md — KEEP
  - Teleport + MSSQL is clearly described.
- docs/architecture/NEW_ARCHITECTURE.mmd — KEEP
  - Mentions Temporal Worker/Workflow; aligned.

## Deployment

- docs/deployment/aws_deploy.md — ARCHIVE
  - Issues: Heavy references to Athena, Lambda, ECS/Fargate, S3 staging for Athena.
  - Action: Move to archive with a note “replaced by Temporal Worker deployment”. Create a new doc: `docs/deployment/temporal_worker_deploy.md` covering: installing Teleport; configuring ODBC; running Temporal Worker; systemd/Docker Compose; environment.

## Development

- docs/development/README.md — ARCHIVE or HEAVY UPDATE
  - Issues: Focused on prior Athena/GCP phase; markdown style errors; misaligned with final architecture.
  - Action: Either move to archive or rewrite as a concise dev index pointing to Temporal and Evidence docs. Fix markdown linting when rewritten.
- docs/development/TESTING_GUIDE.md — UPDATE
  - Issues: Refers to GCP Secret Manager and Cloud Run; tests should center on Temporal worker activities and AWS Secrets Manager.
  - Action: Update prerequisites/env vars; add Temporal-oriented tests (activity retry, serialization); remove GCP sections.
- docs/development/RUNNING_EXTRACTIONS.md — UPDATE
  - Ensure it explains invoking workflow via Temporal (starter script) rather than direct script runners.
- docs/development/POC_FIRST_RUN_PLAN.md — ARCHIVE
  - Contains Athena/Glue/S3 guidance.
- docs/development/BRIDGES_RULES.md — KEEP
  - Business logic baseline; stays as-is.
- docs/development/RECONCILIATION_FLOW.md / RECONCILIATION_FLOW_DIAGRAM.md — KEEP
  - Ensure references align to Temporal orchestration; otherwise minor UPDATE.
- docs/development/TODO_MANUAL_PROCESS.md — KEEP
  - Process reference; not architecture-specific.
- docs/development/evidence_documentation.md — KEEP
  - Evidence 7-file spec; cross-link to Temporal integration.
- docs/development/archive/** — KEEP (as archive)
  - Already historical; leave in place.

## Setup

- docs/setup/DATABASE_CONNECTION.md — KEEP
  - Should reflect Teleport steps; if not, UPDATE.
- docs/setup/CONNECTION_STATUS.md — KEEP
  - Useful operational doc.
- docs/setup/DB_FALLBACK_SUMMARY.md — REVIEW LATER
  - Verify still applicable post-pivot.
- docs/setup/OKTA_AWS_SETUP.md, OKTA_QUICK_REFERENCE.md — KEEP
  - Still relevant for AWS Secrets access (Okta SSO into AWS).
- docs/setup/TIMING_DIFFERENCE_SETUP.md — KEEP
  - Business logic/setup; not architecture-specific.

## Project History

- docs/project-history/** — KEEP (history)
  - Contains GCP references; keep as historical context, don’t surface in primary index.

## Misplaced Content

- “deployment/aws_deploy.md” should move to archive. Replace with Temporal Worker deploy guide.
- Any dev quick-starts that run scripts directly should be updated to reference the Temporal starter script.

## Search Findings (Outdated References)

- Athena/Glue/S3: docs/development/POC_FIRST_RUN_PLAN.md, docs/deployment/aws_deploy.md
- Lambda/ECS/Fargate: docs/deployment/aws_deploy.md
- GCP/Cloud Run: docs/project-history/PHASE_COMPLETE_SUMMARY.md and others (history only); docs/development/TESTING_GUIDE.md (needs update)

## Proposed Information Architecture (IA)

- docs/
  - README.md (index) — succinct map of active docs
  - architecture/ (KEEP)
  - deployment/
    - temporal_worker_deploy.md (NEW, replaces aws_deploy.md)
  - development/
    - evidence_documentation.md (KEEP)
    - BRIDGES_RULES.md (KEEP)
    - TESTING_GUIDE.md (UPDATED for Temporal/AWS SM)
    - RUNNING_EXTRACTIONS.md (UPDATED for Temporal)
    - RECONCILIATION_FLOW*.md (KEEP/UPDATE minor)
    - archive/ (KEEP)
  - setup/ (KEEP)
  - project-history/ (KEEP)

## Quick Fixes (Low-Risk, High-Value)

- Add a banner in README.md: “Update 2025‑11‑06: Orchestration is Temporal.io; previous Flask and serverless (Lambda/Fargate) approaches are deprecated. See src/orchestrators/*.”
- Replace docs/deployment/aws_deploy.md with a new Temporal Worker deploy guide, then move the old file to archive.
- Update TESTING_GUIDE.md to remove GCP references; add sections for Temporal activity retry and evidence generation assertions.
- Fix markdown style warnings when touching docs (blank lines around headers/lists; language tags on fenced blocks).

## Action Plan (Prioritized)

1) Replace deployment guide with Temporal Worker deployment (NEW doc) and archive the old AWS deploy doc.
2) Patch top-level README.md with an “Architecture Update” note + link to orchestrators.
3) Update TESTING_GUIDE.md for AWS Secrets Manager + Temporal; remove GCP.
4) Create docs/README.md as a short index of current docs and hide archived/history paths from newcomers.
5) Sweep development/ for Athena/Lambda mentions and move those docs to archive.

## Notes

- Do not edit the validated SQL baselines in documentation; treat them as references only.
- When archiving, add a one‑line reason and a link to the new authoritative doc.
