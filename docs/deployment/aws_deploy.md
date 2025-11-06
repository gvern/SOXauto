# [DEPRECATED] AWS Deployment Guide (Pre-Temporal Architecture)

> This document is archived. The project now uses a Temporal Worker + Teleport tunnel architecture for orchestration and database access.
> Please refer to `docs/deployment/temporal_worker_deploy.md` for current deployment instructions.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Temporal Setup](#temporal-setup)
3. [Worker Deployment Options](#worker-deployment-options)
4. [Configuration](#configuration)
5. [Testing Deployment](#testing-deployment)
6. [Monitoring and Logging](#monitoring-and-logging)

---

## Prerequisites

### Required Tools
- **Python** 3.11+
- **Docker** (for container builds)
- **Temporal Server** (self-hosted or Temporal Cloud)
- **Teleport (`tsh`)** client configured with access to `fin-sql.jumia.local`

### Temporal Access
- Temporal Server address (e.g., `temporal.example.com:7233` or Temporal Cloud endpoint)
- Temporal namespace access
- TLS certificates (if using Temporal Cloud or mTLS)

---

## (Historical) AWS Services Considered

### 3. Amazon Athena / Redshift (No longer used)
- **Athena**: For ad-hoc SQL queries on S3 data
- **Redshift** (optional): For data warehousing and analytics

### Option 2: Self-Hosted Temporal Server

**Best for**: On-premises or custom infrastructure requirements

#### Using Docker Compose

```bash
# Clone Temporal's docker-compose repository
git clone https://github.com/temporalio/docker-compose.git
cd docker-compose

# Start Temporal Server
docker-compose up -d

# Temporal will be available at localhost:7233
# Temporal Web UI at http://localhost:8080
```

#### Using Kubernetes (Helm)

```bash
# Add Temporal Helm repository
helm repo add temporalio https://go.temporal.io/helm-charts
helm repo update

# Install Temporal
helm install temporal temporalio/temporal \
  --namespace temporal \
  --create-namespace \
  --set server.replicaCount=1 \
  --set cassandra.config.cluster_size=1

# Verify installation
kubectl get pods -n temporal
```

---

## Historical Deployment Options (Deprecated)

### Option 1: AWS Lambda (Deprecated)

**Best for**: Production deployments with container orchestration

#### Build Docker Image

```bash
# Build the Temporal Worker image
docker build -t soxauto-worker:latest .

# Tag for your registry
docker tag soxauto-worker:latest registry.example.com/soxauto-worker:latest

# Push to registry
docker push registry.example.com/soxauto-worker:latest
```

#### Run Worker Container

```bash
# Run the Temporal Worker
docker run -d \
  --name soxauto-worker \
  -e TEMPORAL_ADDRESS="temporal.example.com:7233" \
  -e TEMPORAL_NAMESPACE="default" \
  -e CUTOFF_DATE="2024-05-01" \
  -v /path/to/tsh/certs:/root/.tsh \
  registry.example.com/soxauto-worker:latest
```

### Option 2: Amazon ECS (Deprecated)

**Best for**: Scalable, cloud-native deployments

#### Create Kubernetes Deployment

```yaml
# soxauto-worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: soxauto-worker
  namespace: soxauto
spec:
  replicas: 3
  selector:
    matchLabels:
      app: soxauto-worker
  template:
    metadata:
      labels:
        app: soxauto-worker
    spec:
      containers:
      - name: worker
        image: registry.example.com/soxauto-worker:latest
        env:
        - name: TEMPORAL_ADDRESS
          value: "temporal.temporal.svc.cluster.local:7233"
        - name: TEMPORAL_NAMESPACE
          value: "default"
        - name: CUTOFF_DATE
          valueFrom:
            configMapKeyRef:
              name: soxauto-config
              key: cutoff_date
        volumeMounts:
        - name: teleport-certs
          mountPath: /root/.tsh
          readOnly: true
      volumes:
      - name: teleport-certs
        secret:
          secretName: teleport-certs
```

Apply the deployment:

```bash
# Create namespace
kubectl create namespace soxauto

# Apply deployment
kubectl apply -f soxauto-worker-deployment.yaml

# Verify deployment
kubectl get pods -n soxauto
kubectl logs -n soxauto -l app=soxauto-worker
```

### Option 3: Local Development

**Best for**: Development and testing

```bash
# Set environment variables
export TEMPORAL_ADDRESS="localhost:7233"
export TEMPORAL_NAMESPACE="default"
export CUTOFF_DATE="2024-05-01"

# Establish Teleport tunnel
tsh login --proxy=teleport.jumia.com --user=your-username
tsh db connect fin-sql

# Start the Temporal Worker
python -m src.orchestrators.cpg1_worker
```

---

## Configuration

### Environment Variables

Set these environment variables for the Temporal Worker:

```bash
# Temporal Configuration
TEMPORAL_ADDRESS=temporal.example.com:7233  # or localhost:7233 for local dev
TEMPORAL_NAMESPACE=default                   # or your custom namespace
TEMPORAL_TASK_QUEUE=soxauto-tasks           # Task queue name

# Application Configuration
CUTOFF_DATE=2024-05-01                      # Optional: defaults to last day of previous month
LOG_LEVEL=INFO

# Database Configuration (via Teleport)
# Note: Credentials are managed by Teleport - no passwords stored
DB_CONNECTION_STRING="DRIVER={ODBC Driver 17 for SQL Server};SERVER=fin-sql.jumia.local;Trusted_Connection=yes"
```

### Temporal Schedule Configuration

Configure Temporal Schedules for automatic monthly execution:

```python
# Example: Creating a Temporal Schedule via tctl or code
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleIntervalSpec
from datetime import timedelta

async def create_monthly_schedule():
    client = await Client.connect("temporal.example.com:7233")
    
    # Create monthly schedule (1st of each month at 8 AM UTC)
    # Note: cutoff_date would typically be calculated dynamically in the workflow
    await client.create_schedule(
        "soxauto-monthly-extraction",
        Schedule(
            action=ScheduleActionStartWorkflow(
                "IPEExtractionWorkflow",
                args=[None],  # Workflow will calculate cutoff_date dynamically
                id="monthly-extraction",
                task_queue="soxauto-tasks",
            ),
            spec=ScheduleSpec(
                cron_expressions=["0 8 1 * *"],  # 1st of month at 8 AM
            ),
        ),
    )
```

---

## Testing Deployment

### 1. Test Worker Locally

```bash
# Set environment variables
export TEMPORAL_ADDRESS="localhost:7233"
export TEMPORAL_NAMESPACE="default"
export CUTOFF_DATE="2024-05-01"

# Establish Teleport tunnel
tsh login --proxy=teleport.jumia.com --user=your-username
tsh db connect fin-sql

# Start the Temporal Worker
python -m src.orchestrators.cpg1_worker

# In another terminal, trigger a workflow
python -c "
from temporalio.client import Client
import asyncio

async def trigger_workflow():
    client = await Client.connect('localhost:7233')
    result = await client.execute_workflow(
        'IPEExtractionWorkflow',
        args=['2024-05-01'],
        id='test-workflow-1',
        task_queue='soxauto-tasks'
    )
    print(f'Workflow result: {result}')

asyncio.run(trigger_workflow())
"
```

### 2. Verify Worker Health

```bash
# Check worker logs
docker logs soxauto-worker

# Or for Kubernetes
kubectl logs -n soxauto -l app=soxauto-worker --tail=100

# Check Temporal Web UI
# Navigate to http://temporal-web-ui:8080 to see workflows
```

### 3. Monitor Workflow Execution

Access the Temporal Web UI to monitor:
- Active workflows
- Workflow history
- Task queue status
- Worker status

```
http://temporal-web-ui:8080
# Or for Temporal Cloud: https://cloud.temporal.io
```

---

## Monitoring and Logging

### Temporal Web UI

Access the Temporal Web UI for comprehensive monitoring:

```
# Self-hosted Temporal
http://localhost:8080

# Temporal Cloud
https://cloud.temporal.io
```

The Web UI provides:
- Real-time workflow execution status
- Workflow history and event logs
- Task queue metrics
- Worker status and health
- Execution timelines

### Application Logs

View Worker logs:

```bash
# Docker logs
docker logs soxauto-worker --follow

# Kubernetes logs
kubectl logs -n soxauto -l app=soxauto-worker --follow

# Filter for errors
kubectl logs -n soxauto -l app=soxauto-worker | grep ERROR
```

### Temporal Metrics

Temporal exposes Prometheus metrics for monitoring:

```yaml
# Example Prometheus scrape config
scrape_configs:
  - job_name: 'temporal-worker'
    static_configs:
      - targets: ['soxauto-worker:9090']
    metrics_path: '/metrics'
```

Key metrics to monitor:
- `temporal_worker_task_slots_available` - Available worker capacity
- `temporal_activity_execution_failed` - Failed activities
- `temporal_workflow_completed` - Completed workflows
- `temporal_activity_execution_latency` - Activity latency

### Alerting

Set up alerts based on Temporal metrics:

```yaml
# Example Prometheus alert rules
groups:
  - name: soxauto_alerts
    rules:
      - alert: WorkflowExecutionFailed
        expr: increase(temporal_workflow_failed[5m]) > 0
        labels:
          severity: critical
        annotations:
          summary: "SOXauto workflow execution failed"
          description: "Workflow {{ $labels.workflow_type }} failed"
      
      - alert: HighActivityFailureRate
        expr: rate(temporal_activity_execution_failed[10m]) > 0.1
        labels:
          severity: warning
        annotations:
          summary: "High activity failure rate detected"
```

---

## Troubleshooting

### Common Issues

**1. Worker Cannot Connect to Temporal**
- Verify `TEMPORAL_ADDRESS` environment variable
- Check network connectivity to Temporal Server
- Verify mTLS certificates (if using Temporal Cloud)
- Check Temporal namespace exists

**2. Teleport Connection Issues**
- Ensure `tsh login` is executed and session is active
- Verify Teleport tunnel is established: `tsh db ls`
- Check database permissions in Teleport

**3. Activity Timeout**
- Increase `start_to_close_timeout` in activity options
- Check database query performance
- Verify network latency to SQL Server

**4. Worker Not Processing Tasks**
- Verify task queue name matches workflow configuration
- Check worker logs for errors
- Ensure worker has sufficient resources (CPU/memory)

### Debug Worker

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m src.orchestrators.cpg1_worker

# Check Temporal connection
tctl --namespace default workflow list

# Describe a specific workflow
tctl --namespace default workflow describe --workflow_id <workflow-id>

# Query workflow state
tctl --namespace default workflow query \
  --workflow_id <workflow-id> \
  --query_type __stack_trace
```

---

## Cost Considerations

### Temporal Cloud Pricing

**Temporal Cloud** (estimated monthly costs):
- Actions: $0.25 per 1M actions (free tier: 200M actions/month)
- Storage: $0.00042 per GB-hour
- Data transfer: Standard cloud provider rates

**Estimated for SOXauto** (monthly extraction of 10 IPEs):
- Actions: ~1M actions = $0.25 (within free tier)
- Storage: ~10 GB-month = ~$4.20
- **Total**: ~$5-10/month (mostly free tier)

### Self-Hosted Temporal

**Infrastructure costs** (Kubernetes on cloud):
- Temporal Server: 2-4 vCPUs, 8GB RAM = ~$50-100/month
- Database (PostgreSQL/Cassandra): ~$30-50/month
- Workers: 1-2 vCPUs per worker, 2GB RAM = ~$20-40/month per worker
- **Total**: ~$100-190/month

### Cost Optimization Tips

1. Use Temporal Cloud free tier for development/testing
2. Scale workers based on workload (horizontal scaling)
3. Use workflow continue-as-new for long-running workflows
4. Implement efficient activity retry policies
5. Archive old workflow histories periodically


---

## Security Best Practices

1. **mTLS Authentication**: Use mutual TLS for Temporal Cloud connections
2. **Teleport Security**: Leverage Teleport for secure database access (no stored credentials)
3. **Workflow Isolation**: Run workers in isolated containers/pods
4. **Secrets Management**: Use environment variables or secret managers for sensitive config
5. **Audit Logging**: Temporal provides complete workflow execution history
6. **Evidence Integrity**: Digital Evidence Packages use SHA-256 hashing

---

## Next Steps

1. ✅ Set up Temporal Server (Cloud or self-hosted)
2. ✅ Deploy Temporal Workers (Docker, Kubernetes, or local)
3. ✅ Configure Temporal Schedules for monthly execution
4. ✅ Set up monitoring via Temporal Web UI
5. ✅ Run test workflow execution
6. ✅ Verify evidence packages are generated
7. ✅ Document operational procedures

For questions or issues, refer to:
- [Temporal Documentation](https://docs.temporal.io/)
- [Project README](../../README.md)
- [Temporal Web UI](https://docs.temporal.io/web-ui)
