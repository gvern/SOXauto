-- =====================================================================
-- IPE_REC_ERRORS: Master Integration Errors Query (Validated Schema)
-- =====================================================================

-- 1. 3PL Manual Transactions
SELECT 
    '3PL Manual Transactions' AS Source_System,
    [country] AS ID_Company,
    CAST([LPMT_Code] AS NVARCHAR(255)) AS Transaction_ID,
    [lPmT_Amount] AS Amount,
    [Nav_Error_Message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_3PL_MANUAL_TRANSACTIONS_ERRORS]

UNION ALL

-- 2. Cash Deposits
SELECT 
    'Cash Deposits' AS Source_System,
    [country] AS ID_Company,
    CAST([Oms_Payment_No] AS NVARCHAR(255)) AS Transaction_ID,
    [OMS Payment Amount] AS Amount,
    [Nav_Error_Message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_CASHDEPOSIT_ERRORS]

UNION ALL

-- 3. Collection Adjustments
SELECT 
    'Collection Adjustments' AS Source_System,
    [Id_Company] AS ID_Company,
    CAST([NUMBER] AS NVARCHAR(255)) AS Transaction_ID,
    [AMOUNT] AS Amount,
    [ERROR MESSAGE] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_COLLECTIONADJ_ERRORS]

UNION ALL

-- 4. Delivery Fees
SELECT 
    'Delivery Fees' AS Source_System,
    [country] AS ID_Company,
    CAST([Transaction_No] AS NVARCHAR(255)) AS Transaction_ID,
    [OMS_Amount] AS Amount,
    [Nav_Error_Message] AS Integration_Status
FROM [dbo].[V_REC_INTERNATIONAL_DELIVERY_FEES_ERRORS]

UNION ALL

-- 5. Exception Account Statements
SELECT 
    'Exception Account Statements' AS Source_System,
    [country] AS ID_Company,
    CAST([RING_Transaction_Statement_No] AS NVARCHAR(255)) AS Transaction_ID,
    [RING_Closing_Balance] AS Amount,
    [Nav_Error_Message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_EXC_ACCOUNT_STATEMENTS_ERRORS]

UNION ALL

-- 6. JForce Payouts
SELECT 
    'JForce Payouts' AS Source_System,
    [country] AS ID_Company,
    CAST([Payout_Number] AS NVARCHAR(255)) AS Transaction_ID,
    [Payout_Amount] AS Amount,
    [Nav_Error_Message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_JFORCE_PAYOUTS_ERRORS]

UNION ALL

-- 7. JPay App Transactions
SELECT 
    'JPay App Transactions' AS Source_System,
    [country] AS ID_Company,
    CAST([ring_Transaction_Number] AS NVARCHAR(255)) AS Transaction_ID,
    [Ring_Amount] AS Amount,
    [Nav_Error_Message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_JPAYAPP_TRANSACTIONS_ERRORS]

UNION ALL

-- 8. Marketplace Shipping Fees
SELECT 
    'Marketplace Shipping Fees' AS Source_System,
    [Country] AS ID_Company,
    CAST([transaction_number] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount After Discount] AS Amount,
    [nav_error_message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_SC_TRANSACTIONS_CUSTOMER_ERRORS]

UNION ALL

-- 9. Packlist Payments (Payment Reconciles)
SELECT 
    'Packlist Payments' AS Source_System,
    [country] AS ID_Company,
    CAST([OMS Pay. Rec N°] AS NVARCHAR(255)) AS Transaction_ID,
    [OMS reconciled amount] AS Amount,
    [Nav Error Message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_PAYMENT_RECONCILES_ERRORS]

UNION ALL

-- 10. Prepaid Deliveries
SELECT 
    'Prepaid Deliveries' AS Source_System,
    [country] AS ID_Company,
    CAST([OMS Package N°] AS NVARCHAR(255)) AS Transaction_ID,
    [AR] AS Amount,
    [Nav Error Message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_PREPAID_DELIVERIES_ERRORS]

UNION ALL

-- 11. SOI Prepayments
SELECT 
    'SOI Prepayments' AS Source_System,
    [country] AS ID_Company,
    CAST([OMS_Order_No] AS NVARCHAR(255)) AS Transaction_ID,
    [OMS_Pre_payment_Amount] AS Amount,
    [Nav_Error_Message] AS Integration_Status
FROM AIG_Nav_Jumia_Reconciliation.dbo.V_REC_CUSTOMER_PRE_PAYMENTS_ERRORS

UNION ALL

-- 12. Refunds
SELECT 
    'Refunds' AS Source_System,
    [country] AS ID_Company,
    CAST([OMS_refund_no] AS NVARCHAR(255)) AS Transaction_ID,
    [OMS_Refund_Amount] AS Amount,
    [Nav_Error_Message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_CUSTOMER_REFUNDS_ERRORS]

UNION ALL

-- 13. Seller Transactions
SELECT 
    'Seller Transactions' AS Source_System,
    [Country] AS ID_Company,
    CAST([transaction_number] AS NVARCHAR(255)) AS Transaction_ID,
    [Amount After Discount] AS Amount,
    [nav_error_message] AS Integration_Status
FROM AIG_Nav_Jumia_Reconciliation.dbo.V_REC_SC_TRANSACTIONS_ERRORS

UNION ALL

-- 14. Ring Account Statements
SELECT 
    'Ring Account Statements' AS Source_System,
    [country] AS ID_Company,
    CAST([statement_number] AS NVARCHAR(255)) AS Transaction_ID,
    [Total Amount] AS Amount,
    [nav_error_message] AS Integration_Status
FROM AIG_Nav_Jumia_Reconciliation.dbo.V_REC_SC_ACCOUNTSTATEMENTS_ERRORS

UNION ALL

-- 15. Vendor Payments
SELECT 
    'Vendor Payments' AS Source_System,
    [country] AS ID_Company,
    CAST([Payout_Number] AS NVARCHAR(255)) AS Transaction_ID,
    [Payout_Amount] AS Amount,
    [Nav_Error_Message] AS Integration_Status
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_REC_VENDOR_PAYMENTS_ERRORS]
