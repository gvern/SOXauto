"""
Tests for FX conversion utilities (fx_utils.py).

Tests the FXConverter class for converting local currency amounts to USD
using monthly FX rates from CR_05.
"""

import os
import sys
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.utils.fx_utils import FXConverter


def test_fx_converter_init_valid():
    """Test FXConverter initialization with valid CR_05 data."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH', 'EC_NG', 'EC_KE'],
        'FX_rate': [15.5, 4.0, 30.0]
    })
    
    converter = FXConverter(cr05_df)
    
    assert len(converter.rates_dict) == 3
    assert converter.rates_dict['JD_GH'] == 15.5
    assert converter.rates_dict['EC_NG'] == 4.0
    assert converter.rates_dict['EC_KE'] == 30.0


def test_fx_converter_init_empty_df():
    """Test FXConverter raises error with empty DataFrame."""
    empty_df = pd.DataFrame()
    
    with pytest.raises(ValueError, match="cannot be None or empty"):
        FXConverter(empty_df)


def test_fx_converter_init_none():
    """Test FXConverter raises error with None input."""
    with pytest.raises(ValueError, match="cannot be None or empty"):
        FXConverter(None)


def test_fx_converter_init_missing_columns():
    """Test FXConverter raises error when required columns are missing."""
    df_missing_rate = pd.DataFrame({
        'Company_Code': ['JD_GH', 'EC_NG']
    })
    
    with pytest.raises(ValueError, match="missing required columns"):
        FXConverter(df_missing_rate)


def test_fx_converter_init_with_nulls():
    """Test FXConverter handles null values correctly during initialization."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH', None, 'EC_KE', 'EC_TZ'],
        'FX_rate': [15.5, 4.0, None, 0.0]  # null company, null rate, zero rate
    })
    
    converter = FXConverter(cr05_df)
    
    # Should only have JD_GH (valid company and rate)
    # EC_KE has null rate, EC_TZ has zero rate, row 2 has null company
    assert len(converter.rates_dict) == 1
    assert converter.rates_dict['JD_GH'] == 15.5


def test_convert_to_usd_basic():
    """Test basic USD conversion."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH', 'EC_NG'],
        'FX_rate': [15.5, 4.0]
    })
    
    converter = FXConverter(cr05_df)
    
    # Test conversion: Amount_USD = Amount_LCY / FX_rate
    result = converter.convert_to_usd(1550.0, 'JD_GH')
    assert result == pytest.approx(100.0, rel=1e-6)
    
    result = converter.convert_to_usd(400.0, 'EC_NG')
    assert result == pytest.approx(100.0, rel=1e-6)


def test_convert_to_usd_unknown_company():
    """Test conversion with unknown company code uses default rate."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH'],
        'FX_rate': [15.5]
    })
    
    converter = FXConverter(cr05_df, default_rate=1.0)
    
    # Unknown company should use default rate (1.0)
    result = converter.convert_to_usd(100.0, 'UNKNOWN_CO')
    assert result == pytest.approx(100.0, rel=1e-6)


def test_convert_to_usd_null_amount():
    """Test conversion with null/NaN amount returns 0."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH'],
        'FX_rate': [15.5]
    })
    
    converter = FXConverter(cr05_df)
    
    result = converter.convert_to_usd(None, 'JD_GH')
    assert result == 0.0
    
    result = converter.convert_to_usd(pd.NA, 'JD_GH')
    assert result == 0.0


def test_convert_to_usd_null_company():
    """Test conversion with null company code uses default rate."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH'],
        'FX_rate': [15.5]
    })
    
    converter = FXConverter(cr05_df, default_rate=1.0)
    
    result = converter.convert_to_usd(100.0, None)
    assert result == pytest.approx(100.0, rel=1e-6)


def test_convert_series_to_usd():
    """Test vectorized series conversion."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH', 'EC_NG', 'EC_KE'],
        'FX_rate': [15.5, 4.0, 30.0]
    })
    
    converter = FXConverter(cr05_df)
    
    amounts = pd.Series([1550.0, 400.0, 3000.0])
    companies = pd.Series(['JD_GH', 'EC_NG', 'EC_KE'])
    
    result = converter.convert_series_to_usd(amounts, companies)
    
    assert result[0] == pytest.approx(100.0, rel=1e-6)
    assert result[1] == pytest.approx(100.0, rel=1e-6)
    assert result[2] == pytest.approx(100.0, rel=1e-6)


def test_convert_series_to_usd_length_mismatch():
    """Test that series conversion raises error on length mismatch."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH'],
        'FX_rate': [15.5]
    })
    
    converter = FXConverter(cr05_df)
    
    amounts = pd.Series([100.0, 200.0])
    companies = pd.Series(['JD_GH'])  # Different length
    
    with pytest.raises(ValueError, match="must have the same length"):
        converter.convert_series_to_usd(amounts, companies)


def test_convert_series_with_mixed_valid_invalid():
    """Test series conversion with mix of valid and invalid companies."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH', 'EC_NG'],
        'FX_rate': [15.5, 4.0]
    })
    
    converter = FXConverter(cr05_df, default_rate=1.0)
    
    amounts = pd.Series([1550.0, 400.0, 100.0])
    companies = pd.Series(['JD_GH', 'EC_NG', 'UNKNOWN'])
    
    result = converter.convert_series_to_usd(amounts, companies)
    
    # First two should convert with their rates
    assert result[0] == pytest.approx(100.0, rel=1e-6)
    assert result[1] == pytest.approx(100.0, rel=1e-6)
    # Third should use default rate (1.0)
    assert result[2] == pytest.approx(100.0, rel=1e-6)


def test_fx_converter_custom_default_rate():
    """Test FXConverter with custom default rate."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH'],
        'FX_rate': [15.5]
    })
    
    # Use custom default rate
    converter = FXConverter(cr05_df, default_rate=2.0)
    
    # Unknown company should use default rate (2.0)
    result = converter.convert_to_usd(200.0, 'UNKNOWN')
    assert result == pytest.approx(100.0, rel=1e-6)


def test_fx_converter_real_world_scenario():
    """Test FXConverter with realistic data scenario."""
    # Simulate real CR_05 data with multiple companies
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH', 'EC_NG', 'EC_KE', 'JM_EG', 'EC_MA'],
        'Company_Name': ['Jumia Ghana', 'Jumia Nigeria', 'Jumia Kenya', 'Jumia Egypt', 'Jumia Morocco'],
        'FX_rate': [15.5, 1650.0, 142.0, 48.9, 10.8]
    })
    
    converter = FXConverter(cr05_df)
    
    # Test Ghana conversion
    gh_amount_lcy = 15500.0  # 15,500 GHS
    gh_amount_usd = converter.convert_to_usd(gh_amount_lcy, 'JD_GH')
    assert gh_amount_usd == pytest.approx(1000.0, rel=1e-6)
    
    # Test Nigeria conversion (Naira has large denominations)
    ng_amount_lcy = 1650000.0  # 1,650,000 NGN
    ng_amount_usd = converter.convert_to_usd(ng_amount_lcy, 'EC_NG')
    assert ng_amount_usd == pytest.approx(1000.0, rel=1e-6)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
