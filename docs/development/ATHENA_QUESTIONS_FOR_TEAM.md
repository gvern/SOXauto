# Questions for Carlos/Joao - Athena Data Mapping

**Date**: 17 October 2025  
**Context**: Refactoring SOXauto to use AWS Athena instead of direct SQL Server connection  
**Discovery**: Successfully connected to Athena and found 148 databases  
**Source**: Official Common Report Reference documentation from Confluence

---

## ✅ What We Discovered

### Athena Access Confirmed
I can successfully access AWS Athena and found these relevant databases:

1. **`process_central_fin_dwh`** - 1 table (`central_fin_dwh_ecommerce_customer`)
2. **`raw_central_fin_dwh`** - 1 table (`central_fin_dwh_customer_history`)
3. **`process_pg_bob`** - 29 tables (sales_order, customer, seller, etc.)
4. **`raw_pg_bob`** - 23 tables (history versions)
5. **`process_pg_dwh`** - 11 tables (vendor_perf, purchase_order, etc.)

Total access: **148 Athena databases** ✅

### Official Source Documentation Found
I now have the **official Common Report Reference table** from Confluence that maps every IPE/CR report to its exact SQL Server source. This is the authoritative mapping used by the entire SOX team.

---

## 🚨 OFFICIAL C-PG-1 SOURCE MAPPING (From Confluence)

Based on the official Common Report Reference documentation, here are the **exact SQL Server sources** used by C-PG-1:

| Report ID | Source System | Database | SQL Server Table(s) | Purpose in C-PG-1 |
|-----------|---------------|----------|---------------------|-------------------|
| **CR_04** | NAV | FinRec | `[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]` | **ACTUALS** - NAV GL Balance |
| **IPE_07** | NAV | NAVBI | `[AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]`<br>`[AIG_Nav_DW].[dbo].[Customer Ledger Entries]` | Customer AR Balances |
| **IPE_08** | BOB | FinRec | `[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]` | Voucher Liabilities |
| **IPE_10** | OMS | FinRec | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` | Customer Prepayments |
| **IPE_12** | OMS | FinRec | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` | Packages Not Reconciled |
| **IPE_31** | OMS | FinRec | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_TRANSACTION]`<br>`[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS]`<br>`[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]`<br>`[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]` | Collection Accounts Detail |
| **IPE_34** | OMS | FinRec | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` | Marketplace Refund Liability |
| **CR_05** | NAV | FinRec | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]` | FX Rates (Supporting) |

**Total Sources**: 3 databases, 10 unique tables (with `RPT_SOI` used 3 times with different filters)

---

## ❓ Critical Questions - UPDATED WITH SPECIFIC MAPPINGS

**Note**: I discovered the exact source tables used in the manual reconciliation process. Below are **precise mapping questions** based on the actual IPE reports.

---

## 🎯 PRIORITY 1: NAV GL Balances (The "Actuals" Side)

### IPE Report: `CR_04` - NAV GL Balances

**Manual Process Source**:
- **SQL Server Table**: `[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]`
- **Used For**: Getting the final GL balance from NAV (the "source of truth")
- **Tool**: PowerPivot query

**❓ QUESTION**: What is the Athena equivalent of this view?
- Database: `process_central_fin_dwh`?
- Table name: `v_bs_anaplan_import_ifrs_mapping_currency_split`?
- Or is it transformed/renamed in Athena?

**Why Critical**: This is the **"Actuals"** side of every reconciliation. Without this, I cannot get the final balance to compare against.

---

## 🎯 PRIORITY 2: Customer Balances (Major Component)

### IPE Report: `IPE_07` - Customer Balances

**Manual Process Sources**:
- **SQL Server Tables**: 
  - `[AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]`
  - `[AIG_Nav_DW].[dbo].[Customer Ledger Entries]`
- **Used For**: Monthly customer AR aging (GLs 13003, 13004, 13009)
- **Output File**: `2. All Countries June-25 - IBSAR - Customer Accounts.xlsx`
- **Tool**: PowerBI Custom Report

**❓ QUESTIONS**:
1. What is the Athena equivalent of `[Detailed Customer Ledg_ Entry]`?
   - Database: `process_central_fin_dwh`?
   - Table: `detailed_customer_ledg_entry` or `customer_ledger_entries_detailed`?

2. What is the Athena equivalent of `[Customer Ledger Entries]`?
   - Same database?
   - Column naming: Are spaces replaced with underscores? (e.g., `[Posting Date]` → `posting_date`)

---

## 🎯 PRIORITY 3: Multi-Source Tables from FinRec

### IPE Report: `IPE_10` - Customer Prepayments TV

**Manual Process Source**:
- **SQL Server Table**: `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]`
- **System**: OMS/FinRec
- **Used For**: Customer prepayments (GL 18350)
- **Output File**: `4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx`

### IPE Report: `IPE_34` - Marketplace Refund Liability

**Manual Process Source**:
- **SQL Server Table**: `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` (same table, different query)
- **System**: OMS/FinRec
- **Used For**: Refund liability (GL 18317)

### IPE Report: `IPE_12` - Packages Delivered Not Reconciled

**Manual Process Source**:
- **SQL Server Table**: `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` (same table again)
- **System**: OMS/FinRec
- **Used For**: Unreconciled packages (GLs 13005, 13024)

**❓ QUESTION**: What is the Athena equivalent of `[RPT_SOI]`?
- This table is used by **3 different IPE reports** with different filters
- Database: `process_central_fin_dwh`?
- Table name: `rpt_soi`?
- Does it contain all the same columns as SQL Server version?

---

## 🎯 PRIORITY 4: BOB System Tables

### IPE Report: `IPE_08` - TV Voucher Liabilities

**Manual Process Source**:
- **SQL Server View**: `[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]`
- **System**: BOB/FinRec
- **Used For**: Voucher liabilities (GL 18412)
- **Output File**: `All Countries - Jun.25 - Voucher TV Extract.xlsx`

**❓ QUESTION**: What is the Athena equivalent of this BOB voucher view?
- Is it in `process_pg_bob`?
- Table/view name: `v_storecreditvoucher_closing` or different?

---

## 🎯 PRIORITY 5: Complex Multi-Table Extraction

### IPE Report: `IPE_31` - PG Detailed TV Extraction

**Manual Process Sources** (Multiple tables):
- `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_TRANSACTION]`
- `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS]`
- `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]`
- `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]`

**System**: OMS/FinRec
**Used For**: Collection accounts detail
**Output File**: `Jun25 - ECL - CPMT detailed open balances - 08.07.2025.xlsx`
**Tool**: PowerPivot with complex joins

**❓ QUESTIONS**:
1. Are all 4 of these tables available in Athena?
2. What database are they in? (`process_central_fin_dwh`?)
3. Are the table names the same (just lowercase)?
4. Can I join them the same way as in SQL Server?

---

## 🎯 PRIORITY 6: FX Rates Reference Data

### Control Report: `CR_05` - FX Rates

**Manual Process Source**:
- **SQL Server Table**: `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]`
- **System**: NAV/FinRec
- **Used For**: Currency conversion in all reconciliations

**❓ QUESTION**: What is the Athena equivalent for FX rates?
- Is this a separate table or embedded in transaction tables?

---

### 4. Data Freshness & Update Frequency

**Question**: How often is the Athena data updated from the source SQL Servers?

- Real-time?
- Hourly?
- Daily (batch ETL)?
- Other schedule?

**Why this matters**: For SOX compliance, I need to know if the data in Athena is current enough for month-end reconciliations.

---

### 5. Schema & Column Mapping

**Question**: Are the column names in Athena tables the same as in SQL Server?

Example:
- SQL Server: `[Posting Date]` (with spaces)
- Athena: `posting_date` (lowercase, underscores)?

**Request**: Can you share a schema mapping document or Glue Data Catalog access?

---

### 6. Athena Workgroup & Query Limits

**Question**: What Athena workgroup should I use?

- Default workgroup?
- Specific workgroup for SOX/Finance?

**Related**:
- Are there query limits (timeout, data scanned)?
- Cost budgets I should be aware of?

---

### 7. Authentication Method

**Current setup**: I'm using temporary credentials from AWS portal:
```
https://jumia.awsapps.com/start → 007809111365 → "Command line access"
```

**Question**: For the automated Python script, what's the recommended auth method?

- Continue with profile `007809111365_Data-Prod-DataAnalyst-NonFinance`?
- Use a service account?
- AWS SSO programmatic access?
- Other?

---

### 8. Missing Databases

I noticed databases like `consume_central_core` exist, but I couldn't find:
- A specific `nav_bi` database
- A specific `finrec` database
- A specific `gl_entries` table

**Question**: Are these integrated into other databases? Or do they have different names in Athena?

---

## 📊 COMPLETE SQL SERVER → ATHENA MAPPING TABLE

This table shows **every single source table** used in the manual C-PG-1 reconciliation process:

| IPE Report | SQL Server Source | Source System | Athena Database (?) | Athena Table (?) | Priority |
|------------|-------------------|---------------|---------------------|------------------|----------|
| **CR_04** - NAV GL Balances | `[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]` | NAV/FinRec | `process_central_fin_dwh`? | `v_bs_anaplan_import_ifrs_mapping_currency_split`? | **CRITICAL** |
| **IPE_07** - Customer Balances | `[AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]` | NAV BI | `process_central_fin_dwh`? | `detailed_customer_ledg_entry`? | **HIGH** |
| **IPE_07** - Customer Balances | `[AIG_Nav_DW].[dbo].[Customer Ledger Entries]` | NAV BI | `process_central_fin_dwh`? | `customer_ledger_entries`? | **HIGH** |
| **IPE_10** - Customer Prepayments | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` | OMS/FinRec | `process_central_fin_dwh`? | `rpt_soi`? | **HIGH** |
| **IPE_34** - Refund Liability | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` | OMS/FinRec | Same as above | Same as above | **HIGH** |
| **IPE_12** - Packages Not Reconciled | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` | OMS/FinRec | Same as above | Same as above | **HIGH** |
| **IPE_08** - Voucher Liabilities | `[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]` | BOB/FinRec | `process_pg_bob`? | `v_storecreditvoucher_closing`? | **MEDIUM** |
| **IPE_31** - TV Collection Details | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_TRANSACTION]` | OMS/FinRec | `process_central_fin_dwh`? | `rpt_cashrec_transaction`? | **MEDIUM** |
| **IPE_31** - TV Collection Details | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS]` | OMS/FinRec | `process_central_fin_dwh`? | `rpt_cashrec_reallocations`? | **MEDIUM** |
| **IPE_31** - TV Collection Details | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]` | OMS/FinRec | `process_central_fin_dwh`? | `rpt_packlist_payments`? | **MEDIUM** |
| **IPE_31** - TV Collection Details | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]` | OMS/FinRec | `process_central_fin_dwh`? | `rpt_cashdeposit`? | **MEDIUM** |
| **CR_05** - FX Rates | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]` | NAV/FinRec | `process_central_fin_dwh`? | `rpt_fx_rates`? | **MEDIUM** |
| **IPE_11** - Marketplace Accrued Revenue | `[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING]` | Seller Center/FinRec | `process_central_fin_dwh`? | `v_bs_anaplan_import_ifrs_mapping`? | **LOW** |

**Key Observation**: Most tables come from the `[AIG_Nav_Jumia_Reconciliation]` database (the FinRec reconciliation layer), NOT directly from operational systems.

---

## 🎯 What I Need to Proceed

**MINIMUM REQUIRED** (to unblock development):

Please fill in the "?" columns in the table above. Specifically:

1. **Confirm or correct the Athena database name** for each source
2. **Confirm or correct the Athena table/view name** for each source
3. **Flag any tables that DON'T exist in Athena** (so I know to find alternatives)

**IDEAL ADDITIONAL INFORMATION**:

1. **Schema comparison**: Do column names match exactly? (e.g., `[Posting Date]` vs `posting_date`)
2. **Data freshness**: ETL schedule for `process_central_fin_dwh` updates
3. **Join keys**: Any differences in how tables relate to each other in Athena vs SQL Server
4. **Sample query**: One working Athena query that joins 2+ of these tables (so I can see the pattern)

---

## 📋 Example Query Translation I Need Help With

### SQL Server Query (Manual Process - IPE_07)

```sql
SELECT 
    Country,
    [Posting Date],
    [Customer No_],
    [Document No_],
    [Amount (LCY)]
FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
WHERE [Posting Date] <= '2025-09-30'
    AND [Entry Type] = 'Application'
ORDER BY Country, [Posting Date]
```

### Athena Query (What I Need to Write)

```sql
SELECT 
    country,              -- ?? Confirm exact column name
    posting_date,         -- ?? Confirm exact column name
    customer_no,          -- ?? Confirm exact column name  
    document_no,          -- ?? Confirm exact column name
    amount_lcy            -- ?? Confirm exact column name
FROM process_central_fin_dwh.detailed_customer_ledg_entry  -- ?? Confirm database.table
WHERE posting_date <= DATE '2025-09-30'
    AND entry_type = 'Application'  -- ?? Confirm column name
ORDER BY country, posting_date
```

**Can you provide the exact Athena syntax for this query?**

---

## 🚀 Next Steps After Your Response

Once I have the mapping, I will:

1. **Update all IPE configurations** (`ipe_configs_athena.py`) with correct database.table names
2. **Refactor `IPERunner`** to execute Athena queries instead of SQL Server
3. **Test each IPE extraction** individually against Athena
4. **Build the multi-source aggregation logic** for calculating target values
5. **Validate results** against the manual Excel files

**Timeline**: If I get this mapping today, I can have a working prototype by end of week.

---

## 💡 Why This Information Is Critical

The manual reconciliation process works like this:

```
                    MANUAL C-PG-1 RECONCILIATION
                            
┌─────────────────────────────────────────────────────────────┐
│                     "ACTUALS" (NAV GL)                      │
│   Source: V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT   │
│                    (Single table query)                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
                      [ COMPARE / RECONCILE ]
                              ↑
┌─────────────────────────────────────────────────────────────┐
│                    "TARGET VALUES"                          │
│           (Aggregated from multiple sources)                │
│                                                             │
│  1. Customer Balances (IPE_07)                              │
│     + Detailed Customer Ledg_ Entry                         │
│     + Customer Ledger Entries                               │
│                                                             │
│  2. Customer Prepayments (IPE_10)                           │
│     + RPT_SOI                                               │
│                                                             │
│  3. Voucher Liabilities (IPE_08)                            │
│     + V_STORECREDITVOUCHER_CLOSING                          │
│                                                             │
│  4. Collection Accounts (IPE_31)                            │
│     + RPT_CASHREC_TRANSACTION                               │
│     + RPT_CASHREC_REALLOCATIONS                             │
│     + RPT_PACKLIST_PAYMENTS                                 │
│     + RPT_CASHDEPOSIT                                       │
│                                                             │
│  5. Refund Liability (IPE_34)                               │
│     + RPT_SOI (different filter)                            │
│                                                             │
│  6. Packages Not Reconciled (IPE_12)                        │
│     + RPT_SOI (different filter)                            │
│                                                             │
│  → SUM all components → Compare with NAV GL                 │
└─────────────────────────────────────────────────────────────┘
```

**Without the Athena table mappings, I cannot replicate this process in code.**

---

## 📞 Contact

Ready to answer follow-up questions or hop on a call to walk through this together.

**Goal**: Replace 40+ hours/month of manual Excel work with automated Athena queries. This mapping is the final piece I need.

---

## 📊 Example Query Translation Needed

### SQL Server Query (Current Manual Process)

```sql
SELECT 
    [Posting Date],
    [G_L Account No_],
    [Amount],
    [Description]
FROM [AIG_Nav_DW].[dbo].[G_L Entries]
WHERE [Posting Date] < '2025-09-30'
ORDER BY [Posting Date] DESC
```

### Athena Query (What I Need to Write)

```sql
SELECT 
    posting_date,    -- ?? Confirm column name
    gl_account_no,   -- ?? Confirm column name
    amount,          -- ?? Confirm column name
    description      -- ?? Confirm column name
FROM ???.???        -- Which database.table?
WHERE posting_date < DATE('2025-09-30')
ORDER BY posting_date DESC
```

**Can you help fill in the `???` parts?**

---

## 🚀 Next Steps After Your Response

Once I have the mapping, I will:

1. **Update IPE configurations** with correct Athena database/table names
2. **Refactor `IPERunner`** to use `awswrangler` instead of `pyodbc`
3. **Test extraction** on a sample IPE (e.g., IPE_07)
4. **Validate data quality** by comparing Athena vs. SSMS results
5. **Deploy automated extraction** for all IPEs

---

## 📝 Current Code Architecture

For reference, here's what I'm changing:

### Before (SQL Server - Current)
```python
import pyodbc
connection = pyodbc.connect("DRIVER={...};SERVER=fin-sql.jumia.local;...")
df = pd.read_sql(query, connection)
```

### After (Athena - Target)
```python
import awswrangler as wr
df = wr.athena.read_sql_query(
    sql=query,
    database="???",  # Need to confirm
    s3_output="s3://athena-query-results-s3-ew1-production-jdata/"
)
```

---

## 🆘 Urgent Priority

**Most critical for immediate progress**:

1. ✅ Athena database name for NAV_BI → G_L Entries
2. ✅ Athena database name for FINREC → RPT_SOI  
3. ✅ Confirmation that `process_pg_bob` is correct for BOB

Everything else can be figured out afterwards, but I need these three mappings to refactor the IPE extraction code.

---

**Thank you!** 🙏

Let me know if you need any clarification on these questions or if there's documentation I should read first.

---

**Contact**: Gustave  
**AWS Profile**: `007809111365_Data-Prod-DataAnalyst-NonFinance`  
**Athena Access**: ✅ Confirmed (148 databases visible)
