"""
Smoke test for NAV pivot generation module.

Verifies that the module can be imported and has the expected API.

Run with: pytest tests/test_pivot_smoke.py -v
"""

import pandas as pd

from src.core.reconciliation.analysis.pivots import build_nav_pivot


def test_build_nav_pivot_import():
    """Test that build_nav_pivot can be imported."""
    assert callable(build_nav_pivot)


def test_build_nav_pivot_empty_input():
    """Test that build_nav_pivot handles empty input gracefully."""
    nav_pivot, nav_lines = build_nav_pivot(pd.DataFrame())
    
    assert isinstance(nav_pivot, pd.DataFrame)
    assert isinstance(nav_lines, pd.DataFrame)
    assert nav_pivot.empty
    assert nav_lines.empty


def test_build_nav_pivot_basic_functionality():
    """Test basic pivot generation with minimal data."""
    # Arrange
    test_data = pd.DataFrame({
        'bridge_category': ['Issuance', 'Usage'],
        'voucher_type': ['Refund', 'Store Credit'],
        'amount': [-1000.0, 500.0],
    })
    
    # Act
    nav_pivot, nav_lines = build_nav_pivot(test_data)
    
    # Assert - Basic structure checks
    assert not nav_pivot.empty
    assert not nav_lines.empty
    assert 'amount_lcy' in nav_pivot.columns
    assert 'row_count' in nav_pivot.columns
    assert nav_pivot.index.names == ['category', 'voucher_type']
    
    # Assert - Data integrity
    assert len(nav_lines) == 2  # Two input rows
    assert ('Issuance', 'Refund') in nav_pivot.index
    assert ('Usage', 'Store Credit') in nav_pivot.index
    
    print("✓ Smoke test passed: build_nav_pivot works correctly")


if __name__ == "__main__":
    # Run smoke test directly
    test_build_nav_pivot_import()
    print("✓ Import test passed")
    
    test_build_nav_pivot_empty_input()
    print("✓ Empty input test passed")
    
    test_build_nav_pivot_basic_functionality()
    print("✓ Basic functionality test passed")
    
    print("\n✅ All smoke tests passed!")
