# SOXauto Data Architecture - Temporal.io Orchestration

**Date**: 06 November 2025  
**Architecture**: Temporal.io workflow orchestration with direct connection to on-premises SQL Server via Teleport secure tunnel

---

## 🎯 Overview: Temporal-Orchestrated Data Access

SOXauto uses Temporal.io for durable workflow orchestration and connects directly to the on-premises SQL Server database using:

1. **Orchestration**: Temporal.io Workflows and Activities
2. **Worker**: Temporal Worker (`src/orchestrators/cpg1_worker.py`)
3. **Connection Method**: Teleport (`tsh`) secure tunnel
4. **Database Server**: `fin-sql.jumia.local` (SQL Server)
5. **Runner Module**: `src/core/runners/mssql_runner.py`
6. **Authentication**: Teleport-managed credentials

---

## 📊 Architecture Details

| Aspect | Implementation |
|--------|----------------|
| **Orchestration** | Temporal.io Workflows and Activities |
| **Worker** | Temporal Worker (`src/orchestrators/cpg1_worker.py`) |
| **Connection Tool** | Teleport (`tsh`) |
| **Server** | `fin-sql.jumia.local` |
| **Authentication** | Teleport-managed (no local credentials) |
| **Data Location** | Live SQL Server Database |
| **Access Method** | Secure tunnel via Teleport |
| **Purpose** | Automated IPE extraction with SOX compliance |
| **Database Protocol** | SQL Server (TDS) over Teleport tunnel |
| **Result Format** | Pandas DataFrame |
| **Evidence Generation** | Full Digital Evidence Package (SHA-256 hashes) |

---

## 🔍 Connection Flow

### How SOXauto Accesses Data

```
Temporal Scheduler
    ↓
[Temporal Workflow: Execute IPE Extraction]
    ↓
[Temporal Worker: cpg1_worker.py]
    ↓
[Temporal Activity: IPE Extraction for each IPE]
    ↓
[Authenticate via Teleport]
    ↓
Teleport Secure Tunnel (tsh)
    ↓
fin-sql.jumia.local (SQL Server)
    ↓
Databases:
  - NAV_BI (AIG_Nav_DW)
  - FINREC
  - BOB
    ↓
mssql_runner.py extracts data
    ↓
Evidence Manager generates audit trail
```

### Connection Details

**Orchestration**: Temporal.io  
**Worker**: `src/orchestrators/cpg1_worker.py`  
**Server**: `fin-sql.jumia.local`  
**Authentication**: Teleport-managed  
**Access Tool**: Python with pyodbc via Teleport tunnel  
**Access Via**: Teleport secure tunnel  

### Example Workflow and Activity

```python
# Temporal Workflow definition
from temporalio import workflow
from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_ipe_config

@workflow.defn
class IPEExtractionWorkflow:
    @workflow.run
    async def run(self, cutoff_date: str) -> dict:
        # Execute IPE extraction as Temporal Activity
        result = await workflow.execute_activity(
            extract_ipe_activity,
            args=["IPE_07", cutoff_date],
            start_to_close_timeout=timedelta(minutes=10)
        )
        return result

@activity.defn
async def extract_ipe_activity(ipe_id: str, cutoff_date: str) -> dict:
    # Load IPE configuration
    config = get_ipe_config(ipe_id)
    
    # Execute via Teleport tunnel
    runner = IPERunner(config, cutoff_date=cutoff_date)
    df = runner.run()  # Returns pandas DataFrame with validation
    
    return {"rows": len(df), "status": "success"}
```

### Why This Architecture

- 🔒 **Security**: Teleport manages all credentials and access
- 🔄 **Reliability**: Temporal provides durable, fault-tolerant workflows
- ⚡ **Scalability**: Temporal Workers can scale horizontally
- 🎯 **Direct Access**: No intermediate data lakes or ETL
- 📊 **Observability**: Temporal UI provides real-time workflow visibility
- ✅ **SOX Compliant**: Digital Evidence Package for every extraction

---

## 🗄️ Database Structure

### Available Databases on fin-sql.jumia.local

| Database | Description | Primary Use |
|----------|-------------|-------------|
| NAV_BI (AIG_Nav_DW) | Main data warehouse | General ledger, customer balances |
| FINREC | Financial reconciliation | Reconciliation data |
| BOB | Back Office Banking | BOB-specific operations |

### Example Tables

| Database | Table | Description |
|----------|-------|-------------|
| NAV_BI (AIG_Nav_DW) | `[dbo].[G_L Entries]` | General ledger entries |
| NAV_BI (AIG_Nav_DW) | `[dbo].[Customer Ledger Entry]` | Customer transactions |
| FINREC | `[dbo].[RPT_SOI]` | Statement of Income reporting |
| BOB | `[dbo].[orders]` | BOB orders |

---

## 🔐 Security & Compliance

### Teleport Security Features

- **No Local Credentials**: All authentication managed by Teleport
- **Audit Logging**: Complete connection and query audit trail
- **Session Recording**: All database sessions can be recorded
- **Access Control**: Fine-grained permissions via Teleport roles
- **Certificate-Based Auth**: Short-lived certificates instead of passwords

### SOX Compliance

Every IPE extraction generates a complete Digital Evidence Package:

1. **01_executed_query.sql** - Exact SQL query executed
2. **02_query_parameters.json** - Parameters used
3. **03_data_snapshot.csv** - Data snapshot (first 100 rows)
4. **04_data_summary.json** - Statistical summary
5. **05_integrity_hash.json** - SHA-256 hash of complete dataset
6. **06_validation_results.json** - SOX validation results
7. **07_execution_log.json** - Complete execution log

---

## 🛠️ Implementation

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Temporal Worker** | `src/orchestrators/cpg1_worker.py` | Executes workflows and activities |
| **Temporal Workflows** | `src/orchestrators/workflow.py` | Orchestrates IPE extraction process |
| **IPE Runner** | `src/core/runners/mssql_runner.py` | Executes IPE queries |
| **Evidence Manager** | `src/core/evidence/manager.py` | Generates SOX evidence |
| **IPE Catalog** | `src/core/catalog/cpg1.py` | IPE definitions |

### Environment Variables

```bash
# Temporal configuration
TEMPORAL_ADDRESS="localhost:7233"  # Temporal server address
TEMPORAL_NAMESPACE="default"       # Temporal namespace

# Database connection (via Teleport)
# Note: Actual credentials are managed by Teleport - no passwords stored locally
DB_CONNECTION_STRING="DRIVER={ODBC Driver 17 for SQL Server};SERVER=fin-sql.jumia.local;Trusted_Connection=yes"

# Execution parameters
CUTOFF_DATE="2025-09-30"
```

**Security Note**: Authentication is handled entirely by Teleport. No database passwords or credentials are stored in environment variables or configuration files.

---

## 📝 IPE Configuration Example

```python
{
    "id": "IPE_07",
    "description": "Customer balances - Monthly balances at date",
    "secret_name": "jumia/sox/db-credentials-nav-bi",
    "main_query": """
        SELECT [Customer No_], [Customer Name], [Posting Date], [Amount]
        FROM [AIG_Nav_DW].[dbo].[Customer Ledger Entry]
        WHERE [Posting Date] <= ?
    """,
    "validation": {
        "completeness_query": "...",
        "accuracy_positive_query": "...",
        "accuracy_negative_query": "..."
    }
}
```

---

## 🔄 Data Flow

```
1. Temporal Scheduler triggers Workflow execution (monthly)
         ↓
2. Temporal Workflow starts on Worker (cpg1_worker.py)
         ↓
3. Workflow loads IPE configurations from catalog
         ↓
4. For each IPE, Workflow executes Activity
         ↓
5. Activity establishes Teleport tunnel connection
         ↓
6. Activity executes SQL query on fin-sql.jumia.local
         ↓
7. Activity loads results into Pandas DataFrame
         ↓
8. Activity runs SOX validation queries
         ↓
9. Activity generates Digital Evidence Package
         ↓
10. Activity saves evidence to local directory
         ↓
11. Activity returns validated data to Workflow
         ↓
12. Workflow completes when all IPEs are processed
```

---

## 📚 References

- **Teleport Documentation**: [https://goteleport.com/docs/](https://goteleport.com/docs/)
- **SQL Server Documentation**: [https://learn.microsoft.com/en-us/sql/](https://learn.microsoft.com/en-us/sql/)
- **SOX Compliance**: [https://www.sox-online.com/](https://www.sox-online.com/)

---

**Last Updated**: 06 November 2025
