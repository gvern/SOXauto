# SOXauto Data Architecture - The Two Paths

**Date**: 17 October 2025  
**Critical Understanding**: You're connecting to TWO different environments for TWO different purposes

---

## 🎯 Overview: Manual vs. Automated

SOXauto operates in a **dual-access architecture** common in large enterprises:

1. **Manual Path**: Human developers → Teleport Jump Server → SQL Server (for exploration)
2. **Automated Path**: Python Script → AWS Athena → S3 Data Lake (for production)

---

## 📊 Architecture Comparison

| Aspect | Manual Connection (Exploration) | **Automated Script (Production)** |
|--------|--------------------------------|-----------------------------------|
| **Tool** | SQL Server Management Studio (SSMS) | **Python Script (`awswrangler`)** |
| **Server** | `fin-sql.jumia.local` | **AWS Athena API** |
| **Authentication** | Windows Authentication via Teleport | **Okta → AWS IAM Role** |
| **Data Location** | Live SQL Server Database | **Files on Amazon S3** |
| **Access Method** | Jump Server (`BA-RDS-JUMP...`) | **AWS SDK (boto3)** |
| **Purpose** | Manual investigation, ad-hoc queries | **Automated IPE extraction** |
| **Connection String** | `DRIVER={...};SERVER=fin-sql.jumia.local;...` | **No connection string (S3 + Athena)** |
| **Database Protocol** | SQL Server (TDS) | **HTTP/HTTPS (REST API)** |
| **Result Format** | SSMS result grid | **Pandas DataFrame** |

---

## 🔍 Path 1: Manual Connection (Jump Server)

### How You Access Data Manually

```
Developer (You)
    ↓
[Authenticate via Okta]
    ↓
Teleport Jump Server (BA-RDS-JUMP...)
    ↓
[Windows Authentication: JUMIA\username]
    ↓
SQL Server Management Studio (SSMS)
    ↓
fin-sql.jumia.local (SQL Server)
    ↓
Databases:
  - NAV_BI (AIG_Nav_DW)
  - FINREC
  - BOB
```

### Connection Details

**Server**: `fin-sql.jumia.local`  
**Authentication**: Windows Authentication (`JUMIA\username`)  
**Access Tool**: SQL Server Management Studio (SSMS)  
**Access Via**: Teleport Jump Server  

### Example Manual Query

```sql
-- Run this in SSMS on the jump server
SELECT TOP 100 *
FROM [AIG_Nav_DW].[dbo].[G_L Entries]
WHERE [Posting Date] < '2025-09-30'
```

### Why This Path Exists

- 🔍 **Exploration**: Ad-hoc queries and investigation
- 🐛 **Debugging**: Validate data quality
- 📊 **Analysis**: Quick lookups and manual reports
- 🎓 **Learning**: Understand schema and data

### ⚠️ Why Your Script CANNOT Use This Path

- ❌ Cannot programmatically login to Windows jump server
- ❌ No automation support for Teleport authentication
- ❌ Not designed for scheduled, unattended execution
- ❌ Security restrictions prevent direct SQL Server access from AWS

---

## 🚀 Path 2: Automated Connection (AWS Athena)

### How Your Script Accesses Data

```
Python Script (SOXauto)
    ↓
[Okta Authentication]
    ↓
AWS IAM Role (temporary credentials)
    ↓
AWS Athena API
    ↓
Query Execution on S3 Data
    ↓
Amazon S3 Buckets:
  - s3://athena-query-results-s3-ew1-production-jdata/
  - s3://artifact-central-fin-dwh-s3-ew1-production-jdata/
  - s3://artifact-central-finrec-s3-ew1-production-jdata/
    ↓
Results → Pandas DataFrame
```

### Connection Details

**Query Engine**: AWS Athena  
**Data Storage**: Amazon S3 (Parquet, CSV, or other formats)  
**Authentication**: Okta → AWS IAM Role  
**Access Tool**: Python (`awswrangler`, `boto3`)  
**Profile**: `007809111365_Data-Prod-DataAnalyst-NonFinance`  

### Example Automated Query

```python
import awswrangler as wr

# Query Athena (not SQL Server!)
df = wr.athena.read_sql_query(
    sql="SELECT * FROM nav_bi.g_l_entries WHERE posting_date < DATE('2025-09-30')",
    database="nav_bi",
    s3_output="s3://athena-query-results-s3-ew1-production-jdata/"
)
```

### Why This Path Exists

- 🤖 **Automation**: Scheduled, unattended execution
- 🔒 **Security**: IAM roles, no hardcoded credentials
- 📈 **Scalability**: Process millions of rows efficiently
- 🌐 **Cloud-Native**: Integrates with AWS services
- 💰 **Cost-Effective**: Pay per query (no idle servers)

---

## 🗄️ Database Mapping

### SQL Server → Athena Translation

| SQL Server Database | SQL Server Table | **Athena Database** | **Athena Table** |
|---------------------|------------------|---------------------|------------------|
| NAV_BI (AIG_Nav_DW) | `[dbo].[G_L Entries]` | `nav_bi` | `g_l_entries` (?) |
| FINREC | `[dbo].[RPT_SOI]` | `finrec` | `rpt_soi` (?) |
| BOB | `[dbo].[orders]` | `bob` | `orders` (?) |

**⚠️ IMPORTANT**: Table and database names in Athena may differ from SQL Server. **You must confirm these with Carlos/Joao**.

### Known S3 Buckets (From Your Access)

```
✅ artifact-central-fin-dwh-s3-ew1-production-jdata
✅ artifact-central-finrec-s3-ew1-production-jdata
✅ athena-query-results-s3-ew1-production-jdata
```

These buckets likely contain:
- `fin-dwh`: Financial data warehouse (NAV_BI equivalent)
- `finrec`: Financial reconciliation data (FINREC equivalent)
- `athena-query-results`: Athena query output staging area

---

## 🔄 Data Flow: SQL Server → S3 → Athena

```
[SQL Server: fin-sql.jumia.local]
         ↓
    ETL Pipeline (AWS Glue? or other)
         ↓
[Amazon S3: s3://artifact-central-fin-dwh-s3-ew1-production-jdata/]
         ↓
    AWS Glue Crawler (schema discovery)
         ↓
[AWS Glue Data Catalog]
         ↓
[AWS Athena: Query Interface]
         ↓
[Your Python Script: awswrangler.athena.read_sql_query()]
```

### Key Points

1. **Data is Replicated**: SQL Server data is copied/streamed to S3
2. **S3 is the Source of Truth** for your script
3. **Athena is a Virtual Database**: No actual database server, just an API that queries S3 files
4. **Glue Catalog**: Metadata about tables, schemas, partitions

---

## 🛠️ Required Changes to SOXauto

### ❌ What to REMOVE

```python
# ❌ REMOVE: pyodbc connection to SQL Server
import pyodbc
connection = pyodbc.connect("DRIVER={...};SERVER=fin-sql.jumia.local;...")
```

```python
# ❌ REMOVE: DB_CONNECTION_STRING environment variable (for SQL Server)
os.environ['DB_CONNECTION_STRING'] = "..."
```

```python
# ❌ REMOVE: AWSSecretsManager for DB credentials
secret_manager = AWSSecretsManager()
connection_string = secret_manager.get_secret('jumia/sox/db-credentials-nav-bi')
```

### ✅ What to ADD

```python
# ✅ ADD: awswrangler for Athena queries
import awswrangler as wr

# ✅ ADD: Athena query execution
df = wr.athena.read_sql_query(
    sql=query,
    database="nav_bi",  # Athena database name (confirm this!)
    s3_output="s3://athena-query-results-s3-ew1-production-jdata/"
)
```

```python
# ✅ ADD: Environment variables for Athena
os.environ['ATHENA_DATABASE'] = 'nav_bi'
os.environ['ATHENA_S3_OUTPUT'] = 's3://athena-query-results-s3-ew1-production-jdata/'
```

---

## 📝 Updated IPE Configuration

### Old Configuration (SQL Server)

```json
{
  "ipe_id": "IPE_07",
  "secret_name": "jumia/sox/db-credentials-nav-bi",
  "query": "SELECT * FROM [AIG_Nav_DW].[dbo].[G_L Entries] WHERE ..."
}
```

### New Configuration (Athena)

```json
{
  "ipe_id": "IPE_07",
  "athena_database": "nav_bi",
  "athena_s3_output": "s3://athena-query-results-s3-ew1-production-jdata/",
  "query": "SELECT * FROM g_l_entries WHERE posting_date < DATE('2025-09-30')"
}
```

---

## 🎯 Immediate Next Steps

### 1. Confirm Athena Resources

**Ask Carlos/Joao**:
```
"What are the exact names of the Athena databases and tables that correspond to:
- NAV_BI (AIG_Nav_DW) → Athena database: ?
- FINREC → Athena database: ?
- BOB → Athena database: ?

Specifically, what are the Athena table names for:
- [G_L Entries] → ?
- [RPT_SOI] → ?
- [Orders] → ?
"
```

### 2. Confirm Authentication Process

**Ask Carlos/Joao**:
```
"What is the exact process for our Python script to programmatically authenticate 
via Okta to get AWS credentials?

- Do we use aws-okta CLI?
- Do we use boto3 with SSO profiles?
- Is there an existing service account or role we should use?
"
```

### 3. Test Athena Access

```bash
# Test if you can list Athena databases
aws athena list-databases --catalog-name AwsDataCatalog --profile 007809111365_Data-Prod-DataAnalyst-NonFinance

# Test if you can query Athena
aws athena start-query-execution \
  --query-string "SHOW DATABASES" \
  --result-configuration "OutputLocation=s3://athena-query-results-s3-ew1-production-jdata/" \
  --profile 007809111365_Data-Prod-DataAnalyst-NonFinance
```

---

## 🔒 Security Model

### Manual Path (Jump Server)

- **Authentication**: Windows Active Directory (JUMIA\username)
- **Authorization**: SQL Server permissions
- **Access Control**: Teleport session recording
- **Audit**: SQL Server audit logs

### Automated Path (Athena)

- **Authentication**: Okta → AWS STS temporary credentials
- **Authorization**: AWS IAM policies
- **Access Control**: S3 bucket policies + Athena permissions
- **Audit**: AWS CloudTrail logs

---

## 📚 Related Documentation

- [OKTA_AWS_SETUP.md](../setup/OKTA_AWS_SETUP.md) - AWS authentication
- [DATABASE_CONNECTION.md](../setup/DATABASE_CONNECTION.md) - Connection methods (now deprecated for SQL Server)
- [CONNECTION_STATUS.md](../setup/CONNECTION_STATUS.md) - Current AWS access status

---

## 💡 Key Takeaways

1. **Two Separate Worlds**: Manual (SQL Server) ≠ Automated (Athena/S3)
2. **Your Script Uses Athena**: No direct SQL Server connection
3. **S3 is the Data Source**: Data is replicated from SQL Server to S3
4. **awswrangler is Key**: Use this library instead of pyodbc
5. **Confirm Everything**: Table names, database names, authentication method

---

**Status**: ✅ Architecture Understood  
**Next**: Confirm Athena resources and refactor code  
**Impact**: Major refactoring required, but architecture is clearer
