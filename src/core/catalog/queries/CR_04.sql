-- =============================================
-- Report: NAV GL Balances (CR_04)
-- Description: General ledger Balances 
-- Parameters: {year_start}, {year_end}, {gl_accounts_cr_04}
-- Source: NAV Data Warehouse
-- GL Accounts: 18650,18397
-- Purpose: Extract GL balances for variance analysis 
-- =============================================
SELECT *
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]
WHERE CLOSING_DATE BETWEEN CAST({year_start} AS DATE) AND CAST({year_end} AS DATE)
    AND 
        (
            GROUP_COA_ACCOUNT_NO LIKE '145%' 
            OR GROUP_COA_ACCOUNT_NO LIKE '15%' 
            OR GROUP_COA_ACCOUNT_NO IN {gl_accounts_cr_04}
        )													
