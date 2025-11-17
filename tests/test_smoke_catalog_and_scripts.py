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
    
    # Verify the query uses the "Issuance" baseline with aggregated sd3 subquery
    assert "LEFT JOIN" in item.sql_query, "IPE_08 should use LEFT JOIN"
    assert "sd3" in item.sql_query, "IPE_08 should use the sd3 aggregated subquery (Issuance baseline)"
    assert "GROUP BY" in item.sql_query, "IPE_08 should use GROUP BY in the sd3 subquery for aggregation"
    
    # Verify the sd3 subquery joins on voucher_code (not fk_Sales_Order_Item)
    assert "scv.[code]=sd3.[voucher_code]" in item.sql_query or "scv.[code] = sd3.[voucher_code]" in item.sql_query, \
        "IPE_08 should join sd3 subquery on voucher_code"
    
    # Verify aggregated columns from sd3 are included
    assert "shipping_discount" in item.sql_query, "IPE_08 should include shipping_discount from sd3"
    assert "shipping_storecredit" in item.sql_query, "IPE_08 should include shipping_storecredit from sd3"
    assert "MPL_storecredit" in item.sql_query, "IPE_08 should include MPL_storecredit from sd3"
    assert "RTL_storecredit" in item.sql_query, "IPE_08 should include RTL_storecredit from sd3"
    assert "TotalAmountUsed" in item.sql_query, "IPE_08 should calculate TotalAmountUsed"
    assert "TotalRemainingAmount" in item.sql_query, "IPE_08 should calculate TotalRemainingAmount"
    
    # Verify it does NOT use row-level join to RPT_SOI (that was the incorrect PR #56 version)
    assert "fk_Sales_Order_Item" not in item.sql_query, "IPE_08 should NOT use fk_Sales_Order_Item (row-level join)"
    assert "Order_Creation_Date" not in item.sql_query, "IPE_08 should NOT include Order_Creation_Date (not in Issuance baseline)"
    assert "Order_Delivery_Date" not in item.sql_query, "IPE_08 should NOT include Order_Delivery_Date (not in Issuance baseline)"
    assert "Order_Cancellation_Date" not in item.sql_query, "IPE_08 should NOT include Order_Cancellation_Date (not in Issuance baseline)"
    
    # Verify sources list contains all 3 required tables for the Issuance query
    assert item.sources is not None and len(item.sources) == 3, "IPE_08 should have exactly 3 sources"
    
    source_locations = [src.location for src in item.sources]
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]" in source_locations, \
        "IPE_08 should have V_STORECREDITVOUCHER_CLOSING as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[StoreCreditVoucher]" in source_locations, \
        "IPE_08 should have StoreCreditVoucher as a source (for template_id and template_name)"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]" in source_locations, \
        "IPE_08 should have RPT_SOI as a source (used in sd3 aggregated subquery)"


def test_catalog_has_cr_03_with_sql_and_sources():
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("CR_03")
    assert item is not None, "CR_03 should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "CR_03 should have a non-empty sql_query"
    
    # Check that required parameters are present in the query
    assert "{year_start}" in item.sql_query, "CR_03 sql_query should contain {year_start} parameter"
    assert "{year_end}" in item.sql_query, "CR_03 sql_query should contain {year_end} parameter"
    assert "{gl_accounts}" in item.sql_query, "CR_03 sql_query should contain {gl_accounts} parameter"
    
    # Verify [Voucher No_] column is present in the SELECT list (official join key for VTC reconciliation)
    assert "gl.[Voucher No_]" in item.sql_query, "CR_03 sql_query should include gl.[Voucher No_] column for VTC reconciliation"
    
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


def test_catalog_ipe_31_aligned_with_baseline():
    """Test IPE_31 query is aligned with audited baseline (parameterized, 11 tables, no @subsequentmonth)."""
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("IPE_31")
    assert item is not None, "IPE_31 should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "IPE_31 should have a non-empty sql_query"
    
    # Verify {cutoff_date} parameter is used (not hardcoded @subsequentmonth variable)
    assert "{cutoff_date}" in item.sql_query, "IPE_31 should use {cutoff_date} parameter"
    assert "@subsequentmonth" not in item.sql_query, "IPE_31 should not use @subsequentmonth variable"
    
    # Verify no DECLARE or SET statements (query should be fully parameterized)
    assert "Declare" not in item.sql_query, "IPE_31 should not have DECLARE statements"
    assert "SET @" not in item.sql_query, "IPE_31 should not have SET variable statements"
    
    # Verify DATEADD(day, 1, '{cutoff_date}') pattern is used (replaces @subsequentmonth)
    assert "DATEADD(day, 1, '{cutoff_date}')" in item.sql_query, \
        "IPE_31 should use DATEADD(day, 1, '{cutoff_date}') pattern for subsequent month calculation"
    
    # Verify it uses CTE for complex collection TV query
    assert ";WITH CTE AS" in item.sql_query or "WITH CTE AS" in item.sql_query, \
        "IPE_31 should use CTE (Common Table Expression)"
    
    # Verify all 4 UNION ALL parts exist in the complex query
    assert item.sql_query.count("UNION ALL") >= 3, \
        "IPE_31 should have at least 3 UNION ALL clauses (4-part query)"
    
    # Verify key business logic elements
    assert "OPEN TRANSACTIONS" in item.sql_query, "IPE_31 should have OPEN TRANSACTIONS section"
    assert "TRANSACTIONLISTS IN PROGRESS" in item.sql_query, \
        "IPE_31 should have TRANSACTIONLISTS IN PROGRESS section"
    assert "PAYMENTS/TRANSFERS IN PROGRESS" in item.sql_query, \
        "IPE_31 should have PAYMENTS/TRANSFERS IN PROGRESS section"
    
    # Verify all 11 required tables are in sources
    assert item.sources is not None and len(item.sources) == 11, \
        "IPE_31 should have exactly 11 sources to match baseline"
    
    source_locations = [src.location for src in item.sources]
    
    # OMS tables (8)
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_TRANSACTION]" in source_locations, \
        "IPE_31 should have RPT_CASHREC_TRANSACTION"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PACKAGES]" in source_locations, \
        "IPE_31 should have RPT_PACKLIST_PACKAGES"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]" in source_locations, \
        "IPE_31 should have RPT_PACKLIST_PAYMENTS"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]" in source_locations, \
        "IPE_31 should have RPT_CASHDEPOSIT"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS]" in source_locations, \
        "IPE_31 should have RPT_CASHREC_REALLOCATIONS"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONADJ]" in source_locations, \
        "IPE_31 should have RPT_COLLECTIONADJ"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_HUBS_3PL_MAPPING]" in source_locations, \
        "IPE_31 should have RPT_HUBS_3PL_MAPPING"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONPARTNERS]" in source_locations, \
        "IPE_31 should have RPT_COLLECTIONPARTNERS"
    
    # NAV tables (3)
    assert "[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]" in source_locations, \
        "IPE_31 should have Dim_Company"
    assert "[AIG_Nav_DW].[dbo].[Bank Accounts]" in source_locations, \
        "IPE_31 should have Bank Accounts"
    assert "[AIG_Nav_DW].[dbo].[Bank Account Posting Group]" in source_locations, \
        "IPE_31 should have Bank Account Posting Group"


def test_catalog_doc_voucher_usage_with_sql_and_sources():
    """Test DOC_VOUCHER_USAGE query for Timing Difference Bridge (Usage May 2025 Query - Corrected)."""
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("DOC_VOUCHER_USAGE")
    assert item is not None, "DOC_VOUCHER_USAGE should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "DOC_VOUCHER_USAGE should have a non-empty sql_query"
    
    # Verify item metadata
    assert item.item_type == "DOC", "DOC_VOUCHER_USAGE should be a DOC type"
    assert item.control == "C-PG-1", "DOC_VOUCHER_USAGE should be for control C-PG-1"
    assert item.status == "Completed", "DOC_VOUCHER_USAGE should have Completed status"
    assert item.baseline_required == True, "DOC_VOUCHER_USAGE should require baseline"
    
    # Check that required parameters are present in the query
    assert "{cutoff_date}" in item.sql_query, "DOC_VOUCHER_USAGE sql_query should contain {cutoff_date} parameter"
    assert "{id_companies_active}" in item.sql_query, "DOC_VOUCHER_USAGE sql_query should contain {id_companies_active} parameter"
    
    # Verify the query uses RPT_SOI table
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]" in item.sql_query, \
        "DOC_VOUCHER_USAGE should query from RPT_SOI table"
    
    # Verify joins with new tables
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]" in item.sql_query, \
        "DOC_VOUCHER_USAGE should join with V_STORECREDITVOUCHER_CLOSING table"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_TRANSACTIONS_SELLER]" in item.sql_query, \
        "DOC_VOUCHER_USAGE should join with RPT_TRANSACTIONS_SELLER table"
    
    # Verify key business logic filters
    assert "VOUCHER_TYPE] = 'reusablecredit'" in item.sql_query, \
        "DOC_VOUCHER_USAGE should filter for reusablecredit voucher type"
    assert "PACKAGE_DELIVERY_DATE] <" in item.sql_query, \
        "DOC_VOUCHER_USAGE should filter by PACKAGE_DELIVERY_DATE"
    assert "year(soi.[DELIVERED_DATE]) > 2014" in item.sql_query, \
        "DOC_VOUCHER_USAGE should filter DELIVERED_DATE year > 2014"
    
    # Verify aggregation columns (note: new query structure)
    assert "sum(ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT],0)) shipping_storecredit" in item.sql_query, \
        "DOC_VOUCHER_USAGE should aggregate MTR_SHIPPING_VOUCHER_DISCOUNT"
    assert "MPL_storecredit" in item.sql_query, \
        "DOC_VOUCHER_USAGE should calculate MPL_storecredit for marketplace"
    assert "RTL_storecredit" in item.sql_query, \
        "DOC_VOUCHER_USAGE should calculate RTL_storecredit for retail"
    assert "TotalAmountUsed" in item.sql_query, \
        "DOC_VOUCHER_USAGE should calculate TotalAmountUsed"
    
    # Verify business_use column from V_STORECREDITVOUCHER_CLOSING
    assert "business_use" in item.sql_query, \
        "DOC_VOUCHER_USAGE should include business_use from V_STORECREDITVOUCHER_CLOSING"
    
    # Verify GROUP BY clause (note: different grouping in new query)
    assert "group by" in item.sql_query.lower(), "DOC_VOUCHER_USAGE should have GROUP BY clause"
    assert "soi.[ID_Company]" in item.sql_query, "DOC_VOUCHER_USAGE should group by ID_Company"
    assert "soi.[voucher_type]" in item.sql_query, "DOC_VOUCHER_USAGE should group by voucher_type"
    
    # Verify sources list (now includes 3 tables)
    assert item.sources is not None and len(item.sources) == 3, "DOC_VOUCHER_USAGE should have exactly 3 sources"
    
    source_locations = [src.location for src in item.sources]
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]" in source_locations, \
        "DOC_VOUCHER_USAGE should have RPT_SOI as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]" in source_locations, \
        "DOC_VOUCHER_USAGE should have V_STORECREDITVOUCHER_CLOSING as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_TRANSACTIONS_SELLER]" in source_locations, \
        "DOC_VOUCHER_USAGE should have RPT_TRANSACTIONS_SELLER as a source"
    
    # Verify source metadata (all should be from OMS/FinRec)
    for source in item.sources:
        assert source.system == "OMS", f"DOC_VOUCHER_USAGE source {source.location} should be from OMS system"
        assert source.domain == "FinRec", f"DOC_VOUCHER_USAGE source {source.location} should be from FinRec domain"


def test_catalog_cr_05_aligned_with_baseline():
    """Test CR_05 query is aligned with correct audited baseline (3-table join with CASE WHEN FX logic)."""
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("CR_05")
    assert item is not None, "CR_05 should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "CR_05 should have a non-empty sql_query"
    
    # Verify {year} and {month} parameters are used (not hardcoded values)
    assert "{year}" in item.sql_query, "CR_05 should use {year} parameter"
    assert "{month}" in item.sql_query, "CR_05 should use {month} parameter"
    
    # Verify correct baseline field names (year, cod_month)
    assert "[year]" in item.sql_query, "CR_05 should use [year] field for year filtering"
    assert "[cod_month]" in item.sql_query, "CR_05 should use [cod_month] field for month filtering"
    
    # Verify all 3 tables are joined (Dim_Company as main, RPT_FX_RATES subquery, Dim_Country)
    assert "[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]" in item.sql_query, \
        "CR_05 should query from Dim_Company table"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]" in item.sql_query, \
        "CR_05 should join with RPT_FX_RATES table"
    assert "[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Country]" in item.sql_query, \
        "CR_05 should join with Dim_Country table"
    
    # Verify 3 LEFT JOINs exist (subquery fx and table c)
    assert item.sql_query.lower().count("left join") >= 2, \
        "CR_05 should have at least 2 LEFT JOIN clauses"
    
    # Verify CASE WHEN logic for FX rate special handling
    assert "case" in item.sql_query.lower() and "when" in item.sql_query.lower(), \
        "CR_05 should have CASE WHEN logic"
    assert "'United States of America'" in item.sql_query, \
        "CR_05 should include USA special handling in CASE WHEN"
    assert "'Germany'" in item.sql_query, \
        "CR_05 should include Germany special handling in CASE WHEN"
    assert "right(comp.[Company_Code],4)='_USD'" in item.sql_query, \
        "CR_05 should check for _USD suffix in Company_Code for Germany"
    assert "then 1" in item.sql_query, \
        "CR_05 should set FX_rate to 1 for USA and Germany _USD companies"
    assert "else fx.rate" in item.sql_query, \
        "CR_05 should use fx.rate as default in CASE WHEN"
    
    # Verify WHERE clause with specific filters in the subquery
    assert "[base_currency] = 'USD'" in item.sql_query, \
        "CR_05 should filter for USD base currency"
    assert "[rate_type] = 'Closing'" in item.sql_query, \
        "CR_05 should filter for Closing rate type"
    assert "country <> 'United arab emirates (the)'" in item.sql_query, \
        "CR_05 should exclude 'United arab emirates (the)'"
    
    # Verify sources list contains all 3 tables
    assert item.sources is not None and len(item.sources) == 3, \
        "CR_05 should have exactly 3 sources (Dim_Company, RPT_FX_RATES, Dim_Country)"
    
    source_locations = [src.location for src in item.sources]
    assert "[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]" in source_locations, \
        "CR_05 should have Dim_Company as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]" in source_locations, \
        "CR_05 should have RPT_FX_RATES as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Country]" in source_locations, \
        "CR_05 should have Dim_Country as a source"


def test_catalog_ipe_rec_errors_with_sql_and_sources():
    """Test IPE_REC_ERRORS query - Master Integration Errors consolidation for Task 3."""
    from src.core.catalog.cpg1 import get_item_by_id

    item = get_item_by_id("IPE_REC_ERRORS")
    assert item is not None, "IPE_REC_ERRORS should exist in the catalog"
    assert isinstance(item.sql_query, str) and item.sql_query.strip(), "IPE_REC_ERRORS should have a non-empty sql_query"
    
    # Verify item metadata
    assert item.item_type == "IPE", "IPE_REC_ERRORS should be an IPE type"
    assert item.control == "C-PG-1", "IPE_REC_ERRORS should be for control C-PG-1"
    assert item.change_status == "New IPE", "IPE_REC_ERRORS should be marked as New IPE"
    assert "Task 3" in item.description or "Task 3" in item.cross_reference, \
        "IPE_REC_ERRORS should reference Task 3 in description or cross_reference"
    
    # Verify UNION ALL structure (consolidates multiple tables)
    union_count = item.sql_query.count("UNION ALL")
    assert union_count >= 10, f"IPE_REC_ERRORS should have at least 10 UNION ALL clauses (found {union_count})"
    
    # Verify standardized output columns are present in each SELECT
    required_columns = ["Source_System", "ID_Company", "Transaction_ID", "Amount", "Integration_Status"]
    for col in required_columns:
        assert col in item.sql_query, f"IPE_REC_ERRORS should have {col} in standardized schema"
    
    # Verify filter for non-integrated records
    assert "NOT IN ('Posted', 'Integrated')" in item.sql_query, \
        "IPE_REC_ERRORS should filter for non-integrated records (NOT IN ('Posted', 'Integrated'))"
    assert "[Nav_Integration_Status]" in item.sql_query, \
        "IPE_REC_ERRORS should use Nav_Integration_Status column"
    
    # Verify key source tables from requirements are in the query
    key_tables = [
        "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]",
        "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_JFORCE_PAYOUTS]",
        "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_JPAY_APP_TRANSACTION]",
        "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]",
        "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_REFUNDS]",
        "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_VENDOR_PAYMENTS]",
    ]
    for table in key_tables:
        assert table in item.sql_query, f"IPE_REC_ERRORS should query from {table}"
    
    # Verify source metadata lists multiple tables (15+ as per requirements)
    assert item.sources is not None and len(item.sources) >= 15, \
        f"IPE_REC_ERRORS should have at least 15 sources (found {len(item.sources) if item.sources else 0})"
    
    # Verify some specific source systems are listed in the metadata
    source_locations = [src.location for src in item.sources]
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_3PL_MANUAL_TRANSACTIONS]" in source_locations, \
        "IPE_REC_ERRORS should have RPT_3PL_MANUAL_TRANSACTIONS as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]" in source_locations, \
        "IPE_REC_ERRORS should have RPT_CASHDEPOSIT as a source"
    assert "[AIG_Nav_Jumia_Reconciliation].[RING].[RPT_ACCOUNTSTATEMENTS]" in source_locations, \
        "IPE_REC_ERRORS should have RING.RPT_ACCOUNTSTATEMENTS as a source"


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
