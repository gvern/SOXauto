#!/usr/bin/env python3
"""
Manual verification script for NAV pivot implementation.

This script tests the build_nav_pivot() function with various scenarios
to ensure it meets all acceptance criteria.

Run with: python3 tests/manual_verify_pivot.py
"""

import pandas as pd
import sys
import os

# Add the repo root to the path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.core.reconciliation.analysis.pivots import build_nav_pivot


def test_scenario(name, test_func):
    """Helper to run a test scenario."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)
    try:
        test_func()
        print(f"✅ PASSED: {name}")
        return True
    except AssertionError as e:
        print(f"❌ FAILED: {name}")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {name}")
        print(f"   Exception: {type(e).__name__}: {e}")
        return False


def test_missing_voucher_type():
    """Test that missing voucher_type is filled with 'Unknown'."""
    cr_03_df = pd.DataFrame({
        'bridge_category': ['Issuance', 'Usage', 'Expired'],
        'voucher_type': ['Refund', None, pd.NA],
        'amount': [-1000.0, 500.0, 200.0],
    })
    
    nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
    
    # Verify Unknown bucket exists
    voucher_types = nav_pivot.index.get_level_values('voucher_type').unique()
    assert 'Unknown' in voucher_types, "Missing 'Unknown' voucher_type bucket"
    
    # Verify amounts are correctly aggregated
    usage_unknown = nav_pivot.loc[('Usage', 'Unknown'), 'amount_lcy']
    expired_unknown = nav_pivot.loc[('Expired', 'Unknown'), 'amount_lcy']
    
    assert usage_unknown == 500.0, f"Expected 500.0, got {usage_unknown}"
    assert expired_unknown == 200.0, f"Expected 200.0, got {expired_unknown}"
    
    print("   ✓ Missing voucher_type correctly mapped to 'Unknown'")
    print(f"   ✓ Found {len([vt for vt in voucher_types if vt == 'Unknown'])} 'Unknown' entries")


def test_empty_dataset():
    """Test that empty DataFrame returns empty pivot with correct structure."""
    empty_df = pd.DataFrame()
    
    nav_pivot, nav_lines = build_nav_pivot(empty_df, dataset_id='CR_03')
    
    assert nav_pivot.empty, "Pivot should be empty"
    assert nav_lines.empty, "Lines should be empty"
    assert nav_pivot.index.names == ['category', 'voucher_type'], "Index names incorrect"
    assert list(nav_pivot.columns) == ['amount_lcy', 'row_count'], "Columns incorrect"
    
    print("   ✓ Empty DataFrame handled correctly")


def test_mixed_types():
    """Test handling of mixed data types in amounts."""
    cr_03_df = pd.DataFrame({
        'bridge_category': ['Issuance', 'Usage', 'VTC'],
        'voucher_type': ['Refund', 'Store Credit', 'Bank'],
        'amount': [-1000, 500.5, 300],  # Mix of int and float
    })
    
    nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
    
    total_amount = nav_pivot.loc[('__TOTAL__', ''), 'amount_lcy']
    expected = -1000 + 500.5 + 300
    
    assert abs(total_amount - expected) < 0.01, f"Expected {expected}, got {total_amount}"
    
    print(f"   ✓ Mixed types handled: total = {total_amount}")


def test_negative_and_positive_amounts():
    """Test both negative (issuance) and positive (usage) amounts."""
    cr_03_df = pd.DataFrame({
        'bridge_category': ['Issuance', 'Issuance', 'Usage', 'Usage'],
        'voucher_type': ['Refund', 'Apology', 'Store Credit', 'Refund'],
        'amount': [-1000.0, -500.0, 800.0, 200.0],
    })
    
    nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
    
    issuance_total = nav_pivot.xs('Issuance', level='category')['amount_lcy'].sum()
    usage_total = nav_pivot.xs('Usage', level='category')['amount_lcy'].sum()
    
    assert issuance_total == -1500.0, f"Expected -1500.0, got {issuance_total}"
    assert usage_total == 1000.0, f"Expected 1000.0, got {usage_total}"
    
    net_amount = nav_pivot.loc[('__TOTAL__', ''), 'amount_lcy']
    assert net_amount == -500.0, f"Expected -500.0, got {net_amount}"
    
    print(f"   ✓ Issuance total: {issuance_total}")
    print(f"   ✓ Usage total: {usage_total}")
    print(f"   ✓ Net amount: {net_amount}")


def test_deterministic_ordering():
    """Test that pivot rows are ordered deterministically (alphabetically)."""
    cr_03_df = pd.DataFrame({
        'bridge_category': ['VTC', 'Issuance', 'Usage', 'Expired'],
        'voucher_type': ['Z_Type', 'A_Type', 'M_Type', 'B_Type'],
        'amount': [100.0, -200.0, 300.0, -50.0],
    })
    
    nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
    
    categories = nav_pivot.index.get_level_values('category').tolist()
    categories_no_total = [c for c in categories if c != '__TOTAL__']
    
    # Check alphabetical ordering
    expected_categories = sorted(['Expired', 'Issuance', 'Usage', 'VTC'])
    
    assert categories_no_total == expected_categories, \
        f"Expected {expected_categories}, got {categories_no_total}"
    
    print(f"   ✓ Categories ordered alphabetically: {categories_no_total}")


def test_required_columns_missing():
    """Test that missing required columns raises ValueError."""
    cr_03_df = pd.DataFrame({
        'bridge_category': ['Issuance', 'Usage'],
        'voucher_type': ['Refund', 'Store Credit'],
        # 'amount' is missing
    })
    
    try:
        build_nav_pivot(cr_03_df, dataset_id='CR_03')
        raise AssertionError("Should have raised ValueError for missing 'amount' column")
    except ValueError as e:
        error_msg = str(e)
        assert "Required columns missing" in error_msg, f"Wrong error message: {error_msg}"
        assert "amount" in error_msg, f"Error should mention 'amount': {error_msg}"
        print(f"   ✓ Correctly raised ValueError: {error_msg[:80]}...")


def test_realistic_scenario():
    """Test with realistic reconciliation data."""
    cr_03_df = pd.DataFrame({
        'bridge_category': [
            'Issuance - Refund', 'Issuance - Apology', 'Usage', 'Usage',
            'VTC', 'Expired - Apology', 'Cancellation - Store Credit'
        ],
        'voucher_type': [
            'Refund', 'Apology', 'Store Credit', 'Store Credit',
            'Bank Transfer', 'Apology', 'Credit Memo'
        ],
        'amount': [-50000.0, -25000.0, 30000.0, 15000.0, 10000.0, 5000.0, 3000.0],
        'country_code': ['NG', 'NG', 'NG', 'NG', 'NG', 'NG', 'NG'],
    })
    
    nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
    
    # Check total amount
    total_amount = nav_pivot.loc[('__TOTAL__', ''), 'amount_lcy']
    expected_total = -50000 - 25000 + 30000 + 15000 + 10000 + 5000 + 3000
    
    assert abs(total_amount - expected_total) < 0.01, \
        f"Expected {expected_total}, got {total_amount}"
    
    # Check category breakdown
    categories = nav_pivot.index.get_level_values('category').unique()
    categories = [c for c in categories if c != '__TOTAL__']
    
    assert len(categories) == 5, f"Expected 5 categories, got {len(categories)}"
    
    # Verify lines DataFrame preserves country_code
    assert all(nav_lines['country_code'] == 'NG'), "Country code not preserved"
    
    print(f"   ✓ Total amount: {total_amount:,.2f}")
    print(f"   ✓ Number of categories: {len(categories)}")
    print(f"   ✓ Country code preserved in lines")
    
    # Print pivot summary
    print("\n   Pivot Summary:")
    for idx in nav_pivot.index:
        if idx[0] != '__TOTAL__':
            amount = nav_pivot.loc[idx, 'amount_lcy']
            count = nav_pivot.loc[idx, 'row_count']
            print(f"      {idx[0]:30} | {idx[1]:15} | {amount:>12,.2f} | {int(count):>5} rows")


def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("NAV PIVOT IMPLEMENTATION VERIFICATION")
    print("="*60)
    
    tests = [
        ("Missing voucher_type handling", test_missing_voucher_type),
        ("Empty dataset handling", test_empty_dataset),
        ("Mixed data types", test_mixed_types),
        ("Negative and positive amounts", test_negative_and_positive_amounts),
        ("Deterministic ordering", test_deterministic_ordering),
        ("Required columns validation", test_required_columns_missing),
        ("Realistic scenario", test_realistic_scenario),
    ]
    
    results = []
    for name, test_func in tests:
        results.append(test_scenario(name, test_func))
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Implementation is ready!")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED - Please review")
        return 1


if __name__ == "__main__":
    sys.exit(main())
