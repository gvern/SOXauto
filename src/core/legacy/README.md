# Legacy Configuration Files

This directory contains archived configuration files from the original flat `src/core/` structure. These files have been refactored into a more organized package structure.

## ⚠️ Status: DEPRECATED - Reference Only

**Do not use these files for new development.** They are preserved here for:
- Historical reference
- Understanding the original implementation
- Supporting any emergency rollback scenarios

## Migration Guide

### What Moved Where

| Old Location | New Location | Purpose |
|--------------|--------------|---------|
| `config.py` | `src.core.catalog/` | IPE definitions (legacy SQL Server) |
| `config_athena.py` | `src.core.catalog/` | IPE definitions moved to unified catalog |
| `config_cpg1_athena.py` | `src.core.catalog/` (data) + `src.core.recon.cpg1` (logic) | Split IPE definitions and reconciliation |
| `ipe_catalog_pg1.py` | `src.core.catalog.pg1_catalog` | Now the canonical catalog location |
| `ipe_runner.py` | `src.core.runners.mssql_runner` | SQL Server execution engine |
| `ipe_runner_athena.py` | `src.core.runners.athena_runner` | Athena execution engine |
| `evidence_manager.py` | `src.core.evidence.manager` | SOX evidence generation |

### Before & After Import Examples

#### Example 1: Loading IPE Configuration (Athena)

**Before:**
```python
from src.core.config_athena import IPEConfigAthena

config = IPEConfigAthena.load_ipe_config('IPE_09')
```

**After:**
```python
from src.core.catalog import get_athena_config

config = get_athena_config('IPE_09')
```

#### Example 2: Running an IPE Extraction (Athena)

**Before:**
```python
from src.core.ipe_runner_athena import IPERunnerAthena
from src.core.config_athena import IPEConfigAthena

config = IPEConfigAthena.load_ipe_config('IPE_09')
runner = IPERunnerAthena(
    ipe_id=config['ipe_id'],
    query=config['query'],
    database=config['database']
)
```

**After:**
```python
from src.core.runners import IPERunnerAthena

# Option 1: Use catalog factory (recommended)
runner = IPERunnerAthena.from_catalog('IPE_09')

# Option 2: Manual config if needed
from src.core.catalog import get_athena_config
config = get_athena_config('IPE_09')
runner = IPERunnerAthena(
    ipe_id=config['ipe_id'],
    query=config['query'],
    database=config['database']
)
```

#### Example 3: Evidence Generation

**Before:**
```python
from src.core.evidence_manager import IPEEvidenceGenerator

evidence_gen = IPEEvidenceGenerator(
    ipe_id='IPE_09',
    output_dir='evidence/IPE_09'
)
```

**After:**
```python
from src.core.evidence import IPEEvidenceGenerator

evidence_gen = IPEEvidenceGenerator(
    ipe_id='IPE_09',
    output_dir='evidence/IPE_09'
)
```

#### Example 4: Reconciliation Logic

**Before:**
```python
from src.core.config_cpg1_athena import CPG1ReconciliationConfig

recon = CPG1ReconciliationConfig()
variance = recon.calculate_variance(actuals, targets)
```

**After:**
```python
from src.core.recon import CPG1ReconciliationConfig

recon = CPG1ReconciliationConfig()
variance = recon.calculate_variance(actuals, targets)
```

### Backward Compatibility

Deprecation shims have been placed at the original file locations (in `src/core/`) that:
- Emit `DeprecationWarning` messages
- Re-export functionality from new locations when possible
- Raise `NotImplementedError` for truly deprecated features

This allows existing code to continue working while you migrate to the new structure.

### Migration Timeline

- **Phase 1 (Current)**: Deprecation shims in place, warnings emitted
- **Phase 2 (Next sprint)**: Update all imports across codebase
- **Phase 3 (Future)**: Remove deprecation shims once migration complete

### New Package Structure

```
src/core/
├── catalog/          # Single source of truth for IPE/CR definitions
│   ├── __init__.py
│   └── pg1_catalog.py
├── runners/          # Execution engines for different backends
│   ├── __init__.py
│   ├── athena_runner.py
│   └── mssql_runner.py
├── evidence/         # SOX compliance and evidence generation
│   ├── __init__.py
│   └── manager.py
├── recon/           # Reconciliation business logic
│   ├── __init__.py
│   └── cpg1.py
├── orchestrators/   # Workflow orchestration (from main.py)
│   └── __init__.py
└── legacy/          # Archived reference files (this directory)
    ├── README.md
    ├── config.py
    ├── config_athena.py
    └── config_cpg1_athena.py
```

### Questions?

If you encounter issues during migration, check:
1. The deprecation warnings for guidance on new import paths
2. This README for before/after examples
3. Test files in `tests/` for working examples of the new structure

## Archived Files Description

### `config.py`
Legacy SQL Server connection configurations and IPE definitions. Superseded by:
- Catalog: `src.core.catalog.pg1_catalog` for IPE definitions
- Runner: `src.core.runners.mssql_runner` for SQL Server execution

### `config_athena.py`
AWS Athena-specific IPE configurations. All IPE definitions consolidated into unified catalog with backend-specific fields.

### `config_cpg1_athena.py`
Mixed file containing both:
- IPE definitions (→ moved to catalog)
- Reconciliation business logic (→ extracted to `src.core.recon.cpg1`)
- GL account mappings (→ part of reconciliation module)

## Rationale for Refactoring

The old structure had several issues:
- **Redundancy**: Same IPE definitions across multiple config files
- **Mixed concerns**: Configs containing data, business logic, and execution code
- **Hard to test**: Tightly coupled components
- **Poor discoverability**: Flat structure with unclear responsibilities

The new structure follows separation of concerns:
- **Data** (catalog) separate from **logic** (recon) separate from **execution** (runners)
- Single source of truth for IPE definitions
- Clear package boundaries with explicit exports
- Easier to test and maintain
