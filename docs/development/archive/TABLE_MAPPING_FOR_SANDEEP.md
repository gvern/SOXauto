# SQL Server → Athena Table Mapping - Complete Request for Sandeep

**Date**: 21 October 2025  
**From**: Gustave Vernay (SOXauto Automation)  
**To**: Sandeep  
**Purpose**: Unblock C-PG-1 automation with complete Athena table mappings

---

## 🎯 Executive Summary

I need Athena table mappings for **14 unique SQL Server tables** used across 10 IPEs/CRs in the C-PG-1 control. This is the final blocker for full automation that will save **40+ hours/month**.

**Current Status**:
- ✅ 1 IPE working (IPE_09 - BOB Sales Orders)
- ❌ 9 IPEs blocked waiting for table mappings
- 📊 Evidence generation framework complete
- 🔧 Code ready to deploy once mappings confirmed

**What I Need**:
1. Athena database names for each table
2. Athena table names (if different from SQL Server)
3. Key column names (especially if renamed)
4. Join keys for multi-table IPEs (especially IPE_31)
5. Filter columns for tables used multiple ways (RPT_SOI)

---

## 📊 Complete Table Mapping Request

### Priority 1: ACTUALS - GL Balance (CR_04)

**Critical**: This is the "ACTUALS" side of the reconciliation

| SQL Server Table | SQL Server DB | Used By | Athena DB | Athena Table | Status |
|------------------|---------------|---------|-----------|--------------|--------|
| `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT` | `AIG_Nav_Jumia_Reconciliation` | CR_04 | ??? | ??? | ❓ CRITICAL |

**Questions**:
1. What is the exact Athena table name?
2. Which database: `process_central_fin_dwh` or other?
3. Key columns needed:
   - GL Account number
   - Country/Company code
   - Balance amount (LCY)
   - Currency code
   - Posting date

**Why Critical**: This is the NAV GL balance that all IPEs reconcile TO. Without this, no reconciliation is possible.

---

### Priority 2: Customer Balances (IPE_07)

**Description**: Customer AR aging details

| SQL Server Table | SQL Server DB | Used By | Athena DB | Athena Table | Status |
|------------------|---------------|---------|-----------|--------------|--------|
| `Detailed Customer Ledg_ Entry` | `AIG_Nav_DW` | IPE_07 | ??? | ??? | ❓ HIGH |
| `Customer Ledger Entries` | `AIG_Nav_DW` | IPE_07 | ??? | ??? | ❓ HIGH |

**Questions**:
1. Are these in `process_central_fin_dwh` or different database?
2. Confirm column names:
   - `[Posting Date]` → `posting_date`?
   - `[Customer No_]` → `customer_no`?
   - `[Amount (LCY)]` → `amount_lcy`?
   - `[Entry Type]` → `entry_type`?
3. Are these two tables or one table in Athena?

**Sample Query I Need to Write**:
```sql
-- Target Athena query (need your help filling in ???)
SELECT 
    country,              -- ??? Confirm column name
    posting_date,         -- ??? Confirm column name
    customer_no,          -- ??? Confirm column name
    document_no,          -- ??? Confirm column name
    amount_lcy,           -- ??? Confirm column name
    entry_type            -- ??? Confirm column name
FROM ???.???              -- ??? Which database.table?
WHERE posting_date <= DATE '2025-09-30'
    AND entry_type = 'Application'
    AND country = 'KE'
ORDER BY posting_date
```

---

### Priority 3: Multi-Purpose OMS Table (IPE_10, IPE_12, IPE_34)

**Critical**: One table used 3 different ways

| SQL Server Table | SQL Server DB | Used By | Purpose | Athena DB | Athena Table | Status |
|------------------|---------------|---------|---------|-----------|--------------|--------|
| `RPT_SOI` | `AIG_Nav_Jumia_Reconciliation` | IPE_10 | Customer Prepayments | ??? | ??? | ❓ HIGH |
| `RPT_SOI` | `AIG_Nav_Jumia_Reconciliation` | IPE_12 | Unreconciled Packages | ??? | ??? | ❓ HIGH |
| `RPT_SOI` | `AIG_Nav_Jumia_Reconciliation` | IPE_34 | Marketplace Refunds | ??? | ??? | ❓ HIGH |

**Critical Question**: What column do I filter on to distinguish these 3 use cases?

**Hypothesis**:
```sql
-- IPE_10: Customer Prepayments
SELECT * FROM rpt_soi 
WHERE transaction_type = 'PREPAYMENT'  -- ??? Is this correct?
  AND gl_account = '18350'

-- IPE_12: Unreconciled Packages  
SELECT * FROM rpt_soi
WHERE transaction_type = 'PACKAGE'     -- ??? Is this correct?
  AND reconciliation_status = 'PENDING'
  AND gl_account IN ('13005', '13024')

-- IPE_34: Marketplace Refunds
SELECT * FROM rpt_soi
WHERE transaction_type = 'REFUND'      -- ??? Is this correct?
  AND gl_account = '18317'
```

**Please confirm**:
1. Athena database and table name
2. Filter column(s) to distinguish these 3 scenarios
3. Key columns available:
   - Transaction type?
   - GL account?
   - Reconciliation status?
   - Order/package ID?

---

### Priority 4: BOB Voucher Table (IPE_08)

**Description**: Store credit voucher liabilities

| SQL Server Table | SQL Server DB | Used By | Athena DB | Athena Table | Status |
|------------------|---------------|---------|-----------|--------------|--------|
| `V_STORECREDITVOUCHER_CLOSING` | `AIG_Nav_Jumia_Reconciliation` | IPE_08 | ??? | ??? | ❓ MEDIUM |

**Questions**:
1. Is this in `process_pg_bob` or `process_central_fin_dwh`?
2. Exact Athena table name?
3. Key columns:
   - Voucher ID
   - Customer ID
   - Voucher amount
   - Issue date
   - Expiry date
   - Status (active/used/expired)

---

### Priority 5: Marketplace Accrued Revenues (IPE_11)

**Description**: Seller Center to NAV reconciliation

| SQL Server Table | SQL Server DB | Used By | Athena DB | Athena Table | Status |
|------------------|---------------|---------|-----------|--------------|--------|
| `RPT_SC_TRANSCATIONS` | `AIG_Nav_Jumia_Reconciliation` | IPE_11 | ??? | ??? | ❓ MEDIUM |
| `RPT_SC_ACCOUNTSTATEMENTS` | `AIG_Nav_Jumia_Reconciliation` | IPE_11 | ??? | ??? | ❓ MEDIUM |
| `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` | `AIG_Nav_Jumia_Reconciliation` | IPE_11 | ??? | ??? | ❓ MEDIUM |

**Questions**:
1. Are these 3 tables in Athena?
2. Which database(s)?
3. Join keys between:
   - `RPT_SC_TRANSCATIONS` ↔ `RPT_SC_ACCOUNTSTATEMENTS`
   - `RPT_SC_ACCOUNTSTATEMENTS` ↔ `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING`

---

### Priority 6: Collection Accounts Detail (IPE_31) - COMPLEX!

**Critical**: Multi-table join with 7 tables

| # | SQL Server Table | SQL Server DB | Athena DB | Athena Table | Status |
|---|------------------|---------------|-----------|--------------|--------|
| 1 | `RPT_CASHREC_TRANSACTION` | `AIG_Nav_Jumia_Reconciliation` | ??? | ??? | ❓ MEDIUM |
| 2 | `RPT_CASHREC_REALLOCATIONS` | `AIG_Nav_Jumia_Reconciliation` | ??? | ??? | ❓ MEDIUM |
| 3 | `RPT_PACKLIST_PAYMENTS` | `AIG_Nav_Jumia_Reconciliation` | ??? | ??? | ❓ MEDIUM |
| 4 | `RPT_CASHDEPOSIT` | `AIG_Nav_Jumia_Reconciliation` | ??? | ??? | ❓ MEDIUM |
| 5 | `RPT_PACKLIST_PACKAGES` | `AIG_Nav_Jumia_Reconciliation` | ??? | ??? | ❓ MEDIUM |
| 6 | `RPT_HUBS_3PL_MAPPING` | `AIG_Nav_Jumia_Reconciliation` | ??? | ??? | ❓ MEDIUM |
| 7 | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` | `AIG_Nav_Jumia_Reconciliation` | ??? | ??? | ❓ MEDIUM |

**Critical Questions**:
1. Are all 7 tables available in Athena?
2. Which database(s)?
3. **Join structure** - please provide join keys:

```sql
-- Hypothetical join structure (NEED YOUR HELP!)
SELECT 
    t.transaction_id,
    t.transaction_date,
    t.amount,
    p.package_id,
    p.payment_amount,
    d.deposit_date,
    h.hub_name,
    m.gl_account
FROM 
    ???.rpt_cashrec_transaction t
    LEFT JOIN ???.rpt_cashrec_reallocations r ON ???  -- Join key?
    LEFT JOIN ???.rpt_packlist_payments p ON ???      -- Join key?
    LEFT JOIN ???.rpt_cashdeposit d ON ???            -- Join key?
    LEFT JOIN ???.rpt_packlist_packages pkg ON ???   -- Join key?
    LEFT JOIN ???.rpt_hubs_3pl_mapping h ON ???      -- Join key?
    LEFT JOIN ???.v_bs_anaplan_import_ifrs_mapping m ON ???  -- Join key?
WHERE 
    t.transaction_date <= DATE '2025-09-30'
```

**Specific Questions**:
1. What's the primary key of each table?
2. How do `RPT_PACKLIST_PACKAGES` and `RPT_PACKLIST_PAYMENTS` relate?
3. What's the role of `RPT_HUBS_3PL_MAPPING`? (Hub lookup?)
4. Why is `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` needed? (GL mapping?)

---

### Priority 7: FX Rates (CR_05)

**Description**: Foreign exchange rates for currency conversion

| SQL Server Table | SQL Server DB | Used By | Athena DB | Athena Table | Status |
|------------------|---------------|---------|-----------|--------------|--------|
| `RPT_FX_RATES` | `AIG_Nav_Jumia_Reconciliation` | CR_05 | ??? | ??? | ❓ LOW |

**Questions**:
1. Athena database and table name?
2. Key columns:
   - Currency pair (from/to)
   - Rate
   - Effective date
   - Rate type (spot/average/closing?)

---

## 📋 Summary Table (Quick Reference)

**Please fill in the "Athena DB" and "Athena Table Name" columns:**

| # | SQL Server Table | SQL Server DB | Report(s) | Athena DB | Athena Table Name | Column Naming Change? |
|---|------------------|---------------|-----------|-----------|-------------------|-----------------------|
| 1 | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT` | FinRec | CR_04 | ??? | ??? | ??? |
| 2 | `Detailed Customer Ledg_ Entry` | NAV BI | IPE_07 | ??? | ??? | ??? |
| 3 | `Customer Ledger Entries` | NAV BI | IPE_07 | ??? | ??? | ??? |
| 4 | `RPT_SOI` | FinRec | IPE_10, 12, 34 | ??? | ??? | ??? |
| 5 | `V_STORECREDITVOUCHER_CLOSING` | FinRec | IPE_08 | ??? | ??? | ??? |
| 6 | `RPT_SC_TRANSCATIONS` | FinRec | IPE_11 | ??? | ??? | ??? |
| 7 | `RPT_SC_ACCOUNTSTATEMENTS` | FinRec | IPE_11 | ??? | ??? | ??? |
| 8 | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` | FinRec | IPE_11, 31 | ??? | ??? | ??? |
| 9 | `RPT_CASHREC_TRANSACTION` | FinRec | IPE_31 | ??? | ??? | ??? |
| 10 | `RPT_CASHREC_REALLOCATIONS` | FinRec | IPE_31 | ??? | ??? | ??? |
| 11 | `RPT_PACKLIST_PAYMENTS` | FinRec | IPE_31 | ??? | ??? | ??? |
| 12 | `RPT_CASHDEPOSIT` | FinRec | IPE_31 | ??? | ??? | ??? |
| 13 | `RPT_PACKLIST_PACKAGES` | FinRec | IPE_31 | ??? | ??? | ??? |
| 14 | `RPT_HUBS_3PL_MAPPING` | FinRec | IPE_31 | ??? | ??? | ??? |
| 15 | `RPT_FX_RATES` | FinRec | CR_05 | ??? | ??? | ??? |

**Legend**:
- **FinRec** = `AIG_Nav_Jumia_Reconciliation`
- **NAV BI** = `AIG_Nav_DW`

---

## 🔍 General Mapping Questions

### Question 1: Database Location Pattern

Based on SQL Server sources, I see two main databases:
- `AIG_Nav_Jumia_Reconciliation` (FinRec) - Most tables
- `AIG_Nav_DW` (NAV BI) - Customer ledger tables

**In Athena, are these mapped as**:
- FinRec → `process_central_fin_dwh`?
- NAV BI → `process_central_fin_dwh` or separate database?
- BOB data → `process_pg_bob` or `process_central_fin_dwh`?

---

### Question 2: Column Naming Convention

**Do column names transform from SQL Server to Athena?**

Common patterns I've seen:
- `[Posting Date]` → `posting_date` (lowercase, underscores)?
- `[G_L Account No_]` → `gl_account_no` (remove trailing underscore)?
- `[Amount (LCY)]` → `amount_lcy` (remove parentheses)?
- `[Customer No_]` → `customer_no` (lowercase, underscore)?

**Please confirm**: Are column names in Athena:
- ✅ Lowercase?
- ✅ Underscores instead of spaces?
- ✅ Special characters removed?
- ❓ Or exactly the same as SQL Server (with brackets)?

---

### Question 3: Schema Differences

**Are there schema differences between SQL Server and Athena?**

Possible changes:
- Additional columns added in Athena?
- Columns renamed or removed?
- Data type changes (e.g., `DATETIME` vs `TIMESTAMP`)?
- Partition columns added?

---

### Question 4: Data Freshness

**How often is Athena data refreshed from SQL Server?**

- Daily?
- Real-time replication?
- Batch windows (e.g., nightly)?

**Why this matters**: For cutoff date logic - if I run on Oct 20 with cutoff Sept 30, is Sept 30 data guaranteed to be in Athena?

---

## 💡 Working Example (IPE_09 - Already Confirmed)

Here's the **one working example** I have for reference:

### SQL Server (hypothetical)
```sql
-- Hypothetical SQL Server query
SELECT 
    [Order Date],
    [Order ID],
    [Customer ID],
    [Total Amount],
    [Order Status]
FROM [AIG_BOB].[dbo].[SalesOrders]
WHERE [Order Date] < '2025-09-30'
ORDER BY [Order Date] DESC
```

### Athena (confirmed working)
```sql
-- Confirmed working Athena query
SELECT 
    order_date,        -- Note: lowercase, underscore
    order_id,
    customer_id,
    total_amount,
    order_status
FROM process_pg_bob.pg_bob_sales_order  -- Note: database.table format
WHERE order_date < DATE('2025-09-30')   -- Note: DATE() function
ORDER BY order_date DESC
```

**Key differences I've learned**:
1. Column names: lowercase with underscores
2. Database syntax: `database.table` format
3. Date functions: `DATE('YYYY-MM-DD')` instead of string literal
4. No square brackets needed

**Can you confirm**: Are all other tables similar?

---

## 🚀 Impact & Benefits

### Time Savings
- **Current manual process**: 40+ hours/month per country
- **Automated with mappings**: 2 hours/month
- **Total savings**: 95% time reduction

### Risk Reduction
- Eliminates manual data entry errors
- Consistent query logic month-over-month
- Automated SOX validation tests
- Complete audit trail with cryptographic integrity

### Scalability
- Once mapped, all 10 IPEs automated
- Can easily add new countries
- Can extend to other controls (C-PG-2, C-PG-3, etc.)

---

## 📞 How to Respond

### Option 1: Fill in the table (Easiest)
Copy the summary table above, fill in the ??? fields, and send back via email.

### Option 2: Provide sample queries (Most helpful)
Send me 2-3 sample Athena queries for any of these tables. I can extrapolate the patterns.

### Option 3: Screen share session (15-30 min)
We can hop on a call and walk through the mappings together. I can screen share and take notes.

### Option 4: Share documentation
If you have an existing SQL Server → Athena mapping document, that would be perfect!

---

## 🎯 Next Steps After Receiving Mappings

Once I have the mappings, I will:

1. **Week 1**: Update catalog with Athena configurations (2 hours)
2. **Week 2**: Write and test queries for all IPEs (8 hours)
3. **Week 3**: Generate evidence packages for all IPEs (4 hours)
4. **Week 4**: End-to-end reconciliation testing (8 hours)

**Target**: Full automation by **Mid-November 2025**

---

## 📎 Appendices

### Appendix A: Current Catalog Structure
See: `/src/core/catalog/pg1_catalog.py`

### Appendix B: Official Mapping Request
See: `/docs/development/OFFICIAL_TABLE_MAPPING.md`

### Appendix C: Quick Reference Card
See: `/docs/development/QUICK_REFERENCE_FOR_TEAM.md`

### Appendix D: Working IPE Example
See: `/evidence/IPE_09/20251020_174311_789/01_executed_query.sql`

### Appendix E: Evidence Package Structure
See: `/docs/development/EVIDENCE_PACKAGE_PRESENTATION.md`

---

## ❓ Priority Questions Summary

**If you can only answer 3 questions, please answer these:**

1. **CR_04 Table** (CRITICAL): What is the Athena equivalent of `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT`?
   - This is the NAV GL balance - the entire reconciliation depends on it

2. **RPT_SOI Filters** (HIGH): What column do I filter on to distinguish:
   - Prepayments (IPE_10)
   - Unreconciled Packages (IPE_12)
   - Refunds (IPE_34)

3. **IPE_31 Joins** (MEDIUM): How do the 7 Collection Account tables join together?
   - `RPT_CASHREC_TRANSACTION` (main table?)
   - `RPT_PACKLIST_PAYMENTS` (join via what key?)
   - `RPT_PACKLIST_PACKAGES` (join via what key?)
   - Others...

---

**Thank you for your help unblocking this critical automation!**

**Contact**: Gustave Vernay  
**Email**: [your email]  
**Slack**: @gustave  
**Meeting**: Happy to schedule 15-30 min session if easier

---

**END OF DOCUMENT**

**Prepared**: 21 October 2025  
**Version**: 1.0  
**Status**: Awaiting Sandeep's response
