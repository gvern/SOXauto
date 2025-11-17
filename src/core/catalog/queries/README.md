# SQL Query Catalog

This directory contains SQL query definitions for IPEs (Internal Process Evidence) and CRs (Control Reports) used in the SOXauto C-PG-1 control framework.

## Query Files

### IPE Queries

- **IPE_07.sql** - Customer balances - Monthly balances at date (Ageing details)
- **IPE_08.sql** - TV - Voucher liabilities (Issuance baseline)
- **IPE_10.sql** - Customer prepayments TV (PBI report)
- **IPE_31.sql** - PG detailed TV extraction (Collection Accounts)
- **IPE_REC_ERRORS.sql** - Master Integration Errors consolidation (Task 3)

### CR Queries

- **CR_03.sql** - NAV GL Entries (detailed transaction entries)
- **CR_04.sql** - NAV GL Balances (actuals side of reconciliation)
- **CR_05.sql** - FX rates (with special USA/Germany handling)
- **CR_05a.sql** - FA table - FX rates (Fixed Assets)

### DOC Queries

- **DOC_VOUCHER_USAGE.sql** - Voucher Usage TV Extract (for Timing Bridge)

## Query Loading

All queries are loaded by the catalog system via the `_load_sql()` function in `src/core/catalog/cpg1.py`:

```python
from src.core.catalog.cpg1 import get_item_by_id

# Load an IPE with its SQL query
ipe = get_item_by_id("IPE_REC_ERRORS")
print(ipe.sql_query)  # Full SQL query text
```

## Query Conventions

1. **Parameterization**: Use `{parameter_name}` placeholders for dynamic values:
   - `{cutoff_date}` - Period end date for reporting
   - `{year}`, `{month}` - For date filtering
   - `{gl_accounts}` - For account filtering
   - `{id_companies_active}` - For company filtering

2. **Temp Tables**: Use global temp tables (`##temp`) when needed for performance

3. **Comments**: Include header comments explaining purpose, output schema, and key logic

4. **Standards**: Follow SQL Server T-SQL syntax standards

## IPE_REC_ERRORS (New - Task 3)

The **IPE_REC_ERRORS.sql** query is a master consolidation query that:

- Unifies 36 FinRec tables into a single standardized view
- Provides foundation for Task 3 (Integration Errors Bridge)
- Outputs standardized schema: `Source_System`, `ID_Company`, `Transaction_ID`, `Amount`, `Integration_Status`
- Filters for non-integrated records (Nav_Integration_Status NOT IN ('Posted', 'Integrated'))

### Current Implementation (15 Tables)

The query currently implements 15 explicitly mapped tables as specified in the requirements:

1. RPT_3PL_MANUAL_TRANSACTIONS
2. RPT_CASHDEPOSIT
3. RPT_COLLECTIONADJ
4. RPT_DELIVERY_FEES
5. RPT_EXC_ACCOUNTSTATEMENTS
6. RPT_JFORCE_PAYOUTS
7. RPT_JPAY_APP_TRANSACTION
8. RPT_MARKETPLACE_SHIPPING_FEES
9. RPT_PACKLIST_PAYMENTS
10. RPT_PREPAID_DELIVERIES
11. RPT_SOI (Prepayments)
12. RPT_REFUNDS
13. RPT_TRANSACTIONS_SELLER
14. RING.RPT_ACCOUNTSTATEMENTS
15. RPT_VENDOR_PAYMENTS

### Future Expansion

The query includes guidance for adding the remaining 21 tables to reach the target of 36 total tables. Before deployment, verify that column names (especially `Transaction_ID`) match actual table schemas in the SQL Server database.

## Testing

All queries have corresponding test cases in `tests/test_smoke_catalog_and_scripts.py` that validate:

- Query loads successfully from file
- Required parameters are present
- Key business logic is implemented
- Source tables are correctly listed in catalog metadata

Run tests with:
```bash
pytest tests/test_smoke_catalog_and_scripts.py -v
```
