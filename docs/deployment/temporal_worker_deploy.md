# Deploying the Temporal Worker (C-PG-1)

This guide replaces previous Lambda/ECS deployment instructions. The production runtime is a Temporal Worker that executes C-PG-1 workflow activities and connects to on‑prem MSSQL through a Teleport (`tsh`) tunnel.

## Prerequisites

- Temporal Server (self-hosted or managed) and credentials
- Teleport client (`tsh`) with database access to `fin-sql.jumia.local`
- ODBC Driver 17/18 for SQL Server installed
- Python 3.11 runtime (or Docker image)
- AWS credentials (Okta SSO or IAM) to read Secrets Manager (DB connection string)

## Environment variables

- DB_CONNECTION_STRING (optional if using Secrets Manager inside activities)
- AWS_REGION (e.g., eu-west-1)
- ENV (dev|staging|prod) — used in logs
- SOX_SERVICE=soxauto-cpg1
- TEMPORAL_HOST (e.g., localhost:7233 or temporal.example.com:7233)
- TEMPORAL_NAMESPACE (default unless customized)
- TEMPORAL_TASK_QUEUE=cpg1-task-queue

## Teleport tunnel

1. Authenticate with your SSO provider
2. Establish DB tunnel

```bash
# Example (replace with your proxy and resource names)
tsh login --proxy=teleport.example.com --user $USER
# Depending on setup: tsh db connect fin-sql
# Or start a local listener that maps to fin-sql.jumia.local
```

Ensure that your ODBC connection string points at the local Teleport-forwarded endpoint.

## Running the worker (bare metal)

```bash
export TEMPORAL_HOST="localhost:7233"
export TEMPORAL_NAMESPACE="default"
export TEMPORAL_TASK_QUEUE="cpg1-task-queue"

# Optional: set DB_CONNECTION_STRING if not using Secrets Manager directly
# export DB_CONNECTION_STRING="DRIVER={ODBC Driver 17 for SQL Server};SERVER=127.0.0.1,1433;DATABASE=...;UID=...;PWD=..."

python -m src.orchestrators.cpg1_worker
```

The worker will register activities from `src/orchestrators/cpg1_activities.py` and listen on the task queue.

## Running the worker (Docker Compose)

docker-compose.yml snippet:

```yaml
version: "3.9"
services:
  sox-worker:
    build: .
    image: soxauto/worker:latest
    environment:
      TEMPORAL_HOST: ${TEMPORAL_HOST}
      TEMPORAL_NAMESPACE: ${TEMPORAL_NAMESPACE:-default}
      TEMPORAL_TASK_QUEUE: ${TEMPORAL_TASK_QUEUE:-cpg1-task-queue}
      ENV: ${ENV:-prod}
      SOX_SERVICE: soxauto-cpg1
      AWS_REGION: ${AWS_REGION:-eu-west-1}
      # DB_CONNECTION_STRING: ${DB_CONNECTION_STRING}
    command: ["python", "-m", "src.orchestrators.cpg1_worker"]
    restart: unless-stopped
```

## Observability

- Logs are JSON-formatted by default via `src/utils/logging.py`
- Each activity log line includes workflow_id, run_id, and activity_id for correlation
- Evidence packages include execution metadata (consider adding workflow_id and run_id)

## Resilience & timeouts

- Activities are called with start_to_close timeouts from the workflow
- Add RetryPolicy for transient DB errors (see workflow for settings)
- Use smaller queries or batch processing if you encounter DB gateway timeouts

## Security notes

- Do not log secrets or full connection strings
- Use AWS Secrets Manager to store the ODBC connection string when possible
- Ensure Teleport audit logging is enabled

## Health checks

- Optional: run a lightweight `SELECT 1` activity before heavy queries
- Add a worker startup check that confirms ODBC driver is available

## Starter script

Run the workflow using `scripts/run_full_reconciliation.py` to kick off a reconciliation with specific parameters and wait for completion.
