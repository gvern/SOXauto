# Official SQL Server → Athena Table Mapping Request

**Date**: 17 October 2025  
**Source**: Common Report Reference from Confluence (official documentation)  
**Purpose**: Complete table mapping for C-PG-1 automation

---

## 📋 Critical Tables for C-PG-1 Reconciliation

Based on the official Common Report Reference documentation, here are the **exact tables** I need mapped from SQL Server to Athena:

### Priority 1: ACTUALS (NAV GL Balance)

| # | Report | SQL Server Source | Source DB | Expected Athena DB | Athena Table Name | Status |
|---|--------|-------------------|-----------|-------------------|-------------------|--------|
| 1 | CR_04 | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT` | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ CRITICAL |

**Question**: What is the exact Athena table name for the NAV GL balance view?

---

### Priority 2: NAV BI Tables (Customer Ledger)

| # | Report | SQL Server Source | Source DB | Expected Athena DB | Athena Table Name | Status |
|---|--------|-------------------|-----------|-------------------|-------------------|--------|
| 2 | IPE_07 | `Detailed Customer Ledg_ Entry` | `AIG_Nav_DW` | `process_central_fin_dwh`? | ??? | ❓ HIGH |
| 3 | IPE_07 | `Customer Ledger Entries` | `AIG_Nav_DW` | `process_central_fin_dwh`? | ??? | ❓ HIGH |

**Question**: Are these NAV BI tables in `process_central_fin_dwh` or a different database?

---

### Priority 3: Multi-Purpose OMS Table (Used 3 Times)

| # | Report | SQL Server Source | Source DB | Expected Athena DB | Athena Table Name | Status |
|---|--------|-------------------|-----------|-------------------|-------------------|--------|
| 4 | IPE_10 | `RPT_SOI` (filter: prepayments) | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ HIGH |
| 5 | IPE_12 | `RPT_SOI` (filter: unreconciled packages) | `AIG_Nav_Jumia_Reconciliation` | Same as above | Same as above | ❓ HIGH |
| 6 | IPE_34 | `RPT_SOI` (filter: refunds) | `AIG_Nav_Jumia_Reconciliation` | Same as above | Same as above | ❓ HIGH |

**Question**: This table is used by 3 different reports with different filters. What columns should I filter on to distinguish:
- Prepayment transactions (IPE_10)
- Unreconciled package transactions (IPE_12)
- Refund transactions (IPE_34)

---

### Priority 4: BOB Voucher Table

| # | Report | SQL Server Source | Source DB | Expected Athena DB | Athena Table Name | Status |
|---|--------|-------------------|-----------|-------------------|-------------------|--------|
| 7 | IPE_08 | `V_STORECREDITVOUCHER_CLOSING` | `AIG_Nav_Jumia_Reconciliation` | `process_pg_bob`? | ??? | ❓ MEDIUM |

**Question**: Is this BOB data in `process_pg_bob` or in `process_central_fin_dwh`?

---

### Priority 5: Multi-Table Join (Collection Accounts) - **UPDATED**

**Important**: Operational docs reveal IPE_31 uses **7 tables**, not 4!

| # | Report | SQL Server Source | Source DB | Expected Athena DB | Athena Table Name | Status |
|---|--------|-------------------|-----------|-------------------|-------------------|--------|
| 8 | IPE_31 | `RPT_CASHREC_TRANSACTION` | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ MEDIUM |
| 9 | IPE_31 | `RPT_CASHREC_REALLOCATIONS` | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ MEDIUM |
| 10 | IPE_31 | `RPT_PACKLIST_PAYMENTS` | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ MEDIUM |
| 11 | IPE_31 | `RPT_CASHDEPOSIT` | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ MEDIUM |
| 12 | IPE_31 | `RPT_PACKLIST_PACKAGES` | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ MEDIUM |
| 13 | IPE_31 | `RPT_HUBS_3PL_MAPPING` | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ MEDIUM |
| 14 | IPE_31 | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ MEDIUM |

**Question**: Are all 7 of these tables available in Athena? What are the join keys between them?

---

### Priority 6: FX Rates (Supporting Data)

| # | Report | SQL Server Source | Source DB | Expected Athena DB | Athena Table Name | Status |
|---|--------|-------------------|-----------|-------------------|-------------------|--------|
| 12 | CR_05 | `RPT_FX_RATES` | `AIG_Nav_Jumia_Reconciliation` | `process_central_fin_dwh`? | ??? | ❓ LOW |

**Question**: Is this table available in Athena?

---

## 🎯 Summary Table (Quick Reference) - **UPDATED**

**Please fill in the "Athena Table Name" column:**

| SQL Server Table | SQL Server DB | Report(s) | Athena DB | Athena Table Name |
|------------------|---------------|-----------|-----------|-------------------|
| `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT` | FinRec | CR_04 | ??? | ??? |
| `G_L Entries` | NAV BI | CR_03 | ??? | ??? |
| `Detailed Customer Ledg_ Entry` | NAV BI | IPE_07 | ??? | ??? |
| `Customer Ledger Entries` | NAV BI | IPE_07 | ??? | ??? |
| `RPT_SOI` | FinRec | IPE_10, IPE_12, IPE_34 | ??? | ??? |
| `V_STORECREDITVOUCHER_CLOSING` | FinRec | IPE_08 | ??? | ??? |
| `RPT_CASHREC_TRANSACTION` | FinRec | IPE_31 | ??? | ??? |
| `RPT_CASHREC_REALLOCATIONS` | FinRec | IPE_31 | ??? | ??? |
| `RPT_PACKLIST_PAYMENTS` | FinRec | IPE_31 | ??? | ??? |
| `RPT_CASHDEPOSIT` | FinRec | IPE_31 | ??? | ??? |
| `RPT_PACKLIST_PACKAGES` | FinRec | IPE_31 | ??? | ??? |
| `RPT_HUBS_3PL_MAPPING` | FinRec | IPE_31 | ??? | ??? |
| `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` | FinRec | IPE_31 | ??? | ??? |
| `RPT_FX_RATES` | FinRec | CR_05 | ??? | ??? |

**Total**: 14 unique tables (was 10, now updated with operational docs)

---

## 📊 Additional Mapping Questions

### 1. Database Location Pattern

Based on the SQL Server sources, I see:
- Most tables are in `AIG_Nav_Jumia_Reconciliation` (FinRec database)
- Some tables are in `AIG_Nav_DW` (NAV BI database)

**Question**: In Athena, are these typically mapped as:
- FinRec → `process_central_fin_dwh`?
- NAV BI → `process_central_fin_dwh` or a separate database?

### 2. Column Naming Convention

**Question**: Do column names in Athena match SQL Server exactly?

Example transformation possibilities:
- `[Posting Date]` → `posting_date` (lowercase, underscores)?
- `[G_L Account No_]` → `gl_account_no` (remove underscores at end)?
- `[Amount (LCY)]` → `amount_lcy` (remove parentheses)?

### 3. Schema Differences

**Question**: Are there any schema differences between SQL Server and Athena versions?
- Additional columns added in Athena?
- Columns renamed or removed?
- Data type changes (e.g., DATETIME vs TIMESTAMP)?

---

## 🚀 Example Query I Need to Write

### SQL Server Query (Current - Manual Process)

```sql
-- IPE_07: Customer AR Balances
SELECT 
    Country,
    [Posting Date],
    [Customer No_],
    [Document No_],
    [Amount (LCY)],
    [Entry Type]
FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
WHERE [Posting Date] <= '2025-09-30'
    AND [Entry Type] = 'Application'
    AND Country = 'KE'
ORDER BY [Posting Date]
```

### Athena Query (Target - Need Your Help)

```sql
-- IPE_07: Customer AR Balances (Athena version)
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

**Can you provide the exact Athena syntax for this query?**

---

## 💡 Why This Is Critical

### The Reconciliation Process

```
┌─────────────────────────────────────────┐
│  ACTUALS (from CR_04)                   │
│  → NAV GL Balance                       │
│  → Single query                         │
└─────────────────────────────────────────┘
                 ↓
         [ COMPARE & RECONCILE ]
                 ↑
┌─────────────────────────────────────────┐
│  TARGET VALUES (sum of 6 components)    │
│  → IPE_07: Customer AR                  │
│  → IPE_10: Prepayments                  │
│  → IPE_08: Vouchers                     │
│  → IPE_31: Collections                  │
│  → IPE_34: Refunds                      │
│  → IPE_12: Unreconciled                 │
└─────────────────────────────────────────┘
```

**Without these table mappings, I cannot automate this reconciliation.**

---

## 📞 What I'll Do With This Information

Once you provide the table mappings, I will:

1. **Update `config_athena.py`** with the correct database.table names
2. **Write 12 Athena queries** (one for each source table)
3. **Test each query** individually to verify data matches SQL Server
4. **Build aggregation logic** to sum the 6 target value components
5. **Implement reconciliation** comparison (Actuals vs Target)
6. **Generate evidence** JSON files automatically

**Timeline**: 3-5 days after receiving this mapping

---

## 🎯 Immediate Next Step

**Please respond with:**
1. The filled-in "Summary Table" above (Athena database and table names)
2. Sample query for one of the tables (e.g., IPE_07) showing exact Athena syntax
3. Any notes about schema differences or special considerations

**Impact**: This will unblock the entire C-PG-1 automation and save 40+ hours/month of manual Excel work.

Thank you! 🙏
