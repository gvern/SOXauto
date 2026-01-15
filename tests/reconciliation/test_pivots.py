"""
Unit tests for NAV reconciliation pivot generation.

Tests the build_nav_pivot() function that creates canonical pivot tables
(Category × Voucher Type → Amount_LCY) from classified CR_03 voucher entries.

Test Coverage:
- Missing values (None, NaN) in category and voucher_type
- Empty DataFrames
- Mixed data types
- Negative and positive amounts
- Deterministic ordering
- Column validation
- Edge cases (zero amounts, large numbers, duplicates)
"""

import pandas as pd
import pytest

from src.core.reconciliation.analysis.pivots import build_nav_pivot


class TestBuildNavPivot:
    """Tests for build_nav_pivot() function."""

    def test_basic_pivot_structure(self):
        """Test basic pivot generation with simple categorized data."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage', 'VTC'],
            'voucher_type': ['Refund', 'Store Credit', 'Bank Transfer'],
            'amount': [-1000.0, 500.0, 300.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        assert not nav_pivot.empty
        assert 'amount_lcy' in nav_pivot.columns
        assert 'row_count' in nav_pivot.columns
        assert nav_pivot.index.names == ['category', 'voucher_type']
        
        # Check totals row exists
        assert ('__TOTAL__', '') in nav_pivot.index
        
        # Verify amount calculation
        total_amount = nav_pivot.loc[('__TOTAL__', ''), 'amount_lcy']
        assert total_amount == -200.0  # -1000 + 500 + 300
    
    def test_missing_voucher_type_filled_with_unknown(self):
        """Test that missing voucher_type values are filled with 'Unknown'."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage', 'Expired'],
            'voucher_type': ['Refund', None, pd.NA],
            'amount': [-1000.0, 500.0, 200.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        # Check that "Unknown" appears in the voucher_type level
        voucher_types = nav_pivot.index.get_level_values('voucher_type').unique()
        assert 'Unknown' in voucher_types
        
        # Verify both missing values are mapped to Unknown
        usage_unknown = nav_pivot.loc[('Usage', 'Unknown'), 'amount_lcy']
        expired_unknown = nav_pivot.loc[('Expired', 'Unknown'), 'amount_lcy']
        assert usage_unknown == 500.0
        assert expired_unknown == 200.0
    
    def test_missing_bridge_category_filled_with_uncategorized(self):
        """Test that missing bridge_category values are filled with 'Uncategorized'."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', None, pd.NA],
            'voucher_type': ['Refund', 'Store Credit', 'Unknown'],
            'amount': [-1000.0, 500.0, 200.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        # Check that "Uncategorized" appears in the category level
        categories = nav_pivot.index.get_level_values('category').unique()
        assert 'Uncategorized' in categories
        
        # Verify the two missing categories are aggregated
        uncategorized_total = nav_pivot.xs('Uncategorized', level='category')['amount_lcy'].sum()
        assert uncategorized_total == 700.0
    
    def test_empty_dataframe_returns_empty_pivot(self):
        """Test that empty DataFrame returns empty pivot with correct structure."""
        # Arrange
        cr_03_df = pd.DataFrame()
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        assert nav_pivot.empty
        assert nav_lines.empty
        assert nav_pivot.index.names == ['category', 'voucher_type']
        assert list(nav_pivot.columns) == ['amount_lcy', 'row_count']
    
    def test_none_dataframe_returns_empty_pivot(self):
        """Test that None DataFrame returns empty pivot with correct structure."""
        # Act
        nav_pivot, nav_lines = build_nav_pivot(None, dataset_id='CR_03')  # type: ignore
        
        # Assert
        assert nav_pivot.empty
        assert nav_lines.empty
    
    def test_deterministic_ordering_alphabetical(self):
        """Test that pivot rows are ordered deterministically (alphabetically)."""
        # Arrange - Create data in non-alphabetical order
        cr_03_df = pd.DataFrame({
            'bridge_category': ['VTC', 'Issuance', 'Usage', 'Expired'],
            'voucher_type': ['Z_Type', 'A_Type', 'M_Type', 'B_Type'],
            'amount': [100.0, -200.0, 300.0, -50.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert - Check alphabetical ordering
        categories = nav_pivot.index.get_level_values('category').tolist()
        
        # Remove the __TOTAL__ row for ordering check
        categories_no_total = [c for c in categories if c != '__TOTAL__']
        
        # First category should be "Expired" (alphabetically first)
        assert categories_no_total[0] == 'Expired'
        # Last regular category should be "VTC"
        assert categories_no_total[-1] == 'VTC'
        
        # Verify the full ordered list (excluding total)
        expected_categories = sorted(['Expired', 'Issuance', 'Usage', 'VTC'])
        assert categories_no_total == expected_categories
    
    def test_negative_and_positive_amounts(self):
        """Test that both negative (issuance) and positive (usage) amounts are handled."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Issuance', 'Usage', 'Usage'],
            'voucher_type': ['Refund', 'Apology', 'Store Credit', 'Refund'],
            'amount': [-1000.0, -500.0, 800.0, 200.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        issuance_total = nav_pivot.xs('Issuance', level='category')['amount_lcy'].sum()
        usage_total = nav_pivot.xs('Usage', level='category')['amount_lcy'].sum()
        
        assert issuance_total == -1500.0  # Negative amounts
        assert usage_total == 1000.0      # Positive amounts
        
        # Net should be -500
        net_amount = nav_pivot.loc[('__TOTAL__', ''), 'amount_lcy']
        assert net_amount == -500.0
    
    def test_multiple_rows_same_category_voucher_type(self):
        """Test aggregation of multiple rows with same category and voucher type."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Issuance', 'Issuance'],
            'voucher_type': ['Refund', 'Refund', 'Refund'],
            'amount': [-1000.0, -500.0, -250.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        refund_row = nav_pivot.loc[('Issuance', 'Refund'), :]
        assert refund_row['amount_lcy'] == -1750.0
        assert refund_row['row_count'] == 3
    
    def test_row_count_aggregation(self):
        """Test that row_count is correctly aggregated."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance'] * 5 + ['Usage'] * 3,
            'voucher_type': ['Refund'] * 5 + ['Store Credit'] * 3,
            'amount': [-100.0] * 5 + [50.0] * 3,
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        issuance_count = nav_pivot.loc[('Issuance', 'Refund'), 'row_count']
        usage_count = nav_pivot.loc[('Usage', 'Store Credit'), 'row_count']
        total_count = nav_pivot.loc[('__TOTAL__', ''), 'row_count']
        
        assert issuance_count == 5
        assert usage_count == 3
        assert total_count == 8
    
    def test_required_columns_missing_raises_error(self):
        """Test that missing required columns raises ValueError."""
        # Arrange - Missing 'amount' column
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage'],
            'voucher_type': ['Refund', 'Store Credit'],
            # 'amount' is missing
        })
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        assert "Required columns missing" in str(exc_info.value)
        assert "amount" in str(exc_info.value)
    
    def test_enriched_lines_includes_optional_columns(self):
        """Test that nav_lines_df includes optional columns when available."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage'],
            'voucher_type': ['Refund', 'Store Credit'],
            'amount': [-1000.0, 500.0],
            'country_code': ['NG', 'NG'],
            'voucher_no': ['V001', 'V002'],
            'document_no': ['D001', 'D002'],
            'posting_date': ['2025-09-30', '2025-09-29'],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert - Check optional columns are included
        assert 'country_code' in nav_lines.columns
        assert 'voucher_no' in nav_lines.columns
        assert 'document_no' in nav_lines.columns
        assert 'posting_date' in nav_lines.columns
        
        # Verify data preservation
        assert list(nav_lines['country_code']) == ['NG', 'NG']
        assert list(nav_lines['voucher_no']) == ['V001', 'V002']
    
    def test_mixed_data_types_in_amounts(self):
        """Test handling of mixed data types in amount column."""
        # Arrange - Mix of int and float
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage', 'VTC'],
            'voucher_type': ['Refund', 'Store Credit', 'Bank'],
            'amount': [-1000, 500.5, 300],  # Mix of int and float
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert - Should handle mixed types correctly
        assert not nav_pivot.empty
        total_amount = nav_pivot.loc[('__TOTAL__', ''), 'amount_lcy']
        assert total_amount == pytest.approx(-199.5, rel=1e-5)
    
    def test_zero_amounts_handled_correctly(self):
        """Test that zero amounts are included in the pivot."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage', 'VTC'],
            'voucher_type': ['Refund', 'Store Credit', 'Bank'],
            'amount': [0.0, 0.0, 100.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        issuance_amount = nav_pivot.loc[('Issuance', 'Refund'), 'amount_lcy']
        usage_amount = nav_pivot.loc[('Usage', 'Store Credit'), 'amount_lcy']
        
        assert issuance_amount == 0.0
        assert usage_amount == 0.0
    
    def test_very_large_amounts(self):
        """Test handling of very large financial amounts."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage'],
            'voucher_type': ['Refund', 'Store Credit'],
            'amount': [-1e12, 1e12],  # 1 trillion
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        total_amount = nav_pivot.loc[('__TOTAL__', ''), 'amount_lcy']
        assert total_amount == 0.0  # Should net to zero
    
    def test_duplicate_categories_with_different_types(self):
        """Test handling of same category with multiple voucher types."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Issuance', 'Issuance'],
            'voucher_type': ['Refund', 'Apology', 'JForce'],
            'amount': [-1000.0, -500.0, -250.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        issuance_rows = nav_pivot.xs('Issuance', level='category')
        assert len(issuance_rows) == 3  # Three different voucher types
        
        # Check individual voucher types
        assert ('Issuance', 'Refund') in nav_pivot.index
        assert ('Issuance', 'Apology') in nav_pivot.index
        assert ('Issuance', 'JForce') in nav_pivot.index
    
    def test_whitespace_in_category_and_type(self):
        """Test handling of whitespace in category and voucher type values."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['  Issuance  ', 'Usage', 'VTC  '],
            'voucher_type': ['Refund  ', '  Store Credit', '  Bank  '],
            'amount': [-1000.0, 500.0, 300.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert - Values should be preserved as-is (no automatic stripping)
        # This is by design - categorization pipeline should handle normalization
        categories = nav_pivot.index.get_level_values('category').unique().tolist()
        
        # Remove __TOTAL__ for checking
        categories = [c for c in categories if c != '__TOTAL__']
        
        # Should contain the whitespace versions
        assert any('Issuance' in c for c in categories)
        assert any('Usage' in c for c in categories)
    
    def test_multiindex_structure_correct(self):
        """Test that the MultiIndex structure is correctly formed."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage'],
            'voucher_type': ['Refund', 'Store Credit'],
            'amount': [-1000.0, 500.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        assert isinstance(nav_pivot.index, pd.MultiIndex)
        assert nav_pivot.index.nlevels == 2
        assert nav_pivot.index.names == ['category', 'voucher_type']
        
        # Test index access
        assert ('Issuance', 'Refund') in nav_pivot.index
        assert ('Usage', 'Store Credit') in nav_pivot.index


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_single_row_dataframe(self):
        """Test pivot generation with single-row DataFrame."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance'],
            'voucher_type': ['Refund'],
            'amount': [-1000.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        assert len(nav_pivot) == 2  # One data row + one total row
        assert nav_pivot.loc[('Issuance', 'Refund'), 'amount_lcy'] == -1000.0
    
    def test_all_unknown_voucher_types(self):
        """Test when all voucher types are missing."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage', 'VTC'],
            'voucher_type': [None, pd.NA, None],
            'amount': [-1000.0, 500.0, 300.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        # All should be mapped to "Unknown"
        voucher_types = nav_pivot.index.get_level_values('voucher_type').unique()
        voucher_types = [vt for vt in voucher_types if vt != '']  # Exclude total row
        assert voucher_types == ['Unknown']
    
    def test_amount_column_renamed_to_amount_lcy(self):
        """Test that 'amount' column is renamed to 'amount_lcy' in output."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance'],
            'voucher_type': ['Refund'],
            'amount': [-1000.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        assert 'amount_lcy' in nav_pivot.columns
        assert 'amount' not in nav_pivot.columns
        assert 'amount_lcy' in nav_lines.columns


class TestIntegrationScenarios:
    """Tests for realistic integration scenarios."""
    
    def test_realistic_reconciliation_scenario(self):
        """Test with realistic data resembling actual reconciliation output."""
        # Arrange - Representative fixture data
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
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        # Check total amount (should be net of all transactions)
        total_amount = nav_pivot.loc[('__TOTAL__', ''), 'amount_lcy']
        expected_total = -50000 - 25000 + 30000 + 15000 + 10000 + 5000 + 3000
        assert total_amount == pytest.approx(expected_total, rel=1e-5)
        
        # Check category breakdown
        # Use nav_lines (raw lines) to avoid counting synthetic __TOTAL__ rows from the pivot
        categories = nav_lines['category'].unique()
        categories = [c for c in categories if c != '__TOTAL__']
        assert len(categories) == 5  # 5 distinct categories (excluding '__TOTAL__')
        
        # Verify lines DataFrame preserves country_code
        assert all(nav_lines['country_code'] == 'NG')
