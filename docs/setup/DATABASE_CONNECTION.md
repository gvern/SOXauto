# Database Connection Configuration

## Overview

The SOXauto system supports two methods for database authentication:

1. **AWS Secrets Manager** (Recommended for production)
2. **Environment Variable** (Fallback for development/testing)

## Connection Fallback Order

The `IPERunner` attempts to connect to the database in the following order:

```
1. DB_CONNECTION_STRING environment variable (if set)
   ↓ (if not found)
2. AWS Secrets Manager (using secret_name from IPE config)
   ↓ (if fails)
3. Raises IPEConnectionError
```

## Method 1: AWS Secrets Manager (Production)

### Prerequisites
- AWS credentials configured
- IAM permissions: `secretsmanager:GetSecretValue`
- Secret stored in Secrets Manager

### Configuration
Each IPE configuration file specifies its secret name:

```json
{
  "ipe_id": "IPE_07",
  "secret_name": "jumia/sox/db-credentials-nav-bi",
  ...
}
```

### Required IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:jumia/sox/*"
    }
  ]
}
```

### Requesting Access
If you receive `AccessDeniedException`, contact your AWS administrator to add the policy above to your role.

## Method 2: Environment Variable (Development)

### When to Use
- **Development environment** without Secrets Manager access
- **Testing** with local databases
- **Troubleshooting** connection issues
- **CI/CD pipelines** with injected secrets

### Setup

#### Option A: Using .env File
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Add your connection string:
   ```bash
   # Database Connection String (fallback if Secrets Manager is not accessible)
   DB_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=your-server.database.windows.net;DATABASE=NAV_BI;UID=sox_user;PWD=your_password;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
   ```

3. Load the environment file:
   ```bash
   source .env  # or use python-dotenv
   ```

#### Option B: Direct Export
```bash
export DB_CONNECTION_STRING="DRIVER={ODBC Driver 18 for SQL Server};SERVER=your-server.database.windows.net;DATABASE=NAV_BI;UID=sox_user;PWD=your_password;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
```

#### Option C: In Test Scripts
```python
import os
os.environ['DB_CONNECTION_STRING'] = "DRIVER={...};SERVER=...;DATABASE=...;"
```

### Connection String Format

#### SQL Server
```
DRIVER={ODBC Driver 18 for SQL Server};SERVER=server.database.windows.net;DATABASE=NAV_BI;UID=username;PWD=password;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
```

#### Azure SQL Database
```
DRIVER={ODBC Driver 18 for SQL Server};SERVER=server.database.windows.net,1433;DATABASE=NAV_BI;UID=username@server;PWD=password;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
```

#### SQL Server with Windows Authentication
```
DRIVER={ODBC Driver 18 for SQL Server};SERVER=server;DATABASE=NAV_BI;Trusted_Connection=yes;
```

### Using an ODBC DSN (macOS/Linux)

You can also configure a DSN in `odbc.ini` and authenticate with a service account:

1. Install ODBC prerequisites (macOS):

```bash
brew install unixodbc
# Install Microsoft ODBC Driver 18 (use official pkg):
# https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server
# Verify driver installation:
odbcinst -q -d | grep -i "ODBC Driver 18"
```

1. Create or update `~/.odbc.ini`:

```ini
[MySqlServer]
Driver = ODBC Driver 18 for SQL Server
Server = your-server.database.windows.net
Database = NAV_BI
Encrypt = yes
TrustServerCertificate = no
```

Optionally, define the driver in `odbcinst.ini` if required by your distro:

```ini
[ODBC Driver 18 for SQL Server]
Description = Microsoft ODBC Driver 18 for SQL Server
Driver = /usr/local/lib/libmsodbcsql.18.dylib
```

1. Export DSN and credentials as environment variables:

```bash
export MSSQL_DSN=MySqlServer
export MSSQL_USER=sox_reader
export MSSQL_PASSWORD=your_password
```

1. Test connectivity:

```bash
python3 scripts/check_mssql_connection.py
```

The script will build a DSN-based connection string automatically when `MSSQL_DSN` is set.

### Security Considerations

⚠️ **IMPORTANT**: Never commit `.env` files or connection strings to version control!

1. Ensure `.env` is in `.gitignore`:
   ```bash
   echo ".env" >> .gitignore
   ```

2. Use restrictive file permissions:
   ```bash
   chmod 600 .env
   ```

3. Rotate credentials regularly

4. Use read-only database accounts for SOX audits

5. Consider using Azure Key Vault or AWS Secrets Manager in production

## Testing Database Connection

### Test Script

```bash
python3 tests/test_database_connection.py
```

### Expected Output

#### With Secrets Manager

```text
✅ Secrets Manager accessible
✅ Database connection successful
```

#### With Environment Variable

```text
ℹ️  Using DB_CONNECTION_STRING from environment variable
✅ Database connection successful
```

#### Access Denied

```text
❌ Secrets Manager access denied
ℹ️  Set DB_CONNECTION_STRING environment variable as fallback
```

## Troubleshooting

### Issue: "AccessDeniedException" from Secrets Manager

**Solution**: Set `DB_CONNECTION_STRING` environment variable as fallback

```bash
export DB_CONNECTION_STRING="DRIVER={...};SERVER=...;DATABASE=...;"
python3 tests/test_single_ipe_extraction.py
```

### Issue: "ODBC Driver not found"

**Solution**: Install the appropriate ODBC driver

**macOS**:

```bash
brew install unixodbc
# Install Microsoft ODBC Driver 18 for SQL Server (use the official pkg installer)
# Download from: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server
# After installation, verify with: odbcinst -q -d | grep -i "ODBC Driver 18"
```

**Ubuntu/Debian**:

```bash
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

**Windows**:
Download from [Microsoft ODBC Driver](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### Issue: "Login failed for user"

**Solutions**:

1. Verify username and password
2. Check if user has database access
3. Verify firewall rules allow connection
4. Check if IP is whitelisted (Azure SQL)
5. Verify connection string format

### Issue: Connection timeout

**Solutions**:

1. Increase `Connection Timeout=30` to higher value
2. Check network connectivity
3. Verify server endpoint is correct
4. Check firewall rules

## Best Practices

### Development

- Use environment variable with read-only database account
- Test locally before deploying
- Document connection requirements

### Staging

- Use Secrets Manager with limited permissions
- Test with production-like data
- Validate connection before IPE runs

### Production

- **Always use Secrets Manager**
- Enable CloudTrail logging for secret access
- Rotate credentials quarterly
- Use IAM roles, not hardcoded credentials
- Monitor failed connection attempts

## Migration Path

### Phase 1: Development (Current)

```bash
export DB_CONNECTION_STRING="..."
python3 tests/test_single_ipe_extraction.py
```

### Phase 2: Request Secrets Manager Access

Contact AWS admin with this policy:

```json
{
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": "arn:aws:secretsmanager:*:*:secret:jumia/sox/*"
}
```

### Phase 3: Production

Remove `DB_CONNECTION_STRING` and rely on Secrets Manager

## Examples

### Running IPE Extraction with Fallback

```bash
# Set all required environment variables
export AWS_PROFILE=007809111365_Data-Prod-DataAnalyst-NonFinance
export AWS_REGION=eu-west-1
export CUTOFF_DATE=2024-12-31
export DB_CONNECTION_STRING="DRIVER={ODBC Driver 18 for SQL Server};SERVER=nav-bi.database.windows.net;DATABASE=NAV_BI;UID=sox_reader;PWD=secure_password;"

# Run extraction
python3 tests/test_single_ipe_extraction.py
```

### Using dotenv in Python

```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access connection string
connection_string = os.getenv('DB_CONNECTION_STRING')
```

## Local Connectivity Check

Run a quick connectivity test:

```bash
python3 scripts/check_mssql_connection.py
```

Expected output on success:

```text
✅ Connection successful
Server version:
Microsoft SQL Server ...
```

If you see an ODBC driver error, ensure msodbcsql18 is installed (see above) and the Driver name matches exactly.

## Teleport / Bastion Access (optional)

If access requires a Teleport/bastion path (e.g., fin-sql.jumia.local), ensure the tunnel is active and use the bastion-resolved hostname in MSSQL_SERVER or DB_CONNECTION_STRING. Coordinate with your infra team for the exact setup.

## Summary

| Method | Use Case | Security | Setup Complexity |
|--------|----------|----------|------------------|
| **Secrets Manager** | Production | ⭐⭐⭐⭐⭐ | Medium |
| **Environment Variable** | Development | ⭐⭐⭐ | Low |

Choose **Secrets Manager** for production environments with proper IAM policies.
Use **Environment Variable** for development when Secrets Manager access is unavailable.

## Related Documentation

- [OKTA_AWS_SETUP.md](OKTA_AWS_SETUP.md) - AWS authentication setup
- [CONNECTION_STATUS.md](CONNECTION_STATUS.md) - Current connection status
- [INTEGRATION_TESTING_PREP.md](../development/INTEGRATION_TESTING_PREP.md) - Testing guide
