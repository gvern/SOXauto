-- =============================================
-- Report: TV Voucher Issuance (IPE_08_ISSUANCE)
-- Description: Store credit voucher issuance with aggregated usage
-- Parameters: {cutoff_date}, {id_companies_active}
-- GL Account: 18412
-- =============================================

SELECT
    scv.[ID_COMPANY],
    scv.[id],
    scv.[business_use],
    CASE WHEN scv.[business_use] = 'jpay_store_credit' THEN (
        CASE WHEN LEFT(scv.[code], 2) = 'GC' THEN 'jpay_store_credit_gift'
            WHEN LEFT(scv.[code], 2) = 'JP' THEN 'jpay_store_credit_DS' 
            ELSE 'jpay_store_credit_other' 
        END)
        ELSE scv.[business_use] 
    END AS 'business_use_formatted',
    scv2.[template_id],
    scv2.[template_name],
    scv.[description],
    scv.[is_active],
    scv.[type],
    scv.[Template_status],
    scv.[discount_amount],
    scv.[from_date],
    scv.[to_date],
    CONCAT(YEAR(scv.[to_date]), '-', MONTH(scv.[to_date])) AS expiration_ym,
    (CASE 
        WHEN scv.[to_date] < CAST({cutoff_date} AS DATE) THEN 'expired' 
        ELSE 'valid' 
    END) AS Is_Valid,
    scv.[created_at],
    CONCAT(YEAR(scv.[created_at]), '-', MONTH(scv.[created_at])) AS creation_ym,
    CONCAT(YEAR(scv.[updated_at]), '-', MONTH(scv.[updated_at])) AS last_update_ym,
    scv.[last_time_used],
    scv.[snapshot_date],
    scv.[voucher_inactive_date],
    scv.[template_inactive_date],
    CONCAT(YEAR(scv.[voucher_inactive_date]), '-', MONTH(scv.[voucher_inactive_date])) AS codeinactive_ym,
    CONCAT(YEAR(scv.[template_inactive_date]), '-', MONTH(scv.[template_inactive_date])) AS templateinactive_ym,
    scv.[reason],
    scv.[updated_at],
    scv.[fk_customer],
    scv.[used_discount_amount],
    scv.[times_used],
    scv.[remaining_amount],
    sd3.[voucher_type],
    ISNULL(sd3.shipping_discount, 0) AS shipping_discount,
    ISNULL(sd3.shipping_storecredit, 0) AS shipping_storecredit,
    ISNULL(sd3.MPL_storecredit, 0) AS MPL_storecredit,
    ISNULL(sd3.RTL_storecredit, 0) AS RTL_storecredit,
    (ISNULL(sd3.shipping_storecredit, 0) + ISNULL(sd3.MPL_storecredit, 0) + ISNULL(sd3.RTL_storecredit, 0)) AS TotalAmountUsed,
    (ISNULL(scv.discount_amount, 0) - (ISNULL(sd3.shipping_storecredit, 0) + ISNULL(sd3.MPL_storecredit, 0) + ISNULL(sd3.RTL_storecredit, 0))) AS TotalRemainingAmount,
    CASE 
        WHEN scv.[to_date] > (
            CASE 
                WHEN scv.[voucher_inactive_date] > scv.[template_inactive_date] 
                THEN scv.[template_inactive_date] 
                ELSE scv.[voucher_inactive_date] 
            END)
        THEN (
            CASE 
                WHEN scv.[voucher_inactive_date] > scv.[template_inactive_date] 
                THEN scv.[template_inactive_date] 
                ELSE scv.[voucher_inactive_date] 
            END)
        ELSE scv.[to_date] 
    END AS min_inactive_date
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] scv 
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[StoreCreditVoucher] scv2 
    ON scv.id = scv2.id 
    AND scv.ID_COMPANY = scv2.ID_COMPANY
LEFT JOIN (
    SELECT
        [ID_Company],
        [voucher_code],
        [voucher_type],
        SUM(ISNULL([MTR_SHIPPING_DISCOUNT_AMOUNT], 0)) AS shipping_discount,
        SUM(ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT], 0)) AS shipping_storecredit,
        SUM(CASE WHEN [is_marketplace] = 1 THEN ISNULL([MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS MPL_storecredit,
        SUM(CASE WHEN [is_marketplace] = 0 THEN ISNULL([MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS RTL_storecredit
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
    WHERE [PACKAGE_DELIVERY_DATE] < CAST({cutoff_date} AS DATE)
        AND YEAR([DELIVERED_DATE]) > 2014
    GROUP BY
        [ID_Company],
        [voucher_code],
        [voucher_type]
) sd3 
    ON scv.ID_company = sd3.[ID_Company] 
    AND scv.[code] = sd3.[voucher_code]
WHERE scv.ID_company IN {id_companies_active}
    AND scv.created_at > '2016-12-31' 
    AND scv.created_at < CAST({cutoff_date} AS DATE);
