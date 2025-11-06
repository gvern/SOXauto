select
    scv.[ID_COMPANY],
    scv.[id],
    scv.[business_use],
    case when scv.[business_use] = 'jpay_store_credit' then (case when LEFT(scv.[code],2)='GC' then 'jpay_store_credit_gift'
        when LEFT(scv.[code],2)='JP' then 'jpay_store_credit_DS' else 'jpay_store_credit_other' end)
        else scv.[business_use] end as 'business_use_formatted',
    scv2.[template_id],
    scv2.[template_name],
    scv.[description],
    scv.[is_active],
    scv.[type],
    scv.[Template_status]
    -- ,scv.[code],scv.[discount_amount],scv.[from_date],scv.[to_date],concat(year(scv.[to_date]),'-',month(scv.[to_date])) expiration_ym
    ,(case when scv.[to_date]<'{cutoff_date}' then 'expired' else 'valid' end) Is_Valid,
    scv.[created_at],
    concat(year(scv.[created_at]),'-',month(scv.[created_at])) creation_ym,
    concat(year(scv.[updated_at]),'-',month(scv.[updated_at])) last_update_ym,
    scv.[last_time_used],
    scv.[snapshot_date],
    scv.[voucher_inactive_date],
    scv.[template_inactive_date],
    concat(year(scv.[voucher_inactive_date]),'-',month(scv.[voucher_inactive_date])) codeinactive_ym,
    concat(year(scv.[template_inactive_date]),'-',month(scv.[template_inactive_date])) templateinactive_ym,
    scv.[reason],
    scv.[updated_at],
    scv.[fk_customer],
    scv.[used_discount_amount],
    scv.[times_used],
    scv.[remaining_amount],
    sd3.[voucher_type],
    isnull(sd3.shipping_discount,0) shipping_discount,
    isnull(sd3.shipping_storecredit,0) shipping_storecredit,
    isnull(sd3.MPL_storecredit,0) MPL_storecredit,
    isnull(sd3.RTL_storecredit,0) RTL_storecredit,
    (isnull(sd3.shipping_storecredit,0) + isnull(sd3.MPL_storecredit,0) + isnull(sd3.RTL_storecredit,0)) TotalAmountUsed,
    (isnull(scv.discount_amount,0) - (isnull(sd3.shipping_storecredit,0) + isnull(sd3.MPL_storecredit,0) + isnull(sd3.RTL_storecredit,0))) TotalRemainingAmount,
    case when scv.[to_date] >(case when scv.[voucher_inactive_date] > scv.[template_inactive_date] then scv.[template_inactive_date] else scv.[voucher_inactive_date] end)
        then (case when scv.[voucher_inactive_date] > scv.[template_inactive_date] then scv.[template_inactive_date] else scv.[voucher_inactive_date] end)
        else scv.[to_date] end min_inactive_date
from [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] scv
left join [AIG_Nav_Jumia_Reconciliation].[dbo].[StoreCreditVoucher] scv2
    on scv.id=scv2.id and scv.ID_COMPANY=scv2.ID_COMPANY
Left join(
    SELECT
        [ID_Company],
        [voucher_code],
        [voucher_type],
        sum(ISNULL([MTR_SHIPPING_DISCOUNT_AMOUNT],0)) shipping_discount,
        sum(ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT],0)) shipping_storecredit,
        sum(case when [is_marketplace] = 1 then ISNULL([MTR_COUPON_MONEY_VALUE],0) else 0 end) MPL_storecredit,
        sum(case when [is_marketplace] = 0 then ISNULL([MTR_COUPON_MONEY_VALUE],0) else 0 end) RTL_storecredit
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
    where [PACKAGE_DELIVERY_DATE] < '{cutoff_date}' and year([DELIVERED_DATE])>2014
    group by
        [ID_Company],
        [voucher_code],
        [voucher_type]
) sd3
    on scv.ID_company = sd3.[ID_Company] and scv.[code]=sd3.[voucher_code]
where scv.ID_company in {id_companies_active}
and scv.created_at > '2016-12-31'
and scv.created_at < '{cutoff_date}'
