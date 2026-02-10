-- =============================================
-- Report: FX Spot Rates (CR_05a)
-- Description: Most recent exchange rates as of target date
-- Parameters: {fx_date}, {currencies_needed}
-- Source: NAV BC (D365BC14_DZ)
-- Purpose: Get spot rates for immediate conversion
-- =============================================

DECLARE @target_date DATE = {fx_date};

WITH RatesAtDate AS (
    SELECT 
        [Currency Code],
        [Starting Date],
        [Relational Exch_ Rate Amount],
        ROW_NUMBER() OVER (PARTITION BY [Currency Code] ORDER BY [Starting Date] DESC) AS rn
    FROM [ERP_NAVBC01].[D365BC14_DZ].[dbo].[Jade DZ$Currency Exchange Rate]
    WHERE [Starting Date] <= @target_date
        AND [Currency Code] IN {currencies_needed}
)
SELECT 
    [Currency Code],
    [Starting Date] AS exchange_rate_date,
    [Relational Exch_ Rate Amount] AS rate_to_usd,
    CASE 
        WHEN [Relational Exch_ Rate Amount] > 0 
        THEN 1.0 / [Relational Exch_ Rate Amount] 
        ELSE NULL 
    END AS usd_to_currency
FROM RatesAtDate
WHERE rn = 1

UNION ALL

SELECT 
    'USD',
    @target_date,
    1.0,
    1.0

ORDER BY [Currency Code];
