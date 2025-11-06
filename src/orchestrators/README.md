# Temporal.io Workflow Orchestration for C-PG-1

This directory contains the Temporal.io workflow implementation for the C-PG-1 reconciliation process. The new architecture replaces the old "run-and-done" script model with a robust, scalable workflow orchestration system.

## Architecture Overview

### Components

1. **Workflow** (`cpg1_workflow.py`): Defines the orchestration logic - the sequence of operations for the C-PG-1 reconciliation
2. **Activities** (`cpg1_activities.py`): Contains the core business logic wrapped as Temporal activities
3. **Worker** (`cpg1_worker.py`): The service that executes workflows and activities
4. **Starter** (`scripts/run_full_reconciliation.py`): The client that initiates workflow executions

### Why Temporal?

The old script-based orchestration had several limitations:
- **No retry logic**: Script failures required manual intervention
- **No state management**: Progress was lost on failure
- **No observability**: Difficult to track execution status
- **No scalability**: Sequential execution with no parallelization
- **No versioning**: Changes could break running processes

Temporal.io provides:
- ✅ **Automatic retries** with configurable policies
- ✅ **Durable execution** that survives worker restarts
- ✅ **Built-in observability** via the Temporal UI
- ✅ **Parallel execution** of independent activities
- ✅ **Workflow versioning** for safe deployments
- ✅ **Error handling** with compensation logic

## Setup

### Prerequisites

1. **Temporal Server**: You need a running Temporal server
   
   **Option A: Local Development (Docker)**
   ```bash
   # Install Temporal CLI
   curl -sSf https://temporal.download/cli.sh | sh
   
   # Start Temporal server
   temporal server start-dev
   ```
   
   **Option B: Production (Temporal Cloud)**
   - Sign up at https://temporal.io/cloud
   - Get connection details and certificates
   - Set environment variables (see below)

2. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Environment Variables

Set these environment variables in your `.env` file or shell:

```bash
# Temporal Configuration
TEMPORAL_HOST=localhost:7233              # Temporal server address
TEMPORAL_NAMESPACE=default                # Temporal namespace
TEMPORAL_TASK_QUEUE=cpg1-task-queue      # Task queue name

# Database Configuration
DB_CONNECTION_STRING="Driver={ODBC Driver 18 for SQL Server};Server=...;..."

# Reconciliation Parameters
CUTOFF_DATE=2025-01-01                   # Optional: defaults to first day of current month
```

## Usage

### Step 1: Start the Worker

The worker must be running to execute workflows and activities:

```bash
python src/orchestrators/cpg1_worker.py
```

You should see output like:
```
2025-11-06 13:30:00 - INFO - Connecting to Temporal server at localhost:7233
2025-11-06 13:30:00 - INFO - Connected to Temporal server
2025-11-06 13:30:00 - INFO - Worker created successfully
2025-11-06 13:30:00 - INFO - Starting worker... (Press Ctrl+C to stop)
```

**Important**: Keep this worker running! It processes all workflow and activity tasks.

### Step 2: Start a Workflow

In a separate terminal, run the starter script:

```bash
# Run with default parameters
python scripts/run_full_reconciliation.py

# Run with custom cutoff date
python scripts/run_full_reconciliation.py --cutoff-date 2025-01-31

# Run with custom GL accounts
python scripts/run_full_reconciliation.py --gl-accounts 13001 13002 18412
```

The starter will:
1. Connect to the Temporal server
2. Start the C-PG-1 workflow
3. Wait for completion (or you can Ctrl+C - the workflow continues running)
4. Display results when complete

### Step 3: Monitor Execution

**Option A: Temporal UI (Recommended)**

Open http://localhost:8233 in your browser to:
- View workflow execution history
- Inspect activity results
- Retry failed activities
- Cancel running workflows

**Option B: Command Line**

```bash
# List recent workflows
temporal workflow list

# Show workflow details
temporal workflow describe --workflow-id cpg1-reconciliation-20251106_133000

# Show workflow history
temporal workflow show --workflow-id cpg1-reconciliation-20251106_133000
```

## Workflow Details

### Execution Flow

The C-PG-1 workflow executes these steps in sequence:

```
1. Fetch IPE Data (parallel)
   ├─ IPE_07: Customer Accounts
   ├─ IPE_31: Collection Accounts
   ├─ IPE_10: Customer Prepayments
   └─ IPE_08: Voucher Liabilities

2. Fetch CR Data (parallel)
   ├─ CR_04: NAV GL Balances
   ├─ CR_03: NAV GL Entries
   └─ DOC_VOUCHER_USAGE: Voucher Usage

3. Calculate Bridges & Adjustments (parallel)
   ├─ Customer Posting Group Bridge
   ├─ Timing Difference Bridge
   └─ VTC Adjustment

4. Classify Bridges
   └─ Apply classification rules to IPE_31

5. Save Evidence
   ├─ Bridge calculations evidence
   └─ Classification evidence
```

### Activities

Each activity is:
- **Retryable**: Failed activities automatically retry with exponential backoff
- **Timeout-protected**: Activities have configurable execution timeouts
- **Idempotent**: Activities can be safely retried without side effects
- **Observable**: Activity execution is logged and visible in Temporal UI

### Data Flow

Data flows between activities using Temporal's data converter:
- DataFrames are serialized to JSON-compatible dictionaries
- Large datasets are handled efficiently
- Data is automatically persisted in Temporal's event history

## Development

### Adding New Activities

1. Define the activity function in `cpg1_activities.py`:
   ```python
   @activity.defn(name="my_new_activity")
   async def my_new_activity(param1: str, param2: int) -> Dict[str, Any]:
       # Your logic here
       return {"result": "success"}
   ```

2. Register the activity in `cpg1_worker.py`:
   ```python
   worker = Worker(
       client,
       task_queue=task_queue,
       workflows=[Cpg1Workflow],
       activities=[
           # ... existing activities ...
           my_new_activity,
       ],
   )
   ```

3. Call the activity from the workflow in `cpg1_workflow.py`:
   ```python
   result = await workflow.execute_activity(
       my_new_activity,
       args=["param1_value", 42],
       start_to_close_timeout=timedelta(minutes=5),
   )
   ```

### Testing

Run unit tests for activities:
```bash
pytest tests/test_cpg1_activities.py -v
```

Run integration tests (requires Temporal server):
```bash
pytest tests/test_cpg1_workflow.py -v
```

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

View activity inputs/outputs in Temporal UI:
1. Open workflow execution
2. Click on an activity
3. View "Input" and "Output" tabs

## Migration from Old Scripts

### What Changed

**Before (Script-based)**:
```bash
python scripts/generate_customer_accounts.py
python scripts/generate_collection_accounts.py
python scripts/generate_other_ar.py
python scripts/classify_bridges.py
```

**After (Temporal-based)**:
```bash
# Start worker (once)
python src/orchestrators/cpg1_worker.py

# Start workflow (as needed)
python scripts/run_full_reconciliation.py
```

### Obsolete Scripts

The following scripts are **obsolete** and can be deleted after migration:
- ❌ `scripts/generate_customer_accounts.py` → replaced by `execute_ipe_query_activity("IPE_07")`
- ❌ `scripts/generate_collection_accounts.py` → replaced by `execute_ipe_query_activity("IPE_31")`
- ❌ `scripts/generate_other_ar.py` → replaced by `execute_ipe_query_activity("IPE_10")` and `execute_ipe_query_activity("IPE_08")`
- ❌ `scripts/classify_bridges.py` → replaced by `classify_bridges_activity()`

### Benefits of Migration

1. **Reliability**: Automatic retries on transient failures
2. **Observability**: See exactly what's happening in Temporal UI
3. **Scalability**: Run multiple reconciliations in parallel
4. **Maintainability**: Central workflow definition instead of scattered scripts
5. **Error Recovery**: Workflows can be resumed from point of failure

## Production Deployment

### High Availability Setup

For production, run multiple workers for redundancy:

```bash
# Terminal 1
python src/orchestrators/cpg1_worker.py

# Terminal 2
python src/orchestrators/cpg1_worker.py

# Terminal 3
python src/orchestrators/cpg1_worker.py
```

Temporal automatically load-balances work across all workers.

### Monitoring

Set up monitoring and alerting:

1. **Temporal Metrics**: Export to Prometheus/Grafana
2. **Application Logs**: Aggregate logs from all workers
3. **Workflow Alerts**: Alert on failed workflows or slow activities

### Deployment Process

1. Deploy new worker code (Temporal supports versioning)
2. Workers automatically pick up new workflow versions
3. In-flight workflows continue with old code (safe!)
4. New workflows use new code automatically

## Troubleshooting

### Worker Won't Start

**Issue**: `Error: Unable to connect to Temporal server`

**Solution**: Verify Temporal server is running:
```bash
temporal operator cluster health
```

### Activities Timing Out

**Issue**: Activities exceed timeout

**Solution**: Increase timeout in workflow:
```python
result = await workflow.execute_activity(
    my_activity,
    start_to_close_timeout=timedelta(minutes=60),  # Increase timeout
)
```

### Database Connection Errors

**Issue**: Activities fail with "DB_CONNECTION_STRING not set"

**Solution**: Ensure environment variable is set:
```bash
export DB_CONNECTION_STRING="Driver={...};Server=...;..."
```

### Workflow Stuck

**Issue**: Workflow shows as "Running" but no progress

**Solution**: 
1. Check if worker is running
2. Check worker logs for errors
3. Use Temporal UI to see activity status

## Resources

- [Temporal Documentation](https://docs.temporal.io/)
- [Temporal Python SDK](https://github.com/temporalio/sdk-python)
- [Temporal Samples](https://github.com/temporalio/samples-python)
- [Temporal Community](https://community.temporal.io/)

## Support

For questions or issues:
1. Check this README and Temporal documentation
2. Review workflow execution in Temporal UI
3. Check worker logs for error details
4. Contact the development team
