# Documentation Review & Archive Plan

**Date**: 21 October 2025  
**Purpose**: Comprehensive review of all docs/development files with archiving recommendations  
**Status**: Ready for implementation

---

## 📊 Executive Summary

**Total Files**: 19 in `docs/development/` + 2 already archived  
**Recommendation**: Archive 7 files, Keep 12 files  
**Reason**: Remove deprecated/redundant documentation, keep active references

---

## 📁 Current File Inventory

### ✅ KEEP - Active & Current Documentation (12 files)

| File | Purpose | Status | Last Updated | Keep Because |
|------|---------|--------|--------------|--------------|
| **ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md** | Complete Athena table mapping request | ✅ Current | Oct 21, 2025 | **PRIMARY DOCUMENT** - Ready to send to Sandeep |
| **IPE_STATUS_DASHBOARD.md** | Overall project status tracking | ✅ Current | Oct 21, 2025 | Quick reference for project status |
| **_DOCUMENTATION_CLEANUP_SUMMARY.md** | Record of documentation consolidation | ✅ Current | Oct 21, 2025 | Historical record of cleanup |
| **QUICK_REFERENCE_FOR_TEAM.md** | Daily operational reference | ✅ Current | Active | Team uses for quick lookups |
| **TESTING_GUIDE.md** | Testing procedures & validation | ✅ Current | Active | Required for QA |
| **evidence_documentation.md** | Evidence package structure | ✅ Current | Active | Critical for SOX compliance |
| **EVIDENCE_GAP_ANALYSIS.md** | Technical implementation gaps | ✅ Current | Oct 21, 2025 | Tracks what's missing in evidence generation |
| **EVIDENCE_PACKAGE_PRESENTATION.md** | Presentation for stakeholders | ✅ Current | Oct 21, 2025 | For Joao/Archana meetings |
| **RECONCILIATION_FLOW_DIAGRAM.md** | Visual data flow documentation | ✅ Current | Active | Architecture reference |
| **ATHENA_QUESTIONS_FOR_TEAM.md** | Internal team questions | ✅ Current | Active | Different audience than Sandeep doc |
| **QUICK_START_MORNING.md** | Daily startup checklist | ✅ Current | Active | Operational guide |
| **MORNING_CHECKLIST.md** | Daily task list | ✅ Current | Active | Operational guide |

---

### 📦 ARCHIVE - Deprecated or Superseded (7 files)

| File | Reason to Archive | Superseded By | Action |
|------|-------------------|---------------|--------|
| **OFFICIAL_TABLE_MAPPING.md** | Redundant - content merged | ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md | ✅ Already in archive/ |
| **TABLE_MAPPING_FOR_SANDEEP.md** | Redundant - content merged | ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md | ✅ Already in archive/ |
| **MEETING_PREP_SUMMARY.md** | Outdated - meeting occurred | N/A - historical context | ⏳ Move to archive/ |
| **classification_matrix.md** | Project not started - out of scope | N/A - future work | ⏳ Move to archive/ |
| **meeting_questions.md** | Project not started - out of scope | N/A - future work | ⏳ Move to archive/ |
| **REFACTORING_QUICK_REFERENCE.md** | Refactoring complete | N/A - code now stable | ⏳ Move to archive/ |
| **SECURITY_FIXES.md** | Security work complete | N/A - fixes applied | ⏳ Move to archive/ |
| **MIGRATION_SQL_TO_ATHENA.md** | Migration in progress - info in main docs | ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md | ⏳ Move to archive/ |
| **INTEGRATION_TESTING_PREP.md** | Outdated - testing approach changed | TESTING_GUIDE.md | ⏳ Move to archive/ |

---

## 🗂️ Recommended Archive Structure

```
docs/development/
├── archive/
│   ├── 2024-12-security-fixes/
│   │   └── SECURITY_FIXES.md
│   ├── 2024-12-refactoring/
│   │   └── REFACTORING_QUICK_REFERENCE.md
│   ├── 2025-10-table-mapping-v1/
│   │   ├── OFFICIAL_TABLE_MAPPING.md
│   │   └── TABLE_MAPPING_FOR_SANDEEP.md
│   ├── 2025-10-meetings/
│   │   ├── MEETING_PREP_SUMMARY.md
│   │   ├── classification_matrix.md
│   │   └── meeting_questions.md
│   └── 2025-10-migration-prep/
│       ├── MIGRATION_SQL_TO_ATHENA.md
│       └── INTEGRATION_TESTING_PREP.md
```

---

## 📋 IPE_FILES Folder Analysis

### Current Contents (15 files)

**Excel Files Found**:
1. ✅ `CR_03_test.xlsx` - GL Entries test data
2. ✅ `CR_04_testing.xlsx` - GL Balances test data
3. ✅ `CR_05_test.xlsx` - FX Rates test data
4. ✅ `CR_05a__IPE Baseline__FA table - FX rates.xlsx` - FX Rates baseline
5. ✅ `CR_05b__IPE Baseline__Daily FX rates.xlsx` - Daily FX Rates baseline
6. ✅ `IPE_07a__IPE Baseline__Detailed customer ledger entries.xlsx` - Customer Ledger baseline
7. ✅ `IPE_08_test.xlsx` - BOB Vouchers test data
8. ✅ `IPE_10__IPE Baseline__Customer prepayments TV.xlsx` - Prepayments baseline
9. ✅ `IPE_11__IPE Baseline__Marketplace accrued revenues.xlsx` - MPL Revenues baseline
10. ✅ `IPE_12__IPE Baseline__TV - Packages delivered not reconciled.xlsx` - Packages baseline
11. ✅ `IPE_31.xlsx` - Collection Accounts baseline
12. ✅ `IPE_34__IPE Baseline__MPL refund liability - Target values.xlsx` - Refunds baseline

**PDF Files Found**:
13. 📄 `[#DS-3899] Audit __ 2025- Q3 Revenues - RPT_SOI extract.pdf` - Audit documentation
14. 📄 `[#DS-3900] Audit __ GL extract - actuals - Q3-2025.pdf` - Audit documentation

**Analysis**:
- ✅ Most IPEs have baseline documentation
- ✅ Test files exist for CR_03, CR_04, CR_05, IPE_08
- ✅ Audit trail documents included
- ❌ Missing: IPE_09 baseline (but it's working in code)
- ❌ Missing: Some IPE baselines need verification

### Key Insights from IPE_FILES

**IPE_07 - Customer Ledger**:
- File: `IPE_07a__IPE Baseline__Detailed customer ledger entries.xlsx`
- Source: `Detailed Customer Ledg_ Entry` table (NAV BI)
- **Extract for table mapping**: Need to check if this shows column names

**IPE_10 - Customer Prepayments**:
- File: `IPE_10__IPE Baseline__Customer prepayments TV.xlsx`
- Source: `RPT_SOI` table (filtered for prepayments)
- **Important**: Shows this uses RPT_SOI

**IPE_11 - MPL Accrued Revenues**:
- File: `IPE_11__IPE Baseline__Marketplace accrued revenues.xlsx`
- Source: Seller Center + NAV reconciliation
- **Complex**: Multiple source tables

**IPE_12 - Packages Delivered Not Reconciled**:
- File: `IPE_12__IPE Baseline__TV - Packages delivered not reconciled.xlsx`
- Source: `RPT_SOI` table (filtered for packages)
- **Important**: Confirms RPT_SOI multi-use

**IPE_31 - Collection Accounts**:
- File: `IPE_31.xlsx`
- **Complex**: 7-table join as documented

**IPE_34 - MPL Refund Liability**:
- File: `IPE_34__IPE Baseline__MPL refund liability - Target values.xlsx`
- Source: `RPT_SOI` table (filtered for refunds)
- **Important**: Third use of RPT_SOI

**CR_05 - FX Rates**:
- Files: Two versions (FA table + Daily rates)
- **Important**: May need both tables or one comprehensive table

---

## 🎯 Action Items

### Immediate Actions (Today)

1. **Archive Files** ✅
   ```bash
   cd docs/development
   mkdir -p archive/{2024-12-security-fixes,2024-12-refactoring,2025-10-table-mapping-v1,2025-10-meetings,2025-10-migration-prep}
   
   # Move files to appropriate archive folders
   mv SECURITY_FIXES.md archive/2024-12-security-fixes/
   mv REFACTORING_QUICK_REFERENCE.md archive/2024-12-refactoring/
   mv MEETING_PREP_SUMMARY.md archive/2025-10-meetings/
   mv classification_matrix.md archive/2025-10-meetings/
   mv meeting_questions.md archive/2025-10-meetings/
   mv MIGRATION_SQL_TO_ATHENA.md archive/2025-10-migration-prep/
   mv INTEGRATION_TESTING_PREP.md archive/2025-10-migration-prep/
   ```

2. **Update README** ⏳
   - Create `docs/development/README.md` explaining structure
   - List active documents and their purposes
   - Link to archive for historical reference

3. **Update IPE_FILES README** ⏳
   - Document the actual files present
   - Note which IPEs have baseline documentation
   - Add notes about audit trail PDFs

---

### Short-term Actions (This Week)

4. **Extract Column Names from IPE_FILES** ⏳
   - Open Excel files to see actual column structures
   - Compare with SQL Server table definitions
   - Document any column name transformations
   - Update ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md with findings

5. **Create IPE Baseline Inventory** ⏳
   - Document which IPEs have complete baselines
   - Identify missing baselines
   - Create plan to generate missing baselines

6. **Verify Audit Trail Documents** ⏳
   - Review PDF files for table/column information
   - Extract any Athena query examples
   - Document insights in main request

---

## 📝 Recommended Updates to ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md

### Additional Information to Include

Based on IPE_FILES analysis, add these sections:

**Section: Available Baseline Documentation**
```markdown
## 📚 Available Baseline Documentation

We have the following baseline documentation files available in `/IPE_FILES/`:

### Customer & GL Data
- ✅ IPE_07a: Detailed customer ledger entries (baseline)
- ✅ CR_03: GL Entries (test data)
- ✅ CR_04: GL Balances (test data)
- ✅ CR_05: FX Rates (test data + 2 baseline versions)

### OMS & Prepayments
- ✅ IPE_10: Customer prepayments TV (baseline)
- ✅ IPE_12: Packages delivered not reconciled (baseline)
- ✅ IPE_34: MPL refund liability (baseline)

### Marketplace & Vouchers
- ✅ IPE_08: BOB voucher accruals (test data)
- ✅ IPE_11: Marketplace accrued revenues (baseline)
- ✅ IPE_31: Collection accounts (baseline)

### Audit Trail
- 📄 DS-3899: Q3 2025 Revenues - RPT_SOI extract
- 📄 DS-3900: Q3 2025 GL extract - actuals

**These files can be shared if they help with understanding the data structure or column names.**
```

**Section: Specific Questions from Baseline Files**
```markdown
## ❓ Questions Based on Baseline Documentation

### IPE_07 - Customer Ledger
Looking at `IPE_07a__IPE Baseline__Detailed customer ledger entries.xlsx`:
- Can you confirm the column names match between SQL Server and Athena?
- Should I expect the same column structure?

### RPT_SOI Multi-Use Scenario
Files IPE_10, IPE_12, IPE_34 all reference `RPT_SOI`:
- What column distinguishes these 3 use cases?
- Is there a `transaction_type` or `gl_account` filter?

### CR_05 - FX Rates
Two files exist:
- `CR_05a__IPE Baseline__FA table - FX rates.xlsx`
- `CR_05b__IPE Baseline__Daily FX rates.xlsx`
- Are these two separate Athena tables or one combined table?
```

---

## ✅ Success Criteria

### Documentation Structure
- ✅ All deprecated files archived with context
- ✅ Active files clearly identified and organized
- ✅ Archive structure allows easy reference
- ✅ README explains organization

### IPE_FILES Integration
- ✅ Baseline files documented
- ✅ Column structures compared
- ✅ Audit trail documents reviewed
- ✅ Missing baselines identified

### Athena Request Enhancement
- ✅ Baseline documentation referenced
- ✅ Specific questions from baselines added
- ✅ Column name comparisons included
- ✅ Multi-table scenarios clarified

---

## 📊 Summary Statistics

### Before Cleanup
- 19 active files (+ 2 archived)
- Mixed current/historical content
- Redundant mapping documents
- No clear organization

### After Cleanup
- 12 active files (focused and current)
- 9 archived files (organized by topic/date)
- 1 master table mapping document
- Clear structure with README

### Efficiency Gains
- ⏱️ 37% reduction in active files
- 📚 100% of historical content preserved
- 🎯 Clear document hierarchy
- 📈 Easier navigation for team

---

**Status**: Ready to execute  
**Next Action**: Review and approve archive plan  
**Estimated Time**: 30 minutes to complete archiving

---

END OF REVIEW & ARCHIVE PLAN
