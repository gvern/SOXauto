# C-PG-1 Reconciliation Data Flow Diagram

**Purpose**: Visual explanation of the complete data flow for automation

---

## 🎯 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         MANUAL PROCESS (CURRENT)                          │
│                                                                            │
│  Step 1: Extract from SQL Server (via SSMS on Jump Server)                │
│  Step 2: Load into PowerBI/PowerPivot                                     │
│  Step 3: Apply filters, joins, transformations                            │
│  Step 4: Export to Excel files (8 different files)                        │
│  Step 5: Manually consolidate in master Excel file                        │
│  Step 6: Perform reconciliation calculations                              │
│  Step 7: Save evidence, create audit trail                                │
│                                                                            │
│  Time Required: 40+ hours/month                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
                          [ AUTOMATION TARGET ]
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                      AUTOMATED PROCESS (TARGET)                           │
│                                                                            │
│  Step 1: Execute Athena queries (via Python awswrangler)                  │
│  Step 2: Process results in pandas DataFrames                             │
│  Step 3: Aggregate components programmatically                            │
│  Step 4: Perform reconciliation                                           │
│  Step 5: Generate evidence JSON automatically                             │
│                                                                            │
│  Time Required: < 5 minutes                                               │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Detailed Data Flow

### Current Manual Process

```
                        SQL SERVER SOURCES
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────┐       ┌──────────────┐       ┌────────────┐
│  NAV BI DB  │       │  FinRec DB   │       │  BOB Data  │
│             │       │              │       │            │
│ • Customer  │       │ • RPT_SOI    │       │ • Voucher  │
│   Ledger    │       │ • RPT_CASH*  │       │   Closing  │
│ • G/L       │       │ • FX Rates   │       │            │
│   Entries   │       │ • Anaplan    │       │            │
└─────────────┘       └──────────────┘       └────────────┘
        │                       │                       │
        │         ┌─────────────┼─────────────┐         │
        │         │             │             │         │
        ▼         ▼             ▼             ▼         ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │PowerBI │ │PowerBI │ │PowerBI │ │ Power  │ │ Power  │
    │ IPE_07 │ │ IPE_10 │ │ IPE_34 │ │ Pivot  │ │ Pivot  │
    │        │ │        │ │        │ │ IPE_31 │ │ IPE_08 │
    └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
        │         │             │             │         │
        └─────────┴─────────────┴─────────────┴─────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   EXCEL FILES (8x)    │
                    │                       │
                    │ • Customer Accounts   │
                    │ • Other AR Accounts   │
                    │ • Voucher Extract     │
                    │ • Collection Details  │
                    │ • etc.                │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   MANUAL EXCEL        │
                    │   CONSOLIDATION       │
                    │                       │
                    │ • Copy/paste data     │
                    │ • Manual formulas     │
                    │ • Reconciliation      │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   FINAL EVIDENCE      │
                    │   (Excel + PDF)       │
                    └───────────────────────┘
```

---

### Target Automated Process

```
                      AWS ATHENA SOURCES
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌────────────────┐   ┌────────────┐
│process_central│   │process_central │   │process_pg  │
│  _fin_dwh     │   │  _fin_dwh      │   │  _bob      │
│               │   │                │   │            │
│• customer_    │   │• rpt_soi       │   │• v_store   │
│  ledger_*     │   │• rpt_cashrec_* │   │  credit    │
│• v_bs_anaplan │   │• rpt_fx_rates  │   │  voucher   │
└───────────────┘   └────────────────┘   └────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
            ┌──────────────────────────────────┐
            │   PYTHON IPERunner (SINGLE APP)  │
            │                                  │
            │  1. Execute 12 Athena queries    │
            │     via awswrangler              │
            │                                  │
            │  2. Load results into pandas DFs │
            │                                  │
            │  3. Apply business logic:        │
            │     • Filter by GL accounts      │
            │     • Filter by date ranges      │
            │     • Aggregate by country       │
            │                                  │
            │  4. Calculate:                   │
            │     • Actuals (NAV GL)           │
            │     • Target Values (sum of 6)   │
            │     • Variance                   │
            │                                  │
            │  5. Generate evidence JSON       │
            └──────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  EVIDENCE JSON  │
                    │  (Automated)    │
                    └─────────────────┘
```

---

## 🔍 Detailed Component Breakdown

### ACTUALS Side (Simple - Single Query)

```
┌────────────────────────────────────────────────────────────┐
│  Query 1: Get NAV GL Balance (CR_04)                       │
├────────────────────────────────────────────────────────────┤
│  Source Table:                                             │
│    process_central_fin_dwh.                                │
│      v_bs_anaplan_import_ifrs_mapping_currency_split       │
│                                                            │
│  Filter By:                                                │
│    • gl_account IN ('13003', '13004', '13005', ...)        │
│    • posting_date <= '2025-09-30'                          │
│    • country = 'KE' (or other)                             │
│                                                            │
│  Aggregate:                                                │
│    SUM(amount_lcy)                                         │
│                                                            │
│  Result:                                                   │
│    Single number = NAV GL Balance for Customer AR          │
└────────────────────────────────────────────────────────────┘
```

---

### TARGET VALUES Side (Complex - 6 Components)

```
┌────────────────────────────────────────────────────────────┐
│  Component 1: Customer AR Balances (IPE_07)                │
├────────────────────────────────────────────────────────────┤
│  Query 2a: Detailed Customer Ledger                        │
│    FROM: process_central_fin_dwh.detailed_customer_ledg_entry
│    WHERE: posting_date <= '2025-09-30'                     │
│           AND entry_type = 'Application'                   │
│                                                            │
│  Query 2b: Customer Ledger Summary                         │
│    FROM: process_central_fin_dwh.customer_ledger_entries  │
│    WHERE: posting_date <= '2025-09-30'                     │
│                                                            │
│  Result: Customer AR subtotal                              │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Component 2: Customer Prepayments (IPE_10)                │
├────────────────────────────────────────────────────────────┤
│  Query 3: RPT_SOI - Prepayments Filter                     │
│    FROM: process_central_fin_dwh.rpt_soi                  │
│    WHERE: transaction_type = 'PREPAYMENT' (or similar)     │
│           AND gl_account = '18350'                         │
│           AND posting_date <= '2025-09-30'                 │
│                                                            │
│  Result: Prepayments subtotal                              │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Component 3: Voucher Liabilities (IPE_08)                 │
├────────────────────────────────────────────────────────────┤
│  Query 4: BOB Voucher Closing Balances                     │
│    FROM: process_pg_bob.v_storecreditvoucher_closing      │
│    WHERE: closing_date = '2025-09-30'                      │
│           AND gl_account = '18412'                         │
│                                                            │
│  Result: Voucher liability subtotal                        │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Component 4: Collection Accounts (IPE_31)                 │
├────────────────────────────────────────────────────────────┤
│  Query 5a-5d: Multi-table join                             │
│    FROM: process_central_fin_dwh.rpt_cashrec_transaction  │
│    JOIN: process_central_fin_dwh.rpt_cashrec_reallocations│
│    JOIN: process_central_fin_dwh.rpt_packlist_payments    │
│    JOIN: process_central_fin_dwh.rpt_cashdeposit          │
│    WHERE: transaction_date <= '2025-09-30'                 │
│                                                            │
│  Result: Collection accounts subtotal                      │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Component 5: Refund Liability (IPE_34)                    │
├────────────────────────────────────────────────────────────┤
│  Query 6: RPT_SOI - Refunds Filter                         │
│    FROM: process_central_fin_dwh.rpt_soi                  │
│    WHERE: transaction_type = 'REFUND' (or similar)         │
│           AND gl_account = '18317'                         │
│           AND posting_date <= '2025-09-30'                 │
│                                                            │
│  Result: Refund liability subtotal                         │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Component 6: Packages Not Reconciled (IPE_12)             │
├────────────────────────────────────────────────────────────┤
│  Query 7: RPT_SOI - Unreconciled Packages Filter           │
│    FROM: process_central_fin_dwh.rpt_soi                  │
│    WHERE: reconciliation_status = 'PENDING' (or similar)   │
│           AND gl_account IN ('13005', '13024')             │
│           AND posting_date <= '2025-09-30'                 │
│                                                            │
│  Result: Unreconciled packages subtotal                    │
└────────────────────────────────────────────────────────────┘

        ↓  ↓  ↓  ↓  ↓  ↓
        
┌────────────────────────────────────────────────────────────┐
│  AGGREGATION LOGIC                                         │
├────────────────────────────────────────────────────────────┤
│  target_value = (                                          │
│      component_1_customer_ar                               │
│    + component_2_prepayments                               │
│    + component_3_vouchers                                  │
│    + component_4_collections                               │
│    + component_5_refunds                                   │
│    + component_6_unreconciled                              │
│  )                                                         │
└────────────────────────────────────────────────────────────┘
```

---

### Final Reconciliation

```
┌────────────────────────────────────────────────────────────┐
│  RECONCILIATION CALCULATION                                │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  actuals_value  = result_from_query_1  (NAV GL)            │
│  target_value   = sum_of_queries_2_to_7                    │
│  variance       = actuals_value - target_value             │
│                                                            │
│  IF abs(variance) < threshold:                             │
│      status = "RECONCILED"                                 │
│  ELSE:                                                     │
│      status = "VARIANCE_DETECTED"                          │
│      → Trigger investigation workflow                      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🎯 Critical Questions for Technical Team

To implement this automation, I need to know:

### 1. Table Name Mapping

**Can you confirm the Athena table names for these 12 SQL Server sources?**

| # | SQL Server Source | Athena Equivalent (?) |
|---|-------------------|-----------------------|
| 1 | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT` | `process_central_fin_dwh.___?` |
| 2 | `Detailed Customer Ledg_ Entry` | `process_central_fin_dwh.___?` |
| 3 | `Customer Ledger Entries` | `process_central_fin_dwh.___?` |
| 4-6 | `RPT_SOI` | `process_central_fin_dwh.___?` |
| 7 | `V_STORECREDITVOUCHER_CLOSING` | `process_pg_bob.___?` |
| 8 | `RPT_CASHREC_TRANSACTION` | `process_central_fin_dwh.___?` |
| 9 | `RPT_CASHREC_REALLOCATIONS` | `process_central_fin_dwh.___?` |
| 10 | `RPT_PACKLIST_PAYMENTS` | `process_central_fin_dwh.___?` |
| 11 | `RPT_CASHDEPOSIT` | `process_central_fin_dwh.___?` |
| 12 | `RPT_FX_RATES` | `process_central_fin_dwh.___?` |

### 2. Filter Logic

**For the 3 queries that use `RPT_SOI` with different filters:**

- IPE_10 (Prepayments): What column/value distinguishes prepayment transactions?
- IPE_34 (Refunds): What column/value distinguishes refund transactions?
- IPE_12 (Unreconciled): What column/value distinguishes unreconciled packages?

### 3. Join Keys

**For IPE_31 (4-table join):**

- What are the join keys between the 4 `RPT_CASHREC*` tables?
- Is it a simple `transaction_id` or more complex?

---

## 📊 Success Metrics

Once automated:

| Metric | Current | Target |
|--------|---------|--------|
| **Time per reconciliation** | 5-8 hours | < 5 minutes |
| **Manual Excel files created** | 8 files | 0 files |
| **Data copy/paste operations** | 50+ | 0 |
| **Human error risk** | High | None |
| **Evidence generation** | Manual | Automated |
| **Audit trail completeness** | Partial | 100% |

**Total time saved**: ~40 hours/month → ~480 hours/year

---

## 🚀 Implementation Plan

### Phase 1: Data Access (Current)
- [x] Connect to AWS Athena
- [x] Discover available databases
- [ ] **← WE ARE HERE: Waiting for table mappings**

### Phase 2: Query Development (Week 1)
- [ ] Implement Query 1 (Actuals)
- [ ] Implement Queries 2-7 (Target components)
- [ ] Test each query individually

### Phase 3: Aggregation Logic (Week 2)
- [ ] Build pandas aggregation pipeline
- [ ] Implement reconciliation calculations
- [ ] Add variance detection logic

### Phase 4: Evidence Generation (Week 2)
- [ ] Generate JSON evidence files
- [ ] Add metadata and timestamps
- [ ] Implement audit trail

### Phase 5: Testing & Validation (Week 3)
- [ ] Run against historical data
- [ ] Compare with manual Excel results
- [ ] Fix any discrepancies

### Phase 6: Production Deployment (Week 4)
- [ ] Deploy to production environment
- [ ] Document for SOX auditors
- [ ] Train team on new process

---

## 📞 Next Action

**Send this document + ATHENA_QUESTIONS_FOR_TEAM.md to Carlos/Joao**

Once I get the table mappings back, I can proceed with implementation immediately.
