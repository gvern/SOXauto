-- =============================================
-- Report: Marketplace Accrued Revenues (IPE_11)
-- Description: Seller transactions not yet paid out (accrued revenues)
-- Parameters: {cutoff_date}, {period_month_start}, {subsequent_month_start}
-- Source: RING (Seller Center)
-- GL Accounts: Marketplace accrued revenue accounts
-- Logic: Captures transactions created during the reporting period that remain unpaid
-- =============================================

SELECT 
    trs.[ID_Company],
    trs.[Created_Date] AS SC_Created_Date,
    trs.[ID_Transaction] AS SC_ID_Transaction,
    trs.[Transaction_No] AS SC_Transaction_No,
    RTSR.[Transaction_Type_Name] AS SC_Transaction_Type,
    trs.[Transaction_Type] AS SC_ASG_Name,
    trs.[Nav_Type] AS SC_Nav_Type,
    trs.[ERP_Name] AS SC_Nav_Message,
    trs.[Transaction_Amount] AS SC_Transaction_Amount,
    trs.[Created_Manually] AS SC_Created_Manually,
    trs.[Vendor_Short_Code] AS SC_Vendor_No,
    trs.[BOB_ID_Vendor],
    trs.[Vendor_Name] AS SC_Vendor_Name,
    vnd.Is_Global,
    trs.[SC_ID_Sales_Order_Item],
    trs.[OMS_ID_Sales_Order_Item],
    trs.[BOB_ID_Sales_Order_Item],
    trs.[Order_Number] AS Order_Nr,
    trs.[ID_Account_Statement] AS SC_ID_Account_Statement,
    stt.[RING_Transaction_Statement_No] AS SC_Transaction_Statement_No,
    stt.[RING_Start_Date] AS SC_Start_Date,
    stt.[RING_End_Date] AS SC_End_Date,
    stt.[RING_Paid] AS SC_Paid,
    stt.[RING_Paid_Date] AS SC_Paid_Date,
    asg.[ASG_Level_1],
    asg.[ASG_Level_2],
    asg.[ASG_Level_3],
    asg.[ASG_Level_4]
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_TRANSACTIONS_SELLER] trs
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[RING].[RPT_ACCOUNTSTATEMENTS] stt
    ON stt.id_company = trs.id_company 
    AND stt.[RING_ID_Transaction_Statement] = trs.[ID_Account_Statement]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_VENDORS] vnd
    ON vnd.ID_company = trs.ID_company 
    AND vnd.BOB_ID_Vendor = trs.BOB_ID_Vendor
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_DIM_ASG_V2] asg 
    ON trs.[ID_Company] = asg.[ID_Company] 
    AND trs.[Transaction_Type] = asg.[SC_ASG_Name]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[RING].[RPT_TRANSACTIONS] AS RTSR
    ON trs.ID_Company = RTSR.ID_Company 
    AND trs.ID_Transaction = RTSR.ID_Transaction
WHERE trs.[Created_Date] > '2020-01-01 00:00:00.000'
    AND trs.[Created_Date] >= {period_month_start} -- Start of reporting period (e.g., 2025-08-01 00:00:00)
    AND trs.[Created_Date] < {subsequent_month_start} -- End of reporting period (e.g., 2025-09-01 00:00:00)
    AND asg.ASG_Level_1 = 'Revenues'
    AND (
        trs.[ID_Account_Statement] IS NULL
        OR stt.[RING_End_Date] > {cutoff_date} -- Last second of period (e.g., 2025-08-31 23:59:59)
    );
