-- =============================================
-- Report: FX Spot Rates (CR_05a)
-- Description: Most recent exchange rates as of target date
-- Parameters: {fx_date}, {currencies_needed}
-- Source: NAV BC (D365BC14_DZ)
-- Purpose: Get spot rates for immediate conversion
-- =============================================
SELECT [Currency Code], year([Starting Date]) year, month([Starting Date]) month, [Relational Exch_ Rate Amount]
FROM [D365BC14_DZ].[dbo].[Jade DZ$Currency Exchange Rate]
WHERE [Currency Code] IN {currencies_needed}
AND [Starting Date] = '{fx_date}'
