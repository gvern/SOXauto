# Development Documentation - C-PG-1 SOXauto

**Last Updated**: 21 October 2025  
**Project**: Physical Goods Integrated Balance Sheet Accounts Reconciliation (IBSAR) Automation  
**Status**: Active Development - Athena Migration Phase

---

## 🎯 Quick Start

### New to the Project?
1. **`README.md`** (this file) - Documentation overview
2. **`QUICK_REFERENCE_FOR_TEAM.md`** - Quick lookup for common tasks
3. **`ATHENA_TABLE_MAPPING_REQUEST.md`** - Current blocker (waiting for Sandeep/Carlos)

### Daily Operations
- **Quick Reference**: `QUICK_REFERENCE_FOR_TEAM.md`
- **Testing Guide**: `TESTING_GUIDE.md`
- **Evidence Spec**: `evidence_documentation.md`

---

## 📂 Active Documentation Files

### Core Documentation (Essential)

| File | Purpose | Audience |
|------|---------|----------|
| **ATHENA_TABLE_MAPPING_REQUEST.md** | Athena table mappings needed | Sandeep/Carlos (Data Team) |
| **QUICK_REFERENCE_FOR_TEAM.md** | Quick lookup reference | All team members |
| **TESTING_GUIDE.md** | Testing procedures & validation | Developers & QA |
| **evidence_documentation.md** | SOX evidence structure (7-file system) | Auditors & Developers |
| **EVIDENCE_PACKAGE_PRESENTATION.md** | Evidence package details | Compliance & Auditors |
| **RECONCILIATION_FLOW_DIAGRAM.md** | C-PG-1 process flow | All team members |

---

## � Archive

Historical and working documents archived in `archive/`:
- `2025-10-working-docs/` - Analysis, status tracking, daily checklists (Oct 2025)
- `2025-10-migration-prep/` - Migration planning documents (Oct 2025)
- `2025-10-meetings/` - Meeting notes and prep (Oct 2025)
- `2024-12-refactoring/` - Previous refactoring docs (Dec 2024)
- `2024-12-security-fixes/` - Security fix documentation (Dec 2024)

See `archive/README.md` for details on archived content.

---

## 🔧 Technical References

### Catalog
- Location: `/src/core/catalog/pg1_catalog.py`
- Contents: 11 items (7 IPEs, 3 CRs, 1 DOC)
- Status: All items C-PG-1 specific, baseline files documented

### IPE Baseline Files
- Location: `/IPE_FILES/`
- Contents: 10 baseline Excel files (100% coverage)
- Purpose: Column structure reference and validation

---

## 🚧 Current Status

### Blocked
- **All 10 IPEs** waiting for Athena table mappings from Sandeep/Carlos
- Request document ready: `ATHENA_TABLE_MAPPING_REQUEST.md`

### Active
- Catalog fully documented with baseline file paths
- Evidence framework designed (7-file package)
- Testing procedures documented

---

## 📝 Document Maintenance

### When to Update
- **ATHENA_TABLE_MAPPING_REQUEST.md**: When Sandeep/Carlos provide mappings
- **QUICK_REFERENCE_FOR_TEAM.md**: When procedures change
- **TESTING_GUIDE.md**: When test cases added/modified
- **This README**: When documentation structure changes

### Archive Policy
- Working documents → `archive/2025-10-working-docs/`
- Meeting notes → `archive/2025-10-meetings/`
- Migration prep → `archive/2025-10-migration-prep/`
- Keep only active, reference documents in main folder
| **EVIDENCE_PACKAGE_PRESENTATION.md** | Presentation for stakeholders | Management | ✅ Current |
| **RECONCILIATION_FLOW_DIAGRAM.md** | Visual data flow architecture | Technical Team | ✅ Current |
| **ATHENA_QUESTIONS_FOR_TEAM.md** | Internal technical questions | Data Team | ✅ Current |

---

### 🟢 Priority 4: Historical & Reference

| File | Purpose | Note |
|------|---------|------|
| **_DOCUMENTATION_CLEANUP_SUMMARY.md** | Record of Oct 2025 documentation consolidation | Historical record |
| **DOCUMENTATION_REVIEW_AND_ARCHIVE_PLAN.md** | Archive plan and file inventory | Reference |

---

## 📊 Project Status Overview

### Current State (21 October 2025)

**IPEs Working**: 1 out of 11 (IPE_09 - BOB Sales Orders)  
**Primary Blocker**: Missing Athena table mappings from data team  
**Evidence Generation**: Partial (2/7 files generated)  
**Next Milestone**: Receive table mappings from Sandeep

### Key Metrics
- **Time Savings Target**: 40+ hours/month (95% reduction)
- **Tables Needed**: 15 unique SQL Server → Athena mappings
- **IPEs to Automate**: 10 reports
- **Evidence Files**: 7 per IPE execution

---

## 🗂️ Folder Structure

```
docs/development/
├── README.md (this file)                              # Documentation index
├── ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md               # 🔴 Main table mapping request
├── IPE_STATUS_DASHBOARD.md                            # 🔴 Project status dashboard
├── TESTING_GUIDE.md                                   # 🔴 Testing procedures
├── evidence_documentation.md                          # 🔴 Evidence package guide
├── QUICK_START_MORNING.md                             # 🟠 Daily startup guide
├── MORNING_CHECKLIST.md                               # 🟠 Daily checklist
├── QUICK_REFERENCE_FOR_TEAM.md                        # 🟠 Quick reference
├── EVIDENCE_GAP_ANALYSIS.md                           # 🟡 Technical analysis
├── EVIDENCE_PACKAGE_PRESENTATION.md                   # 🟡 Stakeholder presentation
├── RECONCILIATION_FLOW_DIAGRAM.md                     # 🟡 Architecture diagrams
├── ATHENA_QUESTIONS_FOR_TEAM.md                       # 🟡 Technical questions
├── _DOCUMENTATION_CLEANUP_SUMMARY.md                  # 🟢 Historical record
├── DOCUMENTATION_REVIEW_AND_ARCHIVE_PLAN.md           # 🟢 Archive plan
└── archive/                                           # 📦 Deprecated docs
    ├── README.md                                      # Archive index
    ├── 2024-12-security-fixes/
    ├── 2024-12-refactoring/
    ├── 2025-10-meetings/
    ├── 2025-10-migration-prep/
    └── 2025-10-table-mapping-v1/
```

---

## 🔍 Finding Information

### "How do I...?"

**...get started on a new day?**
→ `QUICK_START_MORNING.md` + `MORNING_CHECKLIST.md`

**...understand project status?**
→ `IPE_STATUS_DASHBOARD.md`

**...request Athena table access?**
→ `ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md` (or send to Sandeep)

**...test an IPE?**
→ `TESTING_GUIDE.md`

**...understand evidence generation?**
→ `evidence_documentation.md`

**...see data flow architecture?**
→ `RECONCILIATION_FLOW_DIAGRAM.md`

**...look up a quick reference?**
→ `QUICK_REFERENCE_FOR_TEAM.md`

**...find old documentation?**
→ `archive/` folder (see `archive/README.md`)

---

## 📋 Document Maintenance

### When to Update Documents

**Daily**:
- `MORNING_CHECKLIST.md` - Check off completed tasks

**Weekly**:
- `IPE_STATUS_DASHBOARD.md` - Update progress metrics

**As Needed**:
- `QUICK_REFERENCE_FOR_TEAM.md` - Add new tips/shortcuts
- `TESTING_GUIDE.md` - Update testing procedures
- `ATHENA_QUESTIONS_FOR_TEAM.md` - Add new questions

**After Major Changes**:
- `evidence_documentation.md` - Update if evidence structure changes
- `RECONCILIATION_FLOW_DIAGRAM.md` - Update if architecture changes

### Archive Policy

Move documents to `archive/` when:
- ✅ Work is complete (e.g., security fixes)
- ✅ Superseded by better documentation
- ✅ Meeting/planning docs after event
- ✅ Historical value but no longer operational

**Never archive**:
- ❌ Active operational guides
- ❌ Current testing procedures
- ❌ Pending requests (like Sandeep's table mapping)

---

## 🎯 Current Priorities (Oct 2025)

### Immediate (This Week)
1. ✅ **Documentation cleanup** - Archive deprecated files
2. ⏳ **Send request** - `ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md` to Sandeep
3. ⏳ **Wait for response** - Table mappings from data team

### Short-term (Next 2 Weeks)
4. ⏳ **Update catalog** - Add Athena configurations to `pg1_catalog.py`
5. ⏳ **Write queries** - Create Athena queries for each IPE
6. ⏳ **Test extractions** - Validate data matches SQL Server

### Medium-term (Next Month)
7. ⏳ **Complete evidence** - Implement all 7 evidence files
8. ⏳ **End-to-end testing** - Full reconciliation flow
9. ⏳ **Production deployment** - Go live with automation

---

## 📞 Contacts & Resources

### Key Stakeholders
- **Sandeep** - Data team, Athena table mappings
- **Joao & Archana** - Evidence validation, SOX compliance
- **Carlos** - AWS architecture, Athena questions

### Related Documentation
- **Catalog**: `/src/core/catalog/pg1_catalog.py` - IPE/CR registry
- **Evidence**: `/evidence/` - Generated evidence packages
- **IPE Files**: `/IPE_FILES/` - Baseline documentation
- **Tests**: `/tests/` - Test scripts

### External Resources
- Confluence: Common Report Reference
- GitHub: `gvern/SOXauto` repository
- AWS: Athena query console
- Okta: AWS access via `scripts/okta_quickstart.sh`

---

## ✅ Documentation Health Check

**Last Review**: 21 October 2025  
**Status**: ✅ Healthy - Well organized and up to date

**Metrics**:
- Active files: 12 (down from 19, -37%)
- Archived files: 9 (organized by topic/date)
- Redundant content: Eliminated
- Clear structure: ✅
- Easy navigation: ✅

**Next Review**: After table mapping response or end of November 2025

---

## 📚 Additional Resources

### Project History
See `/docs/project-history/` for:
- Phase completion summaries
- Architecture evolution
- Refactoring documentation
- English standardization notes

### Setup Guides
See `/docs/setup/` for:
- Database connection setup
- OKTA AWS authentication
- Timing difference configuration

### Architecture
See `/docs/architecture/` for:
- Data architecture overview
- System design documents

---

**Maintained By**: SOXauto Development Team  
**Questions?**: Check this README first, then ask team  
**Contributing**: Keep documents updated as work progresses

---

END OF DEVELOPMENT DOCUMENTATION README
