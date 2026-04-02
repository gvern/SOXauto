# Development Documentation - C-PG-1 SOXauto

**Last Updated**: 16 March 2026
**Project**: C-PG-1 Physical Goods — IBSAR (Integrated Balance Sheet Accounts Reconciliation) Automation
**Status**: Active — Direct pipeline + Streamlit UI

---

## Quick Start

### New to the Project?
1. Read [`README.md`](../../README.md) at the repo root — full architecture overview
2. See [`ENTRY_POINTS.md`](ENTRY_POINTS.md) — how to run reconciliations (UI + CLI)
3. See [`evidence_documentation.md`](evidence_documentation.md) — SOX evidence package spec

### Catalog
- Location: `src/core/catalog/cpg1.py`
- Contents: IPE_07, IPE_08, IPE_09, IPE_10, IPE_11, IPE_12, IPE_31, IPE_34, CR_03, CR_04, CR_05, DOC_VOUCHER_USAGE

---

## Active Documentation Files

### Core Reference

| File | Purpose | Audience |
|------|---------|----------|
| [ENTRY_POINTS.md](ENTRY_POINTS.md) | CLI and Streamlit UI entry points | All |
| [RUNNING_EXTRACTIONS.md](RUNNING_EXTRACTIONS.md) | SQL parameters and environment variables | Developers |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Testing procedures and validation | Developers & QA |
| [evidence_documentation.md](evidence_documentation.md) | SOX evidence package (8-file system) | Auditors & Developers |
| [RECONCILIATION_FLOW.md](RECONCILIATION_FLOW.md) | Full reconciliation pipeline description | Technical Team |

### Utils & Code Reference

| File | Purpose |
|------|---------|
| [DATE_UTILS.md](DATE_UTILS.md) | `src/utils/date_utils.py` API reference |
| [PANDAS_UTILS.md](PANDAS_UTILS.md) | `src/utils/pandas_utils.py` API reference |
| [MERGE_AUDIT_GUIDE.md](MERGE_AUDIT_GUIDE.md) | `src/utils/merge_utils.py` — Cartesian product detection |
| [AUDIT_MERGE_QUICK_REF.md](AUDIT_MERGE_QUICK_REF.md) | Quick reference for `audit_merge` |
| [DEBUG_PROBE.md](DEBUG_PROBE.md) | `src/core/debug_probe.py` — pipeline instrumentation |
| [DEBUG_MAP.md](DEBUG_MAP.md) | 8-step pipeline probe map |

### Schema & Validation

| File | Purpose |
|------|---------|
| [SCHEMA_CONTRACT_SYSTEM.md](SCHEMA_CONTRACT_SYSTEM.md) | YAML schema contract system overview |
| [SCHEMA_CONTRACTS_COMPLETE.md](SCHEMA_CONTRACTS_COMPLETE.md) | Inventory of all 13 contracts |
| [THRESHOLD_CATALOG.md](THRESHOLD_CATALOG.md) | Variance threshold contracts (per-country) |

### Bridges & Business Logic

| File | Purpose |
|------|---------|
| [BRIDGES_RULES.md](BRIDGES_RULES.md) | Bridge classification rules (GL codes, amounts) |
| [BUSINESS_LINE_RECLASS.md](BUSINESS_LINE_RECLASS.md) | Business line reclassification bridge |

---

## Archive

Historical and working documents archived in `archive/`:
- `2025-10-working-docs/` — Analysis, status tracking, daily checklists (Oct 2025)
- `2025-10-migration-prep/` — Athena migration planning (Oct 2025, abandoned)
- `2025-10-meetings/` — Meeting notes (Oct 2025)
- `2024-12-refactoring/` — Previous refactoring docs (Dec 2024)
- `2024-12-security-fixes/` — Security fix documentation (Dec 2024)

Obsolete architecture docs moved from active paths are stored in:
- `../archive/2026-03-obsolete-architecture/`

---

## Document Maintenance

- **When adding a utility**: add a `<MODULE>.md` in this folder referencing the public API
- **When changing a pipeline step**: update `RECONCILIATION_FLOW.md`
- **When adding/modifying schema contracts**: update `SCHEMA_CONTRACTS_COMPLETE.md`
- **When adding threshold rules**: update `THRESHOLD_CATALOG.md`
- Outdated "spike" or exploration docs go to `archive/`

---

**Maintained By**: SOXauto Development Team  
**Questions?**: Check this README first, then ask team  
**Contributing**: Keep documents updated as work progresses

