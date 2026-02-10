-- =============================================
-- Report: TV - Customer Prepayments (IPE_10)
-- Description: Customer prepayment balances - orders paid but not yet delivered/refunded
-- Parameters: {cutoff_date}
-- GL Accounts: Customer prepayment liability accounts
-- =============================================

SELECT
    [ID_COMPANY],
    [IS_PREPAYMENT],
    [COD_OMS_SALES_ORDER_ITEM],
    [ORDER_NR],
    [BOB_ID_CUSTOMER],
    [CURRENT_STATUS],
    CASE WHEN [CURRENT_STATUS] = 'closed' THEN 1 ELSE 0 END AS IS_CLOSED,
    [IS_MARKETPLACE],
    [DELIVERY_TYPE], -- Added: needed for the WHERE clause logic
    [PAYMENT_METHOD],
    [ORDER_CREATION_DATE],
    [FINANCE_VERIFIED_DATE],
    [DELIVERED_DATE],
    [PACKAGE_DELIVERY_DATE],
    [REFUND_COMPLETED],
    [REFUND_DATE],
    [FAIL_DATE],
    -- Calculated fields
    ISNULL([MTR_UNIT_PRICE], 0) - ISNULL([MTR_COUPON_MONEY_VALUE], 0) - ISNULL([MTR_CART_RULE_DISCOUNT], 0) AS PAID_FOR_ITEMS,
    ISNULL([MTR_PAID_PRICE], 0) AS PAID_PRICE,
    ISNULL([MTR_BASE_SHIPPING_AMOUNT], 0) - ISNULL([MTR_SHIPPING_CART_RULE_DISCOUNT], 0) - ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT], 0) + ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT], 0) - ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT], 0) + ISNULL([MTR_INTERNATIONAL_FREIGHT_FEE], 0) AS PAID_FOR_SHIPPING
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
WHERE ORDER_CREATION_DATE > '2018-01-01 00:00:00'
    AND [IS_PREPAYMENT] = 1
    AND [FINANCE_VERIFIED_DATE] BETWEEN '2018-01-01 00:00:00' AND CAST({cutoff_date} AS DATETIME)
    AND (
        -- Marketplace orders: not yet delivered OR not yet refunded
        (
            IS_MARKETPLACE = 1
            AND (
                (
                    [DELIVERED_DATE] IS NULL
                    OR [DELIVERED_DATE] > CAST({cutoff_date} AS DATETIME)
                )
                AND (
                    [REFUND_DATE] IS NULL
                    OR [REFUND_DATE] > CAST({cutoff_date} AS DATETIME)
                )
            )
        )
        OR
        -- Retail orders: different logic based on delivery type
        (
            IS_MARKETPLACE = 0
            AND (
                (
                    -- Digital/Gift Card: check DELIVERED_DATE
                    (
                        [DELIVERY_TYPE] IN ('Digital Content', 'Gift Card')
                        AND (
                            [DELIVERED_DATE] IS NULL
                            OR [DELIVERED_DATE] > CAST({cutoff_date} AS DATETIME)
                        )
                    )
                    OR
                    -- Physical goods: check PACKAGE_DELIVERY_DATE
                    (
                        [DELIVERY_TYPE] NOT IN ('Digital Content', 'Gift Card')
                        AND (
                            [PACKAGE_DELIVERY_DATE] IS NULL
                            OR [PACKAGE_DELIVERY_DATE] > CAST({cutoff_date} AS DATETIME)
                        )
                    )
                )
                AND (
                    [REFUND_DATE] IS NULL
                    OR [REFUND_DATE] > CAST({cutoff_date} AS DATETIME)
                )
            )
        )
    );
