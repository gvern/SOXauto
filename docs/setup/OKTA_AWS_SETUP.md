# AWS Okta SSO Configuration Guide

## Overview
This guide explains how to configure AWS authentication using Okta SSO for the SOXauto PG-01 project. Okta SSO provides secure, centralized authentication without storing long-term credentials.

---

## Prerequisites

### 1. AWS CLI v2
You **must** have AWS CLI version 2 or later installed. AWS CLI v1 does not support SSO.

Check your version:
```bash
aws --version
```

If you need to install or upgrade:
- **macOS**: 
  ```bash
  brew install awscli
  # or download from https://aws.amazon.com/cli/
  ```
- **Windows**: Download installer from https://aws.amazon.com/cli/
- **Linux**: Follow instructions at https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

### 2. Required Information
Get the following information from your AWS administrator:

- **Okta SSO Start URL**: Your organization's Okta portal URL (e.g., `https://mycompany.okta.com/app/amazon_aws/...`)
- **AWS SSO Region**: Usually `eu-west-1` or `us-east-1`
- **AWS Account ID**: Your AWS account number (12 digits)
- **IAM Role Name**: The role you'll assume (e.g., `SOXAutomationRole`, `DataEngineerRole`)

---

## Configuration Methods

### Method 1: Automated Setup (Recommended)

Run the provided setup script:

```bash
python3 scripts/setup_okta_profile.py
```

The script will prompt you for:
1. Profile name (e.g., `jumia-sox-prod`)
2. Okta SSO start URL
3. SSO region
4. AWS account ID
5. IAM role name

### Method 2: Manual Configuration

#### Step 1: Configure AWS SSO Profile

Edit `~/.aws/config` and add your profile:

```ini
[profile jumia-sox-prod]
sso_start_url = https://yourcompany.okta.com/app/amazon_aws/xxxxx
sso_region = eu-west-1
sso_account_id = 123456789012
sso_role_name = SOXAutomationRole
region = eu-west-1
output = json
```

#### Step 2: Login to Okta SSO

```bash
aws sso login --profile jumia-sox-prod
```

This will:
1. Open your browser
2. Prompt you to authenticate with Okta
3. Cache temporary credentials locally

---

## Environment Configuration

### Option A: Use Environment Variables

Create a `.env` file in your project root:

```bash
# AWS Okta Configuration
USE_OKTA_AUTH=true
AWS_PROFILE=jumia-sox-prod
AWS_REGION=eu-west-1

# Database Configuration
CUTOFF_DATE=2024-12-31
```

Load environment variables:
```bash
# Using direnv (recommended)
echo "dotenv" > .envrc
direnv allow

# Or export manually
export $(cat .env | xargs)
```

### Option B: Update config.py

Modify `src/core/config.py`:

```python
# AWS Okta Configuration
USE_OKTA_AUTH = os.getenv("USE_OKTA_AUTH", "true").lower() == "true"
AWS_PROFILE = os.getenv("AWS_PROFILE", "jumia-sox-prod")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
```

---

## Usage Examples

### 1. Using AWS Secrets Manager with Okta

```python
from src.utils.aws_utils import AWSSecretsManager

# Automatic Okta authentication (reads from environment)
sm = AWSSecretsManager(
    region_name='eu-west-1',
    use_okta=True,
    profile_name='jumia-sox-prod'
)

# Retrieve secret
conn_str = sm.get_secret("DB_CREDENTIALS_NAV_BI")
```

### 2. Using S3 with Okta

```python
from src.utils.aws_utils import AWSS3Manager
import pandas as pd

# Initialize with Okta
s3 = AWSS3Manager(
    region_name='eu-west-1',
    use_okta=True,
    profile_name='jumia-sox-prod'
)

# Upload DataFrame
df = pd.DataFrame({'col1': [1, 2, 3]})
s3.upload_dataframe_as_parquet(df, 'jumia-sox-data-lake', 'outputs/test.parquet')
```

### 3. Using Athena with Okta

```python
from src.utils.aws_utils import AWSAthena

# Initialize with Okta
athena = AWSAthena(
    region_name='eu-west-1',
    s3_output_location='s3://jumia-sox-data-lake/athena-results/',
    use_okta=True,
    profile_name='jumia-sox-prod'
)

# Execute query
df = athena.query_to_dataframe(
    query="SELECT * FROM sox_data LIMIT 10",
    database='jumia_sox_db'
)
```

### 4. Direct Okta Authentication

```python
from src.utils.okta_aws_auth import OktaAWSAuth

# Initialize
okta_auth = OktaAWSAuth(
    profile_name='jumia-sox-prod',
    region_name='eu-west-1'
)

# Get authenticated session
session = okta_auth.get_session()

# Use session to create any AWS client
s3_client = session.client('s3')
secrets_client = session.client('secretsmanager')
```

---

## Testing the Configuration

### Test 1: SSO Login
```bash
aws sso login --profile jumia-sox-prod
```

Expected: Browser opens, you authenticate via Okta, success message appears.

### Test 2: Verify Credentials
```bash
aws sts get-caller-identity --profile jumia-sox-prod
```

Expected output:
```json
{
    "UserId": "AROAXXXXXXXXX:user@company.com",
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/SOXAutomationRole/user@company.com"
}
```

### Test 3: Database Connection
```bash
python3 tests/test_database_connection.py
```

Expected: Successful connection to AWS Secrets Manager and database.

### Test 4: Python Okta Auth
```bash
python3 tests/test_okta_auth.py
```

---

## Troubleshooting

### Issue: "aws: command not found"
**Solution**: Install AWS CLI v2 (see Prerequisites)

### Issue: "aws sso login requires AWS CLI v2"
**Solution**: Upgrade to AWS CLI v2

### Issue: "Error loading SSO Token: Token has expired"
**Solution**: Re-authenticate
```bash
aws sso login --profile jumia-sox-prod
```

### Issue: "Unable to locate credentials"
**Solution**: 
1. Check profile name matches in config file
2. Verify you've run `aws sso login`
3. Check environment variables:
   ```bash
   echo $AWS_PROFILE
   echo $USE_OKTA_AUTH
   ```

### Issue: "Access Denied" errors
**Solution**: 
1. Verify your IAM role has necessary permissions
2. Contact AWS administrator to grant access
3. Check you're using the correct AWS account ID

### Issue: Session expires during long-running jobs
**Solution**: 
- SSO sessions typically last 8-12 hours
- Re-run `aws sso login` before long jobs
- Consider using AWS Session Manager for extended sessions

---

## Security Best Practices

### ✅ DO:
- Use Okta SSO for all AWS access
- Keep AWS CLI up to date
- Use separate profiles for dev/staging/prod
- Regularly rotate credentials
- Enable MFA on your Okta account

### ❌ DON'T:
- Store long-term AWS credentials in code or config files
- Share AWS credentials or SSO profiles
- Commit `.aws/credentials` or `.env` files to git
- Use root account credentials
- Bypass Okta authentication

---

## Multiple Environments

Configure multiple profiles for different environments:

```ini
# ~/.aws/config

[profile jumia-sox-dev]
sso_start_url = https://company.okta.com/app/amazon_aws/dev
sso_region = eu-west-1
sso_account_id = 111111111111
sso_role_name = SOXAutomationDevRole
region = eu-west-1

[profile jumia-sox-staging]
sso_start_url = https://company.okta.com/app/amazon_aws/staging
sso_region = eu-west-1
sso_account_id = 222222222222
sso_role_name = SOXAutomationStagingRole
region = eu-west-1

[profile jumia-sox-prod]
sso_start_url = https://company.okta.com/app/amazon_aws/prod
sso_region = eu-west-1
sso_account_id = 333333333333
sso_role_name = SOXAutomationProdRole
region = eu-west-1
```

Switch between environments:
```bash
export AWS_PROFILE=jumia-sox-dev
# or
export AWS_PROFILE=jumia-sox-prod
```

---

## Credential Lifecycle

### Session Duration
- **Okta SSO sessions**: Typically 8-12 hours
- **Temporary credentials**: 1 hour by default
- Credentials are automatically refreshed when possible

### Re-authentication
When credentials expire:
```bash
aws sso login --profile jumia-sox-prod
```

### Logout
```bash
aws sso logout
```

---

## CI/CD Integration

For automated deployments, use:

1. **GitHub Actions**: Use OIDC provider (recommended)
   ```yaml
   - uses: aws-actions/configure-aws-credentials@v2
     with:
       role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
       aws-region: eu-west-1
   ```

2. **AWS Lambda**: Use IAM roles for Lambda execution
3. **ECS/Fargate**: Use IAM roles for tasks

**Never** use Okta SSO credentials in automated systems.

---

## Getting Help

- **AWS CLI Issues**: https://docs.aws.amazon.com/cli/latest/userguide/
- **Okta Support**: Contact your IT administrator
- **Project Issues**: Create a ticket or contact the SOXauto team

---

## Quick Reference

```bash
# Login
aws sso login --profile jumia-sox-prod

# Verify
aws sts get-caller-identity --profile jumia-sox-prod

# Use in Python
export USE_OKTA_AUTH=true
export AWS_PROFILE=jumia-sox-prod

# Run tests
python3 tests/test_database_connection.py

# Logout
aws sso logout
```
