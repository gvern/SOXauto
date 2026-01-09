"""
Schema Contract System - Smoke Tests

Quick validation that the schema contract system is working correctly.
Run with: pytest tests/test_schema_smoke.py -v
"""

import pandas as pd
import pytest

from src.core.schema import (
    get_active_contract,
    load_contract,
    list_available_contracts,
)
from src.core.schema.schema_utils import apply_schema_contract, require_columns


class TestContractLoading:
    """Test contract loading and registry."""
    
    def test_load_ipe_07_contract(self):
        """Test loading IPE_07 contract."""
        contract = load_contract("IPE_07")
        
        assert contract.dataset_id == "IPE_07"
        assert contract.version == 1
        assert len(contract.fields) > 0
        assert contract.contract_hash is not None
        
        # Check key fields exist
        field_names = [f.name for f in contract.fields]
        assert "customer_id" in field_names
        assert "amount_lcy" in field_names
        assert "customer_posting_group" in field_names
    
    def test_load_jdash_contract(self):
        """Test loading JDASH contract."""
        contract = load_contract("JDASH")
        
        assert contract.dataset_id == "JDASH"
        assert contract.version == 1
        
        # Check key fields
        field_names = [f.name for f in contract.fields]
        assert "voucher_id" in field_names
        assert "amount_used" in field_names
    
    def test_list_contracts(self):
        """Test listing all available contracts."""
        contracts = list_available_contracts()
        
        assert isinstance(contracts, dict)
        assert "IPE_07" in contracts
        assert "IPE_08" in contracts
        assert "CR_04" in contracts
        assert "JDASH" in contracts
    
    def test_get_active_contract(self):
        """Test getting active contract (respects env vars)."""
        contract = get_active_contract("IPE_07")
        
        assert contract.dataset_id == "IPE_07"
        # Should get latest version by default
        assert contract.version >= 1


class TestSchemaValidation:
    """Test schema validation on DataFrames."""
    
    def test_apply_schema_with_perfect_match(self):
        """Test applying schema when DataFrame already matches."""
        # Create DataFrame with canonical column names
        df = pd.DataFrame({
            "customer_id": ["C001", "C002"],
            "customer_posting_group": ["RETAIL", "WHOLESALE"],
            "amount_lcy": [1000.0, 2000.0],
            "posting_date": ["2025-09-30", "2025-09-30"]
        })
        
        df_result, report = apply_schema_contract(
            df, "IPE_07", strict=False, cast=True, track=True
        )
        
        assert report.success
        assert len(df_result) == 2
        assert "customer_id" in df_result.columns
        assert report.row_count_before == 2
        assert report.row_count_after == 2
    
    def test_apply_schema_with_aliases(self):
        """Test column name normalization via aliases."""
        # Use alias names that need normalization
        df = pd.DataFrame({
            "Customer No_": ["C001", "C002"],
            "Customer Posting Group": ["RETAIL", "WHOLESALE"],
            "rem_amt_LCY": [1000.0, 2000.0],
            "Posting Date": ["2025-09-30", "2025-09-30"]
        })
        
        df_result, report = apply_schema_contract(
            df, "IPE_07", strict=False, cast=True, track=True
        )
        
        # Check columns were renamed to canonical names
        assert "customer_id" in df_result.columns
        assert "amount_lcy" in df_result.columns
        assert "Customer No_" not in df_result.columns
        
        # Check report recorded renames
        assert len(report.columns_renamed) > 0
        assert "Customer No_" in report.columns_renamed
        assert report.columns_renamed["Customer No_"] == "customer_id"
    
    def test_apply_schema_with_amount_coercion(self):
        """Test amount column coercion (removing commas)."""
        df = pd.DataFrame({
            "voucher_id": ["V001", "V002"],
            "amount_used": ["1,234.56", "2,000.00"]
        })
        
        df_result, report = apply_schema_contract(
            df, "JDASH", strict=False, cast=True, track=True
        )
        
        # Check amounts were coerced to float
        assert df_result["amount_used"].dtype == "float64"
        assert df_result["amount_used"][0] == 1234.56
        assert df_result["amount_used"][1] == 2000.0
        
        # Check report shows cast
        assert "amount_used" in report.columns_cast
    
    def test_strict_mode_missing_required(self):
        """Test that strict mode raises error on missing required columns."""
        df = pd.DataFrame({
            "voucher_id": ["V001", "V002"],
            # Missing required 'amount_used' column
        })
        
        with pytest.raises(ValueError, match="Required columns missing"):
            apply_schema_contract(df, "JDASH", strict=True, cast=True)
    
    def test_non_strict_mode_missing_required(self):
        """Test that non-strict mode logs warning but doesn't fail."""
        df = pd.DataFrame({
            "voucher_id": ["V001", "V002"],
            # Missing required 'amount_used' column
        })
        
        df_result, report = apply_schema_contract(
            df, "JDASH", strict=False, cast=True
        )
        
        # Should succeed but report missing columns
        assert report.success
        assert len(report.validation_warnings) > 0
        assert "amount_used" in report.required_columns_missing
    
    def test_unknown_columns_kept_by_default(self):
        """Test that unknown columns are kept by default."""
        df = pd.DataFrame({
            "voucher_id": ["V001", "V002"],
            "amount_used": [100.0, 200.0],
            "extra_column": ["A", "B"]  # Not in contract
        })
        
        df_result, report = apply_schema_contract(
            df, "JDASH", strict=False, cast=True, drop_unknown=False
        )
        
        # Extra column should still be there
        assert "extra_column" in df_result.columns
        assert "extra_column" in report.unknown_columns_kept


class TestRequireColumns:
    """Test require_columns helper function."""
    
    def test_require_columns_success(self):
        """Test require_columns when columns exist."""
        df = pd.DataFrame({
            "customer_id": ["C001"],
            "amount_lcy": [1000.0]
        })
        
        # Should not raise
        require_columns(df, "IPE_07", ["customer_id", "amount_lcy"])
    
    def test_require_columns_failure(self):
        """Test require_columns raises on missing columns."""
        df = pd.DataFrame({
            "customer_id": ["C001"]
            # Missing amount_lcy
        })
        
        with pytest.raises(ValueError, match="Required columns missing"):
            require_columns(df, "IPE_07", ["customer_id", "amount_lcy"])


class TestTransformationTracking:
    """Test transformation event tracking."""
    
    def test_tracks_renames(self):
        """Test that renames are recorded as events."""
        df = pd.DataFrame({
            "Customer No_": ["C001"],  # Alias
            "amount_lcy": [1000.0]
        })
        
        df_result, report = apply_schema_contract(
            df, "IPE_07", strict=False, cast=True, track=True
        )
        
        # Check events were recorded
        assert len(report.events) > 0
        
        # Find rename event
        rename_events = [e for e in report.events if e.event_type.value == "rename"]
        assert len(rename_events) > 0
        assert rename_events[0].before_name == "Customer No_"
        assert rename_events[0].after_name == "customer_id"
    
    def test_tracks_casts(self):
        """Test that dtype casts are recorded as events."""
        df = pd.DataFrame({
            "voucher_id": ["V001"],
            "amount_used": ["1,234.56"]  # String that needs casting
        })
        
        df_result, report = apply_schema_contract(
            df, "JDASH", strict=False, cast=True, track=True
        )
        
        # Find cast event for amount_used
        cast_events = [e for e in report.events if e.event_type.value == "cast"]
        assert len(cast_events) > 0
        
        amount_cast = [e for e in cast_events if "amount_used" in e.columns]
        assert len(amount_cast) > 0
        assert amount_cast[0].before_dtype != amount_cast[0].after_dtype
