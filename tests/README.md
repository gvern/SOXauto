# Tests Directory

This directory contains integration and unit tests for the SOXauto PG-01 application.

## Test Files

### `test_database_connection.py`
Tests database connectivity and basic query execution.

**Tests:**
- GCP Secret Manager access
- Database connection establishment
- Parameterized query execution

**Run:**
```bash
export GCP_PROJECT_ID="your-project-id"
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
export GCP_PROJECT_ID="your-project-id"
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
   export GCP_PROJECT_ID="your-gcp-project-id"
   export CUTOFF_DATE="2024-01-01"  # Optional
   ```

2. **Authenticate with GCP:**
   ```bash
   gcloud auth application-default login
   gcloud config set project $GCP_PROJECT_ID
   ```

3. **Verify database credentials are in Secret Manager:**
   ```bash
   gcloud secrets list --project=$GCP_PROJECT_ID | grep DB_CREDENTIALS
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

**Issue**: `GCP_PROJECT_ID not set`
```bash
export GCP_PROJECT_ID="your-actual-project-id"
```

**Issue**: `Secret not found`
```bash
# Verify secret exists
gcloud secrets list --project=$GCP_PROJECT_ID | grep DB_CREDENTIALS

# Check permissions
gcloud secrets get-iam-policy DB_CREDENTIALS_NAV_BI --project=$GCP_PROJECT_ID
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
    GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
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
