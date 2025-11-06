# SOXauto Data Architecture - Teleport Connection

**Date**: 06 November 2025  
**Architecture**: Direct connection to on-premises SQL Server via Teleport secure tunnel

---

## 🎯 Overview: Secure Database Access

SOXauto connects directly to the on-premises SQL Server database using:

1. **Connection Method**: Teleport (`tsh`) secure tunnel
2. **Database Server**: `fin-sql.jumia.local` (SQL Server)
3. **Runner Module**: `src/core/runners/mssql_runner.py`
4. **Authentication**: Teleport-managed credentials

---

## 📊 Architecture Details

| Aspect | Implementation |
|--------|----------------|
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
SOXauto Application
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

**Server**: `fin-sql.jumia.local`  
**Authentication**: Teleport-managed  
**Access Tool**: Python with pyodbc via Teleport tunnel  
**Access Via**: Teleport secure tunnel  

### Example Query via mssql_runner.py

```python
from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_ipe_config

# Load IPE configuration
config = get_ipe_config('IPE_07')

# Execute via Teleport tunnel
runner = IPERunner(config, cutoff_date='2025-09-30')
df = runner.run()  # Returns pandas DataFrame with validation
```

### Why This Architecture

- 🔒 **Security**: Teleport manages all credentials and access
- 🤖 **Automation**: Supports scheduled, unattended execution  
- 📊 **Compliance**: Full audit trail via Teleport logging
- 🎯 **Direct Access**: No intermediate data lakes or ETL
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
| **IPE Runner** | `src/core/runners/mssql_runner.py` | Executes IPE queries |
| **Evidence Manager** | `src/core/evidence/manager.py` | Generates SOX evidence |
| **IPE Catalog** | `src/core/catalog/cpg1.py` | IPE definitions |
| **Orchestrator** | `src/orchestrators/workflow.py` | Workflow coordination |

### Environment Variables

```bash
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
1. Orchestrator triggers IPE execution
         ↓
2. IPERunner loads configuration from catalog
         ↓
3. Establish Teleport tunnel connection
         ↓
4. Execute SQL query on fin-sql.jumia.local
         ↓
5. Load results into Pandas DataFrame
         ↓
6. Run SOX validation queries
         ↓
7. Generate Digital Evidence Package
         ↓
8. Save evidence to local directory
         ↓
9. Return validated data to orchestrator
```

---

## 📚 References

- **Teleport Documentation**: [https://goteleport.com/docs/](https://goteleport.com/docs/)
- **SQL Server Documentation**: [https://docs.microsoft.com/en-us/sql/](https://docs.microsoft.com/en-us/sql/)
- **SOX Compliance**: [https://www.sox-online.com/](https://www.sox-online.com/)

---

**Last Updated**: 06 November 2025
