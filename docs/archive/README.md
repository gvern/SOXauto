# Documentation Archive

This folder stores documentation that is no longer valid for the active runtime architecture.

## Purpose

- Preserve historical decisions and migration context
- Keep active documentation clean and actionable
- Avoid mixing obsolete runbooks with current operating instructions

## Current Archive Buckets

- `2026-03-obsolete-architecture/`
  - Legacy Temporal/Athena/GCP/Fargate architecture docs and superseded runbooks
  - Includes: `DB_FALLBACK_SUMMARY.md` (Secrets Manager approach), `CONNECTION_STATUS.md` (stale log), `PHASE_COMPLETE_SUMMARY.md` (Oct 2024, GCP refs)

## Rule

If a document is no longer operationally correct, move it to `docs/archive/` and remove it from active indexes.
