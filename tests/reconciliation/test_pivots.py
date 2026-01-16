"""
Unit tests for pivot generation functions.

Tests both NAV and Target Values pivot generation functions:
- build_target_values_pivot_local(): Target Values pivot with local currency aggregation
- build_nav_pivot(): NAV pivot from classified CR_03 voucher entries

Test Coverage:
- Target Values: voucher type harmonization, multi-country inputs, missing fields
- NAV: canonical pivot tables (Category × Voucher Type → Amount_LCY)
- Common: Missing values (None, NaN), empty DataFrames, mixed data types
- Edge cases: negative/positive amounts, zero amounts, large numbers, duplicates
- Schema validation: deterministic ordering, column validation, error handling
"""

import pandas as pd
import pytest

from src.core.reconciliation.analysis.pivots import (
    build_target_values_pivot_local,
)
from src.core.reconciliation.voucher_classification.voucher_utils import (
    harmonize_voucher_type,
)


class TestHarmonizeVoucherType:
    """Tests for voucher type harmonization function."""

    def test_harmonize_refund_variants(self):
        """Test that various refund labels map to canonical 'refund'."""
        assert harmonize_voucher_type("Refund") == "refund"
        assert harmonize_voucher_type("REFUND") == "refund"
        assert harmonize_voucher_type("rf_") == "refund"
        assert harmonize_voucher_type("RFN") == "refund"

    def test_harmonize_store_credit_variants(self):
        """Test that various store credit labels map to canonical 'store_credit'."""
        assert harmonize_voucher_type("Store Credit") == "store_credit"
        assert harmonize_voucher_type("STORE CREDIT") == "store_credit"
        assert harmonize_voucher_type("store_credit") == "store_credit"
        assert harmonize_voucher_type("storecredit") == "store_credit"

    def test_harmonize_apology_variants(self):
        """Test that apology-related labels map to canonical 'apology'."""
        assert harmonize_voucher_type("Apology") == "apology"
        assert harmonize_voucher_type("APOLOGY") == "apology"
        assert harmonize_voucher_type("Commercial Gesture") == "apology"
        assert harmonize_voucher_type("CXP") == "apology"

    def test_harmonize_jforce_variants(self):
        """Test that JForce labels map to canonical 'jforce'."""
        assert harmonize_voucher_type("JForce") == "jforce"
        assert harmonize_voucher_type("jforce") == "jforce"
        assert harmonize_voucher_type("PYT_") == "jforce"
        assert harmonize_voucher_type("pyt_pf") == "jforce"

    def test_harmonize_expired(self):
        """Test that expired labels map to canonical 'expired'."""
        assert harmonize_voucher_type("Expired") == "expired"
        assert harmonize_voucher_type("EXP") == "expired"

    def test_harmonize_vtc(self):
        """Test that VTC labels map to canonical 'vtc'."""
        assert harmonize_voucher_type("VTC") == "vtc"
        assert harmonize_voucher_type("Voucher to Cash") == "vtc"

    def test_harmonize_missing_values(self):
        """Test that missing/empty values map to 'Unknown'."""
        assert harmonize_voucher_type(None) == "Unknown"
        assert harmonize_voucher_type("") == "Unknown"
        assert harmonize_voucher_type("   ") == "Unknown"
        assert harmonize_voucher_type(pd.NA) == "Unknown"

    def test_harmonize_unknown_types(self):
        """Test that unknown voucher types map to 'other'."""
        assert harmonize_voucher_type("SomethingRandom") == "other"
        assert harmonize_voucher_type("UNKNOWN") == "other"
        assert harmonize_voucher_type("XYZ123") == "other"


class TestBuildTargetValuesPivotLocal:
    """Tests for build_target_values_pivot_local function."""

    def test_single_table_basic_aggregation(self):
        """Test basic aggregation with single input table."""
        df = pd.DataFrame({
            'country_code': ['NG', 'NG', 'EG'],
            'category': ['Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit', 'refund'],
            'amount_local': [1000.0, 2000.0, 500.0]
        })
        
        result = build_target_values_pivot_local(df)
        
        # Check schema
        assert list(result.columns) == ['country_code', 'category', 'voucher_type', 'tv_amount_local']
        
        # Check row count (3 unique combinations)
        assert len(result) == 3
        
        # Check aggregation
        ng_refund = result[
            (result['country_code'] == 'NG') & 
            (result['voucher_type'] == 'refund')
        ]
        assert len(ng_refund) == 1
        assert ng_refund['tv_amount_local'].iloc[0] == 1000.0

    def test_multiple_tables_concatenation(self):
        """Test aggregation across multiple input tables."""
        issuance_df = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'refund'],
            'amount_local': [1000.0, 2000.0]
        })
        
        usage_df = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'amount_local': [-500.0]
        })
        
        result = build_target_values_pivot_local([issuance_df, usage_df])
        
        # Should aggregate across both tables
        ng_refund = result[
            (result['country_code'] == 'NG') & 
            (result['voucher_type'] == 'refund')
        ]
        assert len(ng_refund) == 1
        # 1000 + 2000 - 500 = 2500
        assert ng_refund['tv_amount_local'].iloc[0] == 2500.0

    def test_voucher_type_harmonization(self):
        """Test that voucher types are harmonized before aggregation."""
        df = pd.DataFrame({
            'country_code': ['NG', 'NG', 'NG'],
            'category': ['Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['Refund', 'REFUND', 'rf_'],  # Different labels
            'amount_local': [100.0, 200.0, 300.0]
        })
        
        result = build_target_values_pivot_local(df)
        
        # All should be aggregated under canonical 'refund'
        refund_rows = result[result['voucher_type'] == 'refund']
        assert len(refund_rows) == 1
        assert refund_rows['tv_amount_local'].iloc[0] == 600.0

    def test_missing_voucher_type(self):
        """Test handling of missing voucher_type values."""
        df = pd.DataFrame({
            'country_code': ['NG', 'NG', 'EG'],
            'category': ['Voucher', 'Voucher', 'Voucher'],
            'voucher_type': [None, '', 'refund'],
            'amount_local': [100.0, 200.0, 300.0]
        })
        
        result = build_target_values_pivot_local(df)
        
        # Missing voucher types should be 'Unknown'
        unknown_rows = result[result['voucher_type'] == 'Unknown']
        assert len(unknown_rows) == 1
        # 100 + 200 = 300
        assert unknown_rows['tv_amount_local'].iloc[0] == 300.0
        
        # Refund should be separate
        refund_rows = result[result['voucher_type'] == 'refund']
        assert len(refund_rows) == 1
        assert refund_rows['tv_amount_local'].iloc[0] == 300.0

    def test_empty_dataset(self):
        """Test that empty datasets return empty DataFrame with correct schema."""
        df = pd.DataFrame(columns=['country_code', 'category', 'voucher_type', 'amount_local'])
        
        result = build_target_values_pivot_local(df)
        
        # Should return empty DataFrame with correct columns
        assert list(result.columns) == ['country_code', 'category', 'voucher_type', 'tv_amount_local']
        assert len(result) == 0

    def test_empty_list_input(self):
        """Test handling of empty list or None DataFrames."""
        result = build_target_values_pivot_local([])
        
        assert list(result.columns) == ['country_code', 'category', 'voucher_type', 'tv_amount_local']
        assert len(result) == 0

    def test_none_dataframes_in_list(self):
        """Test that None DataFrames in list are filtered out."""
        valid_df = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'amount_local': [100.0]
        })
        
        result = build_target_values_pivot_local([None, valid_df, None])
        
        assert len(result) == 1
        assert result['tv_amount_local'].iloc[0] == 100.0

    def test_missing_required_columns(self):
        """Test that missing required columns raise ValueError."""
        df = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            # Missing voucher_type
            'amount_local': [100.0]
        })
        
        with pytest.raises(ValueError, match="Required columns missing"):
            build_target_values_pivot_local(df)

    def test_custom_amount_column(self):
        """Test using custom amount column name."""
        df = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'remaining_amount': [1500.0]  # Custom column name
        })
        
        result = build_target_values_pivot_local(df, amount_col='remaining_amount')
        
        assert len(result) == 1
        assert result['tv_amount_local'].iloc[0] == 1500.0

    def test_custom_group_columns(self):
        """Test using custom grouping columns."""
        df = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'refund'],
            'subcategory': ['A', 'B'],  # Additional grouping dimension
            'amount_local': [100.0, 200.0]
        })
        
        result = build_target_values_pivot_local(
            df,
            group_cols=['country_code', 'category', 'voucher_type', 'subcategory']
        )
        
        # Should have 2 rows (one per subcategory)
        assert len(result) == 2
        assert 'subcategory' in result.columns

    def test_multi_country_aggregation(self):
        """Test aggregation across multiple countries."""
        df = pd.DataFrame({
            'country_code': ['NG', 'NG', 'EG', 'EG', 'KE'],
            'category': ['Voucher', 'Voucher', 'Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit', 'refund', 'apology', 'refund'],
            'amount_local': [1000.0, 2000.0, 500.0, 300.0, 1500.0]
        })
        
        result = build_target_values_pivot_local(df)
        
        # Check country-specific aggregations
        ng_rows = result[result['country_code'] == 'NG']
        assert len(ng_rows) == 2  # refund + store_credit
        
        eg_rows = result[result['country_code'] == 'EG']
        assert len(eg_rows) == 2  # refund + apology
        
        ke_rows = result[result['country_code'] == 'KE']
        assert len(ke_rows) == 1  # refund only

    def test_deterministic_sorting(self):
        """Test that output is deterministically sorted."""
        df = pd.DataFrame({
            'country_code': ['KE', 'NG', 'EG', 'NG'],
            'category': ['Voucher', 'Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit', 'refund', 'refund'],
            'amount_local': [100.0, 200.0, 300.0, 400.0]
        })
        
        result = build_target_values_pivot_local(df)
        
        # Should be sorted by (country_code, category, voucher_type)
        expected_order = [
            ('EG', 'Voucher', 'refund'),
            ('KE', 'Voucher', 'refund'),
            ('NG', 'Voucher', 'refund'),
            ('NG', 'Voucher', 'store_credit'),
        ]
        
        actual_order = [
            (row['country_code'], row['category'], row['voucher_type'])
            for _, row in result.iterrows()
        ]
        
        assert actual_order == expected_order

    def test_numeric_coercion(self):
        """Test that amount columns are properly coerced to numeric."""
        df = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'amount_local': ['1,234.56']  # String with comma
        })
        
        result = build_target_values_pivot_local(df)
        
        # Should coerce string to float
        assert result['tv_amount_local'].iloc[0] == 1234.56

    def test_negative_amounts_preserved(self):
        """Test that negative amounts (usage) are preserved."""
        df = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'refund'],
            'amount_local': [1000.0, -500.0]  # Issuance + Usage
        })
        
        result = build_target_values_pivot_local(df)
        
        # Should net to 500.0
        assert result['tv_amount_local'].iloc[0] == 500.0

    def test_zero_amounts_included(self):
        """Test that zero amounts are included in aggregation."""
        df = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'refund'],
            'amount_local': [1000.0, 0.0]
        })
        
        result = build_target_values_pivot_local(df)
        
        assert result['tv_amount_local'].iloc[0] == 1000.0

    def test_nan_amounts_filled_to_zero(self):
        """Test that NaN amounts are filled to 0.0 for aggregation safety."""
        df = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'refund'],
            'amount_local': [1000.0, None]
        })
        
        result = build_target_values_pivot_local(df)
        
        # NaN should be treated as 0.0
        assert result['tv_amount_local'].iloc[0] == 1000.0

    def test_missing_category_column(self):
        """Test that missing category column is auto-filled with default."""
        df = pd.DataFrame({
            'country_code': ['NG', 'EG'],
            'voucher_type': ['refund', 'store_credit'],
            'amount_local': [1000.0, 2000.0]
        })
        
        result = build_target_values_pivot_local(df)
        
        # Should have category column with default value
        assert 'category' in result.columns
        assert all(result['category'] == 'Voucher')

    def test_custom_default_category(self):
        """Test using custom default category value."""
        df = pd.DataFrame({
            'country_code': ['NG'],
            'voucher_type': ['refund'],
            'amount_local': [1000.0]
        })
        
        result = build_target_values_pivot_local(df, default_category='CustomCategory')
        
        assert result['category'].iloc[0] == 'CustomCategory'


class TestPivotIntegration:
    """Integration tests for pivot functions with realistic data."""

    def test_realistic_voucher_lifecycle(self):
        """Test realistic voucher lifecycle with issuance, usage, and expiration."""
        # Issuance data (IPE_08)
        issuance = pd.DataFrame({
            'country_code': ['NG', 'NG', 'EG'],
            'category': ['Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['Refund', 'Store Credit', 'Apology'],
            'amount_local': [5000.0, 10000.0, 2000.0]
        })
        
        # Usage data (DOC_VOUCHER_USAGE)
        usage = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit'],  # Different case
            'amount_local': [-1500.0, -3000.0]
        })
        
        # Expired data
        expired = pd.DataFrame({
            'country_code': ['EG'],
            'category': ['Voucher'],
            'voucher_type': ['Expired'],
            'amount_local': [-500.0]
        })
        
        result = build_target_values_pivot_local([issuance, usage, expired])
        
        # Check NG refund: 5000 - 1500 = 3500
        ng_refund = result[
            (result['country_code'] == 'NG') & 
            (result['voucher_type'] == 'refund')
        ]
        assert ng_refund['tv_amount_local'].iloc[0] == 3500.0
        
        # Check NG store_credit: 10000 - 3000 = 7000
        ng_sc = result[
            (result['country_code'] == 'NG') & 
            (result['voucher_type'] == 'store_credit')
        ]
        assert ng_sc['tv_amount_local'].iloc[0] == 7000.0
        
        # Check EG apology: 2000 (unchanged)
        eg_apology = result[
            (result['country_code'] == 'EG') & 
            (result['voucher_type'] == 'apology')
        ]
        assert eg_apology['tv_amount_local'].iloc[0] == 2000.0
        
        # Check EG expired: -500
        eg_expired = result[
            (result['country_code'] == 'EG') & 
            (result['voucher_type'] == 'expired')
        ]
        assert eg_expired['tv_amount_local'].iloc[0] == -500.0
from src.core.reconciliation.analysis.pivots import build_nav_pivot


class TestBuildNavPivot:
    """Tests for build_nav_pivot() function."""

    def test_basic_pivot_structure(self):
        """Test basic pivot generation with simple categorized data."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage', 'VTC'],
            'voucher_type': ['Refund', 'Store Credit', 'Apology'],
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
        refund_row = nav_pivot.loc[('Issuance', 'refund'), :]
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
        issuance_count = nav_pivot.loc[('Issuance', 'refund'), 'row_count']
        usage_count = nav_pivot.loc[('Usage', 'store_credit'), 'row_count']
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
        """Test handling of mixed data types in amount column.
        
        Uses canonical voucher types per schema.
        """
        # Arrange - Mix of int and float
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage', 'VTC'],
            'voucher_type': ['Refund', 'Store Credit', 'Refund'],
            'amount': [-1000, 500.5, 300],  # Mix of int and float
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert - Should handle mixed types correctly
        assert not nav_pivot.empty
        total_amount = nav_pivot.loc[('__TOTAL__', ''), 'amount_lcy']
        assert total_amount == pytest.approx(-199.5, rel=1e-5)
    
    def test_zero_amounts_handled_correctly(self):
        """Test that zero amounts are included in the pivot.
        
        Uses canonical voucher types per schema.
        """
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage', 'VTC'],
            'voucher_type': ['Refund', 'Store Credit', 'Refund'],
            'amount': [0.0, 0.0, 100.0],
        })
        
        # Act
        nav_pivot, nav_lines = build_nav_pivot(cr_03_df, dataset_id='CR_03')
        
        # Assert
        issuance_amount = nav_pivot.loc[('Issuance', 'refund'), 'amount_lcy']
        usage_amount = nav_pivot.loc[('Usage', 'store_credit'), 'amount_lcy']
        
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
        assert ('Issuance', 'refund') in nav_pivot.index
        assert ('Issuance', 'apology') in nav_pivot.index
        assert ('Issuance', 'jforce') in nav_pivot.index
    
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
        assert ('Issuance', 'refund') in nav_pivot.index
        assert ('Usage', 'store_credit') in nav_pivot.index


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
        assert nav_pivot.loc[('Issuance', 'refund'), 'amount_lcy'] == -1000.0
    
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
        """Test that 'amount' column is renamed to 'amount_lcy' in output (default currency)."""
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
    
    def test_currency_name_parameter(self):
        """Test that currency_name parameter dynamically names the output column."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance', 'Usage'],
            'voucher_type': ['Refund', 'Store Credit'],
            'amount': [-1000.0, 500.0],
        })
        
        # Act - Test with NGN currency
        nav_pivot_ngn, nav_lines_ngn = build_nav_pivot(cr_03_df, dataset_id='CR_03', currency_name='NGN')
        
        # Assert
        assert 'amount_ngn' in nav_pivot_ngn.columns
        assert 'amount_ngn' in nav_lines_ngn.columns
        assert nav_pivot_ngn.loc[('__TOTAL__', ''), 'amount_ngn'] == -500.0
        
        # Act - Test with EGP currency
        nav_pivot_egp, nav_lines_egp = build_nav_pivot(cr_03_df, dataset_id='CR_03', currency_name='EGP')
        
        # Assert
        assert 'amount_egp' in nav_pivot_egp.columns
        assert 'amount_egp' in nav_lines_egp.columns
        assert nav_pivot_egp.loc[('__TOTAL__', ''), 'amount_egp'] == -500.0
    
    def test_currency_name_validation(self):
        """Test that invalid currency_name raises ValueError."""
        # Arrange
        cr_03_df = pd.DataFrame({
            'bridge_category': ['Issuance'],
            'voucher_type': ['Refund'],
            'amount': [-1000.0],
        })
        
        # Act & Assert - Invalid characters
        with pytest.raises(ValueError, match="Invalid currency_name"):
            build_nav_pivot(cr_03_df, dataset_id='CR_03', currency_name='NG$')
        
        with pytest.raises(ValueError, match="Invalid currency_name"):
            build_nav_pivot(cr_03_df, dataset_id='CR_03', currency_name='')
        
        with pytest.raises(ValueError, match="Invalid currency_name"):
            build_nav_pivot(cr_03_df, dataset_id='CR_03', currency_name='NG-N')


class TestIntegrationScenarios:
    """Tests for realistic integration scenarios."""
    
    def test_realistic_reconciliation_scenario(self):
        """Test with realistic data resembling actual reconciliation output.
        
        Uses canonical allowed values per schema:
        - Categories: Issuance, Cancellation, Usage, Expired, VTC
        - Voucher Types: Refund, Apology, JForce, Store Credit
        """
        # Arrange - Representative fixture data with canonical category/voucher type values
        cr_03_df = pd.DataFrame({
            'bridge_category': [
                'Issuance', 'Issuance', 'Usage', 'Usage',
                'VTC', 'Expired', 'Cancellation'
            ],
            'voucher_type': [
                'Refund', 'Apology', 'Store Credit', 'Store Credit',
                'Refund', 'Apology', 'Store Credit'
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
        assert len(categories) == 5  # 5 distinct canonical categories (Issuance, Cancellation, Usage, Expired, VTC)
        
        # Verify all categories are from the canonical schema
        canonical_categories = {'Issuance', 'Cancellation', 'Usage', 'Expired', 'VTC'}
        assert set(categories) == canonical_categories, f"Categories should match canonical schema. Got: {set(categories)}"
        
        # Verify all voucher types are from the canonical schema (or Unknown)
        voucher_types = nav_lines['voucher_type'].unique()
        canonical_voucher_types = {'refund', 'apology', 'jforce', 'store_credit', 'Unknown'}
        assert set(voucher_types).issubset(canonical_voucher_types), f"Voucher types should be from canonical schema. Got: {set(voucher_types)}"
        
        # Verify lines DataFrame preserves country_code
        assert all(nav_lines['country_code'] == 'NG')


class TestEndToEndPivotToVariance:
    """End-to-end tests for pivot generation → variance computation workflow."""
    
    def test_end_to_end_pivot_to_variance(self):
        """
        Test complete workflow from pivots to variance computation.
        
        This test validates the integration between:
        1. build_target_values_pivot_local() - TV pivot generation
        2. compute_variance_pivot_local() - Variance computation with FX conversion
        
        Note: NAV pivot typically uses build_nav_pivot() which returns MultiIndex structure.
        For variance computation, a flattened NAV pivot with country_code is expected.
        This test demonstrates the expected input format for variance computation.
        """
        from src.core.reconciliation.analysis.variance import compute_variance_pivot_local
        from src.utils.fx_utils import FXConverter
        
        # Step 1: Build TV pivot from raw issuance/usage data
        issuance_df = pd.DataFrame({
            'country_code': ['NG', 'NG', 'EG', 'EG'],
            'category': ['Voucher', 'Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['Refund', 'Store Credit', 'Refund', 'Apology'],
            'amount_local': [1485000.0, 3135000.0, 44010.0, 24450.0]
        })
        
        usage_df = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'amount_local': [0.0]  # No usage in this period
        })
        
        tv_pivot = build_target_values_pivot_local([issuance_df, usage_df])
        
        # Verify TV pivot structure
        assert list(tv_pivot.columns) == ['country_code', 'category', 'voucher_type', 'tv_amount_local']
        assert len(tv_pivot) == 4
        
        # Step 2: Create NAV pivot (simulated - would come from build_nav_pivot)
        # In real workflow, NAV pivot would be flattened from MultiIndex structure
        # with country_code added to match TV pivot grain
        nav_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG', 'EG', 'EG'],
            'category': ['Voucher', 'Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit', 'refund', 'apology'],
            'nav_amount_local': [1650000.0, 3300000.0, 48900.0, 24450.0]
        })
        
        # Step 3: Prepare FX converter
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG', 'JM_EG'],
            'FX_rate': [1650.0, 48.9]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Step 4: Compute variance with FX conversion
        variance_df = compute_variance_pivot_local(
            nav_pivot_local_df=nav_pivot,
            tv_pivot_local_df=tv_pivot,
            fx_converter=fx_converter,
            cutoff_date="2025-09-30"
        )
        
        # Step 5: Validate results
        assert len(variance_df) == 4
        
        # Check NG refund variance
        ng_refund = variance_df[
            (variance_df['country_code'] == 'NG') & 
            (variance_df['voucher_type'] == 'refund')
        ].iloc[0]
        
        assert ng_refund['nav_amount_local'] == 1650000.0
        assert ng_refund['tv_amount_local'] == 1485000.0
        assert ng_refund['variance_amount_local'] == 165000.0  # 1650000 - 1485000
        assert ng_refund['variance_amount_usd'] == pytest.approx(100.0, rel=1e-6)  # 165000 / 1650
        assert ng_refund['fx_rate_used'] == 1650.0
        assert ng_refund['fx_missing'] == False
        
        # Check EG apology perfect match
        eg_apology = variance_df[
            (variance_df['country_code'] == 'EG') & 
            (variance_df['voucher_type'] == 'apology')
        ].iloc[0]
        
        assert eg_apology['variance_amount_local'] == 0.0  # Perfect match
        assert eg_apology['variance_amount_usd'] == 0.0
        
        # Verify all required columns exist
        expected_columns = [
            'country_code', 'category', 'voucher_type',
            'nav_amount_local', 'tv_amount_local', 'variance_amount_local',
            'nav_amount_usd', 'tv_amount_usd', 'variance_amount_usd',
            'fx_rate_used', 'fx_missing'
        ]
        assert list(variance_df.columns) == expected_columns
    
    def test_end_to_end_with_missing_buckets(self):
        """
        Test end-to-end workflow with buckets missing from NAV or TV.
        
        Validates that outer join preserves all buckets from both sides.
        """
        from src.core.reconciliation.analysis.variance import compute_variance_pivot_local
        from src.utils.fx_utils import FXConverter
        
        # TV pivot has 'expired' bucket that NAV doesn't have
        tv_pivot = build_target_values_pivot_local(
            pd.DataFrame({
                'country_code': ['NG', 'NG'],
                'category': ['Voucher', 'Voucher'],
                'voucher_type': ['refund', 'expired'],
                'amount_local': [1000.0, 500.0]
            })
        )
        
        # NAV pivot has 'jforce' bucket that TV doesn't have
        nav_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'jforce'],
            'nav_amount_local': [1100.0, 300.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Compute variance
        variance_df = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Should have 3 buckets: refund (both), expired (TV only), jforce (NAV only)
        assert len(variance_df) == 3
        
        # Check expired (TV only) - nav should be 0
        expired_row = variance_df[variance_df['voucher_type'] == 'expired'].iloc[0]
        assert expired_row['nav_amount_local'] == 0.0
        assert expired_row['tv_amount_local'] == 500.0
        assert expired_row['variance_amount_local'] == -500.0
        
        # Check jforce (NAV only) - tv should be 0
        jforce_row = variance_df[variance_df['voucher_type'] == 'jforce'].iloc[0]
        assert jforce_row['nav_amount_local'] == 300.0
        assert jforce_row['tv_amount_local'] == 0.0
        assert jforce_row['variance_amount_local'] == 300.0
        
        # Check refund (both) - normal variance
        refund_row = variance_df[variance_df['voucher_type'] == 'refund'].iloc[0]
        assert refund_row['variance_amount_local'] == 100.0  # 1100 - 1000
