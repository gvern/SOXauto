# 🔍 DISCOVERY UPDATE: IPE_31 Complexity Revealed

**Date**: 17 October 2025  
**Source**: Operational C-PG-1 Control Documentation  
**Impact**: IPE_31 (Collection Accounts) is more complex than initially documented

---

## 🚨 Critical Finding

### What We Thought (From Common Report Reference)

IPE_31 uses **4 tables**:
1. `RPT_CASHREC_TRANSACTION`
2. `RPT_CASHREC_REALLOCATIONS`
3. `RPT_PACKLIST_PAYMENTS`
4. `RPT_CASHDEPOSIT`

### What We Now Know (From Operational Docs)

IPE_31 actually uses **7 tables**:
1. ✅ `RPT_CASHREC_TRANSACTION` (confirmed)
2. ✅ `RPT_CASHREC_REALLOCATIONS` (confirmed)
3. ✅ `RPT_PACKLIST_PAYMENTS` (confirmed)
4. ✅ `RPT_CASHDEPOSIT` (confirmed)
5. ❌ `RPT_PACKLIST_PACKAGES` (**NEW**)
6. ❌ `RPT_HUBS_3PL_MAPPING` (**NEW**)
7. ❌ `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` (**NEW**)

**Impact**: We need to update our table mapping request from 10 tables to **14 tables**.

---

## 📊 Complete C-PG-1 Table List (Final)

### Actuals Side (2 sources)

| Report | Table | Database | Purpose |
|--------|-------|----------|---------|
| CR_04 | `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT` | FinRec | NAV GL Balance (primary) |
| CR_03 | `G_L Entries` | NAV BI | NAV GL Entries (alternative/verification) |

### Target Values Side (12 sources)

| Component | Report | Tables | Database |
|-----------|--------|--------|----------|
| **Customer AR** | IPE_07 | • `Detailed Customer Ledg_ Entry`<br>• `Customer Ledger Entries` | NAV BI |
| **Prepayments** | IPE_10 | • `RPT_SOI` | FinRec |
| **Vouchers** | IPE_08 | • `V_STORECREDITVOUCHER_CLOSING` | FinRec/BOB |
| **Collections** | IPE_31 | • `RPT_CASHREC_TRANSACTION`<br>• `RPT_CASHREC_REALLOCATIONS`<br>• `RPT_PACKLIST_PAYMENTS`<br>• `RPT_CASHDEPOSIT`<br>• `RPT_PACKLIST_PACKAGES`<br>• `RPT_HUBS_3PL_MAPPING`<br>• `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING` | FinRec |
| **Refunds** | IPE_34 | • `RPT_SOI` (same as IPE_10) | FinRec |
| **Unreconciled** | IPE_12 | • `RPT_SOI` (same as IPE_10) | FinRec |

### Supporting Data (1 source)

| Report | Table | Database | Purpose |
|--------|-------|----------|---------|
| CR_05 | `RPT_FX_RATES` | FinRec | Currency conversion |

**Grand Total**: 14 unique tables

---

## 🔑 Key Insights from Operational Docs

### 1. Tools Used in Manual Process

| Tool | Usage | Reports |
|------|-------|---------|
| **PowerBI Dashboard** | Complex filtered extractions | IPE_07, IPE_11, IPE_10, IPE_34, IPE_12 |
| **PowerPivot** | Multi-table joins | IPE_08, IPE_31 |
| **Ad-hoc Query** | Simple direct queries | CR_03, CR_04 |

**Implication**: PowerPivot queries are the most complex - IPE_31 joins 7 tables!

### 2. Collection Accounts (IPE_31) Structure

The operational docs break down IPE_31 into 4 separate data sources:

#### Source 1: Packlist Packages
- `RPT_PACKLIST_PACKAGES`
- Likely tracks package delivery status

#### Source 2: Cash Receipts & Deposits
- `RPT_CASHREC_TRANSACTION`
- `RPT_CASHDEPOSIT`
- Tracks actual cash received

#### Source 3: Reallocations & 3PL Mapping
- `RPT_CASHREC_REALLOCATIONS`
- `RPT_HUBS_3PL_MAPPING`
- Handles cash reallocation between hubs/3PL partners

#### Source 4: NAV GL Mapping
- `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING`
- Maps collection data to GL accounts

**This is a complex ETL pipeline in Excel/PowerPivot!**

### 3. Database Sources Clarification

| Database Name | SQL Server | Content |
|---------------|------------|---------|
| **FinRec** | `AIG_Nav_Jumia_Reconciliation` | Pre-reconciled data from multiple systems |
| **NAV BI** | `AIG_Nav_DW` | Direct NAV data warehouse |
| **BOB** | N/A (integrated into FinRec) | BOB system data (vouchers) |

Most tables (11 of 14) are in FinRec, confirming it's a reconciliation data warehouse layer.

---

## 📝 Updated Questions for Technical Team

### New Critical Question for IPE_31

**Question**: IPE_31 (Collection Accounts) uses 7 tables in the manual process:
1. `RPT_CASHREC_TRANSACTION`
2. `RPT_CASHREC_REALLOCATIONS`
3. `RPT_PACKLIST_PAYMENTS`
4. `RPT_CASHDEPOSIT`
5. `RPT_PACKLIST_PACKAGES`
6. `RPT_HUBS_3PL_MAPPING`
7. `V_BS_ANAPLAN_IMPORT_IFRS_MAPPING`

Can you provide:
- Athena table names for all 7?
- The join logic (which columns link these tables)?
- Or better yet: Does a **pre-joined view** exist in Athena for Collection Accounts?

### Possible Simplification

In many data warehouse migrations, complex multi-table joins are pre-materialized into views or tables.

**Follow-up question**: Is there an Athena view like `v_collection_accounts_summary` that already combines these 7 tables?

---

## 🎯 Impact on Implementation

### Before This Discovery
- Planned to query 10 tables
- IPE_31 seemed moderately complex (4-table join)

### After This Discovery
- Need to query 14 tables
- IPE_31 is **highly complex** (7-table join with hub mappings)
- May need to ask if a pre-aggregated view exists

### Updated Timeline

| Task | Original Estimate | Updated Estimate |
|------|-------------------|------------------|
| Get table mappings | 1-3 days | 1-3 days (unchanged) |
| Implement queries | 3-5 days | 5-7 days (+2 days for IPE_31 complexity) |
| Test & validate | 3-5 days | 4-6 days (+1 day for additional tables) |

**New total**: 2.5-3.5 weeks (was 2-3 weeks)

---

## ✅ Action Items

### 1. Update All Documentation ✅ DONE
- [x] `OFFICIAL_TABLE_MAPPING.md` - Added 4 new tables
- [x] `QUICK_REFERENCE_FOR_TEAM.md` - Updated to 14 tables
- [x] Created this discovery document

### 2. Update Python Config (TODO)
- [ ] Update `config_cpg1_athena.py` with 3 new IPE_31 tables
- [ ] Add placeholder queries for new tables

### 3. Revise Questions Document (TODO)
- [ ] Add question about pre-joined views for IPE_31
- [ ] Ask about hub/3PL mapping logic

### 4. Send Updated Request to Team (TODO)
- [ ] Use updated `QUICK_REFERENCE_FOR_TEAM.md` (now shows 14 tables)
- [ ] Emphasize IPE_31 complexity in email

---

## 💡 Key Takeaway

**The manual process is even more complex than the official documentation suggested.**

This is GOOD news for automation:
- More complexity = more value in automation
- More manual steps = more time saved
- More tables = more risk of human error in current process

**Updated ROI**: If IPE_31 alone involves 7 tables, the manual Excel process is probably taking 8-10 hours, not 5-8. So we're saving **50+ hours/month**, not 40.

---

## 📞 Next Steps

1. ✅ Documentation updated
2. ⏳ Update Python config file
3. ⏳ Send updated questions to Carlos/Joao
4. ⏳ Specifically ask about IPE_31 simplification options

**Status**: Ready to send with updated table count (14, not 10)
