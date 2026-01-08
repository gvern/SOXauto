# Business Line Reclass Bridge

## Overview

The Business Line Reclass bridge identifies customers who have balances across multiple business lines within NAV (Navision). This is a **NAV-only reclassification** of balances between business lines and is **not a cross-system variance driver**.

The module analyzes Customer Ledger Entries (CLE) from NAV for the control period and generates a candidate reclass table for review by Accounting Excellence and validation by local finance.

## What It Does

- **Extracts CLE Data**: Analyzes Customer Ledger Entries from NAV with business line codes
- **Pivots by Customer + Business Line**: Groups transactions by customer and business line, summing balances
- **Identifies Multi-BL Customers**: Flags customers with balances across more than one business line
- **Proposes Primary Business Line**: Uses heuristic (largest absolute balance) to suggest "correct" business line
- **Generates Candidate Table**: Outputs review-friendly table showing proposed reclassifications

## What It Does NOT Do

❌ **Does NOT automatically determine the "true" correct business line**
- Requires Accounting Excellence review
- Requires local finance confirmation
- Relies on heuristic (subject to manual override)

❌ **Does NOT post journal entries**
- Output is for review only
- No automatic posting to NAV

❌ **Does NOT make final decisions**
- All output has `review_required=True`
- Final decision is manual/review-driven

❌ **Is NOT a cross-system bridge**
- NAV-only reclassification
- Not a variance driver between systems (e.g., NAV vs PG)

## Required Input: CLE DataFrame Schema

The `identify_business_line_reclass_candidates()` function requires a pandas DataFrame with the following columns:

### Required Columns (Default Names)

| Column Name | Type | Description | Example |
|-------------|------|-------------|---------|
| `customer_id` | str | Unique customer identifier | "C001234" |
| `business_line_code` | str | Business line code from NAV | "BL01", "RETAIL" |
| `amount_lcy` | float | Balance amount in local currency | 1000.00, -500.50 |

### Column Name Customization

If your CLE extract uses different column names, you can map them using optional parameters:

```python
result = identify_business_line_reclass_candidates(
    cle_df,
    cutoff_date="2025-09-30",
    customer_id_col="cust_no",           # Your column name
    business_line_col="bl_code",         # Your column name
    amount_col="balance_lcy",            # Your column name
)
```

### Data Quality Requirements

- **customer_id**: Must not be null/empty (rows with missing customer_id are dropped)
- **business_line_code**: Must not be null/empty (rows with missing BL are dropped)
- **amount_lcy**: Can be:
  - Numeric (float, int)
  - String with commas: "1,234.56"
  - String with spaces: "1 234.56"
  - Empty string or NaN (treated as 0.0)
  - Negative values (allowed)

## Output: Candidate Reclass Table Schema

The function returns a pandas DataFrame with the following columns:

| Column Name | Type | Description |
|-------------|------|-------------|
| `customer_id` | str | Customer identifier |
| `business_line_code` | str | Current business line code |
| `balance_lcy` | float | Balance for this customer+BL combination |
| `num_business_lines_for_customer` | int | Number of distinct BLs this customer has |
| `proposed_primary_business_line` | str | Heuristic selection (largest abs balance) |
| `proposed_reclass_amount_lcy` | float | Amount to reclass FROM this BL TO primary BL |
| `reasoning` | str | Human-readable explanation of the heuristic |
| `review_required` | bool | Always `True` (manual review needed) |

### Output Interpretation

#### If a row has `business_line_code == proposed_primary_business_line`:
- This BL is the proposed "correct" business line for this customer
- `proposed_reclass_amount_lcy = 0.0` (no reclass needed)
- Other BLs for this customer should reclass TO this BL

#### If a row has `business_line_code != proposed_primary_business_line`:
- This BL is proposed as "incorrect" for this customer
- `proposed_reclass_amount_lcy = balance_lcy` (full balance should move)
- Amount should be reclassed FROM this BL TO the primary BL

### Example Output

```python
  customer_id business_line_code  balance_lcy  num_business_lines_for_customer  \
0        C001               BL01      10000.0                                 3   
1        C001               BL02       2500.0                                 3   
2        C001               BL03       -500.0                                 3   

  proposed_primary_business_line  proposed_reclass_amount_lcy  \
0                           BL01                          0.0   
1                           BL01                       2500.0   
2                           BL01                       -500.0   

                                           reasoning  review_required  
0  Customer C001 has 3 business lines. Proposed ...             True  
1  Customer C001 has 3 business lines. Proposed ...             True  
2  Customer C001 has 3 business lines. Proposed ...             True  
```

**Interpretation:**
- Customer C001 has balances across 3 business lines
- Proposed primary: BL01 (largest absolute balance: 10,000)
- Proposed reclass:
  - Move 2,500 from BL02 to BL01
  - Move -500 from BL03 to BL01
- All rows require manual review before posting

## Heuristic: Proposed Primary Business Line Selection

The function uses a **deterministic heuristic** to propose the "correct" business line:

### Rule 1: Largest Absolute Balance
- Select the business line with the **largest absolute balance**
- Example: If BL01 has 1000, BL02 has -1500, BL03 has 200:
  - Primary = BL02 (abs(-1500) = 1500 is largest)

### Rule 2: Tie-Breaker (Alphabetical)
- If multiple business lines have the same absolute balance:
  - Select the **first alphabetically**
- Example: If BL01 has 500, BL02 has -500, BL03 has 400:
  - Primary = BL01 (abs(500) = abs(-500), BL01 comes first alphabetically)

### Limitations of Heuristic

⚠️ **This heuristic is a starting point, not a final decision**

The "largest balance" heuristic may NOT be correct because:
- Customer may have been incorrectly assigned to the larger BL
- Historical data or customer master may indicate different "true" BL
- Business rules may require different classification

**Always review output before using for journal entries.**

## Usage Examples

### Basic Usage

```python
from src.bridges.categorization.business_line_reclass import (
    identify_business_line_reclass_candidates
)
import pandas as pd

# Load IPE_07 data (NAV Customer Ledger Entries)
ipe_07_df = pd.read_csv("ipe_07_extract.csv")

# Identify candidates with IPE_07 column mapping
candidates = identify_business_line_reclass_candidates(
    ipe_07_df,
    cutoff_date="2025-09-30",
    customer_id_col="Customer No_",
    business_line_col="Busline Code",
    amount_col="rem_amt_LCY",
)

# Review output
print(f"Found {len(candidates)} candidate reclass rows")
print(f"Affecting {candidates['customer_id'].nunique()} customers")

# Export for review
candidates.to_excel("business_line_reclass_candidates.xlsx", index=False)
```

### Custom Column Names

```python
# If your CLE extract has different column names
cle_df = pd.read_csv("nav_extract.csv")  # Has: cust_no, bl_code, balance

candidates = identify_business_line_reclass_candidates(
    cle_df,
    cutoff_date="2025-09-30",
    customer_id_col="cust_no",
    business_line_col="bl_code",
    amount_col="balance",
)
```

### Filter by Minimum Amount

```python
# Only consider balances >= 100.00 (reduce noise)
candidates = identify_business_line_reclass_candidates(
    ipe_07_df,
    cutoff_date="2025-09-30",
    customer_id_col="Customer No_",
    business_line_col="Busline Code",
    amount_col="rem_amt_LCY",
    min_abs_amount=100.0,
)
```

### Review Workflow

```python
# 1. Generate candidates from IPE_07
candidates = identify_business_line_reclass_candidates(
    ipe_07_df,
    "2025-09-30",
    customer_id_col="Customer No_",
    business_line_col="Busline Code",
    amount_col="rem_amt_LCY",
)

# 2. Filter to high-value customers only
high_value = candidates[candidates["balance_lcy"].abs() >= 1000]

# 3. Group by customer for review
for customer_id in high_value["customer_id"].unique():
    customer_rows = high_value[high_value["customer_id"] == customer_id]
    print(f"\n{customer_id}:")
    print(customer_rows[["business_line_code", "balance_lcy", "proposed_reclass_amount_lcy"]])

# 4. After manual review and confirmation by Accounting Excellence:
#    - Post journal entries to reclassify balances
#    - Update customer master data if needed
```

## Data Source: IPE_07 (NAV Customer Ledger Entries)

### Overview

Customer Ledger Entries are extracted using **IPE_07**, which is the canonical source for NAV CLE data in the SOXauto repository.

### IPE_07 Column Mapping

When using IPE_07 data with `identify_business_line_reclass_candidates()`, map the columns as follows:

```python
from src.bridges.categorization.business_line_reclass import (
    identify_business_line_reclass_candidates
)

# IPE_07 DataFrame columns:
# - [Customer No_] → customer_id
# - [Busline Code] → business_line_code  
# - rem_amt_LCY → amount_lcy

candidates = identify_business_line_reclass_candidates(
    ipe_07_df,
    cutoff_date="2025-09-30",
    customer_id_col="Customer No_",
    business_line_col="Busline Code",
    amount_col="rem_amt_LCY",
)
```

### IPE_07 Query Details

The IPE_07 query (`src/core/catalog/queries/IPE_07.sql`) extracts:
- Customer Ledger Entries from `[AIG_Nav_DW].[dbo].[Customer Ledger Entries]`
- Aggregated remaining amounts from `[AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]`
- Business line codes via `cle.[Busline Code]`
- Customer information including posting groups
- Filtered for in-scope companies and relevant posting groups

### Integration with SOXauto Pipeline

To integrate with SOXauto's standard extraction pipeline:

1. **Extract IPE_07**: Use `mssql_runner.py` to extract IPE_07 via Temporal workflow
2. **Run Analysis**: Pass extracted IPE_07 DataFrame to `identify_business_line_reclass_candidates()`
3. **Map Columns**: Use column mapping parameters to match IPE_07 schema

Example:

```python
from src.core.runners.mssql_runner import MSSQLRunner
from src.bridges.categorization.business_line_reclass import (
    identify_business_line_reclass_candidates
)

# Extract IPE_07
runner = MSSQLRunner()
ipe_07_df = runner.extract_ipe("IPE_07", cutoff_date="2025-09-30")

# Identify business line reclass candidates
candidates = identify_business_line_reclass_candidates(
    ipe_07_df,
    cutoff_date="2025-09-30",
    customer_id_col="Customer No_",
    business_line_col="Busline Code",
    amount_col="rem_amt_LCY",
)

# Export for review
candidates.to_excel("business_line_reclass_candidates.xlsx", index=False)
```

## Testing

### Unit Tests

Run unit tests:
```bash
pytest tests/test_business_line_reclass.py -v
```

Test coverage:
- Single BL per customer (no candidates)
- Multiple BLs per customer (candidates generated)
- Numeric casting (strings, commas, NaN)
- Negative amounts
- Heuristic selection logic
- Column validation

### Integration Tests

Run integration tests:
```bash
pytest tests/test_business_line_reclass_integration.py -v
```

Test coverage:
- Realistic CLE scenarios
- Output schema stability
- Deterministic ordering
- CSV upload scenarios
- Large dataset performance

## FAQ

### Q: What if the heuristic selects the wrong primary business line?

**A:** This is expected. The heuristic is a **starting point for review**, not a final decision. Accounting Excellence should review all candidates and override the proposed primary BL where needed based on:
- Customer master data
- Historical business line assignments
- Local finance input
- Business rules

### Q: Can I change the heuristic?

**A:** Yes, but it requires code changes to `src/bridges/calculations/business_line_reclass.py`. The current heuristic (largest absolute balance) is deterministic and simple. Alternative heuristics could consider:
- Most recent transaction date
- Transaction count per BL
- Customer master data lookup
- Historical BL assignment

### Q: What about customers with zero balances in some BLs?

**A:** Zero balances are filtered out by the `min_abs_amount` parameter (default 0.01). This reduces noise and focuses review on meaningful balances. Adjust via:
```python
candidates = identify_business_line_reclass_candidates(
    cle_df, "2025-09-30", min_abs_amount=0.0  # Include all balances
)
```

### Q: What if a customer has negative balances across all BLs?

**A:** The heuristic still works using **absolute values**. The BL with the largest absolute balance (ignoring sign) is selected as primary. Negative balances are valid and handled correctly.

### Q: How do I integrate this with the Temporal workflow?

**A:** Example Temporal Activity:

```python
from temporalio import activity
from src.core.runners.mssql_runner import MSSQLRunner
from src.bridges.categorization.business_line_reclass import (
    identify_business_line_reclass_candidates
)

@activity.defn
async def analyze_business_line_reclass(cutoff_date: str) -> dict:
    # 1. Extract IPE_07 (NAV CLE) from NAV
    runner = MSSQLRunner()
    ipe_07_df = runner.extract_ipe("IPE_07", cutoff_date)
    
    # 2. Identify candidates with column mapping
    candidates = identify_business_line_reclass_candidates(
        ipe_07_df,
        cutoff_date,
        customer_id_col="Customer No_",
        business_line_col="Busline Code",
        amount_col="rem_amt_LCY",
    )
    
    # 3. Save to S3 or evidence folder
    candidates.to_csv(f"business_line_reclass_candidates_{cutoff_date}.csv")
    
    return {
        "num_candidates": len(candidates),
        "num_customers": candidates["customer_id"].nunique(),
    }
```

## Support

For questions or issues with the Business Line Reclass bridge:
1. Check test files for usage examples
2. Review function docstrings in `src/bridges/calculations/business_line_reclass.py`
3. Contact Accounting Excellence for business logic clarification

## Change Log

- **2026-01-08**: Initial implementation with CLE-based pivot logic
  - Replaces placeholder `biz_line.py` module
  - Implements heuristic (largest absolute balance)
  - Full unit and integration test coverage
