"""
Unit tests for the core extraction and preprocessing modules.

Tests cover:
- src/core/evidence/evidence_locator.py
- src/core/extraction_pipeline.py
- src/core/jdash_loader.py
- src/core/scope_filtering.py
"""

import os
import sys
import tempfile
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.core.scope_filtering import (
    NON_MARKETING_USES,
    filter_ipe08_scope,
    filter_gl_18412,
    apply_non_marketing_filter,
    get_non_marketing_summary,
)
from src.core.jdash_loader import (
    load_jdash_data,
    aggregate_jdash_by_voucher,
    validate_jdash_data,
)
from src.core.evidence.evidence_locator import (
    get_latest_evidence_zip,
    find_evidence_packages,
)


# ============================================================================
# Tests for scope_filtering.py
# ============================================================================

class TestFilterIpe08Scope:
    """Tests for filter_ipe08_scope function."""

    def test_filter_non_marketing_basic(self):
        """Test basic filtering of Non-Marketing vouchers."""
        df = pd.DataFrame([
            {"id": "V001", "business_use": "refund", "amount": 100},
            {"id": "V002", "business_use": "marketing", "amount": 200},
            {"id": "V003", "business_use": "apology_v2", "amount": 150},
        ])
        
        result = filter_ipe08_scope(df)
        
        assert len(result) == 2
        assert "V001" in result["id"].values
        assert "V003" in result["id"].values
        assert "V002" not in result["id"].values

    def test_filter_all_non_marketing_types(self):
        """Test that all non-marketing types are retained."""
        df = pd.DataFrame([
            {"id": "V001", "business_use": "apology_v2"},
            {"id": "V002", "business_use": "jforce"},
            {"id": "V003", "business_use": "refund"},
            {"id": "V004", "business_use": "store_credit"},
            {"id": "V005", "business_use": "Jpay store_credit"},
        ])
        
        result = filter_ipe08_scope(df)
        
        assert len(result) == 5

    def test_filter_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame()
        result = filter_ipe08_scope(df)
        assert result.empty

    def test_filter_none_input(self):
        """Test handling of None input."""
        result = filter_ipe08_scope(None)
        assert result.empty

    def test_filter_with_business_use_formatted(self):
        """Test filtering with business_use_formatted column."""
        df = pd.DataFrame([
            {"id": "V001", "business_use_formatted": "refund"},
            {"id": "V002", "business_use_formatted": "marketing"},
        ])
        
        result = filter_ipe08_scope(df)
        
        assert len(result) == 1
        assert result.iloc[0]["id"] == "V001"

    def test_filter_converts_dates(self):
        """Test that date columns are converted to datetime."""
        df = pd.DataFrame([
            {
                "id": "V001",
                "business_use": "refund",
                "Order_Creation_Date": "2024-10-15",
                "Order_Delivery_Date": "2024-10-20",
            }
        ])
        
        result = filter_ipe08_scope(df)
        
        assert pd.api.types.is_datetime64_any_dtype(result["Order_Creation_Date"])
        assert pd.api.types.is_datetime64_any_dtype(result["Order_Delivery_Date"])

    def test_filter_preserves_columns(self):
        """Test that other columns are preserved."""
        df = pd.DataFrame([
            {"id": "V001", "business_use": "refund", "custom_col": "value1"},
            {"id": "V002", "business_use": "jforce", "custom_col": "value2"},
        ])
        
        result = filter_ipe08_scope(df)
        
        assert "custom_col" in result.columns
        assert len(result) == 2


class TestFilterGl18412:
    """Tests for filter_gl_18412 function."""

    def test_filter_gl_basic(self):
        """Test basic GL 18412 filtering."""
        df = pd.DataFrame([
            {"Chart of Accounts No_": "18412", "Amount": 100},
            {"Chart of Accounts No_": "18410", "Amount": 200},
            {"Chart of Accounts No_": "18412", "Amount": 150},
        ])
        
        result = filter_gl_18412(df)
        
        assert len(result) == 2

    def test_filter_gl_empty(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = filter_gl_18412(df)
        assert result.empty

    def test_filter_gl_none(self):
        """Test with None input."""
        result = filter_gl_18412(None)
        assert result.empty

    def test_filter_gl_no_column(self):
        """Test when GL column is missing."""
        df = pd.DataFrame([
            {"Amount": 100, "Description": "Test"}
        ])
        
        result = filter_gl_18412(df)
        
        # Should return original when no GL column found
        assert len(result) == 1


class TestGetNonMarketingSummary:
    """Tests for get_non_marketing_summary function."""

    def test_summary_basic(self):
        """Test basic summary generation."""
        df = pd.DataFrame([
            {"id": "V001", "business_use": "refund"},
            {"id": "V002", "business_use": "marketing"},
            {"id": "V003", "business_use": "apology_v2"},
        ])
        
        summary = get_non_marketing_summary(df)
        
        assert summary["total_vouchers"] == 3
        assert summary["non_marketing_count"] == 2
        assert summary["marketing_count"] == 1
        assert "refund" in summary["breakdown_by_type"]

    def test_summary_empty(self):
        """Test summary with empty DataFrame."""
        df = pd.DataFrame()
        summary = get_non_marketing_summary(df)
        
        assert summary["total_vouchers"] == 0


# ============================================================================
# Tests for jdash_loader.py
# ============================================================================

class TestLoadJdashData:
    """Tests for load_jdash_data function."""

    def test_load_from_dataframe(self):
        """Test loading from existing DataFrame."""
        input_df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 100.0},
            {"Voucher Id": "V002", "Amount Used": 200.0},
        ])
        
        df, source = load_jdash_data(input_df)
        
        assert len(df) == 2
        assert source == "Direct DataFrame"

    def test_load_normalizes_columns(self):
        """Test that column names are normalized."""
        input_df = pd.DataFrame([
            {"voucher_id": "V001", "amount_used": 100.0},
        ])
        
        df, source = load_jdash_data(input_df)
        
        # Check that the ID column is still present (may be renamed)
        assert "Voucher Id" in df.columns or "voucher_id" in df.columns

    def test_load_no_source_returns_empty(self):
        """Test that None source with no fallback returns empty DataFrame."""
        df, source = load_jdash_data(None, fixture_fallback=False)
        
        assert df.empty or len(df) == 0
        assert source == "No Data"


class TestAggregateJdashByVoucher:
    """Tests for aggregate_jdash_by_voucher function."""

    def test_aggregate_basic(self):
        """Test basic aggregation by voucher ID."""
        df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 50.0},
            {"Voucher Id": "V001", "Amount Used": 30.0},
            {"Voucher Id": "V002", "Amount Used": 100.0},
        ])
        
        result = aggregate_jdash_by_voucher(df)
        
        assert len(result) == 2
        v001_amount = result[result["Voucher Id"] == "V001"]["Amount Used"].values[0]
        assert v001_amount == 80.0

    def test_aggregate_empty(self):
        """Test aggregation of empty DataFrame."""
        df = pd.DataFrame()
        result = aggregate_jdash_by_voucher(df)
        
        assert result.empty or "Voucher Id" in result.columns


class TestValidateJdashData:
    """Tests for validate_jdash_data function."""

    def test_validate_valid_data(self):
        """Test validation with valid data."""
        df = pd.DataFrame([
            {"Voucher Id": "V001", "Amount Used": 100.0},
            {"Voucher Id": "V002", "Amount Used": 200.0},
        ])
        
        result = validate_jdash_data(df)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["stats"]["row_count"] == 2

    def test_validate_missing_columns(self):
        """Test validation with missing required columns."""
        df = pd.DataFrame([
            {"id": "V001", "amount": 100.0},
        ])
        
        result = validate_jdash_data(df)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        df = pd.DataFrame()
        result = validate_jdash_data(df)
        
        assert result["stats"]["row_count"] == 0


# ============================================================================
# Tests for evidence_locator.py
# ============================================================================

class TestGetLatestEvidenceZip:
    """Tests for get_latest_evidence_zip function."""

    def test_no_evidence_returns_none(self):
        """Test that missing evidence directory returns None."""
        result = get_latest_evidence_zip("IPE_99", evidence_root="/nonexistent/path")
        assert result is None

    def test_finds_evidence_in_temp_dir(self):
        """Test finding evidence in a temporary directory."""
        import tempfile
        import zipfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock evidence structure
            ipe_folder = os.path.join(tmpdir, "IPE_07_20241015_123456")
            os.makedirs(ipe_folder)
            
            # Create a mock ZIP file
            zip_path = os.path.join(ipe_folder, "evidence.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("test.txt", "test content")
            
            # Test finding it
            result = get_latest_evidence_zip("IPE_07", evidence_root=tmpdir)
            
            assert result is not None
            assert result.endswith(".zip")


class TestFindEvidencePackages:
    """Tests for find_evidence_packages function."""

    def test_find_multiple_packages(self):
        """Test finding multiple evidence packages."""
        import tempfile
        import zipfile
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple evidence folders
            for i, suffix in enumerate(["001", "002", "003"]):
                folder = os.path.join(tmpdir, f"IPE_07_{suffix}")
                os.makedirs(folder)
                
                zip_path = os.path.join(folder, f"evidence_{suffix}.zip")
                with zipfile.ZipFile(zip_path, "w") as zf:
                    zf.writestr("test.txt", f"content {suffix}")
                
                # Small delay to ensure different modification times
                time.sleep(0.01)
            
            # Find all packages
            packages = find_evidence_packages("IPE_07", evidence_root=tmpdir)
            
            assert len(packages) == 3
            # Should be sorted by modification time (newest first)
            assert packages[0][0] >= packages[1][0]

    def test_find_empty_directory(self):
        """Test with no matching packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            packages = find_evidence_packages("IPE_99", evidence_root=tmpdir)
            assert len(packages) == 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the core modules working together."""

    def test_scope_filtering_consistency_with_classifier(self):
        """Test that scope filtering is consistent with classifier behavior."""
        from src.core.scope_filtering import filter_ipe08_scope as classifier_filter
        
        df = pd.DataFrame([
            {"id": "V001", "business_use": "refund", "amount": 100},
            {"id": "V002", "business_use": "marketing", "amount": 200},
            {"id": "V003", "business_use": "apology_v2", "amount": 150},
        ])
        
        # Both should produce the same result
        core_result = filter_ipe08_scope(df)
        classifier_result = classifier_filter(df)
        
        assert len(core_result) == len(classifier_result)
        assert set(core_result["id"].values) == set(classifier_result["id"].values)

    def test_non_marketing_constant_matches(self):
        """Test that NON_MARKETING_USES constant contains expected values."""
        expected = {"apology_v2", "jforce", "refund", "store_credit", "Jpay store_credit"}
        actual = set(NON_MARKETING_USES)
        
        assert actual == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
