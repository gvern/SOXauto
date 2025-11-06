SELECT
    soi.[ID_Company],
    soi.[voucher_code],
    soi.[voucher_type],
    sum(ISNULL(soi.[MTR_SHIPPING_DISCOUNT_AMOUNT],0)) shipping_discount,
    sum(ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT],0)) shipping_storecredit,
    sum(case when soi.[is_marketplace] = 1 then ISNULL(soi.[MTR_COUPON_MONEY_VALUE],0) else 0 end) MPL_storecredit,
    sum(case when soi.[is_marketplace] = 0 then ISNULL(soi.[MTR_COUPON_MONEY_VALUE],0) else 0 end) RTL_storecredit,
    sum(
        ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT],0) +
        (case when soi.[is_marketplace] = 1 then ISNULL(soi.[MTR_COUPON_MONEY_VALUE],0) else 0 end) +
        (case when soi.[is_marketplace] = 0 then ISNULL(soi.[MTR_COUPON_MONEY_VALUE],0) else 0 end)
    ) as TotalUsageAmount
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi
WHERE soi.[VOUCHER_TYPE] = 'reusablecredit'
AND soi.[PACKAGE_DELIVERY_DATE] < '{cutoff_date}'
AND year(soi.[DELIVERED_DATE]) > 2014
AND soi.ID_Company in {id_companies_active}
GROUP BY
    soi.[ID_Company],
    soi.[voucher_code],
    soi.[voucher_type]
