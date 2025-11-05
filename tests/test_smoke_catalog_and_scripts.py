import importlib
import os
import sys
import pytest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)


def test_catalog_has_ipe_07_with_sql():
    """Test IPE_07 query is aligned with 2025 audited baseline (temp tables, LOAN-REC-NAT)."""
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("IPE_07")
    assert item is not None, "IPE_07 should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "IPE_07 should have a non-empty sql_query"
    
    # 1. Verify temp table structure (2-step aggregation with ##temp and ##temp2)
    assert "##temp" in item.sql_query, "IPE_07 should use ##temp table for pre-aggregation"
    assert "##temp2" in item.sql_query, "IPE_07 should use ##temp2 table for pre-aggregation"
    assert "CREATE NONCLUSTERED INDEX IDX_Temp" in item.sql_query, "IPE_07 should create index on ##temp"
    assert "CREATE NONCLUSTERED INDEX IDX_Temp2" in item.sql_query, "IPE_07 should create index on ##temp2"
    assert "DROP TABLE ##temp" in item.sql_query, "IPE_07 should clean up ##temp"
    assert "DROP TABLE ##temp2" in item.sql_query, "IPE_07 should clean up ##temp2"
    
    # 2. Verify {cutoff_date} parameterization (no hardcoded GETDATE() logic for date filters)
    assert "{cutoff_date}" in item.sql_query, "IPE_07 should use {cutoff_date} parameter"
    # Note: GETDATE() is still used in the CASE statement for Debit_Credit_DueMonth logic, which is acceptable
    assert "DATEADD(s,-1,DATEADD(mm, DATEDIFF(m,0,GETDATE()),0))" not in item.sql_query, \
        "IPE_07 should not use hardcoded DATEADD/GETDATE logic for date filtering"
    
    # 3. Verify LOAN-REC-NAT is included in Customer Posting Group filter
    assert "'LOAN-REC-NAT'" in item.sql_query, "IPE_07 should include 'LOAN-REC-NAT' in Customer Posting Group filter"
    
    # 4. Verify all 5 required tables are in sources
    assert item.sources is not None and len(item.sources) == 5, "IPE_07 should have exactly 5 sources"
    
    source_locations = [src.location for src in item.sources]
    assert "[AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]" in source_locations, \
        "IPE_07 should have Detailed Customer Ledg_ Entry as a source"
    assert "[AIG_Nav_DW].[dbo].[Customer Ledger Entries]" in source_locations, \
        "IPE_07 should have Customer Ledger Entries as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]" in source_locations, \
        "IPE_07 should have Dim_Company as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Busline]" in source_locations, \
        "IPE_07 should have Dim_Busline as a source"
    assert "[AAN_Nav_Jumia_Reconciliation].[dbo].[Customers]" in source_locations, \
        "IPE_07 should have Customers as a source"


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


def test_catalog_has_cr_03_with_sql_and_sources():
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("CR_03")
    assert item is not None, "CR_03 should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "CR_03 should have a non-empty sql_query"
    
    # Check that required parameters are present in the query
    assert "{year_start}" in item.sql_query, "CR_03 sql_query should contain {year_start} parameter"
    assert "{year_end}" in item.sql_query, "CR_03 sql_query should contain {year_end} parameter"
    assert "{gl_accounts}" in item.sql_query, "CR_03 sql_query should contain {gl_accounts} parameter"
    
    # Verify sources list contains all 5 required tables
    assert item.sources is not None and len(item.sources) == 5, "CR_03 should have exactly 5 sources"
    
    source_locations = [src.location for src in item.sources]
    assert "[AIG_Nav_DW].[dbo].[G_L Entries]" in source_locations, \
        "CR_03 should have G_L Entries as a source"
    assert "[AIG_Nav_DW].[dbo].[Detailed G_L Entry]" in source_locations, \
        "CR_03 should have Detailed G_L Entry as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]" in source_locations, \
        "CR_03 should have Dim_Company as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts]" in source_locations, \
        "CR_03 should have Dim_ChartOfAccounts as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping]" in source_locations, \
        "CR_03 should have GDOC_IFRS_Tabular_Mapping as a source"
def test_catalog_cr_04_aligned_with_baseline():
    """Test CR_04 query is aligned with Query 2 from CR_03_04 mapping (IA baseline)."""
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("CR_04")
    assert item is not None, "CR_04 should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "CR_04 should have a non-empty sql_query"
    
    # Verify it uses specific columns, not SELECT *
    assert "SELECT *" not in item.sql_query, "CR_04 should not use SELECT *, must specify columns"
    
    # Verify specific columns from baseline Query 2 are present
    required_columns = [
        "ID_COMPANY", "COMPANY_NAME", "COUNTRY_CODE", "COUNTRY_NAME",
        "CLOSING_DATE", "REFRESH_DATE", "GROUP_COA_ACCOUNT_NO", "GROUP_COA_ACCOUNT_NAME",
        "REAL_COA", "CURRENCY", "FX_RATE", "BALANCE_AT_DATE",
        "BUSLINE_CODE", "REPORTING_COUNTRY_CODE", "REPORTING_COUNTRY_NAME",
        "PARTNER_CODE", "IC_PARTNER_CODE", "IS_RECHARGE", "IS_RETAINED_EARNINGS",
        "CONSO_ACCOUNT_NO", "CONSO_ACCOUNT_NAME", "IFRS_LEVEL_1_NAME",
        "IFRS_LEVEL_2_NAME", "IFRS_LEVEL_3_NAME", "IS_INTERCO"
    ]
    for col in required_columns:
        assert f"[{col}]" in item.sql_query, f"CR_04 query should contain column [{col}]"
    
    # Verify it uses {cutoff_date} parameter (not BETWEEN with year_start/year_end)
    assert "{cutoff_date}" in item.sql_query, "CR_04 should use {cutoff_date} parameter"
    assert "BETWEEN" not in item.sql_query, "CR_04 should not use BETWEEN for date filtering"
    assert "{year_start}" not in item.sql_query, "CR_04 should not use {year_start} parameter"
    assert "{year_end}" not in item.sql_query, "CR_04 should not use {year_end} parameter"
    
    # Verify it uses {gl_accounts} parameter (not LIKE patterns)
    assert "{gl_accounts}" in item.sql_query, "CR_04 should use {gl_accounts} parameter"
    assert "LIKE" not in item.sql_query, "CR_04 should not use LIKE patterns for account filtering"
    
    # Verify it uses the correct source table
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]" in item.sql_query, \
        "CR_04 should query from V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT"


def test_catalog_ipe_10_aligned_with_baseline():
    """Test IPE_10 query is aligned with audited baseline (parameterized dates)."""
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("IPE_10")
    assert item is not None, "IPE_10 should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "IPE_10 should have a non-empty sql_query"
    
    # Verify {cutoff_date} parameter is used (not hardcoded GETDATE() logic)
    assert "{cutoff_date}" in item.sql_query, "IPE_10 should use {cutoff_date} parameter"
    
    # Verify no hardcoded DATEADD/GETDATE logic for date filtering
    assert "DATEADD(s, - 1, DATEADD(mm, DATEDIFF(m, 0, GETDATE()), 0))" not in item.sql_query, \
        "IPE_10 should not use hardcoded DATEADD/GETDATE logic - use {cutoff_date} instead"
    assert "DATEADD(s,-1,DATEADD(mm, DATEDIFF(m,0,GETDATE()),0))" not in item.sql_query, \
        "IPE_10 should not use hardcoded DATEADD/GETDATE logic (no spaces variant)"
    
    # Verify proper BETWEEN clause structure
    assert "BETWEEN '2018-01-01 00:00:00' AND '{cutoff_date}'" in item.sql_query, \
        "IPE_10 should use proper BETWEEN clause with cutoff_date parameter"
    
    # Verify it uses the correct source table
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]" in item.sql_query, \
        "IPE_10 should query from RPT_SOI table"
    
    # Verify key business logic conditions from baseline
    assert "[IS_PREPAYMENT] = 1" in item.sql_query, "IPE_10 should filter for prepayments"
    assert "IS_MARKETPLACE = 1" in item.sql_query, "IPE_10 should have marketplace logic"
    assert "IS_MARKETPLACE = 0" in item.sql_query, "IPE_10 should have non-marketplace logic"
    assert "[DELIVERY_TYPE] IN" in item.sql_query, "IPE_10 should filter by delivery type"
    assert "'Digital Content'" in item.sql_query, "IPE_10 should include Digital Content in delivery types"
    assert "'Gift Card'" in item.sql_query, "IPE_10 should include Gift Card in delivery types"
    
    # Verify source metadata
    assert item.sources is not None and len(item.sources) == 1, "IPE_10 should have exactly 1 source"
    assert item.sources[0].location == "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]", \
        "IPE_10 source should be RPT_SOI"


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
