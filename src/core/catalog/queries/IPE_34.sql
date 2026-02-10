-- =============================================
-- Report: Marketplace Refund Liability (IPE_34)
-- Description: Refund timing differences - refunded without return or returned without refund
-- Parameters: {cutoff_date}, {subsequent_month_start}, {excluded_countries_ipe34}
-- Source: OMS
-- GL Accounts: Marketplace refund liability
-- Business Logic: Two cases - refunds issued before returns processed, or returns processed before refunds issued
-- =============================================

-- =========================================
-- PART 1: REFUNDED NOT YET RETURNED
-- =========================================
SELECT 
    soi.[ID_COMPANY],
    soi.[CURRENT_STATUS],
    'Refunded not yet returned' AS Case_Type,
    soi.[IS_MARKETPLACE],
    soi.[ORDER_NR],
    soi.[BOB_ID_CUSTOMER],
    soi.[RETURN_DATE],
    soi.[IS_GLOBAL],
    soi.[FINANCE_VERIFIED_DATE],
    soi.[REFUND_DATE],
    rt.OMS_Type,
    ct.Customer_Type_L1,
    -- Calculate refund amount
    ISNULL(soi.MTR_PRICE_AFTER_DISCOUNT, 0)
        + ISNULL(soi.MTR_BASE_SHIPPING_AMOUNT, 0)
        + ISNULL(soi.MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT, 0)
        - ISNULL(soi.MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT, 0)
        - ISNULL(soi.MTR_SHIPPING_CART_RULE_DISCOUNT, 0)
        - (CASE 
            WHEN soi.VOUCHER_TYPE = 'coupon' 
            THEN ISNULL(soi.MTR_SHIPPING_VOUCHER_DISCOUNT, 0) 
            ELSE 0 
        END) AS AmountToRefund
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_REFUND_NO_RETURN] rt
    ON rt.ID_Company = soi.ID_COMPANY 
    AND rt.OMS_ID_Sales_Order_Item = soi.[COD_OMS_SALES_ORDER_ITEM]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_DIM_BOB_CUSTOMER_TYPE] ct 
    ON ct.Bob_Customer_Type = soi.BOB_CUSTOMER_TYPE
WHERE soi.DELIVERED_DATE IS NOT NULL
    AND soi.REFUND_DATE BETWEEN '2019-01-01 00:00:00' AND CAST({cutoff_date} AS DATETIME)
    AND (
        soi.RETURN_DATE IS NULL 
        OR soi.RETURN_DATE >= CAST({subsequent_month_start} AS DATETIME)
    )
    AND soi.[ID_COMPANY] NOT IN {excluded_countries_ipe34}

UNION ALL

-- =========================================
-- PART 2: RETURNED NOT YET REFUNDED
-- =========================================
SELECT 
    soi.[ID_COMPANY],
    soi.[CURRENT_STATUS],
    'Returned not yet refunded' AS Case_Type,
    soi.[IS_MARKETPLACE],
    soi.[ORDER_NR],
    soi.[BOB_ID_CUSTOMER],
    soi.[RETURN_DATE],
    soi.[IS_GLOBAL],
    soi.[FINANCE_VERIFIED_DATE],
    soi.[REFUND_DATE],
    rt.OMS_Type,
    ct.Customer_Type_L1,
    -- Calculate return amount (negative - liability to customer)
    (
        ISNULL(soi.MTR_PRICE_AFTER_DISCOUNT, 0)
            + ISNULL(soi.MTR_BASE_SHIPPING_AMOUNT, 0)
            + ISNULL(soi.MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT, 0)
            - ISNULL(soi.MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT, 0)
            - ISNULL(soi.MTR_SHIPPING_CART_RULE_DISCOUNT, 0)
            - (CASE 
                WHEN soi.VOUCHER_TYPE = 'coupon' 
                THEN ISNULL(soi.MTR_SHIPPING_VOUCHER_DISCOUNT, 0) 
                ELSE 0 
            END)
    ) * -1 AS AmountToRefund
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_REFUND_NO_RETURN] rt
    ON rt.ID_Company = soi.ID_COMPANY 
    AND rt.OMS_ID_Sales_Order_Item = soi.[COD_OMS_SALES_ORDER_ITEM]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_DIM_BOB_CUSTOMER_TYPE] ct 
    ON ct.Bob_Customer_Type = soi.BOB_CUSTOMER_TYPE
WHERE soi.RETURN_DATE BETWEEN '2019-01-01 00:00:00' AND CAST({cutoff_date} AS DATETIME)
    AND (
        soi.REFUND_DATE IS NULL 
        OR soi.REFUND_DATE >= CAST({subsequent_month_start} AS DATETIME)
    )
    AND soi.[ID_COMPANY] NOT IN {excluded_countries_ipe34};
