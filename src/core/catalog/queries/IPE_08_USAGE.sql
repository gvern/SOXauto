-- =============================================
-- Report: TV Voucher Usage (IPE_08_USAGE / DOC_VOUCHER_USAGE)
-- Description: Store credit voucher usage by delivery month
-- Parameters: {cutoff_date}, {cutoff_year}, {id_companies_active}
-- GL Account: 18412
-- =============================================

SELECT 
    soi.[ID_Company],
    scv.[id],
    soi.[voucher_type],
    scv.[business_use],
    YEAR(scv.[created_at]) AS creation_year,
    -- Use YYYYMM format for delivery month (e.g., 202401)
    YEAR(soi.[PACKAGE_DELIVERY_DATE]) * 100 + MONTH(soi.[PACKAGE_DELIVERY_DATE]) AS Delivery_mth,
    SUM(ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT], 0)) AS shipping_storecredit,
    SUM(CASE WHEN soi.[is_marketplace] = 1 THEN ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS MPL_storecredit,
    SUM(CASE WHEN soi.[is_marketplace] = 0 THEN ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS RTL_storecredit,
    SUM(ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) + ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT], 0)) AS TotalAmountUsed
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi
LEFT JOIN (
    SELECT 
        ID_company,
        [id],
        [code],
        [business_use],
        [created_at]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]
) scv
    ON scv.ID_company = soi.[ID_Company] 
    AND scv.[code] = soi.[voucher_code]
WHERE soi.[VOUCHER_TYPE] = 'reusablecredit'
    AND soi.[PACKAGE_DELIVERY_DATE] < CAST({cutoff_date} AS DATE)
    AND YEAR(soi.[DELIVERED_DATE]) > 2014
    AND soi.ID_Company IN {id_companies_active}
GROUP BY
    soi.[ID_Company],
    scv.[id],
    soi.[voucher_type],
    scv.[business_use],
    YEAR(scv.[created_at]),
    YEAR(soi.[PACKAGE_DELIVERY_DATE]) * 100 + MONTH(soi.[PACKAGE_DELIVERY_DATE]);
