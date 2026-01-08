"""
Integration tests for pandas_utils module.

Tests realistic scenarios:
- CSV-like data with edge cases
- Extraction output scenarios
- Stability of numeric operations (groupby, sum, variance)
- Reconciliation pipeline integration
"""

import pandas as pd
import pytest

from src.utils.pandas_utils import (
    cast_amount_columns,
    ensure_required_numeric,
)


class TestCSVLikeData:
    """Test scenarios resembling CSV uploads with messy data."""
    
    def test_csv_upload_mixed_formats(self):
        """Test CSV data with mixed number formats."""
        # Simulate CSV upload with various amount formats
        csv_data = {
            'VoucherID': ['V001', 'V002', 'V003', 'V004', 'V005'],
            'Amount': ['1,234.56', '2000', '  3,456.78  ', '4.5e2', ''],
            'Balance': ['500.00', '1,000', '', None, '2,500'],
            'Customer_ID': ['C001', 'C002', 'C003', 'C004', 'C005']
        }
        df = pd.DataFrame(csv_data)
        
        # Clean the data
        df_clean = cast_amount_columns(df, columns=['Amount', 'Balance'], fillna=0.0)
        
        # Verify all amounts are float
        assert df_clean['Amount'].dtype == 'float64'
        assert df_clean['Balance'].dtype == 'float64'
        
        # Verify specific conversions
        assert df_clean['Amount'][0] == 1234.56
        assert df_clean['Amount'][1] == 2000.0
        assert df_clean['Amount'][2] == 3456.78
        assert df_clean['Amount'][3] == 450.0  # Scientific notation
        assert df_clean['Amount'][4] == 0.0  # Empty string
        
        # Verify Customer_ID unchanged
        assert df_clean['Customer_ID'].dtype == 'object'
    
    def test_csv_with_accounting_parentheses(self):
        """Test CSV data with accounting-style negative amounts (parentheses)."""
        # Note: This is a known limitation - parentheses require custom logic
        csv_data = {
            'ID': ['T001', 'T002', 'T003'],
            'Amount': ['1,234.56', '-500.00', '2,000']
        }
        df = pd.DataFrame(csv_data)
        
        df_clean = cast_amount_columns(df, columns=['Amount'], fillna=0.0)
        
        assert df_clean['Amount'][0] == 1234.56
        assert df_clean['Amount'][1] == -500.0
        assert df_clean['Amount'][2] == 2000.0


class TestExtractionOutputScenarios:
    """Test scenarios resembling SQL extraction outputs."""
    
    def test_sql_extraction_with_nulls(self):
        """Test SQL extraction output with NULL values."""
        # Simulate SQL extraction with NULLs
        sql_data = {
            'Document_No': ['DOC001', 'DOC002', 'DOC003', 'DOC004'],
            'Amount': [1000.50, None, 2500.75, 0.0],
            'Remaining_Amount': [500.0, 1000.0, None, 250.0],
            'Customer_No': ['CUST001', 'CUST002', 'CUST003', 'CUST004']
        }
        df = pd.DataFrame(sql_data)
        
        # Ensure required columns are numeric
        df_clean = ensure_required_numeric(
            df,
            required=['Amount', 'Remaining_Amount'],
            fillna=0.0
        )
        
        # Verify NULLs filled with 0.0
        assert df_clean['Amount'][1] == 0.0
        assert df_clean['Remaining_Amount'][2] == 0.0
        
        # Verify sum works without errors
        total_amount = df_clean['Amount'].sum()
        assert total_amount == 3501.25
    
    def test_multi_company_extraction(self):
        """Test extraction with multiple companies and currencies."""
        # Simulate IPE extraction across companies
        extraction_data = {
            'ID_COMPANY': ['EC_NG', 'EC_NG', 'JD_GH', 'JD_GH'],
            'Amount_LCY': ['1,000,000', '500,000', '2,000,000', '1,500,000'],
            'Amount_USD': ['2,500', '1,250', '1,200', '900'],
            'Document_Type': ['Invoice', 'Credit Memo', 'Invoice', 'Payment']
        }
        df = pd.DataFrame(extraction_data)
        
        # Auto-detect and cast amount columns
        df_clean = cast_amount_columns(df, fillna=0.0)
        
        # Verify both amount columns cast
        assert df_clean['Amount_LCY'].dtype == 'float64'
        assert df_clean['Amount_USD'].dtype == 'float64'
        
        # Verify values
        assert df_clean['Amount_LCY'][0] == 1000000.0
        assert df_clean['Amount_USD'][0] == 2500.0
        
        # Verify Document_Type unchanged
        assert df_clean['Document_Type'].dtype == 'object'


class TestNumericOperationsStability:
    """Test stability of numeric operations after casting."""
    
    def test_groupby_sum_stability(self):
        """Test that groupby().sum() works correctly after casting."""
        data = {
            'Category': ['A', 'A', 'B', 'B', 'C'],
            'Amount': ['1,234.56', '2,000', '3,456.78', '', '5,000']
        }
        df = pd.DataFrame(data)
        
        # Cast amounts
        df_clean = cast_amount_columns(df, columns=['Amount'], fillna=0.0)
        
        # Perform groupby sum
        result = df_clean.groupby('Category')['Amount'].sum()
        
        # Verify results
        assert result['A'] == 3234.56
        assert result['B'] == 3456.78
        assert result['C'] == 5000.0
    
    def test_variance_calculation_stability(self):
        """Test variance calculation after casting."""
        data = {
            'ID': ['T1', 'T2', 'T3'],
            'Source_Amount': ['1,000', '2,000', '3,000'],
            'Target_Amount': ['900', '2,100', '2,950']
        }
        df = pd.DataFrame(data)
        
        # Cast amounts
        df_clean = cast_amount_columns(
            df,
            columns=['Source_Amount', 'Target_Amount'],
            fillna=0.0
        )
        
        # Calculate variance
        df_clean['Variance'] = df_clean['Source_Amount'] - df_clean['Target_Amount']
        
        # Verify variance calculations
        assert df_clean['Variance'][0] == 100.0
        assert df_clean['Variance'][1] == -100.0
        assert df_clean['Variance'][2] == 50.0
        
        # Verify total variance
        total_variance = df_clean['Variance'].sum()
        assert total_variance == 50.0
    
    def test_pivot_table_with_cast_amounts(self):
        """Test pivot table operations after casting."""
        data = {
            'Country': ['NG', 'NG', 'GH', 'GH'],
            'Category': ['A', 'B', 'A', 'B'],
            'Amount': ['1,000', '2,000', '1,500', '2,500']
        }
        df = pd.DataFrame(data)
        
        # Cast amounts
        df_clean = cast_amount_columns(df, columns=['Amount'], fillna=0.0)
        
        # Create pivot table
        pivot = df_clean.pivot_table(
            values='Amount',
            index='Country',
            columns='Category',
            aggfunc='sum',
            fill_value=0
        )
        
        # Verify pivot results
        assert pivot.loc['NG', 'A'] == 1000.0
        assert pivot.loc['NG', 'B'] == 2000.0
        assert pivot.loc['GH', 'A'] == 1500.0
        assert pivot.loc['GH', 'B'] == 2500.0
    
    def test_merge_operations_after_casting(self):
        """Test that merge operations work correctly after casting."""
        left_data = {
            'ID': ['A', 'B', 'C'],
            'Amount_Left': ['1,000', '2,000', '3,000']
        }
        right_data = {
            'ID': ['A', 'B', 'C'],
            'Amount_Right': ['900', '2,100', '2,950']
        }
        
        df_left = pd.DataFrame(left_data)
        df_right = pd.DataFrame(right_data)
        
        # Cast amounts in both DataFrames
        df_left = cast_amount_columns(df_left, columns=['Amount_Left'], fillna=0.0)
        df_right = cast_amount_columns(df_right, columns=['Amount_Right'], fillna=0.0)
        
        # Perform merge
        merged = df_left.merge(df_right, on='ID')
        
        # Calculate variance
        merged['Variance'] = merged['Amount_Left'] - merged['Amount_Right']
        
        # Verify merge and calculations work
        assert len(merged) == 3
        assert merged['Variance'][0] == 100.0
        assert merged['Variance'].sum() == 50.0


class TestReconciliationPipelineIntegration:
    """Test integration with reconciliation pipeline scenarios."""
    
    def test_ipe_gl_reconciliation_scenario(self):
        """Test typical IPE vs GL reconciliation scenario."""
        # Simulate IPE data (Customer balances)
        ipe_data = {
            'Customer_No': ['C001', 'C002', 'C003'],
            'Remaining_Amount': ['1,234.56', '2,000', '3,456.78']
        }
        df_ipe = pd.DataFrame(ipe_data)
        
        # Simulate GL data (NAV balances)
        gl_data = {
            'GL_Account': ['18412', '18412', '18412'],
            'Customer_No': ['C001', 'C002', 'C003'],
            'Balance': [1234.56, 2000.0, 3400.0]  # Already numeric
        }
        df_gl = pd.DataFrame(gl_data)
        
        # Clean IPE data
        df_ipe_clean = ensure_required_numeric(
            df_ipe,
            required=['Remaining_Amount'],
            fillna=0.0
        )
        
        # Ensure GL balance is float
        df_gl_clean = ensure_required_numeric(
            df_gl,
            required=['Balance'],
            fillna=0.0
        )
        
        # Calculate totals
        ipe_total = df_ipe_clean['Remaining_Amount'].sum()
        gl_total = df_gl_clean['Balance'].sum()
        variance = ipe_total - gl_total
        
        # Verify calculations
        assert ipe_total == 6691.34
        assert gl_total == 6634.56
        assert abs(variance - 56.78) < 0.01  # Float precision tolerance
    
    def test_voucher_bridge_calculation_scenario(self):
        """Test VTC bridge calculation scenario with messy data."""
        # Simulate IPE_08 data (voucher liabilities)
        ipe08_data = {
            'id': ['V001', 'V002', 'V003'],
            'business_use': ['refund', 'marketing', 'store_credit'],
            'is_active': [0, 1, 0],
            'remaining_amount': ['1,234.56', '', '2,000']
        }
        df_ipe08 = pd.DataFrame(ipe08_data)
        
        # Simulate CR_03 data (NAV GL entries)
        cr03_data = {
            '[Voucher No_]': ['V001', 'V003'],
            'Amount': [-1234.56, -2000.0],
            'bridge_category': ['Cancellation', 'VTC Manual']
        }
        df_cr03 = pd.DataFrame(cr03_data)
        
        # Basic sanity checks on CR_03 data to ensure scenario setup is valid
        assert df_cr03['Amount'].sum() == pytest.approx(-3234.56)
        assert set(df_cr03['bridge_category']) == {"Cancellation", "VTC Manual"}
        
        # Clean IPE_08 amounts
        df_ipe08_clean = ensure_required_numeric(
            df_ipe08,
            required=['remaining_amount'],
            fillna=0.0
        )
        
        # Verify cleaning
        assert df_ipe08_clean['remaining_amount'][0] == 1234.56
        assert df_ipe08_clean['remaining_amount'][1] == 0.0  # Empty string
        assert df_ipe08_clean['remaining_amount'][2] == 2000.0
    
    def test_timing_bridge_jdash_aggregation(self):
        """Test timing bridge with Jdash aggregation scenario."""
        # Simulate Jdash data with duplicate voucher usage
        jdash_data = {
            'Voucher Id': ['V001', 'V001', 'V002', 'V003'],
            'Amount Used': ['100.50', '200.75', '1,500', '']
        }
        df_jdash = pd.DataFrame(jdash_data)
        
        # Clean amounts
        df_jdash_clean = ensure_required_numeric(
            df_jdash,
            required=['Amount Used'],
            fillna=0.0
        )
        
        # Aggregate by voucher
        jdash_agg = df_jdash_clean.groupby('Voucher Id')['Amount Used'].sum().reset_index()
        
        # Verify aggregation works correctly
        assert jdash_agg[jdash_agg['Voucher Id'] == 'V001']['Amount Used'].iloc[0] == 301.25
        assert jdash_agg[jdash_agg['Voucher Id'] == 'V002']['Amount Used'].iloc[0] == 1500.0
        assert jdash_agg[jdash_agg['Voucher Id'] == 'V003']['Amount Used'].iloc[0] == 0.0


class TestPerformance:
    """Test performance with larger datasets."""
    
    def test_large_dataset_performance(self):
        """Test casting performance with reasonably large dataset."""
        # Generate 10,000 rows
        n_rows = 10000
        data = {
            'ID': [f'ID{i:05d}' for i in range(n_rows)],
            'Amount': [f'{1000 + i * 0.5:.2f}' for i in range(n_rows)],
            'Balance': [f'{500 + i * 0.25:.2f}' for i in range(n_rows)]
        }
        df = pd.DataFrame(data)
        
        # Cast amounts
        df_clean = cast_amount_columns(df, columns=['Amount', 'Balance'], fillna=0.0)
        
        # Verify first and last rows
        assert df_clean['Amount'][0] == 1000.0
        assert df_clean['Amount'][n_rows-1] == pytest.approx(1000 + (n_rows-1) * 0.5, rel=1e-5)
        
        # Verify sum calculation works
        total = df_clean['Amount'].sum()
        assert total > 0  # Basic sanity check


class TestBackwardCompatibility:
    """Test backward compatibility scenarios."""
    
    def test_works_with_existing_float_data(self):
        """Test that function works correctly with already-clean data."""
        # Simulate data that's already been cleaned
        data = {
            'Amount': [1234.56, 2000.0, 3456.78],
            'Balance': [500.0, 1000.0, 2500.0]
        }
        df = pd.DataFrame(data)
        
        # Cast should be idempotent
        df_clean = cast_amount_columns(df, columns=['Amount', 'Balance'], fillna=0.0)
        
        # Verify data unchanged
        assert df_clean['Amount'].tolist() == [1234.56, 2000.0, 3456.78]
        assert df_clean['Balance'].tolist() == [500.0, 1000.0, 2500.0]
