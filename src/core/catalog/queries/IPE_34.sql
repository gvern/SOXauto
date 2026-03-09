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
"SELECT soi.[ID_COMPANY]
      ,soi.[CURRENT_STATUS]
          ,'Refunded not yet returned' as Case_Type
      ,soi.[IS_MARKETPLACE]
      ,soi.[ORDER_NR] 
          ,soi.[BOB_ID_CUSTOMER]
          ,soi.[RETURN_DATE]
      ,soi.[IS_GLOBAL]
      ,soi.[FINANCE_VERIFIED_DATE]  
      ,soi.[REFUND_DATE]  
          ,rt.OMS_Type 
          ,ct.Customer_Type_L1

          ,ISNULL(soi.MTR_PRICE_AFTER_DISCOUNT,0)
          +ISNULL(soi.MTR_BASE_SHIPPING_AMOUNT,0)
          +ISNULL(soi.MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT,0)
          -ISNULL(soi.MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT,0)
          -ISNULL(soi.MTR_SHIPPING_CART_RULE_DISCOUNT,0)
          -(case when VOUCHER_TYPE = 'coupon' then ISNULL(soi.MTR_SHIPPING_VOUCHER_DISCOUNT,0) else 0 end) AmountToRefund  
          
  FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi

  left join [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_REFUND_NO_RETURN] rt
  on rt.ID_Company=soi.ID_COMPANY and rt.OMS_ID_Sales_Order_Item=soi.[COD_OMS_SALES_ORDER_ITEM]
    Left join [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_DIM_BOB_CUSTOMER_TYPE] ct on ct.Bob_Customer_Type=soi.BOB_CUSTOMER_TYPE


  where -- soi.ID_Company = 'EC_NG' and 
  soi.DELIVERED_DATE is not NULL
    and soi.REFUND_DATE between '2019-01-01 00:00:00' and DATEADD(second, -1, CAST('{subsequent_month_start}' AS DATETIME))
    and (soi.RETURN_DATE is NULL OR soi.RETURN_DATE >= CAST('{subsequent_month_start}' AS DATETIME))
    and soi.[ID_COMPANY] NOT IN {excluded_countries_ipe34}

  UNION ALL

  SELECT soi.[ID_COMPANY] 
      ,soi.[CURRENT_STATUS]
          ,'Returned not yet refunded' as Case_Type
      ,soi.[IS_MARKETPLACE]
      ,soi.[ORDER_NR] 
          ,soi.[BOB_ID_CUSTOMER]
          ,soi.[RETURN_DATE]
      ,soi.[IS_GLOBAL]
      ,soi.[FINANCE_VERIFIED_DATE]  
      ,soi.[REFUND_DATE]  
          ,rt.OMS_Type 
          ,ct.Customer_Type_L1
          ,(ISNULL(soi.MTR_PRICE_AFTER_DISCOUNT,0)
          +ISNULL(soi.MTR_BASE_SHIPPING_AMOUNT,0)
          +ISNULL(soi.MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT,0)
          -ISNULL(soi.MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT,0)
          -ISNULL(soi.MTR_SHIPPING_CART_RULE_DISCOUNT,0)
          -(case when VOUCHER_TYPE = 'coupon' then ISNULL(soi.MTR_SHIPPING_VOUCHER_DISCOUNT,0) else 0 end)) * -1 AmountToRefund  
          
  FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi

  left join [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_REFUND_NO_RETURN] rt
  on rt.ID_Company=soi.ID_COMPANY and rt.OMS_ID_Sales_Order_Item=soi.[COD_OMS_SALES_ORDER_ITEM]
    Left join [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_DIM_BOB_CUSTOMER_TYPE] ct on ct.Bob_Customer_Type=soi.BOB_CUSTOMER_TYPE

  where --soi.ID_Company = 'EC_NG' 
    soi.RETURN_DATE between '2019-01-01 00:00:00' and DATEADD(second, -1, CAST('{subsequent_month_start}' AS DATETIME))
    and (soi.REFUND_DATE is NULL OR soi.REFUND_DATE >= CAST('{subsequent_month_start}' AS DATETIME))
    and soi.[ID_COMPANY] NOT IN {excluded_countries_ipe34}"