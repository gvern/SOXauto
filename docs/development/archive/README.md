# Archive - Deprecated & Historical Documentation

**Purpose**: Preserve historical documentation for reference while keeping active documentation clean

---

## 📦 Archive Organization

### 2024-12-security-fixes/
**Period**: December 2024  
**Status**: ✅ Complete - Security hardening finished

- `SECURITY_FIXES.md` - SQL injection vulnerability resolution documentation
  - Critical security issues identified and fixed
  - CTE pattern implementation
  - All `.format()` string interpolation eliminated
  - **Result**: Zero SQL injection vulnerabilities

**Why Archived**: Security work complete, all fixes applied and tested

---

### 2024-12-refactoring/
**Period**: December 2024  
**Status**: ✅ Complete - Code restructuring finished

- `REFACTORING_QUICK_REFERENCE.md` - Migration guide for new `src/core/` structure
  - Package organization: catalog/, runners/, evidence/, recon/, orchestrators/
  - Import path changes
  - Legacy compatibility notes
  - **Result**: Clean, maintainable code structure

**Why Archived**: Refactoring complete, new structure is now standard

---

### 2025-10-meetings/
**Period**: October 2025  
**Status**: ✅ Complete - Meetings occurred

Files:
- `MEETING_PREP_SUMMARY.md` - Prep for Joao/Archana evidence review and Sandeep table mapping
- `classification_matrix.md` - Classification logic for Islam meeting (not started - different project)
- `meeting_questions.md` - Structured questions for Islam meeting (not started - different project)

**Why Archived**: 
- Meeting prep documents served their purpose
- Classification project not in scope for C-PG-1 automation
- Historical reference only

---

### 2025-10-migration-prep/
**Period**: October 2025  
**Status**: 🚧 Superseded - Better documentation created

Files:
- `MIGRATION_SQL_TO_ATHENA.md` - Initial migration guide
- `INTEGRATION_TESTING_PREP.md` - Original testing approach

**Why Archived**:
- Superseded by `ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md` (more comprehensive)
- Testing approach evolved (see `TESTING_GUIDE.md`)
- Still useful for historical context

---

### 2025-10-table-mapping-v1/
**Period**: October 2025  
**Status**: ✅ Consolidated - Merged into single document

Files:
- `OFFICIAL_TABLE_MAPPING.md` - First attempt at table mapping request
- `TABLE_MAPPING_FOR_SANDEEP.md` - Second iteration with more details

**Why Archived**:
- **Superseded by**: `ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md`
- Redundant content - both files covered similar ground
- New document consolidates and improves both versions

---

## 🔍 How to Use This Archive

### When to Reference Archive
1. **Historical Context**: Understanding past decisions and approaches
2. **Security Audits**: Reviewing what vulnerabilities were fixed
3. **Architecture Evolution**: Seeing how code structure changed
4. **Meeting Notes**: Checking what was discussed previously

### When NOT to Use Archive
- ❌ For current operational procedures (use active docs)
- ❌ For table mapping requests (use `ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md`)
- ❌ For testing procedures (use `TESTING_GUIDE.md`)
- ❌ For evidence generation (use `evidence_documentation.md`)

---

## 📊 Archive Statistics

**Total Archived Files**: 9 documents  
**Total Size**: ~3000 lines of documentation  
**Oldest Content**: December 2024 (Security fixes)  
**Most Recent**: October 2025 (Meeting prep, table mapping)

**Categories**:
- Security: 1 file
- Refactoring: 1 file  
- Meetings: 3 files
- Migration: 2 files
- Table Mapping: 2 files

---

## 🗂️ Related Active Documentation

For current project information, see:

- **Main Request**: `../ATHENA_ACCESS_REQUEST_FOR_SANDEEP.md` - Complete table mapping request
- **Status Tracking**: `../IPE_STATUS_DASHBOARD.md` - Current project status
- **Testing**: `../TESTING_GUIDE.md` - Current testing procedures
- **Evidence**: `../evidence_documentation.md` - Evidence package structure
- **Quick Reference**: `../QUICK_REFERENCE_FOR_TEAM.md` - Daily operational guide

---

**Archive Maintained By**: SOXauto Team  
**Last Updated**: 21 October 2025  
**Retention Policy**: Keep indefinitely for SOX compliance and audit trail

---

END OF ARCHIVE README
