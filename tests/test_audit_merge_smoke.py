"""
Quick smoke test to verify audit_merge function can be imported and basic functionality works.

This is a minimal test that can run without pytest fixtures or complex setup.
Run with: python tests/test_audit_merge_smoke.py
"""

import os
import sys
from pathlib import Path

# Add repo root to Python path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def test_import():
    """Test that audit_merge can be imported."""
    print("Testing import...")
    from src.utils.merge_utils import audit_merge
    assert callable(audit_merge)
    print("✓ Import successful")


def test_basic_functionality():
    """Test basic audit_merge functionality."""
    print("\nTesting basic functionality...")
    
    import pandas as pd
    from src.utils.merge_utils import audit_merge
    
    # Create simple test data
    left = pd.DataFrame({'id': [1, 2, 3], 'value': [10, 20, 30]})
    right = pd.DataFrame({'id': [1, 2, 3], 'amount': [100, 200, 300]})
    
    # Run audit (using /tmp for output)
    result = audit_merge(
        left=left,
        right=right,
        on='id',
        name='smoke_test',
        out_dir='/tmp/audit_merge_smoke'
    )
    
    # Verify result structure
    assert 'left_duplicates' in result
    assert 'right_duplicates' in result
    assert 'has_duplicates' in result
    assert 'left_total_rows' in result
    assert 'right_total_rows' in result
    
    # Verify values for clean data
    assert result['left_duplicates'] == 0
    assert result['right_duplicates'] == 0
    assert result['has_duplicates'] is False
    assert result['left_total_rows'] == 3
    assert result['right_total_rows'] == 3
    
    # Verify log file was created
    log_file = Path('/tmp/audit_merge_smoke/merge_audit.log')
    assert log_file.exists()
    
    print("✓ Basic functionality works")


def test_duplicate_detection():
    """Test that duplicates are detected correctly."""
    print("\nTesting duplicate detection...")
    
    import pandas as pd
    from src.utils.merge_utils import audit_merge
    
    # Create data with duplicates
    left = pd.DataFrame({'id': [1, 1, 2], 'value': [10, 15, 20]})  # ID 1 duplicated
    right = pd.DataFrame({'id': [1, 2], 'amount': [100, 200]})
    
    # Run audit
    result = audit_merge(
        left=left,
        right=right,
        on='id',
        name='duplicate_test',
        out_dir='/tmp/audit_merge_smoke'
    )
    
    # Verify duplicates detected
    assert result['left_duplicates'] == 2
    assert result['right_duplicates'] == 0
    assert result['has_duplicates'] is True
    
    # Verify CSV was created
    csv_file = Path('/tmp/audit_merge_smoke/duplicate_test.left_dup_keys.csv')
    assert csv_file.exists()
    
    print("✓ Duplicate detection works")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("AUDIT_MERGE SMOKE TEST")
    print("="*60)
    
    try:
        test_import()
        test_basic_functionality()
        test_duplicate_detection()
        
        print("\n" + "="*60)
        print("ALL SMOKE TESTS PASSED ✓")
        print("="*60)
        
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
