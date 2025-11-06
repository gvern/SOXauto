SELECT
    [ID_COMPANY]
    ,[IS_PREPAYMENT]
    ,[COD_OMS_SALES_ORDER_ITEM]
    ,[ORDER_NR]
    ,[BOB_ID_CUSTOMER]
    ,[CURRENT_STATUS]
    ,case when [CURRENT_STATUS] = 'closed' then 1 else 0 end IS_CLOSED
    ,[IS_MARKETPLACE]
    ,[PAYMENT_METHOD]
    ,[ORDER_CREATION_DATE]
    ,[FINANCE_VERIFIED_DATE]
    ,[DELIVERED_DATE]
    ,[PACKAGE_DELIVERY_DATE]
    ,[REFUND_COMPLETED]
    ,[REFUND_DATE]
    ,[FAIL_DATE]
    ,ISNULL([MTR_UNIT_PRICE],0)-ISNULL([MTR_COUPON_MONEY_VALUE],0)-ISNULL([MTR_CART_RULE_DISCOUNT],0) PAID_FOR_ITEMS
    ,ISNULL([MTR_PAID_PRICE],0) PAID_PRICE
    ,ISNULL([MTR_BASE_SHIPPING_AMOUNT],0)-ISNULL([MTR_SHIPPING_CART_RULE_DISCOUNT],0)-ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT],0)+ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT],0)-ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT],0) + ISNULL([MTR_INTERNATIONAL_FREIGHT_FEE], 0) PAID_FOR_SHIPPING
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
WHERE ORDER_CREATION_DATE > '2018-01-01 00:00:00'
AND [IS_PREPAYMENT] = 1
AND [FINANCE_VERIFIED_DATE] BETWEEN '2018-01-01 00:00:00' AND '{cutoff_date}'
AND (
    IS_MARKETPLACE = 1
    AND (
        (
            [DELIVERED_DATE] IS NULL
            OR [DELIVERED_DATE] > '{cutoff_date}'
        )
        AND (
            [REFUND_DATE] IS NULL
            OR [REFUND_DATE] > '{cutoff_date}'
        )
    )
    OR (
        IS_MARKETPLACE = 0
        AND (
            (
                (
                    [DELIVERY_TYPE] IN (
                        'Digital Content'
                        ,'Gift Card'
                    )
                    AND ([DELIVERED_DATE] IS NULL
                    OR [DELIVERED_DATE] > '{cutoff_date}')
                )
                OR (
                    [DELIVERY_TYPE] NOT IN (
                        'Digital Content'
                        ,'Gift Card'
                    )
                    AND ([PACKAGE_DELIVERY_DATE] IS NULL
                    OR [PACKAGE_DELIVERY_DATE] > '{cutoff_date}')
                )
            )
            AND (
                [REFUND_DATE] IS NULL
                OR [REFUND_DATE] > '{cutoff_date}'
            )
        )
    )
)
