"""
Unit tests for variance calculation functions.

Tests the compute_variance_pivot_local() function which:
1. Outer-joins NAV and TV pivots on (country_code, category, voucher_type)
2. Fills missing amounts with 0.0
3. Computes variance in local currency (NAV - TV)
4. Applies FX conversion to get USD columns
5. Returns DataFrame with both local and USD amounts

Test Coverage:
- Join completeness (missing NAV/TV buckets are preserved)
- Correct variance math (NAV - TV)
- FX conversion applied after variance computation
- Missing FX rate behavior (NaN USD, fx_missing flag)
- Single and multi-country scenarios
- Deterministic ordering
"""

import pandas as pd
import pytest

from src.core.reconciliation.analysis.variance import (
    compute_variance_pivot_local,
    _map_country_to_company,
)
from src.utils.fx_utils import FXConverter


class TestMapCountryToCompany:
    """Tests for country code to Company_Code mapping."""
    
    def test_standard_countries_use_ec_prefix(self):
        """Test that most countries use EC_ prefix."""
        assert _map_country_to_company('NG') == 'EC_NG'
        assert _map_country_to_company('KE') == 'EC_KE'
        assert _map_country_to_company('TZ') == 'EC_TZ'
        assert _map_country_to_company('MA') == 'EC_MA'
        assert _map_country_to_company('CI') == 'EC_CI'
    
    def test_special_egypt_mapping(self):
        """Test that Egypt uses JM_ prefix."""
        assert _map_country_to_company('EG') == 'JM_EG'
    
    def test_special_ghana_mapping(self):
        """Test that Ghana uses JD_ prefix."""
        assert _map_country_to_company('GH') == 'JD_GH'
    
    def test_case_insensitive(self):
        """Test that mapping is case-insensitive."""
        assert _map_country_to_company('ng') == 'EC_NG'
        assert _map_country_to_company('Ng') == 'EC_NG'
        assert _map_country_to_company('eg') == 'JM_EG'
    
    def test_null_country_returns_none(self):
        """Test that None/NaN country code returns None."""
        assert _map_country_to_company(None) is None
        assert _map_country_to_company(pd.NA) is None
    
    def test_unknown_country_gets_ec_prefix(self):
        """Test that unknown countries default to EC_ prefix."""
        assert _map_country_to_company('UNKNOWN') == 'EC_UNKNOWN'
        assert _map_country_to_company('XX') == 'EC_XX'


class TestComputeVariancePivotLocal:
    """Tests for compute_variance_pivot_local function."""
    
    def test_basic_variance_computation(self):
        """Test basic variance computation with single country."""
        # Arrange
        nav_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit'],
            'nav_amount_local': [1000.0, 2000.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit'],
            'tv_amount_local': [900.0, 1800.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert
        assert len(result) == 2
        
        # Check variance computation: NAV - TV
        refund_row = result[result['voucher_type'] == 'refund'].iloc[0]
        assert refund_row['nav_amount_local'] == 1000.0
        assert refund_row['tv_amount_local'] == 900.0
        assert refund_row['variance_amount_local'] == 100.0  # 1000 - 900
        
        sc_row = result[result['voucher_type'] == 'store_credit'].iloc[0]
        assert sc_row['variance_amount_local'] == 200.0  # 2000 - 1800
    
    def test_join_completeness_missing_nav_bucket(self):
        """Test that missing NAV buckets are preserved with nav_amount_local=0."""
        # Arrange - TV has 'apology' but NAV doesn't
        nav_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'nav_amount_local': [1000.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'apology'],
            'tv_amount_local': [900.0, 500.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Both buckets should exist
        assert len(result) == 2
        
        # Check apology bucket has nav_amount_local=0
        apology_row = result[result['voucher_type'] == 'apology'].iloc[0]
        assert apology_row['nav_amount_local'] == 0.0
        assert apology_row['tv_amount_local'] == 500.0
        assert apology_row['variance_amount_local'] == -500.0  # 0 - 500
    
    def test_join_completeness_missing_tv_bucket(self):
        """Test that missing TV buckets are preserved with tv_amount_local=0."""
        # Arrange - NAV has 'jforce' but TV doesn't
        nav_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG'],
            'category': ['Voucher', 'Voucher'],
            'voucher_type': ['refund', 'jforce'],
            'nav_amount_local': [1000.0, 300.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'tv_amount_local': [900.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Both buckets should exist
        assert len(result) == 2
        
        # Check jforce bucket has tv_amount_local=0
        jforce_row = result[result['voucher_type'] == 'jforce'].iloc[0]
        assert jforce_row['nav_amount_local'] == 300.0
        assert jforce_row['tv_amount_local'] == 0.0
        assert jforce_row['variance_amount_local'] == 300.0  # 300 - 0
    
    def test_fx_conversion_applied_after_variance(self):
        """Test that FX conversion is applied to all amount columns."""
        # Arrange
        nav_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'nav_amount_local': [1650000.0]  # 1,650,000 NGN
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'tv_amount_local': [1485000.0]  # 1,485,000 NGN
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]  # 1 USD = 1650 NGN
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Check USD conversion
        row = result.iloc[0]
        
        # NAV: 1,650,000 / 1650 = 1000 USD
        assert row['nav_amount_usd'] == pytest.approx(1000.0, rel=1e-6)
        
        # TV: 1,485,000 / 1650 = 900 USD
        assert row['tv_amount_usd'] == pytest.approx(900.0, rel=1e-6)
        
        # Variance: 165,000 / 1650 = 100 USD
        assert row['variance_amount_usd'] == pytest.approx(100.0, rel=1e-6)
        
        # Check audit fields
        assert row['fx_rate_used'] == 1650.0
        assert row['fx_missing'] == False
    
    def test_missing_fx_rate_behavior(self):
        """Test that missing FX rates result in NaN USD and fx_missing=True."""
        # Arrange
        nav_pivot = pd.DataFrame({
            'country_code': ['KE'],  # Kenya - no FX rate available
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'nav_amount_local': [142000.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['KE'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'tv_amount_local': [128000.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],  # Only NG rate, no KE rate
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df, default_rate=1.0)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - With default_rate=1.0, USD equals local amount
        row = result.iloc[0]
        
        # FX rate should be None/NaN (not in rates_dict)
        assert pd.isna(row['fx_rate_used'])
        assert row['fx_missing'] == True
        
        # With default_rate=1.0, convert_to_usd uses amount / default_rate, so USD == local amount
        assert row['nav_amount_usd'] == 142000.0
        assert row['tv_amount_usd'] == 128000.0
        assert row['variance_amount_usd'] == 14000.0
    
    def test_multi_country_scenario(self):
        """Test variance computation across multiple countries."""
        # Arrange
        nav_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG', 'EG', 'EG'],
            'category': ['Voucher', 'Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit', 'refund', 'apology'],
            'nav_amount_local': [1650000.0, 3300000.0, 48900.0, 24450.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG', 'EG'],
            'category': ['Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit', 'refund'],
            'tv_amount_local': [1485000.0, 3135000.0, 44010.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG', 'JM_EG'],
            'FX_rate': [1650.0, 48.9]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert
        assert len(result) == 4  # 3 from both + 1 only in NAV
        
        # Check NG refund
        ng_refund = result[
            (result['country_code'] == 'NG') & 
            (result['voucher_type'] == 'refund')
        ].iloc[0]
        assert ng_refund['variance_amount_local'] == 165000.0
        assert ng_refund['variance_amount_usd'] == pytest.approx(100.0, rel=1e-6)
        
        # Check EG apology (only in NAV)
        eg_apology = result[
            (result['country_code'] == 'EG') & 
            (result['voucher_type'] == 'apology')
        ].iloc[0]
        assert eg_apology['nav_amount_local'] == 24450.0
        assert eg_apology['tv_amount_local'] == 0.0
        assert eg_apology['variance_amount_local'] == 24450.0
        assert eg_apology['variance_amount_usd'] == pytest.approx(500.0, rel=1e-6)
    
    def test_deterministic_ordering(self):
        """Test that output is deterministically sorted."""
        # Arrange - Create data in non-sorted order
        nav_pivot = pd.DataFrame({
            'country_code': ['NG', 'KE', 'EG', 'NG'],
            'category': ['Voucher', 'Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['store_credit', 'refund', 'refund', 'refund'],
            'nav_amount_local': [2000.0, 1500.0, 500.0, 1000.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['EG', 'KE', 'NG', 'NG'],
            'category': ['Voucher', 'Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['refund', 'refund', 'refund', 'store_credit'],
            'tv_amount_local': [450.0, 1400.0, 900.0, 1900.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG', 'EC_KE', 'JM_EG'],
            'FX_rate': [1650.0, 142.0, 48.9]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Should be sorted by (country_code, category, voucher_type)
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
    
    def test_output_schema(self):
        """Test that output has all required columns in correct order."""
        # Arrange
        nav_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'nav_amount_local': [1000.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'tv_amount_local': [900.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Check column schema
        expected_columns = [
            'country_code',
            'category',
            'voucher_type',
            'nav_amount_local',
            'tv_amount_local',
            'variance_amount_local',
            'nav_amount_usd',
            'tv_amount_usd',
            'variance_amount_usd',
            'fx_rate_used',
            'fx_missing',
        ]
        
        assert list(result.columns) == expected_columns
    
    def test_empty_nav_pivot(self):
        """Test handling of empty NAV pivot."""
        # Arrange
        nav_pivot = pd.DataFrame(columns=[
            'country_code', 'category', 'voucher_type', 'nav_amount_local'
        ])
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'tv_amount_local': [900.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Should have TV row with nav_amount_local=0
        assert len(result) == 1
        row = result.iloc[0]
        assert row['nav_amount_local'] == 0.0
        assert row['tv_amount_local'] == 900.0
        assert row['variance_amount_local'] == -900.0
    
    def test_empty_tv_pivot(self):
        """Test handling of empty TV pivot."""
        # Arrange
        nav_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'nav_amount_local': [1000.0]
        })
        
        tv_pivot = pd.DataFrame(columns=[
            'country_code', 'category', 'voucher_type', 'tv_amount_local'
        ])
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Should have NAV row with tv_amount_local=0
        assert len(result) == 1
        row = result.iloc[0]
        assert row['nav_amount_local'] == 1000.0
        assert row['tv_amount_local'] == 0.0
        assert row['variance_amount_local'] == 1000.0
    
    def test_negative_variance(self):
        """Test that negative variances (TV > NAV) are computed correctly."""
        # Arrange
        nav_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'nav_amount_local': [800.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'tv_amount_local': [1000.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Variance should be negative
        row = result.iloc[0]
        assert row['variance_amount_local'] == -200.0  # 800 - 1000
        assert row['variance_amount_usd'] < 0
    
    def test_zero_variance(self):
        """Test that zero variance (perfect match) is computed correctly."""
        # Arrange
        nav_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'nav_amount_local': [1650000.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'tv_amount_local': [1650000.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Variance should be zero
        row = result.iloc[0]
        assert row['variance_amount_local'] == 0.0
        assert row['variance_amount_usd'] == 0.0
    
    def test_missing_required_columns_nav(self):
        """Test that missing required columns in NAV pivot raise ValueError."""
        # Arrange - Missing voucher_type
        nav_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'nav_amount_local': [1000.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'tv_amount_local': [900.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Required columns missing from NAV pivot"):
            compute_variance_pivot_local(
                nav_pivot, tv_pivot, fx_converter, "2025-09-30"
            )
    
    def test_missing_required_columns_tv(self):
        """Test that missing required columns in TV pivot raise ValueError."""
        # Arrange - Missing country_code
        nav_pivot = pd.DataFrame({
            'country_code': ['NG'],
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'nav_amount_local': [1000.0]
        })
        
        tv_pivot = pd.DataFrame({
            'category': ['Voucher'],
            'voucher_type': ['refund'],
            'tv_amount_local': [900.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG'],
            'FX_rate': [1650.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Required columns missing from TV pivot"):
            compute_variance_pivot_local(
                nav_pivot, tv_pivot, fx_converter, "2025-09-30"
            )


class TestIntegrationScenarios:
    """Integration tests with realistic data scenarios."""
    
    def test_realistic_multi_country_reconciliation(self):
        """Test realistic reconciliation scenario with multiple countries and voucher types."""
        # Arrange - Realistic data with multiple countries
        nav_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG', 'NG', 'EG', 'EG', 'KE', 'KE'],
            'category': ['Voucher', 'Voucher', 'Voucher', 'Voucher', 'Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit', 'apology', 'refund', 'store_credit', 'refund', 'jforce'],
            'nav_amount_local': [5000000.0, 8000000.0, 2000000.0, 150000.0, 100000.0, 500000.0, 200000.0]
        })
        
        tv_pivot = pd.DataFrame({
            'country_code': ['NG', 'NG', 'NG', 'EG', 'EG', 'KE'],
            'category': ['Voucher', 'Voucher', 'Voucher', 'Voucher', 'Voucher', 'Voucher'],
            'voucher_type': ['refund', 'store_credit', 'jforce', 'refund', 'store_credit', 'refund'],
            'tv_amount_local': [4800000.0, 7900000.0, 300000.0, 145000.0, 98000.0, 480000.0]
        })
        
        cr05_df = pd.DataFrame({
            'Company_Code': ['EC_NG', 'JM_EG', 'EC_KE'],
            'FX_rate': [1650.0, 48.9, 142.0]
        })
        fx_converter = FXConverter(cr05_df)
        
        # Act
        result = compute_variance_pivot_local(
            nav_pivot, tv_pivot, fx_converter, "2025-09-30"
        )
        
        # Assert - Check overall structure
        assert len(result) == 8  # 7 NAV + 1 only in TV (NG jforce)
        
        # All rows should have FX rates (no missing)
        assert result['fx_missing'].sum() == 0
        
        # Check specific variances
        ng_refund = result[
            (result['country_code'] == 'NG') & 
            (result['voucher_type'] == 'refund')
        ].iloc[0]
        assert ng_refund['variance_amount_local'] == 200000.0
        assert ng_refund['variance_amount_usd'] == pytest.approx(121.21, rel=1e-2)
        
        # NG apology only in NAV
        ng_apology = result[
            (result['country_code'] == 'NG') & 
            (result['voucher_type'] == 'apology')
        ].iloc[0]
        assert ng_apology['tv_amount_local'] == 0.0
        assert ng_apology['variance_amount_local'] == 2000000.0
        
        # NG jforce only in TV
        ng_jforce = result[
            (result['country_code'] == 'NG') & 
            (result['voucher_type'] == 'jforce')
        ].iloc[0]
        assert ng_jforce['nav_amount_local'] == 0.0
        assert ng_jforce['variance_amount_local'] == -300000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
