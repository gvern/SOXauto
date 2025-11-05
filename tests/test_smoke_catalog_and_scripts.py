import importlib
import os
import sys
import pytest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)


def test_catalog_has_ipe_07_with_sql():
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("IPE_07")
    assert item is not None, "IPE_07 should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "IPE_07 should have a non-empty sql_query"


def test_catalog_has_ipe_08_with_sql_and_sources():
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("IPE_08")
    assert item is not None, "IPE_08 should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "IPE_08 should have a non-empty sql_query"
    
    # Check that {cutoff_date} parameter is present in the query
    assert "{cutoff_date}" in item.sql_query, "IPE_08 sql_query should contain {cutoff_date} parameter"
    
    # Check that {id_companies_active} parameter is present in the query (new parameterized baseline)
    assert "{id_companies_active}" in item.sql_query, "IPE_08 sql_query should contain {id_companies_active} parameter"
    
    # Verify sources list contains all three required tables
    assert item.sources is not None and len(item.sources) == 3, "IPE_08 should have exactly 3 sources"
    
    source_locations = [src.location for src in item.sources]
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]" in source_locations, \
        "IPE_08 should have V_STORECREDITVOUCHER_CLOSING as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[StoreCreditVoucher]" in source_locations, \
        "IPE_08 should have StoreCreditVoucher as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]" in source_locations, \
        "IPE_08 should have RPT_SOI as a source"


@pytest.mark.parametrize(
    "module_name",
    [
        "scripts.generate_customer_accounts",
        "scripts.generate_collection_accounts",
        "scripts.generate_other_ar",
        "scripts.run_sql_from_catalog",
        "scripts.check_mssql_connection",
    ],
)
def test_scripts_importable(module_name):
    mod = importlib.import_module(module_name)
    assert mod is not None


def test_build_connection_string_requires_env():
    # Ensure env vars are cleared for this test
    for k in [
        "DB_CONNECTION_STRING",
        "MSSQL_SERVER",
        "MSSQL_DATABASE",
        "MSSQL_USER",
        "MSSQL_PASSWORD",
    ]:
        os.environ.pop(k, None)

    import scripts.generate_customer_accounts as gca

    with pytest.raises(RuntimeError):
        _ = gca.build_connection_string()
