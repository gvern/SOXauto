SELECT
    t1.[ID_Company],
    t1.[id],
    t1.[Code],
    t1.[Amount],
    t1.[Currency],
    t1.[Business_Use],
    t1.[Status],
    t1.[Creation_Date],
    t1.[End_Date],
    t1.[remaining_amount],
    -- Critical Dates from RPT_SOI
    tTwo.[Order_Creation_Date],
    tTwo.[Order_Delivery_Date],
    tTwo.[Order_Cancellation_Date],
    tTwo.[Order_Item_Status],
    -- Metadata
    t1.[fk_Customer],
    t1.[fk_Sales_Order]
FROM
    [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] t1
LEFT JOIN
    [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] tTwo
    ON t1.fk_Sales_Order_Item = tTwo.ID_Sales_Order_Item
WHERE
    t1.[ID_Company] IN {id_companies_active}
    AND t1.[Creation_Date] < '{cutoff_date}'
    AND t1.[created_at] > '2016-12-31'
