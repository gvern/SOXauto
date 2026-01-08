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
from src.bridges.calculations.business_line_reclass import (
    identify_business_line_reclass_candidates
)
import pandas as pd

# Load CLE data from NAV
cle_df = pd.read_csv("nav_cle_extract.csv")

# Identify candidates
candidates = identify_business_line_reclass_candidates(
    cle_df, 
    cutoff_date="2025-09-30"
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
    cle_df,
    cutoff_date="2025-09-30",
    min_abs_amount=100.0,
)
```

### Review Workflow

```python
# 1. Generate candidates
candidates = identify_business_line_reclass_candidates(cle_df, "2025-09-30")

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

## Data Source: NAV Customer Ledger Entries

### Recommended SQL Query

Customer Ledger Entries can be extracted from NAV using the FINREC database.

Example SQL query structure (adjust for your NAV schema):

```sql
SELECT
    [Customer No_] AS customer_id,
    [Global Dimension 1 Code] AS business_line_code,  -- Or your BL field
    [Remaining Amount (LCY)] AS amount_lcy,
    [Posting Date] AS posting_date,
    [Document No_] AS document_no
FROM [FINREC].[dbo].[Customer Ledger Entry]
WHERE 
    [Posting Date] <= @cutoff_date
    AND [Remaining Amount (LCY)] <> 0  -- Only open entries
ORDER BY [Customer No_], [Global Dimension 1 Code]
```

### Integration with SOXauto Pipeline

To integrate with SOXauto's standard extraction pipeline:

1. **Add SQL File**: Create `src/core/catalog/queries/NAV_CLE.sql`
2. **Add Catalog Entry**: Update `src/core/catalog/cpg1.py` with CLE IPE definition
3. **Run Extraction**: Use `mssql_runner.py` to extract via Temporal workflow
4. **Run Analysis**: Pass extracted DataFrame to `identify_business_line_reclass_candidates()`

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
from src.bridges.calculations.business_line_reclass import (
    identify_business_line_reclass_candidates
)

@activity.defn
async def analyze_business_line_reclass(cutoff_date: str) -> dict:
    # 1. Extract CLE from NAV
    runner = MSSQLRunner()
    cle_df = runner.extract_ipe("NAV_CLE", cutoff_date)
    
    # 2. Identify candidates
    candidates = identify_business_line_reclass_candidates(cle_df, cutoff_date)
    
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
