#!/usr/bin/env python3
"""
Simple validation script to test the audit_merge function.
This script demonstrates the functionality without requiring pytest.
"""

import sys
import os
from pathlib import Path
import pandas as pd

# Add the repo root to Python path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.utils.merge_utils import audit_merge


def test_scenario_1_clean_merge():
    """Test 1: Clean merge with no duplicates."""
    print("\n" + "="*70)
    print("TEST 1: Clean merge (no duplicates)")
    print("="*70)
    
    left = pd.DataFrame({
        'customer_id': [1, 2, 3],
        'customer_name': ['Alice', 'Bob', 'Charlie'],
        'balance': [1000, 2000, 3000]
    })
    
    right = pd.DataFrame({
        'customer_id': [1, 2, 3],
        'gl_amount': [1000, 2000, 3000]
    })
    
    result = audit_merge(
        left, right,
        on='customer_id',
        name='clean_merge_test',
        out_dir='/tmp/audit_merge_demo'
    )
    
    print(f"\nResults: {result}")
    assert result['has_duplicates'] is False, "Should have no duplicates"
    print("✓ TEST 1 PASSED")


def test_scenario_2_left_duplicates():
    """Test 2: Duplicates in left DataFrame only."""
    print("\n" + "="*70)
    print("TEST 2: Left-side duplicates (potential many-to-one)")
    print("="*70)
    
    left = pd.DataFrame({
        'customer_id': [1, 1, 2, 3],  # Customer 1 appears twice
        'document_no': ['D1', 'D2', 'D3', 'D4'],
        'amount': [500, 600, 2000, 3000]
    })
    
    right = pd.DataFrame({
        'customer_id': [1, 2, 3],
        'gl_balance': [1100, 2000, 3000]
    })
    
    result = audit_merge(
        left, right,
        on='customer_id',
        name='left_dup_test',
        out_dir='/tmp/audit_merge_demo'
    )
    
    print(f"\nResults: {result}")
    assert result['left_duplicates'] == 2, "Should have 2 left duplicates"
    assert result['right_duplicates'] == 0, "Should have no right duplicates"
    assert result['has_duplicates'] is True
    
    # Check that CSV was created
    csv_file = Path('/tmp/audit_merge_demo/left_dup_test.left_dup_keys.csv')
    assert csv_file.exists(), "Should create CSV for left duplicates"
    print(f"✓ Duplicate keys CSV created: {csv_file}")
    
    # Show the content
    dup_data = pd.read_csv(csv_file)
    print(f"\nDuplicate rows exported to CSV:")
    print(dup_data)
    
    print("✓ TEST 2 PASSED")


def test_scenario_3_cartesian_risk():
    """Test 3: Duplicates on both sides (Cartesian product risk)."""
    print("\n" + "="*70)
    print("TEST 3: Both sides have duplicates (CARTESIAN RISK!)")
    print("="*70)
    
    # Realistic scenario: Multiple transactions per customer on both sides
    left = pd.DataFrame({
        'customer_id': [1, 1, 2, 3],  # Customer 1 has 2 transactions
        'transaction_id': ['T1', 'T2', 'T3', 'T4'],
        'amount': [500, 600, 2000, 3000]
    })
    
    right = pd.DataFrame({
        'customer_id': [1, 1, 2, 3],  # Customer 1 has 2 GL entries
        'gl_entry': ['GL1', 'GL2', 'GL3', 'GL4'],
        'gl_amount': [400, 700, 2000, 3000]
    })
    
    result = audit_merge(
        left, right,
        on='customer_id',
        name='cartesian_risk_test',
        out_dir='/tmp/audit_merge_demo'
    )
    
    print(f"\nResults: {result}")
    assert result['left_duplicates'] == 2, "Should have 2 left duplicates"
    assert result['right_duplicates'] == 2, "Should have 2 right duplicates"
    assert result['has_duplicates'] is True
    
    print("\n⚠️  WARNING: Merging these DataFrames would create a Cartesian product!")
    print("   Customer 1: 2 left rows × 2 right rows = 4 merged rows (explosion!)")
    
    print("✓ TEST 3 PASSED")


def test_scenario_4_multi_key():
    """Test 4: Multiple join keys."""
    print("\n" + "="*70)
    print("TEST 4: Multiple join keys (customer + product)")
    print("="*70)
    
    left = pd.DataFrame({
        'customer_id': [1, 1, 2, 3],
        'product_id': ['A', 'A', 'B', 'C'],  # (1, A) appears twice
        'order_amount': [100, 150, 200, 300]
    })
    
    right = pd.DataFrame({
        'customer_id': [1, 2, 3],
        'product_id': ['A', 'B', 'C'],
        'inventory_cost': [80, 180, 280]
    })
    
    result = audit_merge(
        left, right,
        on=['customer_id', 'product_id'],
        name='multi_key_test',
        out_dir='/tmp/audit_merge_demo'
    )
    
    print(f"\nResults: {result}")
    assert result['left_duplicates'] == 2, "Should detect duplicate composite key"
    print("✓ TEST 4 PASSED")


def main():
    """Run all validation tests."""
    print("\n" + "#"*70)
    print("# AUDIT_MERGE FUNCTION VALIDATION")
    print("#"*70)
    
    try:
        test_scenario_1_clean_merge()
        test_scenario_2_left_duplicates()
        test_scenario_3_cartesian_risk()
        test_scenario_4_multi_key()
        
        print("\n" + "#"*70)
        print("# ALL TESTS PASSED ✓")
        print("#"*70)
        
        print("\n📁 Output files created in: /tmp/audit_merge_demo/")
        print("   - merge_audit.log (audit log)")
        print("   - *.left_dup_keys.csv (duplicate keys from left side)")
        print("   - *.right_dup_keys.csv (duplicate keys from right side)")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
