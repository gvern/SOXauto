# SOXauto Architecture Discovery - Critical Update

**Date**: 17 October 2025  
**Status**: 🎯 Major Architecture Clarification

---

## 🚨 Critical Discovery

**The data architecture has TWO separate paths**:

### Path 1: Manual Exploration (SSMS)
- **Access**: Teleport → Jump Server → SQL Server Management Studio
- **Server**: `fin-sql.jumia.local`
- **Databases**: NAV_BI, FINREC, BOB
- **Purpose**: Ad-hoc queries, investigation, debugging
- **⚠️ NOT for automation**

### Path 2: Automated Production (AWS Athena)
- **Access**: Python → Okta → AWS IAM → Athena API
- **Data Storage**: Amazon S3
- **Query Engine**: AWS Athena
- **Purpose**: Automated IPE extraction
- **✅ THIS IS WHAT WE NEED**

---

## ✅ What We've Accomplished

### 1. AWS Connection
- ✅ Temporary credentials working
- ✅ S3 access verified (294 buckets)
- ✅ Athena access verified (148 databases)

### 2. Discovery Results
```
Total Athena Databases: 148
Relevant for SOX:
- process_central_fin_dwh (Financial DWH)
- raw_central_fin_dwh (Raw financial data)
- process_pg_bob (BOB - 29 tables)
- raw_pg_bob (BOB history - 23 tables)
- process_pg_dwh (DWH - 11 tables)
```

### 3. Code Prepared
- ✅ Athena test script created (`tests/test_athena_access.py`)
- ✅ Architecture documentation (`docs/architecture/DATA_ARCHITECTURE.md`)
- ✅ Questions document for team (`docs/development/ATHENA_QUESTIONS_FOR_TEAM.md`)

---

## 🔄 Required Refactoring

### What Needs to Change

#### ❌ Remove (SQL Server approach)
```python
# Old: pyodbc connection
import pyodbc
connection = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=fin-sql.jumia.local;..."
)
df = pd.read_sql(query, connection)
```

#### ✅ Add (Athena approach)
```python
# New: awswrangler + Athena
import awswrangler as wr
df = wr.athena.read_sql_query(
    sql=query,
    database="process_central_fin_dwh",  # To be confirmed
    s3_output="s3://athena-query-results-s3-ew1-production-jdata/"
)
```

### Files to Modify

1. **`src/core/ipe_runner.py`**
   - Remove `_get_database_connection()` using pyodbc
   - Add `_execute_athena_query()` using awswrangler
   - Update `run()` method logic

2. **`src/core/config.py`**
   - Remove `secret_name` from IPE configs
   - Add `athena_database` and `athena_table`
   - Update SQL queries for Athena syntax

3. **`src/utils/aws_utils.py`**
   - Remove `AWSSecretsManager` dependency for DB credentials
   - Keep S3 and Athena utilities

4. **`requirements.txt`**
   - Remove `pyodbc` (or keep for other uses)
   - Add `awswrangler`

5. **`.env` and `.env.example`**
   - Remove `DB_CONNECTION_STRING`
   - Add `ATHENA_DATABASE` and `ATHENA_S3_OUTPUT`

---

## ⏳ Blocked / Waiting For

### Critical Information Needed from Team

1. **NAV_BI mapping**: Which Athena database/table = `[G_L Entries]`?
2. **FINREC mapping**: Which Athena database/table = `[RPT_SOI]`?
3. **BOB confirmation**: Is `process_pg_bob` the correct database?
4. **Column naming**: Do column names match SQL Server or use snake_case?
5. **Data freshness**: How often is Athena data updated?

**Action**: Share `docs/development/ATHENA_QUESTIONS_FOR_TEAM.md` with Carlos/Joao

---

## 📊 Current Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| AWS Authentication | ✅ Working | Temporary credentials (manual renewal) |
| S3 Access | ✅ Verified | 294 buckets accessible |
| Athena Access | ✅ Verified | 148 databases discovered |
| Database Mapping | ⏳ Pending | Waiting for team input |
| ODBC Driver | ✅ Installed | Driver 18 (won't be needed) |
| SQL Server Fallback | ❌ Deprecated | Replaced by Athena approach |
| awswrangler | ⏳ To Install | Pending refactoring start |
| IPE Extraction | ⏳ Blocked | Need database mapping |

---

## 🎯 Next Immediate Steps

### Step 1: Contact Team (TODAY)
- Send questions document to Carlos/Joao
- Request Athena database/table mapping
- Ask for Glue Data Catalog access if possible

### Step 2: Install Dependencies (READY)
```bash
pip install awswrangler
```

### Step 3: Refactor Code (AFTER MAPPING CONFIRMED)
1. Update `config.py` with Athena database names
2. Rewrite `IPERunner._get_database_connection()` → `_execute_athena_query()`
3. Test with IPE_07 (G_L Entries)
4. Validate data quality
5. Roll out to all IPEs

### Step 4: Update Documentation
- Mark SQL Server approach as deprecated
- Update README with Athena instructions
- Create Athena quick start guide

---

## 💡 Key Insights

### Why This Makes Sense

1. **Security**: No direct SQL Server access from AWS
2. **Scalability**: Athena handles billions of rows efficiently
3. **Cost**: Pay per query, no idle servers
4. **Cloud-Native**: Integrates with AWS services
5. **Audit Trail**: CloudTrail logs all queries

### What This Changes

- ✅ **Simpler**: No ODBC drivers, no connection strings
- ✅ **More Secure**: IAM roles instead of DB passwords
- ✅ **More Scalable**: Query S3 directly, no DB connection limits
- ⚠️ **Different SQL Syntax**: Some queries need adjustment (e.g., date formats)

---

## 📚 Documentation Created

1. **`docs/architecture/DATA_ARCHITECTURE.md`** - Complete architecture explanation
2. **`docs/development/ATHENA_QUESTIONS_FOR_TEAM.md`** - Questions for Carlos/Joao
3. **`tests/test_athena_access.py`** - Athena discovery script
4. **`docs/setup/DB_FALLBACK_SUMMARY.md`** - SQL Server fallback (now deprecated)

---

## 🔒 What Stays the Same

- AWS authentication (Okta → IAM)
- S3 for evidence storage
- IPE validation logic
- Evidence generation
- Overall SOXauto architecture

---

## 📝 Questions to Ask in Meeting

1. "Can you show me an example Athena query you use for financial data?"
2. "Which Glue catalog/database contains NAV BI data?"
3. "Is there documentation on the ETL pipeline from SQL Server to S3?"
4. "Can I get Glue Data Catalog read access to explore schemas?"
5. "What's the typical query pattern for month-end reconciliations?"

---

## 🚀 Timeline Estimate

| Phase | Duration | Status |
|-------|----------|--------|
| Get team feedback | 1-2 days | ⏳ Waiting |
| Install awswrangler | 5 minutes | Ready |
| Refactor IPERunner | 2-3 hours | Ready to start |
| Test IPE_07 | 1 hour | Ready to start |
| Validate data quality | 1-2 hours | Ready to start |
| Roll out to all IPEs | 4-6 hours | Ready to start |
| **Total** | **1-2 days after team response** | |

---

**Status**: ✅ Architecture understood, ⏳ Waiting for team input  
**Blocker**: Database/table mapping  
**Risk**: Low - clear path forward once mapping confirmed  
**Confidence**: High - Athena access verified, approach validated
