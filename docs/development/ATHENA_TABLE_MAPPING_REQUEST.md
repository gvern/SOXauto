# Athena Table Mapping Request - C-PG-1

**Date**: 21 October 2025  
**From**: Gustave  
**To**: Sandeep / Carlos  
**Purpose**: SQL Server → Athena table mappings for C-PG-1 automation

---

## 📋 Complete Table List (16 SQL Server Tables)

| # | SQL Server Table | SQL Server Database | Used By | GL Accounts | Athena DB | Athena Table |
|---|------------------|---------------------|---------|-------------|-----------|--------------|
| **1** | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT` | `AIG_Nav_Jumia_Reconciliation` | CR_04 | All (ACTUALS) | ? | ? |
| **2** | `Detailed Customer Ledg_ Entry` | `AIG_Nav_DW` | IPE_07 | 13003, 13004, 13009 | ? | ? |
| **3** | `Customer Ledger Entries` | `AIG_Nav_DW` | IPE_07 | 13003, 13004, 13009 | ? | ? |
| **4** | `RPT_SOI` | `AIG_Nav_Jumia_Reconciliation` | IPE_10, 12, 34 | 18350, 13005/24, 18317 | ? | ? |
| **5** | `V_STORECREDITVOUCHER_CLOSING` | `AIG_Nav_Jumia_Reconciliation` | IPE_08 | 18412 | ? | ? |
| **6** | `RPT_SC_TRANSCATIONS` | `AIG_Nav_Jumia_Reconciliation` | IPE_11 | 18304 | ? | ? |
| **7** | `RPT_SC_ACCOUNTSTATEMENTS` | `AIG_Nav_Jumia_Reconciliation` | IPE_11 | 18304 | ? | ? |
| **8** | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` | `AIG_Nav_Jumia_Reconciliation` | IPE_11, 31 | Multiple | ? | ? |
| **9** | `RPT_CASHREC_TRANSACTION` | `AIG_Nav_Jumia_Reconciliation` | IPE_31 | 13001, 13002 | ? | ? |
| **10** | `RPT_CASHREC_REALLOCATIONS` | `AIG_Nav_Jumia_Reconciliation` | IPE_31 | 13001, 13002 | ? | ? |
| **11** | `RPT_PACKLIST_PAYMENTS` | `AIG_Nav_Jumia_Reconciliation` | IPE_31 | 13001, 13002 | ? | ? |
| **12** | `RPT_CASHDEPOSIT` | `AIG_Nav_Jumia_Reconciliation` | IPE_31 | 13001, 13002 | ? | ? |
| **13** | `RPT_PACKLIST_PACKAGES` | `AIG_Nav_Jumia_Reconciliation` | IPE_31 | 13001, 13002 | ? | ? |
| **14** | `RPT_HUBS_3PL_MAPPING` | `AIG_Nav_Jumia_Reconciliation` | IPE_31 | 13001, 13002 | ? | ? |
| **15** | `RPT_FX_RATES` | `AIG_Nav_Jumia_Reconciliation` | CR_05 | N/A | ? | ? |
| **16** | `G_L Entry` | `AIG_Nav_DW` | CR_03 | Multiple | ? | ? |

---

## ❓ Specific Questions

### 1. RPT_SOI Multi-Use (Critical)
`RPT_SOI` is used 3 different ways - what column/filter distinguishes these?

- **IPE_10**: Customer Prepayments (GL 18350)
- **IPE_12**: Unreconciled Packages (GL 13005, 13024)  
- **IPE_34**: Marketplace Refunds (GL 18317)

---

### 2. IPE_31 Join Keys (7 Tables)
What are the join keys for IPE_31's 7 tables?

Main table: `RPT_CASHREC_TRANSACTION`  
Joins to:
- `RPT_CASHREC_REALLOCATIONS`
- `RPT_PACKLIST_PAYMENTS`
- `RPT_CASHDEPOSIT`
- `RPT_PACKLIST_PACKAGES`
- `RPT_HUBS_3PL_MAPPING`
- `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING`

---

### 3. Column Naming Convention
Do column names change from SQL Server to Athena?

Examples:
- `[Posting Date]` → `posting_date`?
- `[G_L Account No_]` → `gl_account_no`?
- `[Customer No_]` → `customer_no`?

---

## 📁 Reference Files Available

Baseline Excel files in `IPE_FILES/` if needed for column verification:
- `IPE_07a__IPE Baseline__Detailed customer ledger entries.xlsx`
- `IPE_08_test.xlsx`, `IPE_10...xlsx`, `IPE_11...xlsx`, `IPE_12...xlsx`
- `IPE_31.xlsx`, `IPE_34...xlsx`
- `CR_03_test.xlsx`, `CR_04_testing.xlsx`, `CR_05a...xlsx`

---

## 🎯 Priority

1. **CR_04** - GL balances (ACTUALS side - critical)
2. **IPE_07** - Customer ledger
3. **RPT_SOI** - Used by 3 IPEs, need filter info
4. **IPE_31** - Complex 7-table join
5. Others

---

Thanks!
