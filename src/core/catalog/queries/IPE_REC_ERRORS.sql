-- =====================================================================
-- IPE_REC_ERRORS: Master Integration Errors Query
-- =====================================================================
-- Purpose: Consolidate integration errors from 36 FinRec tables into
--          a standardized view for Task 3 (Integration Errors Bridge)
--
-- Output Schema:
--   - Source_System (String: e.g., 'Cash Deposits', 'JForce Payouts')
--   - ID_Company (Company identifier)
--   - Transaction_ID (Primary key from source table)
--   - Amount (Monetary value)
--   - Integration_Status (Nav_Integration_Status column)
--
-- Filter: Only non-integrated records (Status NOT IN ('Posted', 'Integrated'))
-- =====================================================================

-- 1. 3PL Manual Transactions
SELECT
    '3PL Manual Transactions' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Transaction_Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_3PL_MANUAL_TRANSACTIONS]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 2. Cash Deposits
SELECT
    'Cash Deposits' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 3. Collection Adjustments
SELECT
    'Collection Adjustments' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONADJ]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 4. Delivery Fees
SELECT
    'Delivery Fees' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_DELIVERY_FEES]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 5. Exception Account Statements
SELECT
    'Exception Account Statements' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Total_Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_EXC_ACCOUNTSTATEMENTS]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 6. JForce Payouts
SELECT
    'JForce Payouts' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_JFORCE_PAYOUTS]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 7. JPay App Transactions
SELECT
    'JPay App Transactions' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Transaction_Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_JPAY_APP_TRANSACTION]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 8. Marketplace Shipping Fees
SELECT
    'Marketplace Shipping Fees' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_MARKETPLACE_SHIPPING_FEES]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 9. Packlist Payments (Payment Reconciles)
SELECT
    'Packlist Payments' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [OMS_Payment_Reconciled_Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 10. Prepaid Deliveries
SELECT
    'Prepaid Deliveries' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PREPAID_DELIVERIES]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 11. SOI Prepayments
SELECT
    'SOI Prepayments' AS Source_System,
    ID_Company,
    CAST([COD_OMS_SALES_ORDER_ITEM] AS NVARCHAR(255)) AS Transaction_ID,
    [MTR_PAID_PRICE] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')
  AND [IS_PREPAYMENT] = 1

UNION ALL

-- 12. Refunds
SELECT
    'Refunds' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_REFUNDS]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 13. Seller Transactions
SELECT
    'Seller Transactions' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Transaction_Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_TRANSACTIONS_SELLER]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 14. Ring Account Statements
SELECT
    'Ring Account Statements' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Statement_Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[RING].[RPT_ACCOUNTSTATEMENTS]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

UNION ALL

-- 15. Vendor Payments
SELECT
    'Vendor Payments' AS Source_System,
    ID_Company,
    CAST([Transaction_ID] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount] AS Amount,
    [Nav_Integration_Status] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_VENDOR_PAYMENTS]
WHERE [Nav_Integration_Status] NOT IN ('Posted', 'Integrated')

-- =====================================================================
-- NOTE: Additional tables can be added following the same pattern.
-- The issue indicates 36 total tables. The 15 tables above represent
-- the explicitly mapped tables from the requirements.
-- 
-- To add more tables:
-- 1. Add UNION ALL clause
-- 2. Map Source_System (descriptive name)
-- 3. Map ID_Company
-- 4. Map Transaction_ID (primary key, cast to NVARCHAR(255))
-- 5. Map Amount (monetary value column)
-- 6. Map Integration_Status (Nav_Integration_Status)
-- 7. Add WHERE clause filtering for non-integrated records
-- =====================================================================
