# Threshold Catalog System

## Overview

The Threshold Catalog System provides a flexible, auditable way to manage variance thresholds for SOX compliance reconciliation. It replaces hardcoded thresholds with YAML-based contracts that support precedence rules, versioning, and cryptographic hashing for evidence integrity.

## Key Features

- **Catalog-Driven**: Thresholds defined in YAML contracts, not hardcoded in Python
- **Country-Specific**: Different thresholds per country with DEFAULT fallback
- **Multiple Threshold Types**: Support for bucket-level, line-item, and materiality thresholds
- **Precedence Rules**: Most specific rule wins (country + GL + category + voucher_type)
- **Versioning**: Contract versions with environment variable pinning
- **Evidence Trail**: SHA256 hashing for audit integrity
- **Backward Compatible**: Fallback to legacy behavior when contracts unavailable

## Threshold Types

### BUCKET_USD
Applied to variance pivot aggregates at the (Category × Voucher Type) level.

**Use Case**: Flag buckets requiring investigation when `abs(variance_usd) >= threshold`

**Example**: If bucket threshold is 1000 USD and variance is +1200 USD → INVESTIGATE

### LINE_ITEM_USD
Applied to individual voucher/transaction line items.

**Use Case**: Mark material line items in review tables for focused accounting review

**Example**: If line-item threshold is 5000 USD and voucher amount is 6000 USD → Material

### COUNTRY_MATERIALITY_USD
Country-level materiality threshold (reserved for future use).

**Use Case**: Aggregate reporting and country-level risk assessment

**Note**: Not currently applied to bucket or line-item evaluation

## Precedence Rules

Threshold resolution follows "most specific wins" logic:

1. **Country-specific contract** with matching rule (most specific scope)
2. **DEFAULT contract** with matching rule (most specific scope)
3. **Hardcoded fallback** (1000 USD for backward compatibility)

Within a contract, rule specificity is determined by scope filters:

- **(GL account + Category + Voucher Type)** → Most specific
- **(GL account + Category)** → More specific
- **(GL account)** → Specific
- **(No filters)** → General

**Example Resolution**:
```python
# Request: EG, GL 18412, Category "Voucher", Type "refund"
# 
# Contract EG.yaml contains:
# Rule 1: GL 18412, Category Voucher, Type refund → 2000 USD (specificity=3)
# Rule 2: GL 18412, Category Voucher → 1500 USD (specificity=2)
# Rule 3: GL 18412 → 1000 USD (specificity=1)
# Rule 4: (no filters) → 500 USD (specificity=0)
#
# Resolution: Rule 1 (most specific) → 2000 USD
```

## Contract Structure

### File Location
```
src/core/reconciliation/thresholds/contracts/
├── DEFAULT.yaml    # Fallback for all countries
├── EG.yaml         # Egypt-specific thresholds
├── NG.yaml         # Nigeria-specific (add as needed)
└── ...
```

### YAML Format

```yaml
version: 1
effective_date: "2025-01-01"
description: "Human-readable contract description"
country_code: "EG"

rules:
  # General bucket threshold
  - threshold_type: BUCKET_USD
    value_usd: 1000.0
    description: "General bucket variance threshold"
    scope:
      # No filters = applies to all
  
  # GL-specific bucket threshold
  - threshold_type: BUCKET_USD
    value_usd: 2000.0
    description: "Higher threshold for GL 18412"
    scope:
      gl_accounts: ["18412"]
  
  # Category-specific line-item threshold
  - threshold_type: LINE_ITEM_USD
    value_usd: 5000.0
    description: "Material line items for Voucher category"
    scope:
      gl_accounts: ["18412"]
      categories: ["Voucher"]
  
  # Country materiality (informational)
  - threshold_type: COUNTRY_MATERIALITY_USD
    value_usd: 22000.0
    description: "Egypt country-level materiality"
    scope: {}
```

### Required Fields

- `version`: Integer version number (≥1)
- `effective_date`: Date string in YYYY-MM-DD format
- `description`: Human-readable contract description
- `country_code`: Country code or "DEFAULT"
- `rules`: List of threshold rules

### Rule Fields

- `threshold_type`: BUCKET_USD | LINE_ITEM_USD | COUNTRY_MATERIALITY_USD
- `value_usd`: Threshold value in USD (must be non-negative)
- `description`: Human-readable rule description
- `scope`: Optional scope filters
  - `gl_accounts`: List of GL account numbers (optional)
  - `categories`: List of category names (optional)
  - `voucher_types`: List of voucher types (optional)

## Usage Examples

### Resolving Thresholds

```python
from src.core.reconciliation.thresholds import (
    resolve_threshold,
    resolve_bucket_threshold,
    resolve_line_item_threshold,
    ThresholdType,
)

# Resolve bucket threshold for Egypt, GL 18412
resolved = resolve_bucket_threshold(
    country_code="EG",
    gl_account="18412",
)
print(f"Threshold: {resolved.value_usd} USD")
print(f"Source: {resolved.source}")
print(f"Contract version: {resolved.contract_version}")
print(f"Contract hash: {resolved.contract_hash[:8]}...")

# Resolve with full context
resolved = resolve_threshold(
    country_code="EG",
    threshold_type=ThresholdType.BUCKET_USD,
    gl_account="18412",
    category="Voucher",
    voucher_type="refund",
)

# Resolve line-item threshold
line_threshold = resolve_line_item_threshold(
    country_code="EG",
    gl_account="18412",
    category="Voucher",
)
```

### Phase 3 Variance Analysis Workflow

```python
from src.core.reconciliation.analysis.variance import (
    compute_variance_pivot_local,
    evaluate_thresholds_variance_pivot,
)
from src.core.reconciliation.analysis.review_tables import build_review_table
from src.utils.fx_utils import FXConverter

# Step 1-3: Build pivots and compute variance (local currency)
variance_df = compute_variance_pivot_local(
    nav_pivot_local_df=nav_pivot,
    tv_pivot_local_df=tv_pivot,
    fx_converter=fx_converter,
    cutoff_date="2025-09-30",
)

# Step 4: Apply FX conversion (already done in compute_variance_pivot_local)
# variance_df now has both LCY and USD columns

# Step 5: Evaluate thresholds (on USD amounts)
evaluated_df = evaluate_thresholds_variance_pivot(
    variance_df=variance_df,
    gl_account="18412",
)

# Check results
investigate_buckets = evaluated_df[evaluated_df["status"] == "INVESTIGATE"]
print(f"Buckets to investigate: {len(investigate_buckets)}")

# Step 6: Build review table for accounting
review_df = build_review_table(
    variance_pivot_with_status=evaluated_df,
    gl_account="18412",
    filter_non_material_lines=False,  # Keep all lines, mark materiality
)
```

## Adding Country Rules

### Step 1: Create Contract File

Create `src/core/reconciliation/thresholds/contracts/<COUNTRY>.yaml`:

```yaml
version: 1
effective_date: "2025-01-15"
description: "Thresholds for <Country Name> reconciliation"
country_code: "<COUNTRY>"

rules:
  - threshold_type: BUCKET_USD
    value_usd: 1000.0
    description: "Bucket threshold for GL 18412"
    scope:
      gl_accounts: ["18412"]
  
  - threshold_type: LINE_ITEM_USD
    value_usd: 5000.0
    description: "Line-item materiality for GL 18412"
    scope:
      gl_accounts: ["18412"]
```

### Step 2: Validate Contract

```python
from src.core.reconciliation.thresholds import load_contract

# Test loading
contract, hash = load_contract("<COUNTRY>")
print(f"Loaded {contract.country_code} v{contract.version}")
print(f"Rules: {len(contract.rules)}")
print(f"Hash: {hash[:8]}...")
```

### Step 3: Test Resolution

```python
from src.core.reconciliation.thresholds import resolve_bucket_threshold

resolved = resolve_bucket_threshold(
    country_code="<COUNTRY>",
    gl_account="18412",
)
print(f"Threshold: {resolved.value_usd} USD")
print(f"Source: {resolved.source}")  # Should be "catalog"
```

## Version Pinning

Pin contract versions using environment variables:

```bash
# Pin Egypt contract to version 1
export THRESHOLD_VERSION_EG=1

# Pin DEFAULT contract to version 2
export THRESHOLD_VERSION_DEFAULT=2
```

In code:
```python
# Will use pinned version from environment
contract, hash = load_contract("EG")
print(f"Version: {contract.version}")
```

## Evidence Logging

Resolved thresholds include full audit trail:

```python
resolved = resolve_bucket_threshold("EG", gl_account="18412")

# Evidence metadata
evidence = {
    "threshold_value_usd": resolved.value_usd,
    "threshold_type": resolved.threshold_type.value,
    "country_code": resolved.country_code,
    "contract_version": resolved.contract_version,
    "contract_hash": resolved.contract_hash,
    "matched_rule": resolved.matched_rule_description,
    "source": resolved.source,  # "catalog" or "fallback"
    "specificity_score": resolved.specificity_score,
}

# Include in evidence package
print(f"Threshold resolved: {evidence}")
```

## Testing

### Unit Tests
```bash
# Test threshold catalog system
pytest tests/test_threshold_catalog.py -v

# Test models, registry, precedence
pytest tests/test_threshold_catalog.py::TestThresholdModels -v
```

### Integration Tests
```bash
# Test variance + threshold integration
pytest tests/test_threshold_integration.py -v

# Test Phase 3 workflow
pytest tests/test_threshold_integration.py::TestPhase3WorkflowOrder -v
```

## Troubleshooting

### Issue: Threshold not resolving as expected

**Diagnosis**: Check precedence and scope matching

```python
from src.core.reconciliation.thresholds import get_contract

# Load contract and inspect rules
contract, _ = get_contract("EG")
for rule in contract.rules:
    print(f"{rule.threshold_type}: {rule.value_usd} USD")
    print(f"  Scope: {rule.scope.__dict__}")
    print(f"  Specificity: {rule.specificity_score()}")
```

### Issue: Using fallback instead of catalog

**Diagnosis**: Contract file missing or parse error

```python
from src.core.reconciliation.thresholds import load_contract

try:
    contract, hash = load_contract("XX")
except FileNotFoundError as e:
    print(f"Contract not found: {e}")
except ValueError as e:
    print(f"Parse error: {e}")
```

### Issue: Contract hash mismatch

**Diagnosis**: Contract file modified after deployment

```python
from src.core.reconciliation.thresholds import get_contract_hash
from pathlib import Path

contract_path = Path("src/core/reconciliation/thresholds/contracts/EG.yaml")
current_hash = get_contract_hash(contract_path)
print(f"Current hash: {current_hash}")

# Compare with expected hash from evidence
```

## Best Practices

1. **Use Catalog for New Reconciliations**: Always use threshold catalog for new controls
2. **Document Rule Descriptions**: Write clear, audit-friendly descriptions
3. **Version Contracts**: Increment version when rules change
4. **Test Before Deploy**: Validate contracts with unit tests
5. **Pin Versions for Production**: Use environment variables to pin critical versions
6. **Log Evidence**: Always include threshold metadata in evidence packages
7. **Review Fallbacks**: Monitor and minimize fallback threshold usage

## Migration from Hardcoded Thresholds

For existing code using hardcoded thresholds:

### Before (Legacy)
```python
threshold = 1000.0
if abs(variance) >= threshold:
    status = "INVESTIGATE"
```

### After (Catalog)
```python
from src.core.reconciliation.thresholds import resolve_bucket_threshold

resolved = resolve_bucket_threshold(
    country_code=country_code,
    gl_account=gl_account,
)
if abs(variance_usd) >= resolved.value_usd:
    status = "INVESTIGATE"
```

### Backward Compatibility

Existing code continues to work with fallback thresholds:
- No contract → falls back to 1000 USD (DEFAULT)
- Legacy tests pass unchanged
- Evidence includes `source="fallback"` for audit trail

## Related Documentation

- [Phase 3 Reconciliation Architecture](./architecture/reconciliation_phases.md)
- [Evidence System](./audit/evidence_system.md)
- [FX Conversion Utilities](./development/fx_conversion.md)
