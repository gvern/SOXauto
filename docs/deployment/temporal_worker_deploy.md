# Deploying the Temporal Worker (C-PG-1)

This guide describes the **current production deployment architecture** for SOXauto using Temporal + Teleport. It replaces the obsolete Lambda/Fargate-based deployment described in the archived documentation.

## Overview

The production runtime is a **Temporal Worker** that:
- Executes C-PG-1 workflow activities for SOX reconciliation
- Connects to on-premises MSSQL Server (`fin-sql.jumia.local`) through a Teleport tunnel
- Uses AWS Secrets Manager for secure credential management
- Generates tamper-proof evidence packages for audit compliance

## Prerequisites

Before deploying the worker, ensure the following prerequisites are met:

### 1. Network Access to Database (Teleport/ODBC)

**Requirement:** The worker must run on a machine with network access to `fin-sql.jumia.local`.

This is achieved through:
- **Teleport client (`tsh`)** configured with database access to `fin-sql.jumia.local`
- **ODBC Driver 17 or 18 for SQL Server** installed on the worker machine
- Active Teleport session with valid credentials

The worker uses an ODBC connection string that points to the Teleport-forwarded endpoint to access the on-premises database securely without exposing credentials.

### 2. AWS Secrets Manager Access

**Requirement:** The worker needs AWS credentials to retrieve the database connection string from Secrets Manager.

Set the following environment variable:
- **`AWS_SECRET_ID`**: The name/ARN of the secret in AWS Secrets Manager containing the database connection string
  - Example: `jumia-sox-prod/mssql-connection`
  - The secret should contain the ODBC connection string with credentials

Alternatively, you can set `DB_CONNECTION_STRING` directly as an environment variable (useful for local development), but using Secrets Manager is recommended for production.

AWS credentials can be configured via:
- Okta SSO (`aws sso login --profile jumia-sox-prod`)
- IAM role (if running on EC2/ECS)
- Standard AWS credentials file (`~/.aws/credentials`)

### 3. Temporal Server Configuration

**Requirement:** The worker must connect to a Temporal server and namespace.

Set these environment variables:
- **`TEMPORAL_ADDRESS`**: Temporal server endpoint (e.g., `temporal.example.com:7233` or `localhost:7233` for local)
- **`TEMPORAL_NAMESPACE`**: Temporal namespace (default: `default`, or your custom namespace like `sox-prod`)
- **`TEMPORAL_TASK_QUEUE`**: Task queue name (default: `cpg1-task-queue`)

For Temporal Cloud or mTLS setups, additional TLS certificates may be required.

### 4. Python Runtime

- **Python 3.11** or higher
- Dependencies installed from `requirements.txt`
- Or use the provided Docker image

## Environment Variables Reference

The following environment variables configure the Temporal Worker:

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TEMPORAL_ADDRESS` | Temporal server endpoint | `temporal.example.com:7233` or `localhost:7233` |
| `TEMPORAL_NAMESPACE` | Temporal namespace | `default` or `sox-prod` |
| `TEMPORAL_TASK_QUEUE` | Task queue name | `cpg1-task-queue` |

### Database Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_SECRET_ID` | AWS Secrets Manager secret name for DB connection | `jumia-sox-prod/mssql-connection` |
| `DB_CONNECTION_STRING` | (Alternative) Direct ODBC connection string | `DRIVER={ODBC Driver 17 for SQL Server};SERVER=...` |

### AWS Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for Secrets Manager | `eu-west-1` |
| `AWS_PROFILE` | AWS profile name for Okta SSO | `jumia-sox-prod` |
| `USE_OKTA_AUTH` | Enable Okta SSO authentication | `true` |

### Optional Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENV` | Environment name (for logging) | `dev`, `staging`, `prod` |
| `SOX_SERVICE` | Service identifier (for logging) | `soxauto-cpg1` |
| `CUTOFF_DATE` | Default cutoff date for reconciliation | `2024-12-31` |
| `LOG_LEVEL` | Logging level | `INFO`, `DEBUG` |

## Teleport Database Tunnel Setup

Before starting the worker, establish a secure tunnel to the on-premises database:

1. **Authenticate with Teleport:**
   ```bash
   # Login to Teleport (replace with your actual proxy and username)
   tsh login --proxy=teleport.jumia.com --user=$USER
   ```

2. **Verify database access:**
   ```bash
   # List available databases
   tsh db ls
   
   # Should show fin-sql.jumia.local or similar
   ```

3. **Start the database tunnel:**
   ```bash
   # Connect to the database (creates local listener)
   tsh db connect fin-sql
   
   # Or start a proxy on a specific port
   tsh proxy db --port=1433 fin-sql
   ```

The Teleport tunnel forwards database traffic securely from your local machine (or worker machine) to `fin-sql.jumia.local`, allowing ODBC connections without storing database passwords.

**Important:** The ODBC connection string should point to the local Teleport-forwarded endpoint (e.g., `SERVER=127.0.0.1,1433` or `SERVER=localhost,1433`).

## Starting the Worker

### Execution Command

Once prerequisites are met and environment variables are configured, start the Temporal Worker with:

```bash
python -m src.orchestrators.cpg1_worker
```

This command:
- Registers all workflow and activity definitions from `src/orchestrators/cpg1_activities.py`
- Connects to the Temporal server at `TEMPORAL_ADDRESS`
- Listens for tasks on the `TEMPORAL_TASK_QUEUE`
- Logs workflow execution details in JSON format

**Expected output:**
```
INFO: Connected to Temporal server at temporal.example.com:7233
INFO: Registered activities: extract_ipe, extract_cr, calculate_bridge, ...
INFO: Worker started on task queue: cpg1-task-queue
INFO: Waiting for workflow tasks...
```

The worker will run continuously, processing workflow tasks as they are dispatched by the Temporal server.

### Running as a Service (Production)

For production deployments, run the worker as a systemd service:

**Create `/etc/systemd/system/soxauto-worker.service`:**
```ini
[Unit]
Description=SOXauto Temporal Worker
After=network.target

[Service]
Type=simple
User=soxauto
WorkingDirectory=/opt/soxauto
Environment="TEMPORAL_ADDRESS=temporal.example.com:7233"
Environment="TEMPORAL_NAMESPACE=sox-prod"
Environment="TEMPORAL_TASK_QUEUE=cpg1-task-queue"
Environment="AWS_REGION=eu-west-1"
Environment="AWS_SECRET_ID=jumia-sox-prod/mssql-connection"
Environment="ENV=prod"
Environment="SOX_SERVICE=soxauto-cpg1"
ExecStart=/opt/soxauto/venv/bin/python -m src.orchestrators.cpg1_worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable soxauto-worker
sudo systemctl start soxauto-worker
sudo systemctl status soxauto-worker
```

## Running the Worker (Docker Compose)

For containerized deployments, use Docker Compose:

**`docker-compose.yml`:**
```yaml
version: "3.9"
services:
  sox-worker:
    build: .
    image: soxauto/worker:latest
    environment:
      TEMPORAL_ADDRESS: ${TEMPORAL_ADDRESS}
      TEMPORAL_NAMESPACE: ${TEMPORAL_NAMESPACE:-default}
      TEMPORAL_TASK_QUEUE: ${TEMPORAL_TASK_QUEUE:-cpg1-task-queue}
      AWS_REGION: ${AWS_REGION:-eu-west-1}
      AWS_SECRET_ID: ${AWS_SECRET_ID}
      ENV: ${ENV:-prod}
      SOX_SERVICE: soxauto-cpg1
      # Optional: DB_CONNECTION_STRING for direct connection
      # DB_CONNECTION_STRING: ${DB_CONNECTION_STRING}
    command: ["python", "-m", "src.orchestrators.cpg1_worker"]
    restart: unless-stopped
    volumes:
      # Mount Teleport credentials if needed
      - ~/.tsh:/root/.tsh:ro
```

**Start the worker:**
```bash
docker-compose up -d sox-worker
docker-compose logs -f sox-worker
```

## Triggering a Workflow Execution

Once the worker is running, trigger a C-PG-1 reconciliation workflow using the starter script:

### Command

```bash
python scripts/run_full_reconciliation.py
```

### Options

```bash
# Run with custom cutoff date
python scripts/run_full_reconciliation.py --cutoff-date 2024-12-31

# Run with specific GL accounts
python scripts/run_full_reconciliation.py --gl-accounts 13001 13002 13003

# Run with custom year range
python scripts/run_full_reconciliation.py \
  --year-start 2024-01-01 \
  --year-end 2024-12-31

# Combine options
python scripts/run_full_reconciliation.py \
  --cutoff-date 2024-12-31 \
  --gl-accounts 13001 13002 13003 \
  --year-start 2024-01-01 \
  --year-end 2024-12-31
```

### What Happens

The script will:
1. Connect to the Temporal server using `TEMPORAL_ADDRESS`
2. Start the `Cpg1Workflow` with the specified parameters
3. Display the workflow ID and run ID
4. Wait for workflow completion (can be interrupted with Ctrl+C)
5. Show results including:
   - IPE extraction results (rows extracted per IPE)
   - CR extraction results
   - Bridge calculation amounts
   - Evidence package file paths

### Example Output

```
Connected to Temporal server at temporal.example.com:7233
Namespace: sox-prod
Task queue: cpg1-task-queue

Starting C-PG-1 Reconciliation Workflow
Workflow ID: cpg1-reconciliation-20241231_143022
Cutoff Date: 2024-12-31
GL Accounts: 13001, 13002, 13003, ...

Workflow started successfully!
Waiting for workflow to complete...

================================================================================
WORKFLOW COMPLETED
================================================================================
Status: success

IPE Results:
  - IPE-01-Customer-AR: 15234 rows extracted
  - IPE-02-Collection-Accounts: 8912 rows extracted
  - IPE-03-Other-AR: 3456 rows extracted

CR Results:
  - CR-01-GL-Detail: 27602 rows extracted

Bridge Calculations:
  - Bridge-A-Timing: $45,231.50
  - Bridge-B-Classification: $12,890.25

Evidence saved to:
  - /opt/soxauto/evidence/CPG1_Evidence_20241231_143545.zip
================================================================================
```

### Monitoring

You can also monitor workflow execution through:
- **Temporal Web UI**: Navigate to your Temporal server's web interface
- **Temporal CLI**: Use `tctl workflow describe --workflow_id <id>`

## Observability & Logging

### Structured Logging

- All logs are JSON-formatted via `src/utils/logging.py`
- Each activity log includes:
  - `workflow_id`: Unique workflow execution identifier
  - `run_id`: Unique run identifier (for retries)
  - `activity_id`: Activity instance identifier
  - `timestamp`: ISO 8601 timestamp
  - `level`: Log level (INFO, WARNING, ERROR)
  - `message`: Human-readable log message

### Log Aggregation

For production deployments, aggregate logs using:
- **CloudWatch Logs** (if running on AWS)
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Grafana Loki** with Promtail
- **Datadog** or other APM solutions

Filter logs by `workflow_id` to trace complete workflow execution.

### Temporal Web UI

Access the Temporal Web UI to:
- View active and completed workflows
- Inspect workflow history and event timelines
- Debug failed activities
- Monitor task queue backlogs
- View worker health and capacity

## Resilience & Fault Tolerance

### Activity Timeouts

Activities are configured with start-to-close timeouts to prevent indefinite hangs:
- Database query activities: 10-15 minutes
- Evidence packaging: 5 minutes
- Bridge calculations: 2-3 minutes

### Retry Policies

Transient failures (database connectivity, network issues) are automatically retried:
- **Initial interval**: 1 second
- **Backoff coefficient**: 2.0
- **Maximum interval**: 60 seconds
- **Maximum attempts**: 5

Non-retryable errors (invalid data, logic errors) fail immediately.

### Best Practices

- Use smaller query batches if encountering database gateway timeouts
- Monitor activity durations and adjust timeouts as needed
- Implement workflow "continue-as-new" for very long-running reconciliations

## Security Considerations

### Credentials Management

✅ **DO:**
- Store database credentials in AWS Secrets Manager
- Use Teleport for database access (no passwords in connection strings)
- Rotate secrets regularly
- Use IAM roles or Okta SSO for AWS authentication

❌ **DO NOT:**
- Log secrets or connection strings
- Commit credentials to source code
- Store passwords in environment variables (use Secrets Manager)
- Disable Teleport audit logging

### Network Security

- Worker should run in a private subnet (if cloud-hosted)
- Restrict inbound traffic to worker instances
- Use TLS/mTLS for Temporal connections
- Enable Teleport session recording for audit compliance

### Evidence Integrity

- Evidence packages use SHA-256 hashing
- Metadata includes workflow_id and run_id for traceability
- Digital signatures can be added for enhanced tamper-proofing
- Store evidence in immutable S3 buckets with versioning

## Health Checks

### Worker Health

Monitor worker health through:
- Temporal Web UI → Workers tab
- Heartbeat logs from activities
- Task queue metrics (available vs. occupied slots)

### Database Connectivity

Optional health check before heavy queries:
```python
# Run a lightweight query to verify connectivity
connection.execute("SELECT 1")
```

### ODBC Driver Verification

At worker startup, verify ODBC driver availability:
```bash
# List installed ODBC drivers
odbcinst -q -d
```

Should show:
```
[ODBC Driver 17 for SQL Server]
[ODBC Driver 18 for SQL Server]
```

## Troubleshooting

### Worker Cannot Connect to Temporal

**Symptoms:** Worker fails to start with connection errors

**Solutions:**
1. Verify `TEMPORAL_ADDRESS` is correct
2. Check network connectivity: `telnet temporal.example.com 7233`
3. Verify namespace exists: `tctl namespace describe <namespace>`
4. Check TLS certificates (if using Temporal Cloud)

### Database Connection Failures

**Symptoms:** Activities fail with "Connection refused" or timeout errors

**Solutions:**
1. Verify Teleport tunnel is active: `tsh db ls`
2. Test ODBC connection: `python scripts/check_mssql_connection.py`
3. Check connection string syntax
4. Verify database permissions

### AWS Secrets Manager Access Denied

**Symptoms:** "AccessDeniedException" when retrieving secrets

**Solutions:**
1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check IAM policy allows `secretsmanager:GetSecretValue`
3. Verify secret ARN/name is correct
4. If using Okta SSO: `aws sso login --profile <profile>`

### Activity Timeout

**Symptoms:** Activity execution exceeds timeout and is retried

**Solutions:**
1. Increase `start_to_close_timeout` in activity options
2. Optimize database queries (add indexes, reduce data volume)
3. Check database server performance
4. Split large queries into smaller batches

### Missing Evidence Packages

**Symptoms:** Workflow completes but evidence files not found

**Solutions:**
1. Check `evidence/` directory exists and is writable
2. Verify disk space: `df -h`
3. Check activity logs for file write errors
4. Verify S3 upload succeeded (if configured)

## Deployment Checklist

Before deploying to production:

- [ ] Temporal server is accessible and healthy
- [ ] Teleport tunnel is configured and tested
- [ ] ODBC Driver 17/18 is installed
- [ ] AWS credentials are configured (IAM role or Okta SSO)
- [ ] AWS Secrets Manager contains database connection string
- [ ] Environment variables are set correctly
- [ ] Worker starts successfully and registers activities
- [ ] Test workflow execution completes end-to-end
- [ ] Evidence packages are generated and verified
- [ ] Logs are aggregated and queryable
- [ ] Monitoring/alerting is configured
- [ ] Security review completed

## Next Steps

After successful deployment:

1. **Schedule recurring workflows** using Temporal Schedules (e.g., monthly on 1st of month)
2. **Set up monitoring** dashboards for workflow metrics
3. **Configure alerts** for workflow failures or SLA breaches
4. **Document operational procedures** for team handoff
5. **Test disaster recovery** procedures

## Additional Resources

- [Temporal Documentation](https://docs.temporal.io/)
- [Teleport Database Access Guide](https://goteleport.com/docs/database-access/)
- [Project README](../../README.md)
- [Temporal Web UI Guide](https://docs.temporal.io/web-ui)
