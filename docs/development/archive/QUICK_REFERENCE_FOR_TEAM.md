# C-PG-1 Table Mapping - Quick Reference Card
<!-- markdownlint-disable -->

**For**: Carlos/Joao (Technical Team)  
**From**: Gustave (SOXauto Automation)  
**Date**: 17 October 2025

---

## 🎯 Simple Request - **UPDATED**

I need the Athena table names for these **14** SQL Server tables used in C-PG-1:

### Core Tables (Priority 1)

| # | SQL Server Table | SQL Server DB | Athena DB? | Athena Table? |
|---|------------------|---------------|------------|---------------|
| 1 | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT` | FinRec | ??? | ??? |
| 2 | `G_L Entries` | NAV BI | ??? | ??? |
| 3 | `Detailed Customer Ledg_ Entry` | NAV BI | ??? | ??? |
| 4 | `Customer Ledger Entries` | NAV BI | ??? | ??? |
| 5 | `RPT_SOI` | FinRec | ??? | ??? |
| 6 | `V_STORECREDITVOUCHER_CLOSING` | FinRec | ??? | ??? |
| 7 | `RPT_FX_RATES` | FinRec | ??? | ??? |

### Collection Accounts Tables (IPE_31 - 7 tables!)

| # | SQL Server Table | SQL Server DB | Athena DB? | Athena Table? |
|---|------------------|---------------|------------|---------------|
| 8 | `RPT_CASHREC_TRANSACTION` | FinRec | ??? | ??? |
| 9 | `RPT_CASHREC_REALLOCATIONS` | FinRec | ??? | ??? |
| 10 | `RPT_PACKLIST_PAYMENTS` | FinRec | ??? | ??? |
| 11 | `RPT_CASHDEPOSIT` | FinRec | ??? | ??? |
| 12 | `RPT_PACKLIST_PACKAGES` | FinRec | ??? | ??? |
| 13 | `RPT_HUBS_3PL_MAPPING` | FinRec | ??? | ??? |
| 14 | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` | FinRec | ??? | ??? |

**Just fill in the "???" columns!**

**Note**: Operational docs revealed IPE_31 uses 7 tables, not 4 as initially documented.

---

## 📋 Bonus Questions (If You Have Time)

### 1. Column Naming
Do column names change from SQL Server to Athena?

Example: `[Posting Date]` → `posting_date`?

### 2. RPT_SOI Filters
This table is used 3 times for different purposes:
- **IPE_10**: Customer Prepayments
- **IPE_12**: Unreconciled Packages  
- **IPE_34**: Refunds

What column do I filter on to distinguish these? (e.g., `transaction_type`?)

### 3. IPE_31 Joins - **UPDATED**
The **7 tables** for Collection Accounts need to be joined. What are the join keys? (e.g., `transaction_id`, `package_id`?)

Specifically:
- How do `RPT_PACKLIST_PACKAGES` and `RPT_PACKLIST_PAYMENTS` join?
- How does `RPT_HUBS_3PL_MAPPING` fit into the join?
- What's the role of `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` in this query?

---

## 🚀 Why This Matters

This will unblock the entire C-PG-1 automation project and save **40 hours/month** of manual work.

---

## 📞 Response Methods

**Option 1**: Fill in the table above and reply via email

**Option 2**: Send me one sample Athena query (any of the 10 tables)

**Option 3**: Hop on a 15-minute call to walk through it together

Thanks! 🙏
