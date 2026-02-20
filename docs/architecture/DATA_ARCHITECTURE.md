# SOXauto Data Architecture - Apache Airflow Orchestration

**Date**: 06 November 2025  
**Architecture**: Apache Airflow DAG orchestration with direct connection to on-premises SQL Server via Teleport secure tunnel

---

## 🎯 Overview: Airflow-Orchestrated Data Access

SOXauto uses Apache Airflow for workflow orchestration and connects directly to the on-premises SQL Server database using:

1. **Orchestration**: Apache Airflow DAGs and Tasks
2. **Runtime**: Airflow Scheduler + Executor Workers
3. **Connection Method**: Teleport (`tsh`) secure tunnel
4. **Database Server**: `fin-sql.jumia.local` (SQL Server)
5. **Runner Module**: `src/core/runners/mssql_runner.py`
6. **Authentication**: Teleport-managed credentials

---

## 📊 Architecture Details

| Aspect | Implementation |
|--------|----------------|
| **Orchestration** | Apache Airflow DAGs and Tasks |
| **Runtime** | Airflow Scheduler + Executor Workers |
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
Airflow Scheduler
    ↓
[Airflow DAG Run: Execute IPE Extraction]
    ↓
[Airflow Worker: task execution]
    ↓
[Airflow Task: IPE Extraction for each IPE]
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

**Orchestration**: Apache Airflow  
**Runtime**: Airflow Scheduler + Workers  
**Server**: `fin-sql.jumia.local`  
**Authentication**: Teleport-managed  
**Access Tool**: Python with pyodbc via Teleport tunnel  
**Access Via**: Teleport secure tunnel  

### Example Airflow DAG and Task

```python
# Airflow DAG definition
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_ipe_config

def extract_ipe_task(ipe_id: str, cutoff_date: str) -> dict:
    config = get_ipe_config(ipe_id)
    runner = IPERunner(config, cutoff_date=cutoff_date)
    df = runner.run()
    return {"rows": len(df), "status": "success"}

with DAG(
    dag_id="soxauto_cpg1_reconciliation",
    start_date=datetime(2025, 1, 1),
    schedule="@monthly",
    catchup=False,
) as dag:
    run_ipe_07 = PythonOperator(
        task_id="extract_ipe_07",
        python_callable=extract_ipe_task,
        op_kwargs={"ipe_id": "IPE_07", "cutoff_date": "{{ ds }}"},
    )
```

### Why This Architecture

- 🔒 **Security**: Teleport manages all credentials and access
- 🔄 **Reliability**: Airflow provides retry policies, backfills, and resilient scheduling
- ⚡ **Scalability**: Airflow workers/executors can scale horizontally
- 🎯 **Direct Access**: No intermediate data lakes or ETL
- 📊 **Observability**: Airflow UI provides real-time DAG/task visibility
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
| **Airflow DAGs** | `dags/` | Orchestrates IPE extraction process |
| **Airflow Tasks** | `dags/` | Executes extraction/reconciliation steps |
| **IPE Runner** | `src/core/runners/mssql_runner.py` | Executes IPE queries |
| **Evidence Manager** | `src/core/evidence/manager.py` | Generates SOX evidence |
| **IPE Catalog** | `src/core/catalog/cpg1.py` | IPE definitions |

### Environment Variables

```bash
# Airflow configuration
AIRFLOW_HOME="/opt/airflow"
AIRFLOW__CORE__EXECUTOR="LocalExecutor"
AIRFLOW__CORE__LOAD_EXAMPLES="False"

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
1. Airflow Scheduler triggers DAG execution (monthly)
         ↓
2. Airflow DAG run starts on Scheduler/Executor
         ↓
3. DAG loads IPE configurations from catalog
         ↓
4. For each IPE, DAG executes Task
         ↓
5. Task establishes Teleport tunnel connection
         ↓
6. Task executes SQL query on fin-sql.jumia.local
         ↓
7. Task loads results into Pandas DataFrame
         ↓
8. Task runs SOX validation queries
         ↓
9. Task generates Digital Evidence Package
         ↓
10. Task saves evidence to local directory
         ↓
11. Task returns validated data to DAG run context
         ↓
12. DAG run completes when all IPEs are processed
```

---

## 📚 References

- **Teleport Documentation**: [https://goteleport.com/docs/](https://goteleport.com/docs/)
- **SQL Server Documentation**: [https://learn.microsoft.com/en-us/sql/](https://learn.microsoft.com/en-us/sql/)
- **SOX Compliance**: [https://www.sox-online.com/](https://www.sox-online.com/)

---

**Last Updated**: 06 November 2025
