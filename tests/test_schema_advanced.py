"""
Tests for Schema Contract System - Advanced Features

Tests for alias collision detection, deterministic ordering, JSON serialization,
and CSV/fixture loading with schema validation.
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.core.schema import load_contract
from src.core.schema.contract_registry import ContractRegistry
from src.core.schema.loaders import (
    load_csv_with_schema,
    load_fixture_with_schema,
    validate_dataframe,
)
from src.core.schema.schema_utils import apply_schema_contract


class TestAliasCollisionDetection:
    """Test that alias collisions are detected and reported."""
    
    def test_detects_alias_in_multiple_fields(self, tmp_path):
        """Test that same alias in multiple fields raises error."""
        # Create a contract with alias collision
        bad_contract = """
dataset_id: TEST_COLLISION
version: 1
fields:
  - name: field_a
    required: true
    aliases: ["col1", "column_one"]
    dtype: string
    semantic_tag: id
  
  - name: field_b
    required: true
    aliases: ["col1", "column_uno"]  # COLLISION: "col1" appears twice!
    dtype: string
    semantic_tag: id
"""
        
        contract_file = tmp_path / "TEST_COLLISION.yaml"
        contract_file.write_text(bad_contract)
        
        # Try to load the contract
        registry = ContractRegistry(contracts_dir=tmp_path)
        
        with pytest.raises(ValueError, match="Alias collisions detected"):
            registry._load_contract_from_file(contract_file)
    
    def test_detects_canonical_name_as_alias(self, tmp_path):
        """Test that using another field's canonical name as alias is detected."""
        bad_contract = """
dataset_id: TEST_CANONICAL_COLLISION
version: 1
fields:
  - name: customer_id
    required: true
    aliases: ["cust_no"]
    dtype: string
    semantic_tag: id
  
  - name: order_id
    required: true
    aliases: ["customer_id"]  # COLLISION: using canonical name of another field!
    dtype: string
    semantic_tag: id
"""
        
        contract_file = tmp_path / "TEST_CANONICAL_COLLISION.yaml"
        contract_file.write_text(bad_contract)
        
        registry = ContractRegistry(contracts_dir=tmp_path)
        
        with pytest.raises(ValueError, match="Alias collisions detected"):
            registry._load_contract_from_file(contract_file)
    
    def test_allows_same_canonical_name_and_alias(self, tmp_path):
        """Test that canonical name appearing in its own aliases is OK."""
        good_contract = """
dataset_id: TEST_SELF_ALIAS
version: 1
fields:
  - name: customer_id
    required: true
    aliases: ["customer_id", "cust_no"]  # Self-reference is OK
    dtype: string
    semantic_tag: id
"""
        
        contract_file = tmp_path / "TEST_SELF_ALIAS.yaml"
        contract_file.write_text(good_contract)
        
        registry = ContractRegistry(contracts_dir=tmp_path)
        
        # Should not raise
        contract = registry._load_contract_from_file(contract_file)
        assert contract.dataset_id == "TEST_SELF_ALIAS"


class TestDeterministicAliasResolution:
    """Test that alias resolution is deterministic and logged."""
    
    def test_first_alias_wins(self):
        """Test that first matching alias in list is used."""
        # Create DataFrame with multiple possible aliases
        df = pd.DataFrame({
            "Customer No_": ["C001"],      # First alias in IPE_07 contract
            "customer_no": ["C002"],       # Later alias
        })
        
        df_result, report = apply_schema_contract(
            df, "IPE_07", strict=False, cast=False, track=True
        )
        
        # Should have renamed "Customer No_" (first match)
        assert "customer_id" in df_result.columns
        assert "Customer No_" in report.columns_renamed
        assert report.columns_renamed["Customer No_"] == "customer_id"
        
        # "customer_no" should remain as unknown column (not matched)
        assert "customer_no" in report.unknown_columns_kept
    
    def test_alias_priority_logged_in_metadata(self):
        """Test that matched alias priority is recorded in event metadata."""
        df = pd.DataFrame({
            "rem_amt_LCY": [1000.0]  # This is an alias for amount_lcy
        })
        
        df_result, report = apply_schema_contract(
            df, "IPE_07", strict=False, cast=True, track=True
        )
        
        # Find rename event for amount_lcy
        rename_events = [
            e for e in report.events
            if e.event_type.value == "rename" and "amount_lcy" in e.columns
        ]
        
        assert len(rename_events) > 0
        event = rename_events[0]
        
        # Check metadata records which alias matched
        assert "alias_matched" in event.metadata
        assert event.metadata["alias_matched"] == "rem_amt_LCY"
        assert "alias_priority" in event.metadata
    
    def test_canonical_name_preferred_over_aliases(self):
        """Test that canonical name takes precedence if it exists."""
        df = pd.DataFrame({
            "customer_id": ["C001"],       # Canonical name
            "Customer No_": ["C002"],      # Also present but shouldn't be used
        })
        
        df_result, report = apply_schema_contract(
            df, "IPE_07", strict=False, cast=False, track=True
        )
        
        # Should NOT rename customer_id (already canonical)
        assert "customer_id" not in report.columns_renamed
        # "Customer No_" should be kept as unknown column
        assert "Customer No_" in report.unknown_columns_kept


class TestJSONSerialization:
    """Test that SchemaReport can be serialized to JSON."""
    
    def test_report_to_dict(self):
        """Test SchemaReport.to_dict() produces valid dictionary."""
        df = pd.DataFrame({
            "Voucher Id": ["V001"],
            "Amount Used": ["1,234.56"]
        })
        
        df_result, report = apply_schema_contract(
            df, "JDASH", strict=False, cast=True, track=True
        )
        
        # Convert to dict
        report_dict = report.to_dict()
        
        assert isinstance(report_dict, dict)
        assert "dataset_id" in report_dict
        assert "version" in report_dict
        assert "timestamp" in report_dict
        assert "success" in report_dict
        assert "summary" in report_dict
        assert "events" in report_dict
    
    def test_report_json_serializable(self):
        """Test that report dict can be serialized to JSON."""
        df = pd.DataFrame({
            "Voucher Id": ["V001"],
            "Amount Used": ["1,234.56"]
        })
        
        df_result, report = apply_schema_contract(
            df, "JDASH", strict=False, cast=True, track=True
        )
        
        # Convert to dict and serialize to JSON
        report_dict = report.to_dict()
        
        # Should not raise
        json_str = json.dumps(report_dict, indent=2)
        
        # Should be parseable
        parsed = json.loads(json_str)
        assert parsed["dataset_id"] == "JDASH"
        assert parsed["success"] is True
    
    def test_event_to_dict(self):
        """Test TransformEvent.to_dict() handles all field types."""
        df = pd.DataFrame({
            "Customer No_": ["C001"],
            "rem_amt_LCY": ["1,234.56"]
        })
        
        df_result, report = apply_schema_contract(
            df, "IPE_07", strict=False, cast=True, track=True
        )
        
        # Check events are serializable
        for event in report.events:
            event_dict = event.to_dict()
            
            # Timestamps should be ISO format strings
            assert isinstance(event_dict["timestamp"], str)
            assert "T" in event_dict["timestamp"]  # ISO format
            
            # Enums should be strings
            assert isinstance(event_dict["event_type"], str)


class TestCSVLoading:
    """Test loading CSV files with schema validation."""
    
    def test_load_csv_with_schema(self, tmp_path):
        """Test loading CSV file with automatic schema validation."""
        # Create a test CSV
        csv_file = tmp_path / "test_jdash.csv"
        df_test = pd.DataFrame({
            "Voucher Id": ["V001", "V002"],
            "Amount Used": ["1,234.56", "2,000.00"]
        })
        df_test.to_csv(csv_file, index=False)
        
        # Load with schema
        df_result, report = load_csv_with_schema(
            csv_file,
            dataset_id="JDASH",
            strict=False,
            cast=True,
            track=True
        )
        
        # Check columns were normalized
        assert "voucher_id" in df_result.columns
        assert "amount_used" in df_result.columns
        
        # Check amounts were coerced
        assert df_result["amount_used"].dtype == "float64"
        assert df_result["amount_used"][0] == 1234.56
        
        # Check source is recorded in report
        source_warnings = [w for w in report.validation_warnings if "CSV file" in w]
        assert len(source_warnings) > 0
    
    def test_load_csv_missing_required_strict(self, tmp_path):
        """Test that strict mode fails on missing required columns."""
        csv_file = tmp_path / "incomplete.csv"
        df_test = pd.DataFrame({
            "Voucher Id": ["V001"]
            # Missing required "Amount Used"
        })
        df_test.to_csv(csv_file, index=False)
        
        with pytest.raises(ValueError, match="Required columns missing"):
            load_csv_with_schema(
                csv_file,
                dataset_id="JDASH",
                strict=True
            )


class TestFixtureLoading:
    """Test loading test fixtures with schema validation."""
    
    def test_load_fixture_non_strict_by_default(self, tmp_path):
        """Test that fixture loading is non-strict by default."""
        # Create a fixture with missing required column
        fixture_file = tmp_path / "fixture_test.csv"
        df_test = pd.DataFrame({
            "voucher_id": ["V001"]
            # Missing required "amount_used"
        })
        df_test.to_csv(fixture_file, index=False)
        
        # Should not raise (non-strict by default)
        df_result, report = load_fixture_with_schema(
            "fixture_test.csv",
            dataset_id="JDASH",
            fixtures_dir=tmp_path
        )
        
        # Should have warning about missing column
        assert len(report.required_columns_missing) > 0
        assert not report.success or len(report.validation_warnings) > 0


class TestDataFrameValidation:
    """Test validating existing DataFrames."""
    
    def test_validate_dataframe_with_source_description(self):
        """Test that source description is recorded in report."""
        df = pd.DataFrame({
            "Voucher Id": ["V001"],
            "Amount Used": [100.0]
        })
        
        df_result, report = validate_dataframe(
            df,
            dataset_id="JDASH",
            source_description="Unit test mock data",
            strict=False
        )
        
        # Check source is recorded
        source_warnings = [w for w in report.validation_warnings if "Unit test" in w]
        assert len(source_warnings) > 0
        
        # Check columns were normalized
        assert "voucher_id" in df_result.columns
        assert "amount_used" in df_result.columns


class TestRealWorldScenarios:
    """Test real-world usage patterns."""
    
    def test_google_sheet_export_with_spaces(self):
        """Test handling Google Sheets exports with spaces in column names."""
        # Google Sheets often exports with spaces
        df = pd.DataFrame({
            "Voucher Id": ["V001"],  # Space
            "Amount Used": ["1,234.56"]  # Space + comma in number
        })
        
        df_result, report = apply_schema_contract(
            df, "JDASH", strict=False, cast=True, track=True
        )
        
        # Should normalize to canonical names
        assert "voucher_id" in df_result.columns
        assert "amount_used" in df_result.columns
        
        # Should parse comma-formatted number
        assert df_result["amount_used"][0] == 1234.56
    
    def test_nav_export_with_underscores(self):
        """Test handling NAV exports with underscores."""
        df = pd.DataFrame({
            "Customer No_": ["C001"],  # Underscore
            "rem_amt_LCY": ["1000.00"]  # Lowercase with underscores
        })
        
        df_result, report = apply_schema_contract(
            df, "IPE_07", strict=False, cast=True, track=True
        )
        
        # Should normalize to canonical names
        assert "customer_id" in df_result.columns
        assert "amount_lcy" in df_result.columns
        
        # Check both renames were logged
        assert "Customer No_" in report.columns_renamed
        assert "rem_amt_LCY" in report.columns_renamed
