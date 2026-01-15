"""
Unit tests for pivot generation functions.

Tests the Target Values pivot generation with local currency aggregation,
voucher type harmonization, and schema contract enforcement.
"""

import pandas as pd
import pytest

from src.core.reconciliation.analysis.pivots import (
    build_target_values_pivot_local,
    _harmonize_voucher_type,
)


class TestHarmonizeVoucherType:
    """Tests for voucher type harmonization function."""

    def test_harmonize_refund_variants(self):
        """Test that various refund labels map to canonical 'refund'."""
        assert _harmonize_voucher_type("Refund") == "refund"
        assert _harmonize_voucher_type("REFUND") == "refund"
        assert _harmonize_voucher_type("rf_") == "refund"
        assert _harmonize_voucher_type("RFN") == "refund"

    def test_harmonize_store_credit_variants(self):
        """Test that various store credit labels map to canonical 'store_credit'."""
        assert _harmonize_voucher_type("Store Credit") == "store_credit"
        assert _harmonize_voucher_type("STORE CREDIT") == "store_credit"
        assert _harmonize_voucher_type("store_credit") == "store_credit"
        assert _harmonize_voucher_type("storecredit") == "store_credit"

    def test_harmonize_apology_variants(self):
        """Test that apology-related labels map to canonical 'apology'."""
        assert _harmonize_voucher_type("Apology") == "apology"
        assert _harmonize_voucher_type("APOLOGY") == "apology"
        assert _harmonize_voucher_type("Commercial Gesture") == "apology"
        assert _harmonize_voucher_type("CXP") == "apology"

    def test_harmonize_jforce_variants(self):
        """Test that JForce labels map to canonical 'jforce'."""
        assert _harmonize_voucher_type("JForce") == "jforce"
        assert _harmonize_voucher_type("jforce") == "jforce"
        assert _harmonize_voucher_type("PYT_") == "jforce"
        assert _harmonize_voucher_type("pyt_pf") == "jforce"

    def test_harmonize_expired(self):
        """Test that expired labels map to canonical 'expired'."""
        assert _harmonize_voucher_type("Expired") == "expired"
        assert _harmonize_voucher_type("EXP") == "expired"

    def test_harmonize_vtc(self):
        """Test that VTC labels map to canonical 'vtc'."""
        assert _harmonize_voucher_type("VTC") == "vtc"
        assert _harmonize_voucher_type("Voucher to Cash") == "vtc"

    def test_harmonize_missing_values(self):
        """Test that missing/empty values map to 'Unknown'."""
        assert _harmonize_voucher_type(None) == "Unknown"
        assert _harmonize_voucher_type("") == "Unknown"
        assert _harmonize_voucher_type("   ") == "Unknown"
        assert _harmonize_voucher_type(pd.NA) == "Unknown"

    def test_harmonize_unknown_types(self):
        """Test that unknown voucher types map to 'other'."""
        assert _harmonize_voucher_type("SomethingRandom") == "other"
        assert _harmonize_voucher_type("UNKNOWN") == "other"
        assert _harmonize_voucher_type("XYZ123") == "other"


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
