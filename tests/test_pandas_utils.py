"""
Unit tests for pandas_utils module.

Tests cover:
- String to float conversion
- Comma handling ("1,234.56")
- NaN/empty string handling
- fillna behavior
- Mixed dtype scenarios
- Negative amounts
- Already-float passthrough
"""

import pandas as pd
import numpy as np
import pytest

from src.utils.pandas_utils import (
    coerce_numeric_series,
    cast_amount_columns,
    ensure_required_numeric,
)


class TestCoerceNumericSeries:
    """Tests for coerce_numeric_series function."""
    
    def test_string_to_float_conversion(self):
        """Test basic string to float conversion."""
        s = pd.Series(['100.5', '200.0', '300'])
        result = coerce_numeric_series(s)
        
        assert result.dtype == 'float64'
        assert result.tolist() == [100.5, 200.0, 300.0]
    
    def test_comma_handling(self):
        """Test handling of commas in string amounts."""
        s = pd.Series(['1,234.56', '2,000', '3,456,789.12'])
        result = coerce_numeric_series(s)
        
        assert result.dtype == 'float64'
        assert result[0] == 1234.56
        assert result[1] == 2000.0
        assert result[2] == 3456789.12
    
    def test_space_handling(self):
        """Test handling of spaces in string amounts."""
        s = pd.Series(['1 234.56', '2 000', ' 300 '])
        result = coerce_numeric_series(s)
        
        assert result.dtype == 'float64'
        assert result[0] == 1234.56
        assert result[1] == 2000.0
        assert result[2] == 300.0
    
    def test_empty_string_becomes_nan(self):
        """Test that empty strings become NaN."""
        s = pd.Series(['100', '', '200'])
        result = coerce_numeric_series(s)
        
        assert result.dtype == 'float64'
        assert result[0] == 100.0
        assert pd.isna(result[1])
        assert result[2] == 200.0
    
    def test_fillna_behavior(self):
        """Test fillna parameter."""
        s = pd.Series(['100', None, '', '200'])
        result = coerce_numeric_series(s, fillna=0.0)
        
        assert result.dtype == 'float64'
        assert result.tolist() == [100.0, 0.0, 0.0, 200.0]
    
    def test_fillna_custom_value(self):
        """Test fillna with custom value."""
        s = pd.Series(['100', None, '200'])
        result = coerce_numeric_series(s, fillna=-999.0)
        
        assert result[1] == -999.0
    
    def test_none_and_nan_handling(self):
        """Test handling of None and NaN values."""
        s = pd.Series([100, None, np.nan, 200])
        result = coerce_numeric_series(s, fillna=0.0)
        
        assert result.dtype == 'float64'
        assert result.tolist() == [100.0, 0.0, 0.0, 200.0]
    
    def test_mixed_dtype(self):
        """Test handling of mixed types in Series."""
        s = pd.Series([100, '200', '1,234.56', None])
        result = coerce_numeric_series(s, fillna=0.0)
        
        assert result.dtype == 'float64'
        assert result[0] == 100.0
        assert result[1] == 200.0
        assert result[2] == 1234.56
        assert result[3] == 0.0
    
    def test_negative_amounts(self):
        """Test handling of negative amounts."""
        s = pd.Series(['-100.5', '-1,234.56', '200'])
        result = coerce_numeric_series(s)
        
        assert result.dtype == 'float64'
        assert result[0] == -100.5
        assert result[1] == -1234.56
        assert result[2] == 200.0
    
    def test_already_float_passthrough(self):
        """Test that already-float data passes through efficiently."""
        s = pd.Series([100.5, 200.0, 300.0], dtype='float64')
        result = coerce_numeric_series(s)
        
        assert result.dtype == 'float64'
        assert result.tolist() == [100.5, 200.0, 300.0]
    
    def test_already_int_to_float(self):
        """Test conversion of integer Series to float."""
        s = pd.Series([100, 200, 300], dtype='int64')
        result = coerce_numeric_series(s)
        
        assert result.dtype == 'float64'
        assert result.tolist() == [100.0, 200.0, 300.0]
    
    def test_invalid_values_become_nan(self):
        """Test that invalid values become NaN."""
        s = pd.Series(['100', 'abc', '200', 'xyz'])
        result = coerce_numeric_series(s, fillna=0.0)
        
        assert result.dtype == 'float64'
        assert result[0] == 100.0
        assert result[1] == 0.0  # 'abc' coerced to NaN then filled
        assert result[2] == 200.0
        assert result[3] == 0.0  # 'xyz' coerced to NaN then filled
    
    def test_scientific_notation(self):
        """Test handling of scientific notation."""
        s = pd.Series(['1.5e3', '2.0e-2', '1e6'])
        result = coerce_numeric_series(s)
        
        assert result.dtype == 'float64'
        assert result[0] == 1500.0
        assert result[1] == 0.02
        assert result[2] == 1000000.0


class TestCastAmountColumns:
    """Tests for cast_amount_columns function."""
    
    def test_explicit_columns_list(self):
        """Test casting with explicit column list."""
        df = pd.DataFrame({
            'Amount': ['1,234.56', '2,000'],
            'Balance': ['500', '750'],
            'ID': ['A1', 'A2']
        })
        
        result = cast_amount_columns(df, columns=['Amount', 'Balance'], fillna=0.0)
        
        assert result['Amount'].dtype == 'float64'
        assert result['Balance'].dtype == 'float64'
        assert result['ID'].dtype == 'object'  # Unchanged
        assert result['Amount'][0] == 1234.56
    
    def test_auto_detection_default_pattern(self):
        """Test auto-detection with default 'amount' pattern."""
        df = pd.DataFrame({
            'Amount': ['1,234.56', '2,000'],
            'Amount_USD': ['100.5', '200'],
            'amount_lcy': ['50', '75'],
            'ID': ['A1', 'A2'],
            'Date': ['2025-01-01', '2025-01-02']
        })
        
        result = cast_amount_columns(df, fillna=0.0)
        
        # Should match Amount, Amount_USD, amount_lcy (case-insensitive)
        assert result['Amount'].dtype == 'float64'
        assert result['Amount_USD'].dtype == 'float64'
        assert result['amount_lcy'].dtype == 'float64'
        # Should NOT match ID or Date
        assert result['ID'].dtype == 'object'
        assert result['Date'].dtype == 'object'
    
    def test_custom_pattern(self):
        """Test auto-detection with custom pattern."""
        df = pd.DataFrame({
            'Total_Amount': ['100', '200'],
            'Grand_Total': ['300', '400'],
            'Subtotal': ['50', '75'],
            'ID': ['A1', 'A2']
        })
        
        result = cast_amount_columns(df, pattern=r'total', fillna=0.0)
        
        # Should match Total_Amount, Grand_Total, Subtotal (case-insensitive)
        assert result['Total_Amount'].dtype == 'float64'
        assert result['Grand_Total'].dtype == 'float64'
        assert result['Subtotal'].dtype == 'float64'
        assert result['ID'].dtype == 'object'
    
    def test_fillna_applied(self):
        """Test that fillna is applied to all cast columns."""
        df = pd.DataFrame({
            'Amount': ['100', None, '200'],
            'Balance': ['50', '', '75']
        })
        
        result = cast_amount_columns(df, columns=['Amount', 'Balance'], fillna=0.0)
        
        assert result['Amount'][1] == 0.0
        assert result['Balance'][1] == 0.0
    
    def test_inplace_modification(self):
        """Test inplace=True modifies original DataFrame."""
        df = pd.DataFrame({
            'Amount': ['100', '200']
        })
        
        result = cast_amount_columns(df, columns=['Amount'], fillna=0.0, inplace=True)
        
        assert result is df  # Same object
        assert df['Amount'].dtype == 'float64'
    
    def test_copy_by_default(self):
        """Test that default behavior returns a copy."""
        df = pd.DataFrame({
            'Amount': ['100', '200']
        })
        
        result = cast_amount_columns(df, columns=['Amount'], fillna=0.0)
        
        assert result is not df  # Different object
        assert df['Amount'].dtype == 'object'  # Original unchanged
        assert result['Amount'].dtype == 'float64'
    
    def test_missing_column_raises_error(self):
        """Test that specifying non-existent column raises ValueError."""
        df = pd.DataFrame({
            'Amount': ['100', '200']
        })
        
        with pytest.raises(ValueError, match="Columns not found"):
            cast_amount_columns(df, columns=['Amount', 'NonExistent'])
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame()
        result = cast_amount_columns(df, columns=[])
        
        assert result.empty
    
    def test_no_matching_columns_warning(self):
        """Test warning when pattern matches zero columns."""
        df = pd.DataFrame({
            'ID': ['A1', 'A2'],
            'Name': ['Test1', 'Test2']
        })
        
        # Should log warning but not fail
        result = cast_amount_columns(df, pattern=r'amount', fillna=0.0)
        
        assert result.equals(df)


class TestEnsureRequiredNumeric:
    """Tests for ensure_required_numeric function."""
    
    def test_all_required_columns_present(self):
        """Test with all required columns present."""
        df = pd.DataFrame({
            'Amount': ['1,234.56', '2,000'],
            'Balance': ['500', '750']
        })
        
        result = ensure_required_numeric(df, required=['Amount', 'Balance'], fillna=0.0)
        
        assert result['Amount'].dtype == 'float64'
        assert result['Balance'].dtype == 'float64'
        assert result['Amount'][0] == 1234.56
    
    def test_missing_required_column_raises_error(self):
        """Test that missing required column raises ValueError."""
        df = pd.DataFrame({
            'Amount': ['100', '200']
        })
        
        with pytest.raises(ValueError, match="Required columns missing"):
            ensure_required_numeric(df, required=['Amount', 'Balance'])
    
    def test_fillna_applied(self):
        """Test that fillna is applied to required columns."""
        df = pd.DataFrame({
            'Amount': ['100', None, '200'],
            'Balance': ['50', '', '75']
        })
        
        result = ensure_required_numeric(df, required=['Amount', 'Balance'], fillna=0.0)
        
        assert result['Amount'][1] == 0.0
        assert result['Balance'][1] == 0.0
    
    def test_always_returns_copy(self):
        """Test that function always returns a copy."""
        df = pd.DataFrame({
            'Amount': ['100', '200']
        })
        
        result = ensure_required_numeric(df, required=['Amount'], fillna=0.0)
        
        assert result is not df  # Different object
        assert df['Amount'].dtype == 'object'  # Original unchanged
        assert result['Amount'].dtype == 'float64'
    
    def test_empty_required_list(self):
        """Test with empty required list."""
        df = pd.DataFrame({
            'Amount': ['100', '200']
        })
        
        result = ensure_required_numeric(df, required=[])
        
        # Should return copy with no modifications
        assert result is not df
        assert result['Amount'].dtype == 'object'
    
    def test_other_columns_unchanged(self):
        """Test that non-required columns are unchanged."""
        df = pd.DataFrame({
            'Amount': ['100', '200'],
            'ID': ['A1', 'A2'],
            'Name': ['Test1', 'Test2']
        })
        
        result = ensure_required_numeric(df, required=['Amount'], fillna=0.0)
        
        assert result['Amount'].dtype == 'float64'
        assert result['ID'].dtype == 'object'
        assert result['Name'].dtype == 'object'


class TestEdgeCases:
    """Tests for edge cases and corner scenarios."""
    
    def test_dataframe_with_only_amount_columns(self):
        """Test DataFrame with only amount-like columns."""
        df = pd.DataFrame({
            'Amount': ['100', '200'],
            'Total_Amount': ['300', '400'],
            'Sum_Amount': ['500', '600']
        })
        
        result = cast_amount_columns(df, fillna=0.0)
        
        assert all(result[col].dtype == 'float64' for col in df.columns)
    
    def test_very_large_numbers(self):
        """Test handling of very large numbers."""
        s = pd.Series(['999999999999.99', '1234567890123.45'])
        result = coerce_numeric_series(s)
        
        assert result[0] == 999999999999.99
        assert result[1] == 1234567890123.45
    
    def test_very_small_decimals(self):
        """Test handling of very small decimal values."""
        s = pd.Series(['0.00001', '0.000000001'])
        result = coerce_numeric_series(s)
        
        assert result[0] == 0.00001
        assert result[1] == 0.000000001
    
    def test_zero_values(self):
        """Test handling of zero values."""
        s = pd.Series(['0', '0.0', '0.00'])
        result = coerce_numeric_series(s)
        
        assert all(v == 0.0 for v in result)
    
    def test_unicode_minus_sign(self):
        """Test handling of unicode minus sign."""
        s = pd.Series(['−100', '−200'])  # Unicode minus (U+2212)
        result = coerce_numeric_series(s, fillna=0.0)
        
        # Should handle gracefully (may coerce to NaN then fill)
        assert result.dtype == 'float64'
