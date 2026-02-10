-- =============================================
-- Report: TV - Packages Delivered Not Reconciled (IPE_12)
-- Description: Packages delivered but not yet reconciled (payment issues)
-- Parameters: {cutoff_date}
-- Source: OMS
-- Purpose: Identify delivery vs payment timing differences
-- Business Logic: Packages delivered up to cutoff date that remain unreconciled
-- =============================================

SELECT 
    soi.[ID_COMPANY],
    soi.[COD_OMS_ID_PACKAGE],
    soi.[PAYMENT_METHOD],
    soi.[IS_MARKETPLACE],
    soi.[Order_nr],
    soi.[PACKAGE_NUMBER],
    soi.[VOUCHER_TYPE],
    soi.[BOB_ID_CUSTOMER],
    soi.[ORDER_NR],
    soi.[ORDER_CREATION_DATE],
    soi.[SHIPPED_DATE],
    soi.[DELIVERED_DATE],
    soi.[PACKAGE_DELIVERY_DATE],
    soi.[IS_PREPAYMENT],
    soi.[MTR_SHIPPING_FEE_MODIFICATION],
    soi.[TRACKING_NUMBER],
    soi.[OMS_PACKAGE_STATUS],
    ct.[Customer_Type_L1] AS [Customer Type],
    pck.amount_expected,
    pck.amount_received,
    pck.fk_package_status,
    pck.delivered_update_date,
    pck.delivery_date,
    pck.fk_collection_partner,
    pck.last_mile,
    pck.package_status,
    pck.payment_method_confirmed,
    pck.order_nr,
    pck.troubleshoot_resolution_date,
    ISNULL(soi.[MTR_AMOUNT_PAID], 0) AS amount_paid,
    ISNULL(soi.[MTR_PAID_PRICE], 0) AS paid_price,
    ISNULL(soi.[MTR_BASE_SHIPPING_AMOUNT], 0)
        - ISNULL(soi.[MTR_SHIPPING_CART_RULE_DISCOUNT], 0)
        - ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT], 0)
        + ISNULL(soi.[MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT], 0)
        - ISNULL(soi.[MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT], 0)
        + ISNULL(soi.[MTR_INTERNATIONAL_FREIGHT_FEE], 0)
        - ISNULL(soi.[MTR_INTERNATIONAL_DELIVERY_FEE_CART_RULE], 0) AS paid_shipping
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi
LEFT JOIN [STG_AIG_NAV_JUMIA_REC].[OMS].[PACKAGE_CASHREC] pck
    ON pck.ID_COMPANY = soi.ID_COMPANY 
    AND pck.[package_nr] = soi.PACKAGE_NUMBER
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_DIM_BOB_CUSTOMER_TYPE] ct 
    ON ct.Bob_Customer_Type = soi.BOB_CUSTOMER_TYPE
WHERE soi.IS_PREPAYMENT = 0 
    AND soi.Payment_method <> 'NoPayment' 
    AND soi.DELIVERED_DATE BETWEEN '2019-01-01 00:00:00' AND CAST({cutoff_date} AS DATE)
    AND (
        pck.troubleshoot_resolution_date IS NULL 
        OR pck.troubleshoot_resolution_date > CAST({cutoff_date} AS DATE)
    );
