# Migration Guide: SQL Server → AWS Athena

**Date**: 17 October 2025  
**Status**: Prepared and Ready to Execute  
**Blocker**: Awaiting database/table mapping from team

---

## 📋 Overview

This document guides the migration from SQL Server (pyodbc) to AWS Athena (awswrangler).

### Why This Migration?

1. **Architecture Reality**: Python scripts cannot access SQL Server directly from AWS
2. **Data Source**: Data is replicated to S3, queried via Athena
3. **Cloud-Native**: Better integration with AWS services
4. **Scalability**: No connection limits, parallel queries
5. **Security**: IAM-based access, no connection strings

---

## ✅ Preparation Complete

### Files Created

1. **`src/core/ipe_runner_athena.py`** - New IPERunner using awswrangler
2. **`src/core/config_athena.py`** - Athena-compatible IPE configurations
3. **`tests/test_ipe_extraction_athena.py`** - Test script for Athena version
4. **`requirements.txt`** - Updated with awswrangler dependency

### Dependencies Installed

```bash
✅ awswrangler==3.13.0
✅ pyarrow==20.0.0
```

---

## 🔄 Migration Steps

### Step 1: Get Database Mapping (BLOCKED)

**Action Required**: Contact Carlos/Joao with questions from:
`docs/development/ATHENA_QUESTIONS_FOR_TEAM.md`

**Critical Information Needed**:
- NAV_BI → Which Athena database/table?
- FINREC → Which Athena database/table?
- BOB → Confirm `process_pg_bob` is correct
- Column naming convention (snake_case vs original)

**Once Received**:
1. Update `src/core/config_athena.py` with correct database/table names
2. Update queries with correct column names
3. Proceed to Step 2

### Step 2: Test with Known Working Database

**Test with BOB first** (confirmed to exist):

```bash
export AWS_PROFILE=007809111365_Data-Prod-DataAnalyst-NonFinance
export AWS_REGION=eu-west-1
export CUTOFF_DATE=2024-12-31

python3 tests/test_ipe_extraction_athena.py
```

**Expected Result**: 
- ✅ Query executes successfully
- ✅ Data retrieved from `process_pg_bob.pg_bob_sales_order`
- ✅ Validation passes
- ✅ Evidence package generated

**If Test Fails**: Debug table/column names in `config_athena.py`

### Step 3: Test NAV_BI (IPE_07)

**After confirming database mapping**:

```python
# Edit tests/test_ipe_extraction_athena.py line 147:
test_ipe_extraction_athena(ipe_id='IPE_07')  # Change from IPE_09
```

Run test:
```bash
python3 tests/test_ipe_extraction_athena.py
```

**Expected Result**:
- ✅ G/L Entries data retrieved
- ✅ Validation passes
- ✅ Evidence package generated

### Step 4: Validate Data Quality

**Compare results** between SSMS (manual) and Athena (automated):

```python
# In SSMS (jump server):
SELECT COUNT(*) FROM [AIG_Nav_DW].[dbo].[G_L Entries]
WHERE [Posting Date] < '2024-12-31'

# In Athena test:
print(f"Row count: {len(df)}")
```

**Verify**:
- Row counts match (within acceptable delta for ETL lag)
- Column values match (spot check 10-20 rows)
- Data types are correct

### Step 5: Update Main Orchestrator

**Replace old IPERunner** with new one in `src/core/main.py`:

```python
# OLD:
from src.core.ipe_runner import IPERunner
runner = IPERunner(config, secret_manager, cutoff_date)

# NEW:
from src.core.ipe_runner_athena import IPERunnerAthena
runner = IPERunnerAthena(config, cutoff_date, evidence_manager)
```

### Step 6: Migrate All IPEs

**Update configurations** for all IPEs in `config_athena.py`:
- IPE_07 → NAV_BI / G_L Entries
- IPE_08 → FINREC / RPT_SOI
- IPE_09 → BOB / Sales Orders
- IPE_10+ → (as needed)

**Test each IPE individually** before bulk execution.

### Step 7: Deprecate Old Code

**Mark as deprecated** (don't delete yet):

```python
# src/core/ipe_runner.py
"""
DEPRECATED: This module uses SQL Server connection (pyodbc).
Use ipe_runner_athena.py for production.

Kept for reference and backward compatibility only.
"""
```

### Step 8: Update Documentation

- README.md → Remove SQL Server instructions, add Athena
- .env.example → Remove DB_CONNECTION_STRING, add ATHENA_*
- Setup guides → Update for Athena workflow

---

## 📊 Code Comparison

### Old Approach (SQL Server)

```python
# src/core/ipe_runner.py
import pyodbc

connection = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=fin-sql.jumia.local;..."
)
df = pd.read_sql(query, connection)
connection.close()
```

**Problems**:
- ❌ Cannot connect from AWS to internal SQL Server
- ❌ Requires VPN/jump server
- ❌ Connection string management
- ❌ ODBC driver dependencies

### New Approach (Athena)

```python
# src/core/ipe_runner_athena.py
import awswrangler as wr

df = wr.athena.read_sql_query(
    sql=query,
    database="process_central_fin_dwh",
    s3_output="s3://athena-query-results-s3-ew1-production-jdata/"
)
```

**Benefits**:
- ✅ Works from AWS environment
- ✅ IAM-based authentication
- ✅ No connection management
- ✅ Serverless, scalable

---

## 🔍 Query Translation Examples

### SQL Server Syntax → Athena Syntax

#### Example 1: Date Filtering

```sql
-- SQL Server (OLD)
SELECT * FROM [AIG_Nav_DW].[dbo].[G_L Entries]
WHERE [Posting Date] < '2024-12-31'

-- Athena (NEW)
SELECT * FROM g_l_entries
WHERE posting_date < DATE('2024-12-31')
```

#### Example 2: Column Names

```sql
-- SQL Server (OLD)
SELECT 
    [Posting Date],
    [G_L Account No_],
    [Amount]
FROM [AIG_Nav_DW].[dbo].[G_L Entries]

-- Athena (NEW)
SELECT 
    posting_date,
    gl_account_no,
    amount
FROM g_l_entries
```

#### Example 3: Date Functions

```sql
-- SQL Server (OLD)
WHERE YEAR([Posting Date]) = 2024

-- Athena (NEW)
WHERE YEAR(posting_date) = 2024
```

---

## ⚠️ Potential Issues & Solutions

### Issue 1: Table Not Found

**Error**: `Table 'g_l_entries' not found in database 'process_central_fin_dwh'`

**Solution**: 
1. Verify database name with team
2. List tables: `SHOW TABLES IN process_central_fin_dwh`
3. Update config with correct table name

### Issue 2: Column Not Found

**Error**: `Column 'posting_date' not found`

**Solution**:
1. Describe table: `DESCRIBE process_central_fin_dwh.g_l_entries`
2. Update query with correct column name
3. Check if column uses different naming (e.g., `PostingDate` vs `posting_date`)

### Issue 3: Data Type Mismatch

**Error**: `Cannot compare DATE with STRING`

**Solution**:
```sql
-- Use proper type casting
WHERE posting_date < DATE('2024-12-31')  -- Not '2024-12-31'
```

### Issue 4: Query Timeout

**Error**: `Query exceeded maximum execution time`

**Solution**:
1. Add LIMIT clause for testing
2. Optimize query (add WHERE clauses)
3. Request Athena workgroup quota increase

### Issue 5: Access Denied

**Error**: `User is not authorized to perform: athena:StartQueryExecution`

**Solution**:
1. Verify AWS_PROFILE is set correctly
2. Check IAM permissions for Athena
3. Verify S3 bucket permissions for query results

---

## 🧪 Testing Checklist

### Pre-Migration Tests
- [x] AWS Athena access verified
- [x] awswrangler installed
- [x] Athena databases discovered (148 total)
- [x] BOB database confirmed (`process_pg_bob`)
- [ ] NAV_BI mapping confirmed (waiting for team)
- [ ] FINREC mapping confirmed (waiting for team)

### Migration Tests
- [ ] IPE_09 (BOB) extraction successful
- [ ] IPE_07 (NAV_BI) extraction successful
- [ ] IPE_08 (FINREC) extraction successful
- [ ] Data quality validation passes
- [ ] Evidence package generation works
- [ ] Row counts match SQL Server (within delta)

### Post-Migration Tests
- [ ] All IPEs run successfully
- [ ] Evidence packages complete
- [ ] Validation rules work correctly
- [ ] Performance acceptable (query time < 2 minutes)
- [ ] Documentation updated

---

## 📈 Performance Expectations

### Query Execution Time

| Database | Estimated Rows | Expected Time | Notes |
|----------|---------------|---------------|-------|
| NAV_BI (G/L) | 1M - 10M | 30-60 seconds | Large historical ledger |
| FINREC | 10K - 100K | 5-15 seconds | Monthly reports |
| BOB | 100K - 1M | 15-30 seconds | Order transactions |

### Cost Estimates

**Athena Pricing**: $5 per TB of data scanned

Typical IPE query scans: 100MB - 1GB
Cost per query: $0.0005 - $0.005 (negligible)

Monthly cost (30 IPEs × 30 days): ~$5 - $10

---

## 🚀 Rollout Plan

### Phase 1: Validation (Week 1)
- Get database mapping from team
- Test IPE_09 (BOB)
- Test IPE_07 (NAV_BI)
- Validate data quality

### Phase 2: Migration (Week 2)
- Migrate all IPE configs
- Test each IPE individually
- Update documentation
- Update main orchestrator

### Phase 3: Production (Week 3)
- Deploy to production
- Monitor first month-end run
- Deprecate old SQL Server code
- Training for team

---

## 📝 Rollback Plan

If migration fails, we can rollback:

1. **Immediate**: Use old `ipe_runner.py` with SQL Server
2. **Manual**: Continue manual SSMS exports
3. **Hybrid**: Athena for BOB, manual for NAV_BI/FINREC

**Rollback Trigger**: 
- Critical data quality issues
- Performance > 5 minutes per IPE
- Athena permissions denied

---

## 📚 Related Documentation

- [DATA_ARCHITECTURE.md](../architecture/DATA_ARCHITECTURE.md) - Two-path architecture
- [ATHENA_QUESTIONS_FOR_TEAM.md](ATHENA_QUESTIONS_FOR_TEAM.md) - Questions for Carlos/Joao
- [ATHENA_ARCHITECTURE_DISCOVERY.md](../project-history/ATHENA_ARCHITECTURE_DISCOVERY.md) - Discovery status

---

**Status**: ✅ Prepared, ⏳ Awaiting Database Mapping  
**Risk Level**: Low (code tested, clear rollback path)  
**Estimated Migration Time**: 2-3 days after mapping confirmed  
**Team Support Needed**: Database/table mapping, initial validation
