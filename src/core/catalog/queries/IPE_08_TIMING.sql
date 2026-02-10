-- =============================================
-- Report: TV Voucher Timing Differences (IPE_08_TIMING)
-- Description: Inactive vouchers for timing difference bridge
-- Purpose: Vouchers created before cutoff, still valid at cutoff, but inactive
-- Parameters: {cutoff_date}
-- Bridge: Timing Difference
-- =============================================

SELECT
    t1.[ID_Company],
    t1.[Voucher_ID],
    t1.[Code],
    t1.[Amount],
    t1.[Currency],
    t1.[Business_Use],
    t1.[Origin],
    t1.[Status],
    t1.[Creation_Date],
    t1.[Start_Date],
    t1.[End_Date],
    t1.[fk_Sales_Order_Item],
    t1.[ID_Sales_Order_Item],
    tTwo.[Order_Creation_Date],
    tTwo.[Order_Delivery_Date],
    tTwo.[Order_Cancellation_Date],
    tTwo.[Order_Item_Status],
    tTwo.[Payment_Method],
    t1.[fk_Customer],
    t1.[fk_Sales_Order],
    tTwo.[Order_Nr],
    t1.[Comment],
    t1.[Wallet_Name]
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] t1
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] tTwo
    ON t1.fk_Sales_Order_Item = tTwo.ID_Sales_Order_Item
WHERE t1.[Creation_Date] < CAST({cutoff_date} AS DATE)
    AND t1.[Status] = 'inactive'
    AND t1.[End_Date] >= CAST({cutoff_date} AS DATE)
    AND (tTwo.[Order_Item_Status] NOT IN ('delivered', 'cancelled', 'closed') 
         OR tTwo.[Order_Item_Status] IS NULL)
    AND (tTwo.[Order_Delivery_Date] >= CAST({cutoff_date} AS DATE)
         OR tTwo.[Order_Delivery_Date] IS NULL)
    AND (tTwo.[Order_Cancellation_Date] >= CAST({cutoff_date} AS DATE)
         OR tTwo.[Order_Cancellation_Date] IS NULL);
