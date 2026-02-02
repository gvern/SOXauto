-- =============================================
-- Report: Monthly Closing FX Rates (CR_05)
-- Description: Official month-end closing rates for financial reporting
-- Parameters: {fx_year}, {fx_month}
-- Source: RPT_FX_RATES (aggregated rates table)
-- Purpose: Get official closing rates for month-end reconciliation with company mapping
-- =============================================

SELECT
    comp.[Company_Code],
    comp.[Company_Name],
    comp.[Opco/Central_?],
    comp.[Company_Country],
    comp.[Is_Active?],
    fx.[rate_type],
    fx.[year],
    fx.[cod_month],
    CASE
        WHEN c.[Country_Name] IN ('United States of America') 
            OR (c.[Country_Name] IN ('Germany') AND RIGHT(comp.[Company_Code], 4) = '_USD')
        THEN 1
        ELSE fx.rate
    END AS FX_rate,
    c.[Country_Name]
FROM [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
LEFT JOIN (
    SELECT 
        [country_code],
        [rate_type],
        [year],
        [cod_month],
        [rate]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]
    WHERE [year] = {fx_year}
        AND [cod_month] = {fx_month}
        AND [rate_type] = 'Closing'
        AND [base_currency] = 'USD'
        AND [country] <> 'United arab emirates (the)'
) fx
    ON fx.country_code = comp.Company_Country
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Country] c
    ON comp.[Company_Country] = c.[Country_Code];
