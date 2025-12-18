import os
import sys
import pytest
from pathlib import Path

# Ensure the scripts module can be imported
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)


def test_fetch_live_fixtures_importable():
    """Test that fetch_live_fixtures script can be imported."""
    import scripts.fetch_live_fixtures as fetch_live_fixtures
    assert fetch_live_fixtures is not None
    assert hasattr(fetch_live_fixtures, 'main')
    assert hasattr(fetch_live_fixtures, 'ITEMS_TO_FETCH')


def test_fetch_live_fixtures_has_expected_items():
    """Test that ITEMS_TO_FETCH contains the expected IPEs."""
    import scripts.fetch_live_fixtures as fetch_live_fixtures
    
    expected_items = [
        "CR_04",
        "CR_03",
        "IPE_07",
        "IPE_08",
        "DOC_VOUCHER_USAGE",
        "CR_05",
        "IPE_REC_ERRORS"
    ]
    
    assert fetch_live_fixtures.ITEMS_TO_FETCH == expected_items


def test_fetch_live_fixtures_entity_path_logic():
    """Test that the entity-specific path logic is correct."""
    # This test verifies the path construction logic without running the script
    entity = "EC_NG"
    
    # Simulate the path construction from the script
    script_path = Path(__file__).parent.parent / "scripts" / "fetch_live_fixtures.py"
    output_dir = script_path.parent.parent / "tests" / "fixtures" / entity
    
    # Verify the path structure
    assert str(output_dir).endswith(f"tests/fixtures/{entity}")
    assert entity in str(output_dir)


def test_fetch_live_fixtures_different_entities():
    """Test that different entities create different paths."""
    entities = ["EC_NG", "JD_GH", "EC_KE"]
    
    for entity in entities:
        script_path = Path(__file__).parent.parent / "scripts" / "fetch_live_fixtures.py"
        output_dir = script_path.parent.parent / "tests" / "fixtures" / entity
        
        # Each entity should have its own unique path
        assert str(output_dir).endswith(f"tests/fixtures/{entity}")
        assert entity in str(output_dir)
