# Tests Directory

This directory contains integration and unit tests for the SOXauto PG-01 application.

## Test Files

### `test_database_connection.py`
Tests database connectivity and basic query execution.

**Tests:**
- AWS Secrets Manager access
- Database connection establishment
- Parameterized query execution

**Run:**
```bash
export AWS_REGION="eu-west-1"
python3 tests/test_database_connection.py
```

### `test_single_ipe_extraction.py`
Tests complete IPE extraction flow with validation and evidence generation.

**Tests:**
- IPE configuration loading
- Component initialization
- Full IPE extraction
- SOX validation (completeness, accuracy)
- Evidence package generation

**Run:**
```bash
export AWS_REGION="eu-west-1"
export CUTOFF_DATE="2024-01-01"  # Optional

# Test default IPE (IPE_07)
python3 tests/test_single_ipe_extraction.py

# Test specific IPE
TEST_IPE_ID="CR_03_04" python3 tests/test_single_ipe_extraction.py
```

## Prerequisites

Before running tests:

1. **Set environment variables:**
   ```bash
   export AWS_REGION="eu-west-1"
   export CUTOFF_DATE="2024-01-01"  # Optional
   ```

2. **Configure AWS credentials:**
   ```bash
   aws configure
   # Or use environment variables:
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   ```

3. **Verify database credentials are in Secrets Manager:**
   ```bash
   aws secretsmanager list-secrets --region eu-west-1 | grep DB_CREDENTIALS
   ```

## Test Execution Order

Follow this order for integration testing:

1. **Configuration Validation** (no database required):
   ```bash
   python3 scripts/validate_ipe_config.py
   ```

2. **Database Connection Test**:
   ```bash
   python3 tests/test_database_connection.py
   ```

3. **Single IPE Extraction Test**:
   ```bash
   python3 tests/test_single_ipe_extraction.py
   ```

## Expected Results

### ✅ Success Indicators
- All connection tests pass
- IPE extraction completes in < 5 minutes
- All 3 validations pass (completeness, accuracy +/-)
- Evidence package generated with 7 files
- Data integrity hash calculated

### ❌ Failure Indicators
- Connection timeout
- SQL errors
- Validation failures
- Missing evidence files

## Troubleshooting

### Common Issues

**Issue**: `AWS_REGION not set`
```bash
export AWS_REGION="eu-west-1"
```

**Issue**: `Secret not found`
```bash
# Verify secret exists
aws secretsmanager list-secrets --region eu-west-1 | grep DB_CREDENTIALS

# Check permissions
aws secretsmanager describe-secret --secret-id DB_CREDENTIALS_NAV_BI --region eu-west-1
```

**Issue**: `Connection refused`
- Check if database server is accessible
- Verify firewall rules
- Confirm VPN connection if required

**Issue**: `Validation failed`
- Check if witness data exists for test date
- Verify database schema matches queries
- Review validation query logic

## Adding New Tests

When adding new test files:

1. Use descriptive filenames: `test_<feature>_<aspect>.py`
2. Include comprehensive docstrings
3. Add error handling and clear error messages
4. Update this README with new test description
5. Make tests executable: `chmod +x tests/test_*.py`

## Test Data

Test data requirements:
- Customer Ledger Entries with dates before cutoff date
- Witness transactions for accuracy positive tests
- Excluded transactions for accuracy negative tests

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Integration Tests
  env:
    AWS_REGION: ${{ secrets.AWS_REGION }}
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    CUTOFF_DATE: "2024-01-01"
  run: |
    python3 scripts/validate_ipe_config.py
    python3 tests/test_database_connection.py
    python3 tests/test_single_ipe_extraction.py
```

## Related Documentation

- **Integration Testing Prep**: `docs/development/INTEGRATION_TESTING_PREP.md`
- **Testing Guide**: `docs/development/TESTING_GUIDE.md`
- **Security Audit**: `docs/development/SECURITY_FIXES.md`

## Support

For issues or questions:
1. Review the full documentation in `docs/`
2. Check the troubleshooting section above
3. Consult the integration testing preparation guide
