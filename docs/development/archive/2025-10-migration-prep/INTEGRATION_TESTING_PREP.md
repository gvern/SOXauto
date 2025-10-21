# Integration Testing Preparation Guide

**Status**: 🚧 Ready for Database Integration Testing  
**Last Updated**: October 16, 2024  
**Phase**: Post-Security-Hardening Validation

---

## 📋 Prerequisites Checklist

### ✅ Completed
- [x] All SQL injection vulnerabilities eliminated
- [x] Configuration validation tool created (15/15 tests passing)
- [x] Documentation complete (README, SECURITY_FIXES, TESTING_GUIDE)
- [x] Key docstrings standardized to English
- [x] .gitignore updated for Python development
- [x] Changes committed to git

### 🔲 Required for Integration Testing
- [ ] Access to development/staging database
- [ ] GCP_PROJECT_ID environment variable configured
- [ ] Database credentials in GCP Secret Manager
- [ ] Google Cloud SDK installed and authenticated
- [ ] Service account with appropriate permissions
- [ ] Test data verified in database for cutoff date

---

## 🎯 Testing Phases

### Phase 1: Environment Setup (15 minutes)

#### 1.1 Verify GCP Authentication
```bash
# Check current GCP configuration
gcloud config list

# Verify project is set correctly
gcloud config get-value project

# Test authentication
gcloud auth application-default print-access-token
```

**Expected Result**: Valid access token returned

#### 1.2 Configure Environment Variables
```bash
# Set required environment variables
export GCP_PROJECT_ID="your-gcp-project-id"
export GCP_REGION="europe-west1"
export CUTOFF_DATE="2024-01-01"  # Use date with known test data

# Verify variables are set
echo "GCP_PROJECT_ID: $GCP_PROJECT_ID"
echo "CUTOFF_DATE: $CUTOFF_DATE"
```

#### 1.3 Verify Secret Manager Access
```bash
# Test secret access
gcloud secrets versions access latest \
  --secret="DB_CREDENTIALS_NAV_BI" \
  --project="$GCP_PROJECT_ID"
```

**Expected Result**: Connection string returned (verify format but keep it secure)

---

### Phase 2: Configuration Validation (5 minutes)

```bash
# Run automated configuration validator
python3 scripts/validate_ipe_config.py
```

**Expected Output:**
```
======================================================================
IPE CONFIGURATION VALIDATION
======================================================================

🔍 Checking Environment Configuration...
✅ GCP_PROJECT_ID: Using os.getenv() for environment variable

Validating IPE: IPE_07
----------------------------------------------------------------------
✅ Required fields: All present
✅ Main query: Secure (uses ? placeholders)
✅ Completeness query: Secure CTE pattern
✅ Accuracy_positive query: Secure CTE pattern
✅ Accuracy_negative query: Secure CTE pattern

Validating IPE: CR_03_04
----------------------------------------------------------------------
✅ Required fields: All present
✅ Main query: Secure (uses ? placeholders)
✅ Completeness query: Secure CTE pattern
✅ Accuracy_positive query: Secure CTE pattern
✅ Accuracy_negative query: Secure CTE pattern

Validating IPE: IPE_TEMPLATE
----------------------------------------------------------------------
✅ Required fields: All present
✅ Main query: Secure (uses ? placeholders)
✅ Completeness query: Secure CTE pattern
✅ Accuracy_positive query: Secure CTE pattern

======================================================================
VALIDATION SUMMARY
======================================================================

Tests Run: 15
Passed: 15
Failed: 0
Warnings: 0

✅ ALL CHECKS PASSED - Configuration is secure!
======================================================================
```

**Action**: ✅ If all tests pass, proceed to Phase 3. ❌ If any tests fail, fix issues before continuing.

---

### Phase 3: Database Connection Test (10 minutes)

Create test file: `tests/test_database_connection.py`

```python
#!/usr/bin/env python3
"""
Test database connectivity and basic query execution.
"""
import os
import sys
import pyodbc

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.gcp_utils import GCPSecretManager
from src.core.config import GCP_PROJECT_ID

def test_secret_manager():
    """Test Secret Manager access."""
    print("\n🔍 Testing Secret Manager Access...")
    print("-" * 70)
    
    try:
        sm = GCPSecretManager(GCP_PROJECT_ID)
        conn_str = sm.get_secret("DB_CREDENTIALS_NAV_BI")
        print(f"✅ Secret retrieved successfully")
        print(f"   Connection string format: {conn_str[:20]}...")
        return conn_str
    except Exception as e:
        print(f"❌ Secret Manager error: {e}")
        return None

def test_database_connection(conn_str):
    """Test database connection."""
    print("\n🔍 Testing Database Connection...")
    print("-" * 70)
    
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        print("✅ Database connection successful")
        
        # Test simple query
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"   SQL Server version: {version[:50]}...")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_parameterized_query(conn_str):
    """Test parameterized query execution."""
    print("\n🔍 Testing Parameterized Query Execution...")
    print("-" * 70)
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Test query with parameter (adjust table name based on your schema)
        test_query = """
            SELECT COUNT(*) as record_count
            FROM [dbo].[Customer Ledger Entries]
            WHERE [Posting Date] < ?
        """
        
        cutoff_date = os.getenv("CUTOFF_DATE", "2024-01-01")
        cursor.execute(test_query, (cutoff_date,))
        result = cursor.fetchone()
        
        print(f"✅ Parameterized query executed successfully")
        print(f"   Records found (before {cutoff_date}): {result[0]:,}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Parameterized query error: {e}")
        return False

def main():
    """Run all connection tests."""
    print("=" * 70)
    print("DATABASE CONNECTION TESTING")
    print("=" * 70)
    
    # Check environment
    if not os.getenv("GCP_PROJECT_ID"):
        print("❌ GCP_PROJECT_ID environment variable not set")
        return False
    
    # Test sequence
    conn_str = test_secret_manager()
    if not conn_str:
        return False
    
    if not test_database_connection(conn_str):
        return False
    
    if not test_parameterized_query(conn_str):
        return False
    
    print("\n" + "=" * 70)
    print("✅ ALL CONNECTION TESTS PASSED")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

**Run the test:**
```bash
python3 tests/test_database_connection.py
```

**Expected Outcome**: All 3 tests pass (Secret Manager, Connection, Parameterized Query)

---

### Phase 4: Single IPE Extraction Test (30 minutes)

Create test file: `tests/test_single_ipe_extraction.py`

```python
#!/usr/bin/env python3
"""
Test complete IPE extraction flow with a single IPE.
"""
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.ipe_runner import IPERunner
from src.core.config import IPE_CONFIGS, GCP_PROJECT_ID
from src.utils.gcp_utils import GCPSecretManager
from src.core.evidence_manager import DigitalEvidenceManager

def test_ipe_extraction(ipe_id="IPE_07", cutoff_date=None):
    """
    Test complete IPE extraction with validation and evidence generation.
    
    Args:
        ipe_id: IPE to test (default: IPE_07)
        cutoff_date: Cutoff date for extraction (default: 2024-01-01)
    """
    print("=" * 70)
    print(f"SINGLE IPE EXTRACTION TEST: {ipe_id}")
    print("=" * 70)
    
    # Get IPE config
    try:
        ipe_config = next(c for c in IPE_CONFIGS if c['id'] == ipe_id)
        print(f"\n✅ IPE Configuration loaded: {ipe_config['description']}")
    except StopIteration:
        print(f"\n❌ IPE '{ipe_id}' not found in configuration")
        return False
    
    # Setup
    cutoff_date = cutoff_date or os.getenv("CUTOFF_DATE", "2024-01-01")
    print(f"   Cutoff date: {cutoff_date}")
    
    # Initialize components
    print("\n🔍 Initializing components...")
    try:
        secret_manager = GCPSecretManager(GCP_PROJECT_ID)
        evidence_manager = DigitalEvidenceManager()
        print("✅ Components initialized")
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False
    
    # Create IPE runner
    print("\n🔍 Creating IPE runner...")
    try:
        runner = IPERunner(
            ipe_config=ipe_config,
            secret_manager=secret_manager,
            cutoff_date=cutoff_date,
            evidence_manager=evidence_manager
        )
        print("✅ IPE runner created")
    except Exception as e:
        print(f"❌ Runner creation error: {e}")
        return False
    
    # Execute IPE
    print("\n🚀 Executing IPE extraction...")
    print("-" * 70)
    start_time = datetime.now()
    
    try:
        df = runner.run()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print("✅ IPE EXTRACTION SUCCESSFUL")
        print("=" * 70)
        print(f"Execution time: {elapsed:.2f} seconds")
        print(f"Records extracted: {len(df):,}")
        print(f"Columns: {len(df.columns)}")
        
        # Validation summary
        print("\n📊 Validation Results:")
        validation = runner.validation_results
        
        if 'completeness' in validation:
            comp = validation['completeness']
            print(f"   Completeness: {comp['status']}")
            print(f"     Expected: {comp.get('expected_count', 'N/A')}")
            print(f"     Actual: {comp.get('actual_count', 'N/A')}")
        
        if 'accuracy_positive' in validation:
            acc_pos = validation['accuracy_positive']
            print(f"   Accuracy Positive: {acc_pos['status']}")
            print(f"     Witness count: {acc_pos.get('witness_count', 'N/A')}")
        
        if 'accuracy_negative' in validation:
            acc_neg = validation['accuracy_negative']
            print(f"   Accuracy Negative: {acc_neg['status']}")
            print(f"     Excluded count: {acc_neg.get('excluded_count', 'N/A')}")
        
        # Evidence package
        if 'data_integrity_hash' in validation:
            hash_value = validation['data_integrity_hash']
            print(f"\n🔐 Data Integrity Hash: {hash_value[:16]}...")
        
        print("\n✅ All validations passed")
        return True
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("❌ IPE EXTRACTION FAILED")
        print("=" * 70)
        print(f"Execution time: {elapsed:.2f} seconds")
        print(f"Error: {e}")
        
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False

def main():
    """Run single IPE extraction test."""
    # Check environment
    if not os.getenv("GCP_PROJECT_ID"):
        print("❌ GCP_PROJECT_ID environment variable not set")
        return False
    
    # Test IPE_07 (or specify different IPE)
    ipe_to_test = os.getenv("TEST_IPE_ID", "IPE_07")
    success = test_ipe_extraction(ipe_id=ipe_to_test)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

**Run the test:**
```bash
# Test IPE_07 (default)
python3 tests/test_single_ipe_extraction.py

# Or test specific IPE
TEST_IPE_ID="CR_03_04" python3 tests/test_single_ipe_extraction.py
```

**Expected Outcome**: 
- ✅ IPE extraction completes in 2-5 minutes
- ✅ All 3 validations pass (completeness, accuracy positive, accuracy negative)
- ✅ Evidence package generated with integrity hash
- ✅ Data extracted and saved

---

### Phase 5: Evidence Package Verification (10 minutes)

```bash
# Find the most recent evidence package
ls -lth /tmp/evidence/*/

# Example: Inspect evidence package
cd /tmp/evidence/IPE_07/[timestamp]

# Check files in evidence package
ls -la

# Expected files:
# 01_executed_query.sql
# 02_query_parameters.json
# 03_data_snapshot.csv
# 04_data_summary.json
# 05_integrity_hash.json
# 06_validation_results.json
# 07_execution_log.json

# Verify integrity hash
cat 05_integrity_hash.json | python3 -m json.tool

# Check validation results
cat 06_validation_results.json | python3 -m json.tool
```

**Expected Result**: All 7 evidence files present with correct structure

---

## 🚨 Troubleshooting

### Issue: "GCP_PROJECT_ID not set"
**Solution:**
```bash
export GCP_PROJECT_ID="your-actual-project-id"
```

### Issue: "Secret not found"
**Solution:**
```bash
# Verify secret exists
gcloud secrets list --project="$GCP_PROJECT_ID" | grep DB_CREDENTIALS

# Check permissions
gcloud secrets get-iam-policy DB_CREDENTIALS_NAV_BI \
  --project="$GCP_PROJECT_ID"
```

### Issue: "Connection timeout"
**Solution:**
```bash
# Check if database server is accessible
# Test network connectivity
ping your-database-server

# Check firewall rules
gcloud compute firewall-rules list --project="$GCP_PROJECT_ID"
```

### Issue: "Validation failed"
**Solution:**
1. Check if witness data exists for the test date range
2. Verify database schema matches query expectations
3. Review validation query logic in `src/core/config.py`
4. Check execution logs in evidence package

### Issue: "No module named 'src'"
**Solution:**
```bash
# Ensure you're running from project root
cd /path/to/PG-01

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## 📊 Success Criteria

### ✅ Integration Testing Complete When:
1. Configuration validation passes (15/15 tests)
2. Database connection successful
3. Parameterized queries execute correctly
4. At least one full IPE extraction completes successfully
5. All 3 validation types pass (completeness, accuracy +/-)
6. Evidence package generated with all 7 files
7. Data integrity hash calculated and verified
8. No SQL injection vulnerabilities detected
9. Execution time within acceptable range (< 5 minutes for single IPE)

---

## 🎯 Next Steps After Integration Testing

### If All Tests Pass ✅
1. **Document Results**: Create test execution report
2. **Performance Baseline**: Record execution times for each IPE
3. **Docker Build**: Test containerized deployment
4. **CI/CD Setup**: Configure automated testing pipeline
5. **Staging Deployment**: Deploy to staging environment
6. **Production Planning**: Schedule production deployment

### If Tests Fail ❌
1. **Capture Error Details**: Save full error logs and traces
2. **Review Security Audit**: Ensure no regressions introduced
3. **Database Schema Validation**: Verify database structure matches queries
4. **Test Data Verification**: Confirm witness and test data exists
5. **Code Review**: Re-examine modified files for issues
6. **Iterate and Retest**: Fix issues and run tests again

---

## 📝 Test Execution Log Template

```markdown
# Integration Testing Execution Log

**Date**: [YYYY-MM-DD]
**Tester**: [Name]
**Environment**: [Dev/Staging]
**GCP Project**: [project-id]

## Phase 1: Environment Setup
- [ ] GCP authenticated
- [ ] Environment variables set
- [ ] Secret Manager access verified
- **Notes**: 

## Phase 2: Configuration Validation
- [ ] validate_ipe_config.py: 15/15 tests passed
- **Notes**:

## Phase 3: Database Connection
- [ ] Secret Manager test: PASS
- [ ] Database connection test: PASS
- [ ] Parameterized query test: PASS
- **Notes**:

## Phase 4: IPE Extraction
- [ ] IPE_07 extraction: PASS
- [ ] Execution time: ___ seconds
- [ ] Records extracted: ___
- [ ] Completeness validation: PASS
- [ ] Accuracy positive validation: PASS
- [ ] Accuracy negative validation: PASS
- **Notes**:

## Phase 5: Evidence Verification
- [ ] All 7 evidence files present
- [ ] Integrity hash verified
- [ ] Validation results correct
- **Notes**:

## Overall Result
- [ ] ✅ ALL TESTS PASSED - Ready for next phase
- [ ] ❌ TESTS FAILED - Review and fix issues

## Issues Encountered
1. [Issue description and resolution]

## Recommendations
1. [Recommendation for next steps]
```

---

## 🔗 Related Documentation

- **Configuration Validation**: `scripts/validate_ipe_config.py`
- **Testing Guide**: `docs/development/TESTING_GUIDE.md`
- **Security Audit**: `docs/development/SECURITY_FIXES.md`
- **Deployment Guide**: `docs/deployment/deploy.md`
- **Architecture**: `docs/architecture/PG-01 Diagram.png`

---

**Last Updated**: October 16, 2024  
**Status**: 🚧 Ready for database integration testing  
**Next Phase**: Execute integration tests with live database connection
