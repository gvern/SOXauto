# AWS Okta Authentication - Quick Reference

## Initial Setup (One-time)

### 1. Install AWS CLI v2
```bash
# macOS
brew install awscli

# Verify
aws --version  # Should show v2.x.x
```

### 2. Configure Profile
```bash
# Interactive setup
python3 scripts/setup_okta_profile.py

# Or manually edit ~/.aws/config
```

### 3. First Login
```bash
aws sso login --profile jumia-sox-prod
```

---

## Daily Usage

### Login
```bash
# When session expires (typically every 8-12 hours)
aws sso login --profile jumia-sox-prod
```

### Set Environment
```bash
export AWS_PROFILE=jumia-sox-prod
export USE_OKTA_AUTH=true
```

### Verify Connection
```bash
# Check AWS identity
aws sts get-caller-identity --profile jumia-sox-prod

# Test database connection
python3 tests/test_database_connection.py

# Test Okta auth
python3 tests/test_okta_auth.py
```

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `aws: command not found` | Install AWS CLI v2 |
| `Token has expired` | Run `aws sso login --profile <profile>` |
| `Unable to locate credentials` | Check `$AWS_PROFILE` and run login |
| `Access Denied` | Verify IAM permissions with admin |

---

## File Locations

- **AWS Config**: `~/.aws/config`
- **SSO Cache**: `~/.aws/sso/cache/`
- **Project .env**: `.env` (copy from `.env.example`)

---

## Common Commands

```bash
# Login
aws sso login --profile jumia-sox-prod

# Logout
aws sso logout

# Check identity
aws sts get-caller-identity

# List S3 buckets
aws s3 ls --profile jumia-sox-prod

# Get secret
aws secretsmanager get-secret-value \
  --secret-id DB_CREDENTIALS_NAV_BI \
  --profile jumia-sox-prod
```

---

## Multiple Environments

```bash
# Dev
export AWS_PROFILE=jumia-sox-dev

# Staging
export AWS_PROFILE=jumia-sox-staging

# Production
export AWS_PROFILE=jumia-sox-prod
```

---

## Python Usage

```python
# Automatic (reads from environment)
from src.utils.aws_utils import AWSSecretsManager

sm = AWSSecretsManager(use_okta=True)
secret = sm.get_secret("DB_CREDENTIALS_NAV_BI")

# Explicit profile
sm = AWSSecretsManager(
    use_okta=True,
    profile_name='jumia-sox-prod'
)
```

---

## Session Duration

- **SSO Session**: 8-12 hours (depends on org settings)
- **Temp Credentials**: 1 hour (auto-refreshed when possible)
- **Re-login**: Run `aws sso login` when expired

---

## Security Reminders

✅ **DO:**
- Use Okta SSO for all AWS access
- Keep AWS CLI updated
- Enable MFA on Okta

❌ **DON'T:**
- Share SSO sessions or credentials
- Commit `.aws/credentials` to git
- Use long-term access keys

---

## Getting Help

📖 Full Guide: [docs/setup/OKTA_AWS_SETUP.md](OKTA_AWS_SETUP.md)
🧪 Test Script: `python3 tests/test_okta_auth.py`
🔧 Setup Script: `python3 scripts/setup_okta_profile.py`
