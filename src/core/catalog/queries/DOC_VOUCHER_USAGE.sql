select
    soi.[ID_Company]
    ,scv.[id]
    ,VC.Transaction_No
    ,soi.[voucher_type]
    ,scv.[business_use]
    ,year(scv.[created_at]) creation_year
    ,year(soi.[PACKAGE_DELIVERY_DATE])*100+month(soi.[PACKAGE_DELIVERY_DATE]) Delivery_mth
    ,sum(ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT],0)) shipping_storecredit
    ,sum(case when soi.[is_marketplace] = 1 then ISNULL(soi.[MTR_COUPON_MONEY_VALUE],0) else 0 end) MPL_storecredit
    ,sum(case when soi.[is_marketplace] = 0 then ISNULL(soi.[MTR_COUPON_MONEY_VALUE],0) else 0 end) RTL_storecredit
    ,sum(ISNULL(soi.[MTR_COUPON_MONEY_VALUE],0)+ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT],0)) TotalAmountUsed
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi

Left join (
    SELECT ID_company
        ,[id]
        ,[code]
        ,[business_use]
        ,[created_at]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]
) scv
on scv.ID_company = soi.[ID_Company] and scv.[code]=soi.[voucher_code]

Left Join [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_TRANSACTIONS_SELLER] VC
on VC.ID_Company = SOI.ID_COMPANY AND VC.BOB_ID_Sales_Order_Item = SOI.COD_BOB_SALES_ORDER_ITEM AND VC.Transaction_Amount = SOI.MTR_UNIT_PRICE

where soi.[VOUCHER_TYPE] = 'reusablecredit'
and year(soi.[PACKAGE_DELIVERY_DATE]) in (year('{cutoff_date}')-1, year('{cutoff_date}'))
and soi.[PACKAGE_DELIVERY_DATE] < '{cutoff_date}'
and year(soi.[DELIVERED_DATE]) > 2014
and soi.ID_Company in {id_companies_active}

group by
    soi.[ID_Company]
    ,scv.[id]
    ,VC.Transaction_No
    ,soi.[voucher_type]
    ,scv.[business_use]
    ,year(scv.[created_at])
    ,year(soi.[PACKAGE_DELIVERY_DATE])*100+month(soi.[PACKAGE_DELIVERY_DATE])
