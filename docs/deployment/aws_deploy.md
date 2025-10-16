# AWS Deployment Guide for SOXauto PG-01

This guide provides comprehensive instructions for deploying the SOXauto PG-01 automation system to Amazon Web Services (AWS).

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [AWS Services Required](#aws-services-required)
3. [Setup AWS Infrastructure](#setup-aws-infrastructure)
4. [Deployment Options](#deployment-options)
5. [Configuration](#configuration)
6. [Testing Deployment](#testing-deployment)
7. [Monitoring and Logging](#monitoring-and-logging)

---

## Prerequisites

### Required Tools
- **AWS CLI** v2 or later
- **Docker** (for container builds)
- **Python** 3.11+
- **AWS Account** with appropriate permissions

### AWS IAM Permissions
Ensure your AWS user/role has permissions for:
- AWS Secrets Manager (read)
- Amazon S3 (read/write)
- Amazon Athena or Redshift (query execution)
- Amazon ECS or Lambda (deployment)
- CloudWatch Logs (logging)
- ECR (container registry)

---

## AWS Services Required

### 1. AWS Secrets Manager
Stores sensitive credentials:
- `DB_CREDENTIALS_NAV_BI` - SQL Server connection string
- `ODBC_DRIVER_PATH` - Path to ODBC driver (optional)

### 2. Amazon S3
Storage for:
- **Results bucket**: `jumia-sox-results` - Parquet files with extracted data
- **Evidence bucket**: `jumia-sox-evidence` - SOX compliance evidence packages
- **Athena staging**: Query result staging location

### 3. Amazon Athena / Redshift
- **Athena**: For ad-hoc SQL queries on S3 data
- **Redshift** (optional): For data warehousing and analytics

### 4. Compute Options
Choose one:
- **AWS Lambda**: Serverless, event-driven execution
- **Amazon ECS**: Container orchestration for long-running tasks
- **EC2** (optional): For direct control

---

## Setup AWS Infrastructure

### Step 1: Create S3 Buckets

```bash
# Results bucket
aws s3 mb s3://jumia-sox-results --region eu-west-1

# Evidence bucket
aws s3 mb s3://jumia-sox-evidence --region eu-west-1

# Athena staging bucket
aws s3 mb s3://jumia-sox-athena-staging --region eu-west-1

# Enable versioning on evidence bucket for compliance
aws s3api put-bucket-versioning \
  --bucket jumia-sox-evidence \
  --versioning-configuration Status=Enabled
```

### Step 2: Store Secrets in AWS Secrets Manager

```bash
# Store database connection string
aws secretsmanager create-secret \
  --name DB_CREDENTIALS_NAV_BI \
  --description "SQL Server connection string for NAV BI" \
  --secret-string "DRIVER={ODBC Driver 17 for SQL Server};SERVER=your-server;DATABASE=your-db;UID=your-user;PWD=your-password" \
  --region eu-west-1

# Verify secret
aws secretsmanager get-secret-value \
  --secret-id DB_CREDENTIALS_NAV_BI \
  --region eu-west-1
```

### Step 3: Create Athena Database

```bash
# Create Athena database
aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS jumia_sox_db" \
  --result-configuration "OutputLocation=s3://jumia-sox-athena-staging/" \
  --region eu-west-1
```

### Step 4: Build and Push Docker Image

```bash
# Authenticate with ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.eu-west-1.amazonaws.com

# Create ECR repository
aws ecr create-repository \
  --repository-name soxauto-pg01 \
  --region eu-west-1

# Build Docker image
docker build -t soxauto-pg01:latest .

# Tag image
docker tag soxauto-pg01:latest \
  <account-id>.dkr.ecr.eu-west-1.amazonaws.com/soxauto-pg01:latest

# Push to ECR
docker push <account-id>.dkr.ecr.eu-west-1.amazonaws.com/soxauto-pg01:latest
```

---

## Deployment Options

### Option 1: AWS Lambda (Recommended for Scheduled Tasks)

**Best for**: Scheduled monthly IPE executions with predictable duration < 15 minutes

#### Create Lambda Function

```bash
# Create IAM role for Lambda
aws iam create-role \
  --role-name SOXAutoLambdaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name SOXAutoLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name SOXAutoLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

aws iam attach-role-policy \
  --role-name SOXAutoLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Create Lambda function from container
aws lambda create-function \
  --function-name SOXAuto-PG01 \
  --package-type Image \
  --code ImageUri=<account-id>.dkr.ecr.eu-west-1.amazonaws.com/soxauto-pg01:latest \
  --role arn:aws:iam::<account-id>:role/SOXAutoLambdaRole \
  --timeout 900 \
  --memory-size 2048 \
  --environment Variables="{AWS_REGION=eu-west-1,CUTOFF_DATE=2024-01-01}" \
  --region eu-west-1
```

#### Schedule Lambda Execution

```bash
# Create EventBridge rule for monthly execution
aws events put-rule \
  --name SOXAuto-Monthly-Execution \
  --schedule-expression "cron(0 8 1 * ? *)" \
  --description "Execute SOX PG-01 automation on 1st of each month at 8 AM" \
  --region eu-west-1

# Add Lambda as target
aws events put-targets \
  --rule SOXAuto-Monthly-Execution \
  --targets "Id"="1","Arn"="arn:aws:lambda:eu-west-1:<account-id>:function:SOXAuto-PG01" \
  --region eu-west-1

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name SOXAuto-PG01 \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:eu-west-1:<account-id>:rule/SOXAuto-Monthly-Execution
```

### Option 2: Amazon ECS (For Long-Running Tasks)

**Best for**: IPE executions that may take > 15 minutes or require more resources

#### Create ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name soxauto-cluster \
  --region eu-west-1

# Create task definition
cat > task-definition.json << 'EOF'
{
  "family": "soxauto-pg01-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<account-id>:role/SOXAutoTaskRole",
  "containerDefinitions": [{
    "name": "soxauto-container",
    "image": "<account-id>.dkr.ecr.eu-west-1.amazonaws.com/soxauto-pg01:latest",
    "essential": true,
    "environment": [
      {"name": "AWS_REGION", "value": "eu-west-1"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/soxauto-pg01",
        "awslogs-region": "eu-west-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }]
}
EOF

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region eu-west-1

# Create CloudWatch log group
aws logs create-log-group \
  --log-group-name /ecs/soxauto-pg01 \
  --region eu-west-1
```

#### Run ECS Task

```bash
# Run task manually
aws ecs run-task \
  --cluster soxauto-cluster \
  --task-definition soxauto-pg01-task \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --region eu-west-1

# Or create scheduled ECS task with EventBridge
aws events put-rule \
  --name SOXAuto-ECS-Monthly \
  --schedule-expression "cron(0 8 1 * ? *)" \
  --region eu-west-1

aws events put-targets \
  --rule SOXAuto-ECS-Monthly \
  --targets file://ecs-target.json \
  --region eu-west-1
```

---

## Configuration

### Environment Variables

Set these in Lambda or ECS task definition:

```bash
# AWS Configuration
AWS_REGION=eu-west-1
AWS_DEFAULT_REGION=eu-west-1

# Application Configuration
CUTOFF_DATE=2024-01-01  # Optional: defaults to last day of previous month
LOG_LEVEL=INFO

# S3 Configuration
S3_RESULTS_BUCKET=jumia-sox-results
S3_EVIDENCE_BUCKET=jumia-sox-evidence

# Athena Configuration
ATHENA_DATABASE=jumia_sox_db
ATHENA_OUTPUT_LOCATION=s3://jumia-sox-athena-staging/
```

### Update config.py

Ensure `src/core/config.py` uses AWS environment variables:

```python
# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
S3_RESULTS_BUCKET = os.getenv("S3_RESULTS_BUCKET", "jumia-sox-results")
S3_EVIDENCE_BUCKET = os.getenv("S3_EVIDENCE_BUCKET", "jumia-sox-evidence")
ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "jumia_sox_db")
ATHENA_OUTPUT_LOCATION = os.getenv("ATHENA_OUTPUT_LOCATION", "s3://jumia-sox-athena-staging/")
```

---

## Testing Deployment

### 1. Test Lambda Function Locally

```bash
# Install AWS SAM CLI
pip install aws-sam-cli

# Invoke Lambda function locally
sam local invoke SOXAuto-PG01 \
  --event test-event.json \
  --docker-network host
```

### 2. Test Lambda Function on AWS

```bash
# Invoke Lambda function
aws lambda invoke \
  --function-name SOXAuto-PG01 \
  --payload '{"cutoff_date": "2024-01-01"}' \
  --region eu-west-1 \
  response.json

# View response
cat response.json

# Check CloudWatch logs
aws logs tail /aws/lambda/SOXAuto-PG01 --follow
```

### 3. Verify S3 Results

```bash
# List results
aws s3 ls s3://jumia-sox-results/ --recursive

# Download a result file
aws s3 cp s3://jumia-sox-results/ipe_07/20241001_120000.parquet ./test_result.parquet

# List evidence packages
aws s3 ls s3://jumia-sox-evidence/ --recursive
```

---

## Monitoring and Logging

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/SOXAuto-PG01 --follow --format short

# View ECS logs
aws logs tail /ecs/soxauto-pg01 --follow --format short

# Filter errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/SOXAuto-PG01 \
  --filter-pattern "ERROR"
```

### CloudWatch Metrics

Set up custom metrics:

```python
import boto3

cloudwatch = boto3.client('cloudwatch')
cloudwatch.put_metric_data(
    Namespace='SOXAuto/PG01',
    MetricData=[{
        'MetricName': 'IPEExecutionSuccess',
        'Value': 1,
        'Unit': 'Count'
    }]
)
```

### CloudWatch Alarms

```bash
# Create alarm for execution failures
aws cloudwatch put-metric-alarm \
  --alarm-name SOXAuto-Execution-Failures \
  --alarm-description "Alert on SOX automation failures" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=FunctionName,Value=SOXAuto-PG01 \
  --alarm-actions arn:aws:sns:eu-west-1:<account-id>:sox-alerts
```

### SNS Notifications

```bash
# Create SNS topic for alerts
aws sns create-topic --name sox-alerts --region eu-west-1

# Subscribe email to topic
aws sns subscribe \
  --topic-arn arn:aws:sns:eu-west-1:<account-id>:sox-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

---

## Troubleshooting

### Common Issues

**1. Lambda Timeout**
- Increase timeout in Lambda configuration (max 15 minutes)
- Consider switching to ECS for longer-running tasks

**2. Memory Issues**
- Increase Lambda memory allocation
- Optimize DataFrame processing in code

**3. Secret Manager Access Denied**
- Verify IAM role has `secretsmanager:GetSecretValue` permission
- Check secret ARN and region

**4. S3 Permission Errors**
- Ensure IAM role has S3 read/write permissions
- Verify bucket policy allows access

### Debug Lambda Function

```bash
# Enable detailed logging
aws lambda update-function-configuration \
  --function-name SOXAuto-PG01 \
  --environment Variables="{AWS_REGION=eu-west-1,LOG_LEVEL=DEBUG}"

# View recent errors
aws lambda get-function \
  --function-name SOXAuto-PG01 \
  --query 'Configuration.LastUpdateStatus'
```

---

## Cost Optimization

### Estimated Monthly Costs (EU-WEST-1)

**Lambda Option** (assuming 30-minute monthly execution):
- Lambda compute: ~$0.50
- S3 storage (100GB): ~$2.30
- Secrets Manager: ~$0.40
- Athena queries: ~$5.00 (depends on data scanned)
- **Total**: ~$8-10/month

**ECS Fargate Option**:
- Fargate compute (1 vCPU, 2GB, 30 min): ~$0.50
- S3 storage: ~$2.30
- Secrets Manager: ~$0.40
- **Total**: ~$3-5/month + query costs

### Cost Reduction Tips
1. Use S3 Intelligent-Tiering for old evidence files
2. Compress parquet files with snappy/gzip
3. Use Athena workgroup query result reuse
4. Set S3 lifecycle policies to archive old data to Glacier

---

## Security Best Practices

1. **Least Privilege IAM**: Grant only required permissions
2. **Encryption**: Enable S3 bucket encryption with KMS
3. **VPC**: Run Lambda/ECS in private VPC subnets
4. **Secrets Rotation**: Enable automatic rotation for database credentials
5. **Audit Logs**: Enable CloudTrail for API call auditing
6. **Evidence Integrity**: Use S3 Object Lock for evidence immutability

---

## Next Steps

1. ✅ Complete AWS infrastructure setup
2. ✅ Deploy application to Lambda or ECS
3. ✅ Configure monthly schedule
4. ✅ Set up monitoring and alerts
5. ✅ Run test execution
6. ✅ Verify evidence packages
7. ✅ Document operational procedures

For questions or issues, refer to:
- [AWS Documentation](https://docs.aws.amazon.com/)
- [Project README](../../README.md)
- [AWS Migration Guide](../development/aws_migration.md)
