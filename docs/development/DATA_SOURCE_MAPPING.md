# C-PG-1 Reconciliation - Complete Data Source Mapping

**Date**: 17 October 2025  
**Status**: DISCOVERY COMPLETE - Awaiting Athena Table Mapping from Technical Team

---

## 🎯 Executive Summary

I have successfully **reverse-engineered the complete manual reconciliation process** by analyzing the Excel metadata. This document maps every SQL Server table used in the manual process to its (expected) Athena equivalent.

**Key Finding**: The C-PG-1 reconciliation is **NOT a single query**. It's a complex multi-source aggregation that combines data from:
- 2 databases (`AIG_Nav_DW`, `AIG_Nav_Jumia_Reconciliation`)
- 3 source systems (NAV, OMS, BOB)
- 12+ different tables/views
- 8 separate IPE/Control reports

**Blocker**: I need the technical team to confirm/correct the Athena database and table names for each SQL Server source.

---

## 📊 The Two Sides of the Reconciliation

### Side 1: "ACTUALS" (Source of Truth)

**What It Is**: The final general ledger balance from the NAV accounting system.

| Component | SQL Server Source | System | Athena Target (?) |
|-----------|-------------------|--------|-------------------|
| NAV GL Balance | `[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]` | NAV/FinRec | `process_central_fin_dwh.v_bs_anaplan_import_ifrs_mapping_currency_split`? |

**Query Type**: Single query, single source
**IPE Report**: CR_04 - NAV GL Balances
**Frequency**: Monthly (month-end)

---

### Side 2: "TARGET VALUES" (Expected Balance)

**What It Is**: The calculated expected balance, built by aggregating subsidiary ledgers from operational systems.

This is the complex part. It requires **6 separate data extractions** that are then combined:

#### Component 1: Customer AR Balances (IPE_07)

| Sub-component | SQL Server Source | System | Athena Target (?) |
|---------------|-------------------|--------|-------------------|
| Detailed entries | `[AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]` | NAV BI | `process_central_fin_dwh.detailed_customer_ledg_entry`? |
| Summary entries | `[AIG_Nav_DW].[dbo].[Customer Ledger Entries]` | NAV BI | `process_central_fin_dwh.customer_ledger_entries`? |

**Output**: `2. All Countries June-25 - IBSAR - Customer Accounts.xlsx`  
**GL Accounts**: 13003, 13004, 13009  
**Tool**: PowerBI Custom Report

---

#### Component 2: Customer Prepayments (IPE_10)

| Sub-component | SQL Server Source | System | Athena Target (?) |
|---------------|-------------------|--------|-------------------|
| Transaction data | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` | OMS/FinRec | `process_central_fin_dwh.rpt_soi`? |

**Output**: `4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx`  
**GL Accounts**: 18350  
**Filter**: Specific transaction types for prepayments  
**Tool**: PowerBI Custom Report

---

#### Component 3: Voucher Liabilities (IPE_08)

| Sub-component | SQL Server Source | System | Athena Target (?) |
|---------------|-------------------|--------|-------------------|
| Voucher balances | `[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]` | BOB/FinRec | `process_pg_bob.v_storecreditvoucher_closing`? |

**Output**: `All Countries - Jun.25 - Voucher TV Extract.xlsx`  
**GL Accounts**: 18412  
**Tool**: PowerPivot Query

---

#### Component 4: Collection Accounts Detail (IPE_31)

**Complex multi-table join**:

| Sub-component | SQL Server Source | System | Athena Target (?) |
|---------------|-------------------|--------|-------------------|
| Cash receipts | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_TRANSACTION]` | OMS/FinRec | `process_central_fin_dwh.rpt_cashrec_transaction`? |
| Reallocations | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS]` | OMS/FinRec | `process_central_fin_dwh.rpt_cashrec_reallocations`? |
| Packlist payments | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]` | OMS/FinRec | `process_central_fin_dwh.rpt_packlist_payments`? |
| Cash deposits | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]` | OMS/FinRec | `process_central_fin_dwh.rpt_cashdeposit`? |

**Output**: `Jun25 - ECL - CPMT detailed open balances - 08.07.2025.xlsx`  
**Tool**: PowerPivot with complex joins  
**Note**: This extraction supports the Collection Accounts reconciliation

---

#### Component 5: Marketplace Refund Liability (IPE_34)

| Sub-component | SQL Server Source | System | Athena Target (?) |
|---------------|-------------------|--------|-------------------|
| Refund data | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` (same table as IPE_10) | OMS/FinRec | `process_central_fin_dwh.rpt_soi`? |

**Output**: `4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx`  
**GL Accounts**: 18317  
**Filter**: Different filter than IPE_10 (refund-specific transactions)  
**Tool**: PowerBI Custom Report

---

#### Component 6: Packages Delivered Not Reconciled (IPE_12)

| Sub-component | SQL Server Source | System | Athena Target (?) |
|---------------|-------------------|--------|-------------------|
| Package status | `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` (same table again) | OMS/FinRec | `process_central_fin_dwh.rpt_soi`? |

**Output**: Multiple files:
- `2. All Countries June-25 - IBSAR - Customer Accounts.xlsx` (GL 13005)
- `4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx` (GL 13024)

**Filter**: Yet another filter on `RPT_SOI` (unreconciled package transactions)  
**Tool**: PowerBI Custom Report

---

## 🔑 Key Observations

### 1. The `RPT_SOI` Table Is CRITICAL

The table `[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]` is used by **3 different IPE reports**:
- IPE_10 (Customer Prepayments)
- IPE_34 (Refund Liability)
- IPE_12 (Packages Not Reconciled)

Each uses different WHERE clause filters to extract different subsets of data.

**Implication**: I need to understand the full schema of this table to replicate the 3 different filters.

---

### 2. Most Data Comes from FinRec, Not Source Systems

| Source Database | Tables | Systems Fed Into This DB |
|-----------------|--------|--------------------------|
| `AIG_Nav_Jumia_Reconciliation` (FinRec) | 9 tables | NAV, OMS, BOB, Seller Center |
| `AIG_Nav_DW` (NAV BI) | 2 tables | NAV only |

**Implication**: The `AIG_Nav_Jumia_Reconciliation` database is a **reconciliation layer** that pre-aggregates and transforms data from multiple operational systems. This is probably the `process_central_fin_dwh` database in Athena.

---

### 3. PowerBI and PowerPivot Are Key Tools

The manual process uses:
- **PowerBI Custom Reports**: For filtered extractions (IPE_07, IPE_10, IPE_34, IPE_12)
- **PowerPivot Queries**: For multi-table joins (IPE_31, IPE_08)

These tools are essentially visual query builders. My Python script needs to replicate the underlying SQL queries that these tools generate.

---

## 📋 Consolidated Table Mapping (For Technical Team)

**Instructions for Carlos/Joao**: Please fill in the "Athena Database" and "Athena Table/View" columns. Mark any that don't exist in Athena as "N/A".

| # | IPE Report | SQL Server Database | SQL Server Table/View | Source System | Athena Database | Athena Table/View | Status |
|---|------------|---------------------|----------------------|---------------|-----------------|-------------------|--------|
| 1 | CR_04 | `AIG_Nav_Jumia_Reconciliation` | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT` | NAV/FinRec | ? | ? | ❓ |
| 2 | IPE_07 | `AIG_Nav_DW` | `Detailed Customer Ledg_ Entry` | NAV BI | ? | ? | ❓ |
| 3 | IPE_07 | `AIG_Nav_DW` | `Customer Ledger Entries` | NAV BI | ? | ? | ❓ |
| 4 | IPE_10 | `AIG_Nav_Jumia_Reconciliation` | `RPT_SOI` | OMS/FinRec | ? | ? | ❓ |
| 5 | IPE_34 | `AIG_Nav_Jumia_Reconciliation` | `RPT_SOI` (same) | OMS/FinRec | Same as #4 | Same as #4 | ❓ |
| 6 | IPE_12 | `AIG_Nav_Jumia_Reconciliation` | `RPT_SOI` (same) | OMS/FinRec | Same as #4 | Same as #4 | ❓ |
| 7 | IPE_08 | `AIG_Nav_Jumia_Reconciliation` | `V_STORECREDITVOUCHER_CLOSING` | BOB/FinRec | ? | ? | ❓ |
| 8 | IPE_31 | `AIG_Nav_Jumia_Reconciliation` | `RPT_CASHREC_TRANSACTION` | OMS/FinRec | ? | ? | ❓ |
| 9 | IPE_31 | `AIG_Nav_Jumia_Reconciliation` | `RPT_CASHREC_REALLOCATIONS` | OMS/FinRec | ? | ? | ❓ |
| 10 | IPE_31 | `AIG_Nav_Jumia_Reconciliation` | `RPT_PACKLIST_PAYMENTS` | OMS/FinRec | ? | ? | ❓ |
| 11 | IPE_31 | `AIG_Nav_Jumia_Reconciliation` | `RPT_CASHDEPOSIT` | OMS/FinRec | ? | ? | ❓ |
| 12 | CR_05 | `AIG_Nav_Jumia_Reconciliation` | `RPT_FX_RATES` | NAV/FinRec | ? | ? | ❓ |

---

## 🎯 What This Enables

Once I have the Athena table mappings, I can:

1. **Automate the "Actuals" side**: Single query to get NAV GL balance
2. **Automate each "Target Value" component**: 6 separate queries (IPE_07, IPE_10, IPE_08, IPE_31, IPE_34, IPE_12)
3. **Aggregate the components**: Sum all target value components
4. **Perform the reconciliation**: Compare Actuals vs Target Values
5. **Generate evidence**: Export results to JSON/Excel with full audit trail
6. **Eliminate 40+ hours/month** of manual Excel work

---

## 🚀 Timeline

- **Today**: Send questions to technical team
- **This week**: Receive Athena table mappings
- **Next week**: Implement automated queries + test against manual results
- **Week after**: Production deployment

---

## 📞 Next Steps

**Action Required from Technical Team**:
1. Fill in the table mapping above
2. Provide one sample Athena query (any of the 12 tables)
3. Confirm data freshness/ETL schedule
4. Confirm column naming conventions (spaces → underscores?)

**My Commitment**:
Once I have the mappings, I will have a working prototype within 3-5 days.
