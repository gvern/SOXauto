# Quick Reference: New src/core Structure

**Status**: ✅ Live (Phase 1 complete)  
**Migration**: Old imports work but emit warnings  
**Documentation**: See `src/core/legacy/README.md` for detailed guide

## 🎯 TL;DR - What You Need to Know

The `src/core/` folder has been reorganized into focused packages. **Your old imports still work**, but you'll see deprecation warnings. Use this guide to update to the new structure.

## 📦 New Package Structure

```
src/core/
├── catalog/          # 📚 IPE/CR definitions (single source of truth)
├── runners/          # 🚀 Execution engines (Athena, SQL Server)
├── evidence/         # 📋 SOX compliance & evidence generation
├── recon/           # 🧮 Reconciliation business logic
├── orchestrators/   # 🎵 Workflow orchestration (coming soon)
└── legacy/          # 📦 Archived old configs (reference only)
```

## 🔄 Quick Migration Guide

### 1. Loading IPE Configuration

**❌ Old way (deprecated):**
```python
from src.core.config_athena import IPEConfigAthena
config = IPEConfigAthena.load_ipe_config('IPE_09')
```

**✅ New way:**
```python
from src.core.catalog import get_athena_config
config = get_athena_config('IPE_09')
```

### 2. Running IPE Extraction (Athena)

**❌ Old way:**
```python
from src.core.ipe_runner_athena import IPERunnerAthena
runner = IPERunnerAthena(ipe_id='IPE_09', database='...', query='...')
```

**✅ New way (recommended - uses catalog):**
```python
from src.core.runners import IPERunnerAthena
runner = IPERunnerAthena.from_catalog('IPE_09')  # Auto-loads config!
```

**✅ Alternative (manual config):**
```python
from src.core.runners import IPERunnerAthena
from src.core.catalog import get_athena_config

config = get_athena_config('IPE_09')
runner = IPERunnerAthena(
    ipe_id=config['ipe_id'],
    database=config['database'],
    query=config['query']
)
```

### 3. Evidence Generation

**❌ Old way:**
```python
from src.core.evidence_manager import IPEEvidenceGenerator, DigitalEvidenceManager
```

**✅ New way:**
```python
from src.core.evidence import IPEEvidenceGenerator, DigitalEvidenceManager
```

### 4. Reconciliation

**❌ Old way:**
```python
from src.core.config_cpg1_athena import CPG1ReconciliationConfig
```

**✅ New way:**
```python
from src.core.reconciliation import CPG1ReconciliationConfig
```

### 5. SQL Server Runner

**❌ Old way:**
```python
from src.core.ipe_runner import IPERunner
```

**✅ New way:**
```python
from src.core.runners import IPERunnerMSSQL as IPERunner
# Or just: from src.core.runners import IPERunnerMSSQL
```

## 📋 Complete Import Cheat Sheet

| What You Need | New Import | Old Import (deprecated) |
|---------------|------------|-------------------------|
| Get Athena config | `from src.core.catalog import get_athena_config` | `from src.core.config_athena import IPEConfigAthena` |
| List all IPEs | `from src.core.catalog import list_items` | - |
| List Athena IPEs | `from src.core.catalog import list_athena_ipes` | `from src.core.config_athena import list_ipes` |
| Athena runner | `from src.core.runners import IPERunnerAthena` | `from src.core.ipe_runner_athena import IPERunnerAthena` |
| SQL Server runner | `from src.core.runners import IPERunnerMSSQL` | `from src.core.ipe_runner import IPERunner` |
| Evidence manager | `from src.core.evidence import DigitalEvidenceManager` | `from src.core.evidence_manager import DigitalEvidenceManager` |
| Evidence generator | `from src.core.evidence import IPEEvidenceGenerator` | `from src.core.evidence_manager import IPEEvidenceGenerator` |
| Reconciliation | `from src.core.reconciliation import CPG1ReconciliationConfig` | `from src.core.config_cpg1_athena import CPG1ReconciliationConfig` |
| Exceptions | `from src.core.runners import IPEValidationError, IPEConnectionError` | `from src.core.ipe_runner import IPEValidationError` |

## 🎁 New Features

### 1. Catalog Helpers

```python
from src.core.catalog import list_items, get_item_by_id, list_athena_ipes

# Get all catalog items
all_ipes = list_items()
print(f"Total IPEs: {len(all_ipes)}")

# Get specific item
ipe = get_item_by_id('IPE_09')
print(f"{ipe.id}: {ipe.description}")

# List only Athena-configured IPEs
athena_ipes = list_athena_ipes()
for ipe_id in athena_ipes:
    print(f"- {ipe_id}")
```

### 2. Factory Method

```python
from src.core.runners import IPERunnerAthena

# Before: Manual config loading + runner creation (2 steps)
# After: One-liner! (config loaded automatically)
runner = IPERunnerAthena.from_catalog('IPE_09')
results = runner.run()
```

### 3. Reconciliation Helpers

```python
from src.core.reconciliation import CPG1ReconciliationConfig

recon = CPG1ReconciliationConfig()

# Get all component IPEs for reconciliation
components = recon.get_component_ipes()
# ['IPE_09', 'DOC_PG_BALANCES', 'IPE_31', 'IPE_08', 'IPE_11', 'IPE_12', 'IPE_34', 'CR_04']

# Get GL account description
desc = recon.get_gl_description('1020101001')
# "Current Account - Payoneer"

# Calculate variance
variance = recon.calculate_variance(actuals_df, targets_df)
```

## ⚠️ Deprecation Warnings

If you see warnings like:

```
DeprecationWarning: config_athena is deprecated. Use src.core.catalog instead.
```

**Don't panic!** Your code still works. The warnings are there to remind you to update imports when you have time. See migration examples above.

## 🚀 Best Practices

### ✅ DO:
- Use `IPERunnerAthena.from_catalog()` for automatic config loading
- Import from new package locations (`src.core.catalog`, `src.core.runners`)
- Update imports when you touch a file (opportunistic migration)
- Check `src/core/catalog/pg1_catalog.py` to see all available IPEs

### ❌ DON'T:
- Import from `src.core.legacy.*` (those are archived for reference only)
- Modify files in `src/core/legacy/` (read-only archive)
- Create new code using deprecated imports

## 🆘 Troubleshooting

### "Module not found" error

```python
ModuleNotFoundError: No module named 'src.core.config_athena'
```

**Solution**: The deprecation shim might be missing. Check that `src/core/config_athena.py` exists (not in legacy folder). If missing, file a bug.

### "IPE not found in catalog" error

```python
KeyError: 'IPE_07'
```

**Solution**: IPE not yet configured in catalog. Currently only `IPE_09` is fully configured for Athena. Check `src/core/catalog/pg1_catalog.py` for available IPEs. File a ticket to add missing IPEs.

### Deprecation warnings everywhere

**Solution**: This is expected during migration. To suppress warnings temporarily:

```python
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
```

But **please update imports when you have time!**

## 📚 Additional Resources

- **Full migration guide**: `src/core/legacy/README.md`
- **Refactoring summary**: `docs/project-history/REFACTORING_COMPLETE_V2.md`
- **Catalog source**: `src/core/catalog/pg1_catalog.py`
- **Test examples**: `tests/test_ipe_extraction_athena.py`

## 🗓️ Migration Timeline

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Complete | Deprecation shims active, new structure live |
| **Phase 2** | 📋 Current | Update all imports, split main.py, run tests |
| **Phase 3** | 🔮 Future | Remove deprecation shims, delete legacy files |

## 🤝 Questions?

- Check `src/core/legacy/README.md` for before/after examples
- Ask in team chat if stuck
- File a ticket for bugs or missing IPEs

---

**Remember**: Old imports work but emit warnings. Update when you can, but no rush! 🎯
