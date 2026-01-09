# Schema Contracts

This directory contains YAML-based schema contracts for all datasets (IPE, CR, DOC) in the SOXauto PG-01 system.

## What is a Schema Contract?

A schema contract defines the canonical structure for a dataset, including:
- **Canonical column names** (standardized across the system)
- **Allowed aliases** (handles variations like "Customer No_", "Customer No", "customer_no")
- **Required vs optional columns**
- **Data types** (string, float64, datetime64, etc.)
- **Semantic tags** (amount, date, key, id, code) for intelligent coercion
- **Coercion rules** (how to parse strings: remove commas, date formats, etc.)
- **Fill policies** (how to handle NaN: keep, fill with 0, fail, etc.)
- **Validation rules** (min/max values, ranges, patterns)

## Available Contracts

| Contract | Dataset | Source System | Fields | Description |
|----------|---------|---------------|--------|-------------|
| `IPE_07.yaml` | IPE_07 | NAV | 11 | Customer Ledger Entry - Monthly balances |
| `IPE_08.yaml` | IPE_08 | NAV | 11 | Store Credit Voucher Issuance |
| `CR_04.yaml` | CR_04 | NAV | 11 | GL Account Balance at Date |
| `CR_05.yaml` | CR_05 | NAV | 4 | Currency Exchange Rates |
| `JDASH.yaml` | JDASH | Jdash | 6 | Operational voucher usage data |

## Contract Structure

```yaml
dataset_id: IPE_07
version: 1
description: Customer Ledger Entry - Monthly customer balances at cutoff date
source_system: NAV
primary_keys: ["customer_id", "posting_date"]
deprecated: false

fields:
  - name: customer_id                          # Canonical name
    required: true                              # Must exist in data
    aliases: ["Customer No_", "Customer No", "customer_no"]  # Accepted variants
    dtype: string                               # Target data type
    semantic_tag: id                            # Semantic meaning
    description: Unique customer identifier from NAV
    reconciliation_critical: true               # Important for audit
    coercion_rules:
      strip_whitespace: true
      remove_commas: false
      remove_spaces: false
      remove_currency_symbols: false
  
  - name: amount_lcy
    required: true
    aliases: ["rem_amt_LCY", "Amount LCY", "amount_lcy", "Remaining Amount"]
    dtype: float64
    semantic_tag: amount
    description: Remaining amount in local currency
    reconciliation_critical: true
    fill_policy: keep_nan                       # Don't fill NaN by default
    coercion_rules:
      strip_whitespace: true
      remove_commas: true                       # "1,234.56" → 1234.56
      remove_spaces: true                       # "1 234.56" → 1234.56
      remove_currency_symbols: true             # "$1,234" → 1234.0
    validation_rules:
      allow_negative: true
```

## Usage

### Load a Contract

```python
from src.core.schema import load_contract, get_active_contract

# Load specific version
contract = load_contract("IPE_07", version=1)

# Load active version (respects SCHEMA_VERSION_IPE_07 env var)
contract = get_active_contract("IPE_07")
```

### Apply Schema to DataFrame

```python
from src.core.schema import apply_schema_contract

# Validate and normalize DataFrame
df, report = apply_schema_contract(
    raw_df,
    dataset_id="IPE_07",
    strict=True,      # Fail on missing required columns
    cast=True,        # Coerce to target dtypes
    track=True        # Record transformation events
)

# Check what transformations occurred
print(f"Columns renamed: {report.columns_renamed}")
print(f"Columns cast: {report.columns_cast}")
print(f"Invalid values coerced to NaN: {report.total_invalid_coerced}")
```

### Validate Required Columns in Bridges

```python
from src.core.schema import require_columns

def my_bridge_calculation(ipe_07_df, cr_04_df):
    # Validate required columns exist
    require_columns(ipe_07_df, "IPE_07", ["customer_id", "amount_lcy"])
    require_columns(cr_04_df, "CR_04", ["gl_account_no", "balance_at_date"])
    
    # Proceed with calculation
    ...
```

## Version Management

Contracts support versioning for audit reproducibility:

```bash
# Pin a specific version via environment variable
export SCHEMA_VERSION_IPE_07=1

# In evidence packages, we record:
# - dataset_id: IPE_07
# - version: 1
# - contract_hash: sha256(contract_yaml_content)
```

This allows you to:
1. **Reproduce old extractions** using their original contract version
2. **Evolve schemas** without breaking existing code
3. **Track breaking changes** via version increments

## Adding a New Contract

1. Create `NEW_DATASET.yaml` in this directory
2. Define fields with canonical names and aliases
3. Test with: `pytest tests/test_schema_smoke.py -v`
4. The contract is automatically discovered and cached

## Semantic Tags

| Tag | Description | Coercion Behavior |
|-----|-------------|-------------------|
| `amount` | Monetary/numeric amounts | Remove commas, spaces, currency symbols → float64 |
| `date` | Date/datetime fields | Parse multiple formats → datetime64 |
| `key` | Business keys (compound) | String normalization, strip whitespace |
| `id` | Unique identifiers | String normalization, strip whitespace |
| `code` | Classification codes | String normalization |
| `name` | Descriptive names | Basic string handling |
| `flag` | Boolean indicators | String handling (future: bool conversion) |
| `count` | Integer counts | Numeric coercion → int64 |
| `rate` | Rates/percentages | Numeric coercion → float64 |

## Fill Policies

| Policy | Behavior | Use Case |
|--------|----------|----------|
| `keep_nan` | Preserve NaN values (default) | Raw extractions where NaN has meaning |
| `fill_zero` | Replace NaN with 0.0 | Derived totals, aggregations |
| `fill_empty` | Replace NaN with empty string | String fields where empty is valid |
| `fail_on_nan` | Raise error if any NaN | Critical fields that must not be null |

## Alias Mapping Strategy

Aliases handle variations in source data column names:

```yaml
# Canonical name: customer_id
# Aliases handle:
aliases: [
  "Customer No_",        # NAV standard (with underscore)
  "Customer No",         # NAV alternative (no underscore)
  "customer_no",         # Lowercase variant
  "cust_no",            # Abbreviated form
  "CustomerId"          # CamelCase variant
]
```

The first matching alias is used, priority matters!

## Best Practices

1. **Always specify required: true** for columns critical to reconciliation
2. **Use semantic tags** for automatic coercion (don't reinvent parsing logic)
3. **Add comprehensive aliases** based on actual SQL output variations
4. **Document descriptions** for audit readability
5. **Test with malformed data** (commas, dates, nulls) before deploying
6. **Version contracts** when making breaking changes (new required field, semantic change)
7. **Keep unknown columns by default** (audit safety)

## See Also

- [Schema Contract System Documentation](../SCHEMA_CONTRACT_SYSTEM.md)
- [Column Lineage Tracking](../SCHEMA_CONTRACT_SYSTEM.md#transformation-tracking)
- [Quality Rules Integration](../../src/core/quality_checker.py)
