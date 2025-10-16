# Testing Guide for SOXauto PG-01

**Pre-Production Testing Checklist**

This guide provides comprehensive testing procedures to validate the SOXauto application before production deployment, with special focus on the security-hardened CTE-based validation queries.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration Validation](#configuration-validation)
3. [Security Testing](#security-testing)
4. [Integration Testing](#integration-testing)
5. [End-to-End Testing](#end-to-end-testing)
6. [Performance Testing](#performance-testing)
7. [Evidence System Testing](#evidence-system-testing)

---

## Quick Start

### Prerequisites

```bash
# Ensure Python 3.11+ is installed
python3 --version

# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export GCP_PROJECT_ID="your-gcp-project-id"
export CUTOFF_DATE="2024-05-01"  # Optional
```

### Run All Tests

```bash
# 1. Configuration validation (no database required)
python3 scripts/validate_ipe_config.py

# 2. Syntax validation
python3 -m py_compile src/core/*.py src/bridges/*.py src/utils/*.py

# 3. Run unit tests (if available)
pytest tests/ -v

# 4. Docker build test
docker build -t soxauto-pg01-test .
```

---

## Configuration Validation

### Automated Configuration Check

The `validate_ipe_config.py` script performs static analysis on IPE configurations:

```bash
python3 scripts/validate_ipe_config.py
```

**What it checks:**
- ✅ All required fields present (id, description, secret_name, main_query)
- ✅ Main queries use parameterized `?` placeholders
- ✅ Validation queries use secure CTE patterns
- ✅ No SQL injection risks (no `.format()`, `%s`, string concatenation)
- ✅ GCP_PROJECT_ID uses `os.getenv()` instead of hardcoded value

**Expected Output:**
```
✅ ALL CHECKS PASSED - Configuration is secure!
```

### Manual Configuration Review

Review `src/core/config.py` for:

```python
# ✅ CORRECT: Environment variable
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "default-project")

# ❌ WRONG: Hardcoded
GCP_PROJECT_ID = "my-production-project"
```

---

## Security Testing

### SQL Injection Prevention

**Test 1: Verify Parameterized Queries**

```python
# All queries should use ? placeholders
python3 -c "
from src.core.config import IPE_CONFIGS
for ipe in IPE_CONFIGS:
    assert '?' in ipe['main_query'], f'Missing placeholders in {ipe[\"id\"]}'
    print(f'✅ {ipe[\"id\"]}: Uses parameterized queries')
"
```

**Test 2: Verify CTE Pattern**

```python
# All validation queries should use CTEs
python3 -c "
from src.core.config import IPE_CONFIGS
for ipe in IPE_CONFIGS:
    for vtype in ['completeness_query', 'accuracy_positive_query']:
        if vtype in ipe.get('validation', {}):
            query = ipe['validation'][vtype]
            assert 'WITH' in query.upper(), f'Missing CTE in {ipe[\"id\"]} {vtype}'
            print(f'✅ {ipe[\"id\"]} {vtype}: Uses CTE pattern')
"
```

**Test 3: No Format Strings**

```bash
# Grep for dangerous patterns (should return no results)
grep -r "\.format(" src/core/config.py
grep -r "%s" src/core/config.py | grep -v "# "
grep -r "f\"{" src/core/config.py | grep SELECT
```

Expected: No matches (or only in comments)

---

## Integration Testing

### Test Database Connection

Create `tests/test_connection.py`:

```python
import os
from src.utils.gcp_utils import GCPSecretManager

def test_secret_manager_connection():
    """Test connection to GCP Secret Manager."""
    project_id = os.getenv("GCP_PROJECT_ID")
    assert project_id, "GCP_PROJECT_ID not set"
    
    sm = GCPSecretManager(project_id)
    # Try to access a test secret
    try:
        sm.get_secret("DB_CREDENTIALS_NAV_BI")
        print("✅ Secret Manager: Connection successful")
    except Exception as e:
        print(f"⚠️  Secret Manager: {e}")

if __name__ == "__main__":
    test_secret_manager_connection()
```

Run:
```bash
python3 tests/test_connection.py
```

### Test Query Execution (Manual)

**Important**: This test requires access to production database. Only run in controlled environment.

```python
import pyodbc
from src.core.config import IPE_CONFIGS
from src.utils.gcp_utils import GCPSecretManager

# Get first IPE config
ipe = IPE_CONFIGS[0]

# Get credentials
sm = GCPSecretManager(os.getenv("GCP_PROJECT_ID"))
conn_str = sm.get_secret(ipe['secret_name'])

# Test connection
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Test parameterized query
test_query = "SELECT COUNT(*) FROM [table] WHERE date < ?"
cursor.execute(test_query, ('2024-01-01',))
result = cursor.fetchone()

print(f"✅ Query executed successfully: {result[0]} rows")
conn.close()
```

---

## End-to-End Testing

### Test IPE Extraction

Create a test script to run a single IPE:

```python
# tests/test_ipe_extraction.py
import os
from src.core.ipe_runner import IPERunner
from src.core.config import IPE_CONFIGS
from src.utils.gcp_utils import GCPSecretManager

def test_single_ipe():
    """Test complete IPE extraction flow."""
    # Get test IPE (use IPE_07 or smallest dataset)
    ipe_config = next(c for c in IPE_CONFIGS if c['id'] == 'IPE_07')
    
    # Setup
    project_id = os.getenv("GCP_PROJECT_ID")
    secret_manager = GCPSecretManager(project_id)
    
    # Create runner
    runner = IPERunner(
        ipe_config=ipe_config,
        secret_manager=secret_manager,
        cutoff_date="2024-01-01"  # Use test date
    )
    
    # Execute
    try:
        df = runner.run()
        print(f"✅ IPE Extraction: {len(df)} rows extracted and validated")
        return True
    except Exception as e:
        print(f"❌ IPE Extraction failed: {e}")
        return False

if __name__ == "__main__":
    success = test_single_ipe()
    exit(0 if success else 1)
```

Run:
```bash
python3 tests/test_ipe_extraction.py
```

### Test Validation Queries

Verify that all three validation types execute correctly:

```python
# tests/test_validations.py
from src.core.ipe_runner import IPERunner
from src.core.config import IPE_CONFIGS
from src.utils.gcp_utils import GCPSecretManager
import os

def test_all_validations():
    """Test all validation query types."""
    project_id = os.getenv("GCP_PROJECT_ID")
    sm = GCPSecretManager(project_id)
    
    for ipe_config in IPE_CONFIGS[:2]:  # Test first 2 IPEs
        print(f"\nTesting {ipe_config['id']}...")
        
        runner = IPERunner(ipe_config, sm, cutoff_date="2024-01-01")
        
        try:
            # Run extraction (includes all validations)
            df = runner.run()
            
            # Check validation results
            validations = runner.validation_results
            
            assert 'completeness' in validations
            assert validations['completeness']['status'] == 'PASS'
            print(f"  ✅ Completeness: {validations['completeness']}")
            
            if 'accuracy_positive' in validations:
                assert validations['accuracy_positive']['status'] == 'PASS'
                print(f"  ✅ Accuracy Positive: {validations['accuracy_positive']}")
            
            if 'accuracy_negative' in validations:
                assert validations['accuracy_negative']['status'] == 'PASS'
                print(f"  ✅ Accuracy Negative: {validations['accuracy_negative']}")
            
        except Exception as e:
            print(f"  ❌ Validation failed: {e}")
            return False
    
    print("\n✅ All validation tests passed!")
    return True

if __name__ == "__main__":
    success = test_all_validations()
    exit(0 if success else 1)
```

---

## Performance Testing

### Query Performance Benchmarks

```python
# tests/test_performance.py
import time
import pandas as pd
from src.core.ipe_runner import IPERunner
from src.core.config import IPE_CONFIGS
from src.utils.gcp_utils import GCPSecretManager
import os

def benchmark_ipe(ipe_id: str, iterations: int = 3):
    """Benchmark IPE execution time."""
    ipe_config = next(c for c in IPE_CONFIGS if c['id'] == ipe_id)
    sm = GCPSecretManager(os.getenv("GCP_PROJECT_ID"))
    
    times = []
    for i in range(iterations):
        runner = IPERunner(ipe_config, sm, cutoff_date="2024-01-01")
        
        start = time.time()
        df = runner.run()
        elapsed = time.time() - start
        
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.2f}s ({len(df)} rows)")
    
    avg_time = sum(times) / len(times)
    print(f"\n✅ Average time: {avg_time:.2f}s")
    
    # Performance threshold (adjust based on your requirements)
    assert avg_time < 300, f"Performance issue: {avg_time}s > 5min threshold"
    
    return avg_time

if __name__ == "__main__":
    print("IPE Performance Benchmark")
    print("=" * 50)
    benchmark_ipe("IPE_07")
```

---

## Evidence System Testing

### Test Digital Evidence Generation

```python
# tests/test_evidence.py
from src.core.evidence_manager import DigitalEvidenceManager, IPEEvidenceGenerator
import pandas as pd
import os

def test_evidence_generation():
    """Test complete evidence package generation."""
    # Create test data
    test_df = pd.DataFrame({
        'id': [1, 2, 3],
        'amount': [100.0, 200.0, 300.0],
        'date': ['2024-01-01', '2024-01-02', '2024-01-03']
    })
    
    # Generate evidence
    em = DigitalEvidenceManager()
    generator = IPEEvidenceGenerator(
        ipe_id="TEST_IPE",
        ipe_description="Test IPE for evidence validation",
        evidence_manager=em
    )
    
    test_query = "SELECT * FROM test WHERE date < ?"
    test_params = ('2024-01-01',)
    
    generator.set_query_info(test_query, test_params)
    generator.set_data(test_df)
    generator.add_validation_result("completeness", {"status": "PASS", "count": 3})
    
    # Create evidence package
    zip_path = generator.create_evidence_package()
    
    # Validate package exists and has content
    assert os.path.exists(zip_path), "Evidence package not created"
    assert os.path.getsize(zip_path) > 0, "Evidence package is empty"
    
    print(f"✅ Evidence package created: {zip_path}")
    print(f"   Size: {os.path.getsize(zip_path)} bytes")
    
    # Validate integrity
    hash_info = em._compute_integrity_hash(test_df)
    print(f"   Hash: {hash_info['hash_value'][:16]}...")
    
    return True

if __name__ == "__main__":
    test_evidence_generation()
```

---

## Test Execution Checklist

### Before Production Deployment

- [ ] **Configuration Validation**: `python3 scripts/validate_ipe_config.py`
- [ ] **Syntax Check**: All Python files compile without errors
- [ ] **Security Scan**: No SQL injection vulnerabilities detected
- [ ] **Connection Test**: GCP Secret Manager accessible
- [ ] **Query Test**: All validation queries execute successfully
- [ ] **Performance Test**: IPE extraction completes within acceptable time
- [ ] **Evidence Test**: Evidence packages generate with correct integrity hashes
- [ ] **Docker Build**: Container builds successfully
- [ ] **Environment Variables**: All required variables documented and set

### Production Smoke Test

After deployment, run a limited smoke test:

```bash
# 1. Health check
curl https://your-cloud-run-url/health

# 2. Test single IPE extraction
curl -X POST https://your-cloud-run-url/run-ipe \
  -H "Content-Type: application/json" \
  -d '{"ipe_id": "IPE_07", "cutoff_date": "2024-01-01"}'
```

---

## Troubleshooting

### Common Issues

**Issue**: `GCP_PROJECT_ID not set`
**Solution**: Export environment variable: `export GCP_PROJECT_ID="your-project"`

**Issue**: `Secret not found`
**Solution**: Verify secret exists in GCP Secret Manager and service account has access

**Issue**: `SQL injection warning`
**Solution**: Ensure all queries use `?` placeholders and CTE patterns

**Issue**: `Validation failed`
**Solution**: Check witness data exists in database for the test date range

---

## Additional Resources

- **Security Audit Report**: `docs/development/SECURITY_FIXES.md`
- **Deployment Guide**: `docs/deployment/deploy.md`
- **Architecture Diagram**: `docs/architecture/PG-01 Diagram.png`
- **Evidence Documentation**: `docs/development/evidence_documentation.md`

---

**Last Updated**: December 2024  
**Version**: 2.0 (Post Security Hardening)
