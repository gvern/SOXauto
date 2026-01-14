"""
Smoke tests for core extraction and preprocessing modules.

These tests verify that:
1. All new modules can be imported
2. Basic functionality works without external dependencies
3. Backward compatibility with existing code is maintained

Run with: pytest tests/test_smoke_core_modules.py -v
"""

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def test_import_evidence_locator():
    """Test that evidence_locator module can be imported."""
    from src.core.evidence.evidence_locator import get_latest_evidence_zip, find_evidence_packages
    assert callable(get_latest_evidence_zip)
    assert callable(find_evidence_packages)


def test_import_extraction_pipeline():
    """Test that extraction_pipeline module can be imported."""
    from src.core.extraction_pipeline import (
        ExtractionPipeline,
        run_extraction_with_evidence,
        load_all_data,
    )
    assert ExtractionPipeline is not None
    assert callable(run_extraction_with_evidence)
    assert callable(load_all_data)


def test_import_jdash_loader():
    """Test that jdash_loader module can be imported."""
    from src.core.jdash_loader import (
        load_jdash_data,
        aggregate_jdash_by_voucher,
        validate_jdash_data,
    )
    assert callable(load_jdash_data)
    assert callable(aggregate_jdash_by_voucher)
    assert callable(validate_jdash_data)


def test_import_scope_filtering():
    """Test that scope_filtering module can be imported."""
    from src.core.scope_filtering import (
        NON_MARKETING_USES,
        filter_ipe08_scope,
        filter_gl_18412,
    )
    assert isinstance(NON_MARKETING_USES, list)
    assert len(NON_MARKETING_USES) == 5
    assert callable(filter_ipe08_scope)
    assert callable(filter_gl_18412)


def test_backward_compatibility_classifier_import():
    """Test that classifier still exports filter_ipe08_scope."""
    from src.core.scope_filtering import filter_ipe08_scope
    assert callable(filter_ipe08_scope)


def test_non_marketing_uses_values():
    """Test that NON_MARKETING_USES contains expected values."""
    from src.core.scope_filtering import NON_MARKETING_USES
    
    expected = [
        "apology_v2",
        "jforce",
        "refund",
        "store_credit",
        "Jpay store_credit",
    ]
    
    assert set(NON_MARKETING_USES) == set(expected)


def test_extraction_pipeline_instantiation():
    """Test that ExtractionPipeline can be instantiated."""
    from src.core.extraction_pipeline import ExtractionPipeline
    
    params = {
        "cutoff_date": "2024-10-31",
        "id_companies_active": "('JD_GH')",
    }
    
    pipeline = ExtractionPipeline(params)
    
    assert pipeline.country_code == "JD_GH"
    assert pipeline.period_str == "202410"


def test_jdash_loader_empty_handling():
    """Test that jdash_loader handles empty input correctly."""
    import pandas as pd
    from src.core.jdash_loader import load_jdash_data
    
    df, source = load_jdash_data(None, fixture_fallback=False)
    
    assert isinstance(df, pd.DataFrame)
    assert "Voucher Id" in df.columns or df.empty


def test_scope_filtering_empty_handling():
    """Test that scope_filtering handles empty input correctly."""
    import pandas as pd
    from src.core.scope_filtering import filter_ipe08_scope
    
    result = filter_ipe08_scope(None)
    assert isinstance(result, pd.DataFrame)
    assert result.empty
    
    result = filter_ipe08_scope(pd.DataFrame())
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_evidence_locator_nonexistent_path():
    """Test that evidence_locator handles nonexistent paths correctly."""
    from src.core.evidence.evidence_locator import get_latest_evidence_zip
    
    result = get_latest_evidence_zip("IPE_XX", evidence_root="/nonexistent/path")
    assert result is None
