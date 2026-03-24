# SQL Extraction Execution and Parameterization Guide

This guide explains how to run IPE extractions and reconciliation, and how to configure SQL queries with dynamic dates.

---

## 1. How It Works

All SQL queries are stored in the catalog (`src/core/catalog/cpg1.py`) and contain **placeholders** like `{cutoff_date}`.

Execution is triggered via CLI or Streamlit. Before the queries run, placeholders are replaced with values passed as parameters (or via **environment variables**) through `src/utils/sql_template.py`.

---

## 2. Available Parameters

The following parameters are recognized by the scripts. Export them in your terminal before running an extraction.

| Environment Variable   | Required Format              | Description                                              | Used by |
|------------------------|------------------------------|----------------------------------------------------------|---------|
| `CUTOFF_DATE`          | `YYYY-MM-DD`                 | Cutoff date (exclusive) for most IPEs.                   | IPE_07, IPE_10, IPE_31… |
| `YEAR_START`           | `YYYY-MM-DD`                 | Annual period start for consolidated reports.            | CR_04   |
| `YEAR_END`             | `YYYY-MM-DD`                 | Annual period end for consolidated reports.              | CR_04   |
| `FX_DATE`              | `YYYY-MM-DD HH:MM:SS.mmm`    | Exact date for exchange rates.                           | CR_05a  |
| `DB_CONNECTION_STRING` | ODBC connection string        | Direct SQL Server connection (bypasses Secrets Manager). | All IPEs |

---

## 3. Example: September 2025 Close

### a) Configure the Environment

For a close at 30/09/2025, the `CUTOFF_DATE` is the first day of the following month.

```bash
# Cutoff date (exclusive)
export CUTOFF_DATE='2025-10-01'

# Annual period (e.g. 2025)
export YEAR_START='2025-01-01'
export YEAR_END='2025-12-31'

# Exchange rate date (if required by CR_05a)
export FX_DATE='2025-09-30 00:00:00.000'

# Direct SQL Server connection via Teleport (bypasses AWS Secrets Manager)
export DB_CONNECTION_STRING="DRIVER=ODBC Driver 17 for SQL Server;SERVER=fin-sql.jumia.local;DATABASE=AIG_Nav_Jumia_Reconciliation;Trusted_Connection=yes;"
```

On Windows (PowerShell):
```powershell
$env:DB_CONNECTION_STRING="DRIVER={ODBC Driver 17 for SQL Server};SERVER=fin-sql.jumia.local;DATABASE=AIG_Nav_Jumia_Reconciliation;Trusted_Connection=yes;"
```

Tip: Place these variables in a `.env` file and source it. `DB_CONNECTION_STRING` takes precedence over AWS Secrets Manager when set.

### b) Run the extraction (UI or CLI)

**Streamlit UI (interactive)**:

```bash
streamlit run src/frontend/app.py
```

The UI allows selecting the `cutoff_date`, company, and the IPEs/CRs to execute.

**CLI / headless (batch or CI)**:

```bash
python scripts/run_headless_test.py \
  --cutoff-date 2025-10-01 \
  --company EC_NG
```

Available CLI parameters:

```bash
# Specific IPEs only
python scripts/run_headless_test.py --cutoff-date 2025-10-01 --company EC_NG \
  --ipes IPE_07,IPE_08,CR_03

# Without bridge analysis (faster)
python scripts/run_headless_test.py --cutoff-date 2025-10-01 --company EC_NG --no-bridges

# Output to JSON file
python scripts/run_headless_test.py --cutoff-date 2025-10-01 --company EC_NG \
  --output results.json
```

Full help: `python scripts/run_headless_test.py --help`

---

## 4. Error Handling and Debugging

The `render_sql` function raises an error if any placeholders remain unresolved (e.g. missing `{cutoff_date}`). This prevents obscure SQL errors.

To diagnose an execution:

1. Open the generated evidence package: `evidence/<IPE_ID>_<COMPANY>_<PERIOD>_<timestamp>/`
2. Check `01_executed_query.sql` for the executed query and `02_query_parameters.json` for the parameters
3. Check `07_execution_log.json` for the detailed execution log
4. Use debug probes — see [`DEBUG_MAP.md`](DEBUG_MAP.md) and [`DEBUG_PROBE.md`](DEBUG_PROBE.md)

---

## 5. Operational Notes

- The SQL Server connection uses a secure **Teleport (`tsh`)** tunnel to `fin-sql.jumia.local`
- Complete evidence packages (8 files) are generated automatically per IPE in `evidence/<IPE_ID>/`
- The "Bridges & Adjustments" classification is described in `docs/development/BRIDGES_RULES.md`
- Available company variants are defined in `src/core/catalog/cpg1.py`

---

## 6. File Reference

- SQL Catalog: `src/core/catalog/cpg1.py`
- SQL Rendering: `src/utils/sql_template.py`
- IPE Runner: `src/core/runners/mssql_runner.py`
- CLI Entry Point: `scripts/run_headless_test.py`
- UI Entry Point: `src/frontend/app.py`
- Reconciliation: `src/core/reconciliation/run_reconciliation.py`
