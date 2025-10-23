import pytest


def pytest_collection_modifyitems(config, items):
    skip_athena = pytest.mark.skip(reason="Athena path deprecated in SQL-only mode")
    skip_okta = pytest.mark.skip(reason="OKTA/AWS auth tests disabled for local smoke run")
    for item in items:
        path = str(item.fspath)
        if "athena" in path:
            item.add_marker(skip_athena)
        if "okta" in path:
            item.add_marker(skip_okta)
