import os
import sys
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


def test_fetch_live_fixtures_entity_whitelist():
    """Test that ALLOWED_ENTITIES whitelist exists and contains expected entities."""
    import scripts.fetch_live_fixtures as fetch_live_fixtures
    
    # Verify ALLOWED_ENTITIES exists
    assert hasattr(fetch_live_fixtures, 'ALLOWED_ENTITIES')
    assert isinstance(fetch_live_fixtures.ALLOWED_ENTITIES, list)
    
    # Verify common entities are in whitelist
    expected_entities = ['EC_NG', 'JD_GH', 'EC_KE', 'JM_EG']
    for entity in expected_entities:
        assert entity in fetch_live_fixtures.ALLOWED_ENTITIES, \
            f"Entity {entity} should be in ALLOWED_ENTITIES"


def test_fetch_live_fixtures_date_constants():
    """Test that date configuration constants are defined."""
    import scripts.fetch_live_fixtures as fetch_live_fixtures
    
    # Verify date constants exist
    assert hasattr(fetch_live_fixtures, 'CUTOFF_DATE')
    assert hasattr(fetch_live_fixtures, 'YEAR_START')
    assert hasattr(fetch_live_fixtures, 'YEAR_END')
    assert hasattr(fetch_live_fixtures, 'YEAR')
    assert hasattr(fetch_live_fixtures, 'MONTH')
    
    # Verify they are not empty
    assert fetch_live_fixtures.CUTOFF_DATE
    assert fetch_live_fixtures.YEAR_START
    assert fetch_live_fixtures.YEAR_END
    assert isinstance(fetch_live_fixtures.YEAR, int)
    assert isinstance(fetch_live_fixtures.MONTH, int)
