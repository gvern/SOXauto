-- =============================================
-- Report: TV Voucher Timing Differences (IPE_08_TIMING)
-- Description: Inactive vouchers for timing difference bridge
-- Purpose: Vouchers created before cutoff, still valid at cutoff, but inactive
-- Parameters: {cutoff_date}
-- Bridge: Timing Difference
-- =============================================

SELECT
    t1.[ID_Company],
    t1.[id] AS [Voucher_ID],
    t1.[Code],
    t1.[discount_amount] AS [Amount],
    NULL AS [Currency],
    t1.[Business_Use],
    t1.[type] AS [Origin],
    CASE
        WHEN ISNULL(t1.[is_active], 0) = 1 THEN 'active'
        ELSE 'inactive'
    END AS [Status],
    t1.[created_at] AS [Creation_Date],
    t1.[from_date] AS [Start_Date],
    t1.[to_date] AS [End_Date],
    tTwo.[COD_OMS_SALES_ORDER_ITEM] AS [fk_Sales_Order_Item],
    tTwo.[ID_Sales_Order_Item],
    tTwo.[ORDER_CREATION_DATE] AS [Order_Creation_Date],
    tTwo.[DELIVERED_DATE] AS [Order_Delivery_Date],
    tTwo.[CANCELLATION_DATE] AS [Order_Cancellation_Date],
    tTwo.[CURRENT_STATUS] AS [Order_Item_Status],
    tTwo.[Payment_Method],
    t1.[fk_Customer],
    tTwo.[COD_OMS_SALES_ORDER] AS [fk_Sales_Order],
    tTwo.[Order_Nr],
    t1.[description] AS [Comment],
    NULL AS [Wallet_Name]
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] t1
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] tTwo
    ON t1.[ID_Company] = tTwo.[ID_Company]
    AND t1.[Code] = tTwo.[voucher_code]
WHERE t1.[created_at] < CAST('{cutoff_date}' AS DATE)
    AND ISNULL(t1.[is_active], 0) = 0
    AND t1.[to_date] >= CAST('{cutoff_date}' AS DATE)
    AND (
        tTwo.[CURRENT_STATUS] NOT IN ('delivered', 'cancelled', 'closed')
        OR tTwo.[CURRENT_STATUS] IS NULL
    )
    AND (
        tTwo.[DELIVERED_DATE] >= CAST('{cutoff_date}' AS DATE)
        OR tTwo.[DELIVERED_DATE] IS NULL
    )
    AND (
        tTwo.[CANCELLATION_DATE] >= CAST('{cutoff_date}' AS DATE)
        OR tTwo.[CANCELLATION_DATE] IS NULL
    );
