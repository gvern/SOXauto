# Okta AWS Authentication Flow

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User / Developer                             │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       │ 1. aws sso login --profile jumia-sox-prod
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AWS CLI v2 (Local Machine)                        │
│  - Opens browser for SSO authentication                              │
│  - Stores temporary token in ~/.aws/sso/cache/                       │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       │ 2. SSO authentication request
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Okta Identity Provider                           │
│  - User authenticates with Okta credentials + MFA                    │
│  - Okta validates user identity                                      │
│  - Returns SAML assertion                                            │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       │ 3. SAML assertion
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│              AWS IAM Identity Center (SSO Service)                   │
│  - Validates SAML assertion                                          │
│  - Assigns IAM role (e.g., SOXAutomationRole)                        │
│  - Returns temporary credentials (1-hour lifetime)                   │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       │ 4. Temporary credentials cached locally
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Python Application                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  from src.utils.okta_aws_auth import OktaAWSAuth            │   │
│  │                                                               │   │
│  │  okta_auth = OktaAWSAuth(profile_name='jumia-sox-prod')     │   │
│  │  session = okta_auth.get_session()                          │   │
│  │                                                               │   │
│  │  # Automatically uses cached credentials                     │   │
│  │  s3_client = session.client('s3')                           │   │
│  │  secrets_client = session.client('secretsmanager')          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       │ 5. AWS API calls with temporary credentials
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Services                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ Secrets Manager  │  │       S3         │  │     Athena       │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Authentication Methods Comparison

### Method 1: Okta SSO (Recommended) ✅

```
Developer → Okta Login → AWS SSO → Temporary Credentials → AWS Services
```

**Advantages:**
- 🔒 Most secure (no long-term credentials)
- 🔄 Automatic credential rotation
- 👥 Centralized access management
- 📊 Full audit trail
- 🛡️ MFA support

**Use Cases:**
- Development workstations
- Manual testing
- Individual developer access

---

### Method 2: IAM Roles (for Production) ✅

```
ECS Task/Lambda → IAM Role → Temporary Credentials → AWS Services
```

**Advantages:**
- ♾️ No manual login required
- 🔄 Automatic credential refresh
- 🎯 Scoped permissions per service

**Use Cases:**
- Lambda functions
- ECS/Fargate tasks
- EC2 instances
- CI/CD pipelines

---

### Method 3: Access Keys (Legacy) ❌ Not Recommended

```
Developer → Long-term Access Keys → AWS Services
```

**Disadvantages:**
- 🚫 Security risk (keys don't expire)
- 📝 Manual rotation required
- 👥 Keys often shared
- 🔍 Poor auditability

**Avoid for:** All use cases (use Okta SSO or IAM roles instead)

---

## Session Lifecycle

```
Day 1, 9:00 AM
├── User runs: aws sso login --profile jumia-sox-prod
├── Browser opens → Okta authentication (username + MFA)
├── Okta returns SAML assertion
├── AWS IAM Identity Center issues temporary credentials
└── Credentials cached locally (~/.aws/sso/cache/)

Day 1, 9:05 AM - 5:00 PM
├── Python scripts use cached credentials
├── Credentials automatically refreshed when needed
└── No re-authentication required

Day 1, 6:00 PM (or after 8-12 hours)
├── SSO session expires
├── Next script run fails with: "Token has expired"
└── User must re-authenticate: aws sso login

Day 2, 9:00 AM
└── Repeat process (new SSO login required)
```

---

## Code Flow

### Without Okta (Old Method)
```python
# ❌ Requires long-term credentials in environment
import boto3

# Uses AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from environment
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='DB_CREDENTIALS_NAV_BI')
```

### With Okta (New Method)
```python
# ✅ Uses temporary credentials from Okta SSO
from src.utils.okta_aws_auth import OktaAWSAuth

# Automatically handles SSO authentication
okta_auth = OktaAWSAuth(profile_name='jumia-sox-prod')
session = okta_auth.get_session()  # Uses cached SSO token

# Create AWS clients with temporary credentials
secrets_client = session.client('secretsmanager')
secret = secrets_client.get_secret_value(SecretId='DB_CREDENTIALS_NAV_BI')
```

### Simplified with Environment Variables
```python
# ✅ Even simpler - reads config from environment
import os
os.environ['USE_OKTA_AUTH'] = 'true'
os.environ['AWS_PROFILE'] = 'jumia-sox-prod'

from src.utils.aws_utils import AWSSecretsManager

# Automatically uses Okta if USE_OKTA_AUTH=true
sm = AWSSecretsManager()
secret = sm.get_secret('DB_CREDENTIALS_NAV_BI')
```

---

## Multi-Environment Setup

```
┌─────────────────────────────────────────────────────────┐
│          ~/.aws/config (on developer machine)           │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  [profile jumia-sox-dev]                                 │
│  sso_start_url = https://company.okta.com/.../dev        │
│  sso_account_id = 111111111111                           │
│  sso_role_name = SOXAutomationDevRole                    │
│                                                           │
│  [profile jumia-sox-staging]                             │
│  sso_start_url = https://company.okta.com/.../staging    │
│  sso_account_id = 222222222222                           │
│  sso_role_name = SOXAutomationStagingRole                │
│                                                           │
│  [profile jumia-sox-prod]                                │
│  sso_start_url = https://company.okta.com/.../prod       │
│  sso_account_id = 333333333333                           │
│  sso_role_name = SOXAutomationProdRole                   │
│                                                           │
└─────────────────────────────────────────────────────────┘

Switch environments by setting AWS_PROFILE:

  Development:  export AWS_PROFILE=jumia-sox-dev
  Staging:      export AWS_PROFILE=jumia-sox-staging
  Production:   export AWS_PROFILE=jumia-sox-prod
```

---

## Error Handling Flow

```
┌─────────────────────────────────────┐
│  Python script calls AWS service    │
└─────────┬───────────────────────────┘
          │
          ▼
    ┌─────────────────┐
    │ Credentials     │
    │ valid?          │
    └─────┬───────────┘
          │
    ┌─────┴─────┐
    │           │
   Yes          No
    │           │
    │           ▼
    │     ┌──────────────────────┐
    │     │ SSO token cached     │
    │     │ and valid?           │
    │     └─────┬────────────────┘
    │           │
    │     ┌─────┴─────┐
    │     │           │
    │    Yes          No
    │     │           │
    │     │           ▼
    │     │     ┌────────────────────────┐
    │     │     │ Error: Token expired   │
    │     │     │ Action: Run SSO login  │
    │     │     └────────────────────────┘
    │     │
    │     ▼
    │  ┌─────────────────────────┐
    │  │ Get temp credentials    │
    │  │ from SSO cache          │
    │  └─────┬───────────────────┘
    │        │
    ▼        ▼
┌──────────────────────────┐
│  Make AWS API call       │
└──────────────────────────┘
```

---

## Security Comparison

### Before (Manual Credentials)
```
Developer's Machine
├── ~/.aws/credentials
│   ├── aws_access_key_id = AKIAIOSFODNN7EXAMPLE      ← Never expires
│   └── aws_secret_access_key = wJalrXUtnFEMI/...     ← Stored in plaintext
└── Risk: Credentials can be:
    ├── Accidentally committed to git
    ├── Shared between developers
    ├── Stolen if machine compromised
    └── Used indefinitely if not rotated
```

### After (Okta SSO)
```
Developer's Machine
├── ~/.aws/sso/cache/
│   └── abc123.json
│       ├── accessToken (expires in 1 hour)           ← Temporary
│       └── expiresAt: "2024-10-16T18:00:00Z"        ← Auto-expires
└── Benefits:
    ├── Credentials expire automatically
    ├── Cannot be shared (tied to Okta user)
    ├── Revokable via Okta admin console
    ├── MFA enforced
    └── Full audit trail in Okta
```

---

## Quick Reference

| Task | Command/Code |
|------|--------------|
| **Initial Setup** | `python3 scripts/setup_okta_profile.py` |
| **Login** | `aws sso login --profile jumia-sox-prod` |
| **Verify** | `aws sts get-caller-identity` |
| **Logout** | `aws sso logout` |
| **Check Session** | `ls -la ~/.aws/sso/cache/` |
| **Python Usage** | `OktaAWSAuth(profile_name='jumia-sox-prod')` |
| **Test** | `python3 tests/test_okta_auth.py` |

---

## Best Practices

### ✅ DO
1. Use Okta SSO for all local development
2. Use IAM roles for production deployments
3. Enable MFA on your Okta account
4. Keep AWS CLI updated to latest v2
5. Log out when done: `aws sso logout`

### ❌ DON'T
1. Share SSO tokens or credentials
2. Commit `.aws/credentials` to git
3. Use long-term access keys
4. Bypass Okta authentication
5. Store credentials in code or config files

---

For more details, see:
- Setup Guide: [OKTA_AWS_SETUP.md](OKTA_AWS_SETUP.md)
- Quick Reference: [OKTA_QUICK_REFERENCE.md](OKTA_QUICK_REFERENCE.md)
